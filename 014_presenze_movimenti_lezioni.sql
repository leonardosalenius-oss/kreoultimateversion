begin;

create table if not exists gestionale_v2.movimenti_lezioni (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  cliente_id uuid not null
    references gestionale_v2.clienti(id) on delete restrict,
  abbonamento_id uuid not null
    references gestionale_v2.abbonamenti(id) on delete restrict,
  prenotazione_id uuid
    references gestionale_v2.prenotazioni(id) on delete set null,
  movimento_origine_id uuid
    references gestionale_v2.movimenti_lezioni(id) on delete set null,
  data_movimento date not null default current_date,
  tipo text not null,
  quantita integer not null check (quantita <> 0),
  causale text not null,
  stato text not null default 'valido'
    check (stato in ('valido', 'annullato')),
  created_at timestamptz not null default now()
);

create index if not exists idx_movimenti_lezioni_abbonamento
  on gestionale_v2.movimenti_lezioni(
    azienda_id,
    abbonamento_id,
    data_movimento
  );

create index if not exists idx_movimenti_lezioni_prenotazione
  on gestionale_v2.movimenti_lezioni(prenotazione_id);

alter table gestionale_v2.movimenti_lezioni enable row level security;

grant select, insert, update, delete
on gestionale_v2.movimenti_lezioni
to service_role;

create or replace view gestionale_v2.vista_saldi_lezioni
with (security_invoker = false)
as
select
  a.azienda_id,
  a.id as abbonamento_id,
  a.cliente_id,
  a.lezioni_iniziali,
  coalesce(
    sum(m.quantita) filter (where m.stato = 'valido'),
    0
  )::integer as movimenti_lezioni_netto,
  (
    a.lezioni_iniziali
    + coalesce(
        sum(m.quantita) filter (where m.stato = 'valido'),
        0
      )
  )::integer as saldo_lezioni
from gestionale_v2.abbonamenti a
left join gestionale_v2.movimenti_lezioni m
  on m.abbonamento_id = a.id
group by
  a.azienda_id,
  a.id,
  a.cliente_id,
  a.lezioni_iniziali;

create or replace function gestionale_v2.registra_movimento_lezioni(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_abbonamento_id uuid;
  v_quantita integer;
  v_saldo integer;
  v_id uuid;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_abbonamento_id := (payload->>'abbonamento_id')::uuid;
  v_quantita := (payload->>'quantita')::integer;

  if v_quantita = 0 then
    raise exception 'La quantità non può essere zero';
  end if;

  if nullif(trim(payload->>'causale'), '') is null then
    raise exception 'La motivazione è obbligatoria';
  end if;

  select saldo_lezioni
  into v_saldo
  from gestionale_v2.vista_saldi_lezioni
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id
    and abbonamento_id = v_abbonamento_id;

  if v_saldo is null then
    raise exception 'Abbonamento non trovato';
  end if;

  if v_quantita < 0 and abs(v_quantita) > v_saldo then
    raise exception 'Movimento superiore alle lezioni disponibili';
  end if;

  insert into gestionale_v2.movimenti_lezioni (
    azienda_id,
    cliente_id,
    abbonamento_id,
    data_movimento,
    tipo,
    quantita,
    causale,
    stato
  )
  values (
    v_azienda_id,
    v_cliente_id,
    v_abbonamento_id,
    coalesce(
      nullif(payload->>'data_movimento', '')::date,
      current_date
    ),
    payload->>'tipo',
    v_quantita,
    trim(payload->>'causale'),
    'valido'
  )
  returning id into v_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo,
    motivo
  )
  values (
    v_azienda_id,
    'movimenti_lezioni',
    v_id,
    'creazione',
    payload,
    trim(payload->>'causale')
  );

  return jsonb_build_object(
    'movimento_id', v_id,
    'nuovo_saldo', v_saldo + v_quantita
  );
end;
$$;

create or replace function gestionale_v2.cambia_stato_prenotazione(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_azienda_id uuid;
  v_new_state text;
  v_old_state text;
  v_before jsonb;
  v_after jsonb;
  v_cliente_id uuid;
  v_abbonamento_id uuid;
  v_tipologia text;
  v_data date;
  v_delta integer := 0;
  v_booking_net integer := 0;
  v_saldo integer;
  v_movement_id uuid;
begin
  v_id := (payload->>'prenotazione_id')::uuid;
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_new_state := payload->>'stato';

  if v_new_state not in (
    'prenotata',
    'confermata',
    'presente',
    'assente',
    'annullata'
  ) then
    raise exception 'Stato prenotazione non valido';
  end if;

  select
    p.stato,
    to_jsonb(p),
    p.cliente_id,
    p.abbonamento_id,
    p.tipologia,
    p.data_prenotazione
  into
    v_old_state,
    v_before,
    v_cliente_id,
    v_abbonamento_id,
    v_tipologia,
    v_data
  from gestionale_v2.prenotazioni p
  where p.id = v_id
    and p.azienda_id = v_azienda_id;

  if v_before is null then
    raise exception 'Prenotazione non trovata';
  end if;

  if v_old_state = v_new_state then
    return jsonb_build_object(
      'prenotazione_id', v_id,
      'stato', v_new_state,
      'movimento_lezioni', 0
    );
  end if;

  if v_abbonamento_id is not null then
    select coalesce(sum(m.quantita), 0)
    into v_booking_net
    from gestionale_v2.movimenti_lezioni m
    where m.prenotazione_id = v_id
      and m.stato = 'valido';
  end if;

  if v_old_state <> 'presente'
     and v_new_state = 'presente'
     and v_abbonamento_id is not null then

    if v_tipologia in (
      'Lezione ordinaria',
      'Recupero',
      'Lezione extra'
    ) then
      v_delta := -1;
    else
      v_delta := 0;
    end if;

    if v_delta < 0 then
      select saldo_lezioni
      into v_saldo
      from gestionale_v2.vista_saldi_lezioni
      where abbonamento_id = v_abbonamento_id
        and azienda_id = v_azienda_id;

      if coalesce(v_saldo, 0) < abs(v_delta) then
        raise exception 'Nessuna lezione disponibile';
      end if;

      insert into gestionale_v2.movimenti_lezioni (
        azienda_id,
        cliente_id,
        abbonamento_id,
        prenotazione_id,
        data_movimento,
        tipo,
        quantita,
        causale,
        stato
      )
      values (
        v_azienda_id,
        v_cliente_id,
        v_abbonamento_id,
        v_id,
        v_data,
        'Presenza',
        v_delta,
        'Presenza: ' || v_tipologia,
        'valido'
      )
      returning id into v_movement_id;
    end if;

  elsif v_old_state = 'presente'
        and v_new_state <> 'presente'
        and v_abbonamento_id is not null
        and v_booking_net <> 0 then

    v_delta := -v_booking_net;

    insert into gestionale_v2.movimenti_lezioni (
      azienda_id,
      cliente_id,
      abbonamento_id,
      prenotazione_id,
      data_movimento,
      tipo,
      quantita,
      causale,
      stato
    )
    values (
      v_azienda_id,
      v_cliente_id,
      v_abbonamento_id,
      v_id,
      current_date,
      'Storno presenza',
      v_delta,
      'Storno per cambio stato prenotazione',
      'valido'
    )
    returning id into v_movement_id;
  end if;

  update gestionale_v2.prenotazioni
  set
    stato = v_new_state,
    motivo_ultimo_stato = nullif(payload->>'motivo', ''),
    annullata_il = case
      when v_new_state = 'annullata' then now()
      else annullata_il
    end,
    updated_at = now()
  where id = v_id
    and azienda_id = v_azienda_id;

  select to_jsonb(p)
  into v_after
  from gestionale_v2.prenotazioni p
  where p.id = v_id;

  insert into gestionale_v2.eventi_prenotazione (
    azienda_id,
    prenotazione_id,
    azione,
    stato_precedente,
    stato_successivo,
    dati_precedenti,
    dati_successivi,
    motivo
  )
  values (
    v_azienda_id,
    v_id,
    'cambio_stato',
    v_old_state,
    v_new_state,
    v_before,
    v_after,
    nullif(payload->>'motivo', '')
  );

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    valore_successivo,
    motivo
  )
  values (
    v_azienda_id,
    'prenotazioni',
    v_id,
    'cambio_stato',
    v_before,
    v_after,
    nullif(payload->>'motivo', '')
  );

  return jsonb_build_object(
    'prenotazione_id', v_id,
    'stato', v_new_state,
    'movimento_lezioni', v_delta,
    'movimento_id', v_movement_id
  );
end;
$$;

create or replace view gestionale_v2.vista_movimenti_lezioni_operativa
with (security_invoker = false)
as
select
  m.azienda_id,
  m.id as movimento_id,
  m.cliente_id,
  m.abbonamento_id,
  m.prenotazione_id,
  c.cognome || ' ' || c.nome as cliente,
  pck.nome as pacchetto,
  m.data_movimento,
  m.tipo,
  m.quantita,
  m.causale,
  m.stato,
  p.data_prenotazione,
  p.ora_inizio,
  p.ora_fine,
  p.tipologia as tipologia_prenotazione,
  m.created_at
from gestionale_v2.movimenti_lezioni m
join gestionale_v2.clienti c
  on c.id = m.cliente_id
join gestionale_v2.abbonamenti a
  on a.id = m.abbonamento_id
join gestionale_v2.pacchetti pck
  on pck.id = a.pacchetto_id
left join gestionale_v2.prenotazioni p
  on p.id = m.prenotazione_id;

create or replace view gestionale_v2.vista_prenotazioni_operativa
with (security_invoker = false)
as
select
  p.azienda_id,
  p.id as prenotazione_id,
  p.cliente_id,
  p.abbonamento_id,
  p.operatore_id,
  c.cognome || ' ' || c.nome as cliente,
  pac.nome as pacchetto,
  oa.nome_visualizzato as operatore,
  p.data_prenotazione,
  p.ora_inizio,
  p.ora_fine,
  p.tipologia,
  p.stato,
  p.note,
  p.motivo_ultimo_stato,
  p.created_at,
  p.updated_at,
  sl.lezioni_iniziali,
  sl.movimenti_lezioni_netto,
  sl.saldo_lezioni
from gestionale_v2.prenotazioni p
join gestionale_v2.clienti c
  on c.id = p.cliente_id
left join gestionale_v2.abbonamenti a
  on a.id = p.abbonamento_id
left join gestionale_v2.pacchetti pac
  on pac.id = a.pacchetto_id
left join gestionale_v2.operatori_agenda oa
  on oa.id = p.operatore_id
left join gestionale_v2.vista_saldi_lezioni sl
  on sl.abbonamento_id = p.abbonamento_id;

create or replace view gestionale_v2.vista_abbonamenti_operativa
with (security_invoker = false)
as
select
  a.azienda_id,
  a.id as abbonamento_id,
  a.cliente_id,
  a.pacchetto_id,
  a.abbonamento_precedente_id,
  c.cognome || ' ' || c.nome as cliente,
  p.nome as pacchetto,
  a.data_inizio,
  a.data_fine_prevista,
  a.prezzo_concordato,
  a.lezioni_iniziali,
  a.tipologia_pagamento,
  a.stato,
  a.note,
  a.motivo_stato,
  a.data_sospensione,
  a.fine_sospensione_prevista,
  a.data_riattivazione,
  a.data_chiusura,
  coalesce(
    sum(i.importo) filter (where i.stato = 'valido'),
    0
  )::numeric(12,2) as pagato,
  greatest(
    a.prezzo_concordato
    - coalesce(
        sum(i.importo) filter (where i.stato = 'valido'),
        0
      ),
    0
  )::numeric(12,2) as residuo,
  nr.data_scadenza as prossima_rata_data,
  nr.residuo_rata::numeric(12,2) as prossima_rata_importo,
  case
    when a.stato = 'sospeso' then 'Sospeso'
    when a.stato = 'terminato' then 'Terminato'
    when a.stato = 'chiuso_anticipatamente' then 'Chiuso anticipatamente'
    when a.stato = 'annullato' then 'Annullato'
    when a.data_inizio > current_date then 'Da attivare'
    when a.data_fine_prevista < current_date then 'Scaduto'
    when a.data_fine_prevista <= current_date + 15 then 'In scadenza'
    else 'Attivo'
  end as stato_visuale,
  coalesce(sl.movimenti_lezioni_netto, 0) as movimenti_lezioni_netto,
  coalesce(sl.saldo_lezioni, a.lezioni_iniziali) as saldo_lezioni
from gestionale_v2.abbonamenti a
join gestionale_v2.clienti c
  on c.id = a.cliente_id
join gestionale_v2.pacchetti p
  on p.id = a.pacchetto_id
left join gestionale_v2.incassi i
  on i.abbonamento_id = a.id
left join gestionale_v2.vista_saldi_lezioni sl
  on sl.abbonamento_id = a.id
left join lateral (
  select
    vr.data_scadenza,
    vr.residuo_rata
  from gestionale_v2.vista_rate_operativa vr
  where vr.abbonamento_id = a.id
    and vr.residuo_rata > 0
  order by vr.data_scadenza, vr.numero_rata
  limit 1
) nr on true
group by
  a.azienda_id,
  a.id,
  a.cliente_id,
  a.pacchetto_id,
  a.abbonamento_precedente_id,
  c.cognome,
  c.nome,
  p.nome,
  sl.movimenti_lezioni_netto,
  sl.saldo_lezioni,
  nr.data_scadenza,
  nr.residuo_rata;

create or replace function gestionale_v2.get_abbonamento_dettaglio(
  p_abbonamento_id uuid
)
returns jsonb
language sql
security definer
set search_path = gestionale_v2, public
as $$
  select jsonb_build_object(
    'abbonamento',
    (
      select to_jsonb(v)
      from gestionale_v2.vista_abbonamenti_operativa v
      where v.abbonamento_id = p_abbonamento_id
    ),
    'rate',
    coalesce((
      select jsonb_agg(
        to_jsonb(v)
        order by v.data_scadenza, v.numero_rata
      )
      from gestionale_v2.vista_rate_operativa v
      where v.abbonamento_id = p_abbonamento_id
    ), '[]'::jsonb),
    'incassi',
    coalesce((
      select jsonb_agg(
        to_jsonb(v)
        order by v.data_incasso desc, v.created_at desc
      )
      from gestionale_v2.vista_incassi_operativa v
      where v.abbonamento_id = p_abbonamento_id
    ), '[]'::jsonb),
    'movimenti_lezioni',
    coalesce((
      select jsonb_agg(
        to_jsonb(v)
        order by v.data_movimento desc, v.created_at desc
      )
      from gestionale_v2.vista_movimenti_lezioni_operativa v
      where v.abbonamento_id = p_abbonamento_id
    ), '[]'::jsonb),
    'eventi_stato',
    coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'azione', e.azione,
          'stato_precedente', e.stato_precedente,
          'stato_successivo', e.stato_successivo,
          'data_evento', e.data_evento,
          'fine_sospensione_prevista',
            e.fine_sospensione_prevista,
          'giorni_prolungamento',
            e.giorni_prolungamento,
          'motivo', e.motivo,
          'created_at', e.created_at
        )
        order by e.data_evento desc, e.created_at desc
      )
      from gestionale_v2.eventi_stato_abbonamento e
      where e.abbonamento_id = p_abbonamento_id
    ), '[]'::jsonb)
  );
$$;

grant execute
on function gestionale_v2.registra_movimento_lezioni(jsonb)
to service_role;

grant execute
on function gestionale_v2.cambia_stato_prenotazione(jsonb)
to service_role;

grant select
on gestionale_v2.vista_saldi_lezioni
to service_role;

grant select
on gestionale_v2.vista_movimenti_lezioni_operativa
to service_role;

grant select
on gestionale_v2.vista_prenotazioni_operativa
to service_role;

grant select
on gestionale_v2.vista_abbonamenti_operativa
to service_role;

commit;

notify pgrst, 'reload schema';
