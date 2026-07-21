begin;

alter table gestionale_v2.abbonamenti
  add column if not exists abbonamento_precedente_id uuid
    references gestionale_v2.abbonamenti(id) on delete set null,
  add column if not exists data_sospensione date,
  add column if not exists fine_sospensione_prevista date,
  add column if not exists data_riattivazione date,
  add column if not exists data_chiusura date,
  add column if not exists motivo_stato text;

create table if not exists gestionale_v2.eventi_stato_abbonamento (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  abbonamento_id uuid not null
    references gestionale_v2.abbonamenti(id) on delete cascade,
  stato_precedente text,
  stato_successivo text not null,
  azione text not null,
  data_evento date not null,
  fine_sospensione_prevista date,
  prolunga_scadenza boolean not null default false,
  giorni_prolungamento integer not null default 0,
  motivo text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_eventi_abbonamento
  on gestionale_v2.eventi_stato_abbonamento(
    azienda_id,
    abbonamento_id,
    data_evento desc
  );

alter table gestionale_v2.eventi_stato_abbonamento
  enable row level security;

grant select, insert, update, delete
on gestionale_v2.eventi_stato_abbonamento
to service_role;

create or replace function gestionale_v2.crea_abbonamento_cliente(
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
  v_rata jsonb;
  v_incasso_id uuid;
  v_totale_rate numeric;
  v_prezzo numeric;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_prezzo := (payload->>'prezzo_concordato')::numeric;

  if not exists (
    select 1
    from gestionale_v2.clienti c
    where c.id = v_cliente_id
      and c.azienda_id = v_azienda_id
      and c.stato <> 'annullato'
  ) then
    raise exception 'Cliente non trovato';
  end if;

  select coalesce(
    sum((value->>'importo_previsto')::numeric),
    0
  )
  into v_totale_rate
  from jsonb_array_elements(payload->'rate');

  if abs(v_totale_rate - v_prezzo) > 0.01 then
    raise exception 'La somma delle rate non coincide con il prezzo';
  end if;

  insert into gestionale_v2.abbonamenti (
    azienda_id,
    cliente_id,
    pacchetto_id,
    abbonamento_precedente_id,
    data_inizio,
    data_fine_prevista,
    prezzo_concordato,
    lezioni_iniziali,
    tipologia_pagamento,
    note,
    stato
  )
  values (
    v_azienda_id,
    v_cliente_id,
    (payload->>'pacchetto_id')::uuid,
    nullif(payload->>'abbonamento_precedente_id', '')::uuid,
    (payload->>'data_inizio')::date,
    (payload->>'data_fine_prevista')::date,
    v_prezzo,
    coalesce((payload->>'lezioni_iniziali')::integer, 0),
    payload->>'tipologia_pagamento',
    nullif(payload->>'note', ''),
    case
      when (payload->>'data_inizio')::date > current_date
        then 'da_attivare'
      else 'attivo'
    end
  )
  returning id into v_abbonamento_id;

  for v_rata in
    select value
    from jsonb_array_elements(payload->'rate')
  loop
    insert into gestionale_v2.rate (
      azienda_id,
      abbonamento_id,
      numero_rata,
      data_scadenza,
      importo_previsto
    )
    values (
      v_azienda_id,
      v_abbonamento_id,
      (v_rata->>'numero_rata')::integer,
      (v_rata->>'data_scadenza')::date,
      (v_rata->>'importo_previsto')::numeric
    );
  end loop;

  if payload->'pagamento_iniziale' is not null then
    insert into gestionale_v2.incassi (
      azienda_id,
      cliente_id,
      abbonamento_id,
      data_incasso,
      importo,
      metodo_pagamento,
      tipo_incasso,
      causale,
      stato
    )
    values (
      v_azienda_id,
      v_cliente_id,
      v_abbonamento_id,
      (payload->'pagamento_iniziale'->>'data_incasso')::date,
      (payload->'pagamento_iniziale'->>'importo')::numeric,
      payload->'pagamento_iniziale'->>'metodo_pagamento',
      'abbonamento',
      coalesce(
        payload->'pagamento_iniziale'->>'causale',
        'Acconto abbonamento'
      ),
      'valido'
    )
    returning id into v_incasso_id;
  end if;

  perform gestionale_v2.ricalcola_allocazioni_abbonamento(
    v_abbonamento_id
  );

  insert into gestionale_v2.eventi_stato_abbonamento (
    azienda_id,
    abbonamento_id,
    stato_precedente,
    stato_successivo,
    azione,
    data_evento,
    motivo
  )
  select
    v_azienda_id,
    v_abbonamento_id,
    null,
    a.stato,
    'Creazione',
    a.data_inizio,
    'Creazione abbonamento'
  from gestionale_v2.abbonamenti a
  where a.id = v_abbonamento_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo
  )
  values (
    v_azienda_id,
    'abbonamenti',
    v_abbonamento_id,
    'creazione',
    payload
  );

  return jsonb_build_object(
    'abbonamento_id', v_abbonamento_id,
    'incasso_id', v_incasso_id
  );
end;
$$;

create or replace function gestionale_v2.rinnova_abbonamento_cliente(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_precedente_id uuid;
  v_precedente_stato text;
  v_result jsonb;
begin
  v_precedente_id :=
    (payload->>'abbonamento_precedente_id')::uuid;

  select stato
  into v_precedente_stato
  from gestionale_v2.abbonamenti
  where id = v_precedente_id
    and cliente_id = (payload->>'cliente_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if v_precedente_stato is null then
    raise exception 'Abbonamento precedente non trovato';
  end if;

  v_result := gestionale_v2.crea_abbonamento_cliente(payload);

  if coalesce(
    (payload->>'chiudi_precedente')::boolean,
    false
  ) then
    update gestionale_v2.abbonamenti
    set
      stato = 'terminato',
      data_chiusura = (payload->>'data_inizio')::date,
      motivo_stato = 'Rinnovato con nuovo abbonamento'
    where id = v_precedente_id
      and stato <> 'annullato';

    insert into gestionale_v2.eventi_stato_abbonamento (
      azienda_id,
      abbonamento_id,
      stato_precedente,
      stato_successivo,
      azione,
      data_evento,
      motivo
    )
    values (
      (payload->>'azienda_id')::uuid,
      v_precedente_id,
      v_precedente_stato,
      'terminato',
      'Rinnovo',
      (payload->>'data_inizio')::date,
      'Chiusura per rinnovo'
    );
  end if;

  return v_result;
end;
$$;

create or replace function gestionale_v2.cambia_stato_abbonamento(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_abbonamento_id uuid;
  v_azione text;
  v_stato_precedente text;
  v_stato_successivo text;
  v_data_evento date;
  v_fine_prevista date;
  v_prolunga boolean;
  v_giorni integer := 0;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_abbonamento_id := (payload->>'abbonamento_id')::uuid;
  v_azione := payload->>'azione';
  v_data_evento := (payload->>'data_evento')::date;
  v_fine_prevista :=
    nullif(payload->>'fine_sospensione_prevista', '')::date;
  v_prolunga := coalesce(
    (payload->>'prolunga_scadenza')::boolean,
    false
  );

  select stato
  into v_stato_precedente
  from gestionale_v2.abbonamenti
  where id = v_abbonamento_id
    and azienda_id = v_azienda_id;

  if v_stato_precedente is null then
    raise exception 'Abbonamento non trovato';
  end if;

  if v_azione = 'Sospendi' then
    if v_stato_precedente not in ('attivo', 'da_attivare') then
      raise exception 'Lo stato attuale non consente la sospensione';
    end if;

    v_stato_successivo := 'sospeso';

    update gestionale_v2.abbonamenti
    set
      stato = v_stato_successivo,
      data_sospensione = v_data_evento,
      fine_sospensione_prevista = v_fine_prevista,
      motivo_stato = payload->>'motivo'
    where id = v_abbonamento_id;

  elsif v_azione = 'Riattiva' then
    if v_stato_precedente <> 'sospeso' then
      raise exception 'Solo un abbonamento sospeso può essere riattivato';
    end if;

    v_stato_successivo := 'attivo';

    select
      case
        when a.data_sospensione is not null
          then greatest(v_data_evento - a.data_sospensione, 0)
        else 0
      end
    into v_giorni
    from gestionale_v2.abbonamenti a
    where a.id = v_abbonamento_id;

    if not v_prolunga then
      v_giorni := 0;
    end if;

    update gestionale_v2.abbonamenti
    set
      stato = v_stato_successivo,
      data_riattivazione = v_data_evento,
      data_fine_prevista =
        data_fine_prevista + v_giorni,
      motivo_stato = payload->>'motivo'
    where id = v_abbonamento_id;

  elsif v_azione = 'Termina' then
    v_stato_successivo := 'terminato';

    update gestionale_v2.abbonamenti
    set
      stato = v_stato_successivo,
      data_chiusura = v_data_evento,
      motivo_stato = payload->>'motivo'
    where id = v_abbonamento_id;

  elsif v_azione = 'Chiudi anticipatamente' then
    v_stato_successivo := 'chiuso_anticipatamente';

    update gestionale_v2.abbonamenti
    set
      stato = v_stato_successivo,
      data_chiusura = v_data_evento,
      motivo_stato = payload->>'motivo'
    where id = v_abbonamento_id;

  else
    raise exception 'Azione non valida';
  end if;

  insert into gestionale_v2.eventi_stato_abbonamento (
    azienda_id,
    abbonamento_id,
    stato_precedente,
    stato_successivo,
    azione,
    data_evento,
    fine_sospensione_prevista,
    prolunga_scadenza,
    giorni_prolungamento,
    motivo
  )
  values (
    v_azienda_id,
    v_abbonamento_id,
    v_stato_precedente,
    v_stato_successivo,
    v_azione,
    v_data_evento,
    v_fine_prevista,
    v_prolunga,
    v_giorni,
    payload->>'motivo'
  );

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
    'abbonamenti',
    v_abbonamento_id,
    'cambio_stato',
    jsonb_build_object(
      'stato_precedente', v_stato_precedente,
      'stato_successivo', v_stato_successivo,
      'data_evento', v_data_evento,
      'giorni_prolungamento', v_giorni
    ),
    payload->>'motivo'
  );

  return jsonb_build_object(
    'abbonamento_id', v_abbonamento_id,
    'stato', v_stato_successivo,
    'giorni_prolungamento', v_giorni
  );
end;
$$;

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
  end as stato_visuale
from gestionale_v2.abbonamenti a
join gestionale_v2.clienti c
  on c.id = a.cliente_id
join gestionale_v2.pacchetti p
  on p.id = a.pacchetto_id
left join gestionale_v2.incassi i
  on i.abbonamento_id = a.id
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
on function gestionale_v2.crea_abbonamento_cliente(jsonb)
to service_role;

grant execute
on function gestionale_v2.rinnova_abbonamento_cliente(jsonb)
to service_role;

grant execute
on function gestionale_v2.cambia_stato_abbonamento(jsonb)
to service_role;

grant execute
on function gestionale_v2.get_abbonamento_dettaglio(uuid)
to service_role;

grant select
on gestionale_v2.vista_abbonamenti_operativa
to service_role;

commit;

notify pgrst, 'reload schema';
