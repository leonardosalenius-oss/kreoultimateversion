begin;

alter table gestionale_v2.pacchetti
  add column if not exists senza_scadenza boolean not null default false;

alter table gestionale_v2.abbonamenti
  alter column data_fine_prevista drop not null;

update gestionale_v2.pacchetti
set senza_scadenza = true
where modalita_lezioni = 'Pacchetto lezioni';

create or replace function gestionale_v2.salva_pacchetto(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_mode text;
  v_total integer;
begin
  v_id := nullif(payload->>'pacchetto_id', '')::uuid;
  v_mode := payload->>'modalita_lezioni';
  v_total := coalesce((payload->>'lezioni_totali')::integer, 0);

  if nullif(trim(payload->>'nome'), '') is null then
    raise exception 'Nome pacchetto obbligatorio';
  end if;

  if v_mode = 'Pacchetto lezioni' and v_total <= 0 then
    raise exception 'Il numero totale di lezioni deve essere maggiore di zero';
  end if;

  if v_id is null then
    insert into gestionale_v2.pacchetti (
      azienda_id,
      nome,
      periodicita,
      prezzo_standard,
      durata_numero,
      durata_unita,
      modalita_lezioni,
      lezioni_per_periodo,
      lezioni_totali,
      lezioni_standard,
      senza_scadenza,
      attivo
    )
    values (
      (payload->>'azienda_id')::uuid,
      trim(payload->>'nome'),
      payload->>'periodicita',
      (payload->>'prezzo_standard')::numeric,
      coalesce((payload->>'durata_numero')::integer, 0),
      payload->>'durata_unita',
      v_mode,
      coalesce((payload->>'lezioni_per_periodo')::integer, 0),
      v_total,
      case when v_mode = 'Pacchetto lezioni' then v_total else 0 end,
      v_mode = 'Pacchetto lezioni',
      coalesce((payload->>'attivo')::boolean, true)
    )
    returning id into v_id;
  else
    update gestionale_v2.pacchetti
    set
      nome = trim(payload->>'nome'),
      periodicita = payload->>'periodicita',
      prezzo_standard = (payload->>'prezzo_standard')::numeric,
      durata_numero = coalesce((payload->>'durata_numero')::integer, 0),
      durata_unita = payload->>'durata_unita',
      modalita_lezioni = v_mode,
      lezioni_per_periodo =
        coalesce((payload->>'lezioni_per_periodo')::integer, 0),
      lezioni_totali = v_total,
      lezioni_standard =
        case when v_mode = 'Pacchetto lezioni' then v_total else 0 end,
      senza_scadenza = v_mode = 'Pacchetto lezioni',
      attivo = coalesce((payload->>'attivo')::boolean, true)
    where id = v_id
      and azienda_id = (payload->>'azienda_id')::uuid;

    if not found then
      raise exception 'Pacchetto non trovato';
    end if;
  end if;

  return jsonb_build_object('pacchetto_id', v_id);
end;
$$;


create or replace function gestionale_v2.normalizza_abbonamento_lezioni()
returns trigger
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_mode text;
  v_total integer;
  v_per_period integer;
begin
  select
    p.modalita_lezioni,
    coalesce(p.lezioni_totali, 0),
    coalesce(p.lezioni_per_periodo, 0)
  into
    v_mode,
    v_total,
    v_per_period
  from gestionale_v2.pacchetti p
  where p.id = new.pacchetto_id;

  if v_mode = 'Pacchetto lezioni' then
    new.data_fine_prevista := null;
    new.lezioni_iniziali := v_total;

  elsif v_mode = 'Settimanale' then
    if new.data_fine_prevista is null then
      raise exception 'La data fine è obbligatoria per i pacchetti settimanali';
    end if;

    new.lezioni_iniziali := round(
      (
        ((new.data_fine_prevista - new.data_inizio) + 1)::numeric
        * v_per_period::numeric
      ) / 7
    )::integer;

  elsif v_mode = 'Mensile' then
    if new.data_fine_prevista is null then
      raise exception 'La data fine è obbligatoria per i pacchetti mensili';
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_normalizza_abbonamento_lezioni
on gestionale_v2.abbonamenti;

create trigger trg_normalizza_abbonamento_lezioni
before insert or update of
  pacchetto_id,
  data_inizio,
  data_fine_prevista
on gestionale_v2.abbonamenti
for each row
execute function gestionale_v2.normalizza_abbonamento_lezioni();


create or replace function gestionale_v2.calcola_lezioni_contrattuali(
  p_pacchetto_id uuid,
  p_data_inizio date,
  p_data_fine date
)
returns integer
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_mode text;
  v_total integer;
  v_per_period integer;
  v_duration integer;
begin
  select
    p.modalita_lezioni,
    coalesce(p.lezioni_totali, 0),
    coalesce(p.lezioni_per_periodo, 0),
    coalesce(p.durata_numero, 1)
  into
    v_mode,
    v_total,
    v_per_period,
    v_duration
  from gestionale_v2.pacchetti p
  where p.id = p_pacchetto_id;

  if v_mode is null then
    raise exception 'Pacchetto non trovato';
  end if;

  if v_mode = 'Pacchetto lezioni' then
    return v_total;
  end if;

  if p_data_fine is null then
    raise exception 'Data fine obbligatoria per il pacchetto selezionato';
  end if;

  if p_data_fine < p_data_inizio then
    raise exception 'La data fine precede la data inizio';
  end if;

  if v_mode = 'Settimanale' then
    return round(
      (
        ((p_data_fine - p_data_inizio) + 1)::numeric
        * v_per_period::numeric
      ) / 7
    )::integer;
  end if;

  return v_per_period * v_duration;
end;
$$;


create or replace function gestionale_v2.genera_ricevuta_incasso(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_incasso record;
  v_ricevuta_id uuid;
  v_numero integer;
  v_anno integer;
  v_snapshot jsonb;
begin
  select i.*
  into v_incasso
  from gestionale_v2.incassi i
  where i.id = (payload->>'incasso_id')::uuid
    and i.azienda_id = (payload->>'azienda_id')::uuid
    and i.stato = 'valido';

  if v_incasso.id is null then
    raise exception 'Incasso valido non trovato';
  end if;

  select r.id
  into v_ricevuta_id
  from gestionale_v2.ricevute r
  where r.incasso_id = v_incasso.id
  limit 1;

  if v_ricevuta_id is not null then
    return jsonb_build_object(
      'ricevuta_id', v_ricevuta_id,
      'gia_esistente', true
    );
  end if;

  v_anno := extract(year from v_incasso.data_incasso)::integer;

  select coalesce(max(r.numero_progressivo), 0) + 1
  into v_numero
  from gestionale_v2.ricevute r
  where r.azienda_id = v_incasso.azienda_id
    and r.anno = v_anno;

  select jsonb_build_object(
    'azienda', to_jsonb(a),
    'cliente', to_jsonb(c),
    'incasso', to_jsonb(v_incasso)
  )
  into v_snapshot
  from gestionale_v2.aziende a
  join gestionale_v2.clienti c
    on c.id = v_incasso.cliente_id
  where a.id = v_incasso.azienda_id;

  insert into gestionale_v2.ricevute (
    azienda_id,
    cliente_id,
    incasso_id,
    anno,
    numero_progressivo,
    data_emissione,
    importo,
    metodo_pagamento,
    causale,
    snapshot_dati
  )
  values (
    v_incasso.azienda_id,
    v_incasso.cliente_id,
    v_incasso.id,
    v_anno,
    v_numero,
    v_incasso.data_incasso,
    v_incasso.importo,
    v_incasso.metodo_pagamento,
    v_incasso.causale,
    v_snapshot
  )
  returning id into v_ricevuta_id;

  return jsonb_build_object(
    'ricevuta_id', v_ricevuta_id,
    'gia_esistente', false
  );
end;
$$;


-- Riallinea i pacchetti a lezioni esistenti.
update gestionale_v2.abbonamenti a
set
  data_fine_prevista = null,
  lezioni_iniziali = p.lezioni_totali
from gestionale_v2.pacchetti p
where p.id = a.pacchetto_id
  and p.modalita_lezioni = 'Pacchetto lezioni'
  and a.stato <> 'annullato';


-- Vista di compatibilità: conserva la data tecnica per le funzioni legacy,
-- ma espone anche la vera assenza di scadenza.
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
  coalesce(a.data_fine_prevista, date '9999-12-31')
    as data_fine_prevista,
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
    when a.data_fine_prevista is null then
      case
        when coalesce(sl.saldo_lezioni, a.lezioni_iniziali) <= 0
          then 'Terminato'
        else 'Attivo'
      end
    when a.data_fine_prevista < current_date then 'Scaduto'
    when a.data_fine_prevista <= current_date + 15 then 'In scadenza'
    else 'Attivo'
  end as stato_visuale,
  coalesce(sl.movimenti_lezioni_netto, 0)
    as movimenti_lezioni_netto,
  coalesce(sl.saldo_lezioni, a.lezioni_iniziali)
    as saldo_lezioni,
  p.senza_scadenza,
  a.data_fine_prevista as data_fine_reale
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
  p.senza_scadenza,
  sl.movimenti_lezioni_netto,
  sl.saldo_lezioni,
  nr.data_scadenza,
  nr.residuo_rata;


grant execute
on function gestionale_v2.salva_pacchetto(jsonb)
to service_role;

grant execute
on function gestionale_v2.genera_ricevuta_incasso(jsonb)
to service_role;

grant select
on gestionale_v2.vista_abbonamenti_operativa
to service_role;

commit;

notify pgrst, 'reload schema';
