begin;

-- ============================================================
-- CERTIFICATO: STATO UNICO, VISIBILE ANCHE SE DA VERIFICARE
-- ============================================================

create or replace view gestionale_v2.vista_certificati_clienti
with (security_invoker = false)
as
select
  c.azienda_id,
  c.id as cliente_id,
  d.id as documento_id,
  d.tipo_documento_id,
  d.nome_documento,
  d.file_path,
  d.data_documento,
  d.data_caricamento,
  d.data_scadenza,
  d.note,
  d.stato as stato_documento,
  case
    when d.id is null then 'Mancante'
    when d.stato = 'da_verificare' then 'Da verificare'
    when d.stato = 'scaduto' then 'Scaduto'
    when d.data_scadenza is not null
      and d.data_scadenza < (now() at time zone 'Europe/Rome')::date
      then 'Scaduto'
    when d.stato = 'in_scadenza' then 'In scadenza'
    when d.data_scadenza is not null
      and d.data_scadenza <=
        (now() at time zone 'Europe/Rome')::date + 30
      then 'In scadenza'
    when d.stato = 'valido' then 'Valido'
    else initcap(replace(d.stato, '_', ' '))
  end as certificato_stato
from gestionale_v2.clienti c
left join lateral (
  select d0.*
  from gestionale_v2.documenti_clienti d0
  join gestionale_v2.tipi_documento td
    on td.id = d0.tipo_documento_id
  where d0.azienda_id = c.azienda_id
    and d0.cliente_id = c.id
    and d0.stato <> 'annullato'
    and lower(td.nome) = 'certificato medico'
  order by
    case d0.stato
      when 'da_verificare' then 1
      when 'valido' then 2
      when 'in_scadenza' then 3
      when 'scaduto' then 4
      else 5
    end,
    d0.data_caricamento desc
  limit 1
) d on true;

grant select
on gestionale_v2.vista_certificati_clienti
to service_role;


create or replace function gestionale_v2.modifica_documento_cliente(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := (payload->>'documento_id')::uuid;
  v_azienda_id uuid := (payload->>'azienda_id')::uuid;
  v_tipo_id uuid := (payload->>'tipo_documento_id')::uuid;
  v_stato text := payload->>'stato';
begin
  if v_stato not in (
    'valido',
    'in_scadenza',
    'scaduto',
    'mancante',
    'da_verificare',
    'annullato'
  ) then
    raise exception 'Stato documento non valido';
  end if;

  if not exists (
    select 1
    from gestionale_v2.tipi_documento td
    where td.id = v_tipo_id
      and td.azienda_id = v_azienda_id
      and td.attivo = true
  ) then
    raise exception 'Tipo documento non valido';
  end if;

  update gestionale_v2.documenti_clienti
  set
    tipo_documento_id = v_tipo_id,
    nome_documento = nullif(trim(payload->>'nome_documento'), ''),
    data_documento = nullif(payload->>'data_documento', '')::date,
    data_scadenza = nullif(payload->>'data_scadenza', '')::date,
    stato = v_stato,
    note = nullif(trim(payload->>'note'), ''),
    updated_at = now()
  where id = v_id
    and azienda_id = v_azienda_id;

  if not found then
    raise exception 'Documento non trovato';
  end if;

  return jsonb_build_object(
    'documento_id', v_id,
    'stato', v_stato
  );
end;
$$;

grant execute
on function gestionale_v2.modifica_documento_cliente(jsonb)
to service_role;


-- ============================================================
-- SLOT CLIENTE: 7 GIORNI, MASSIMO 10
-- ============================================================

create or replace function gestionale_v2.app_cliente_slot_disponibili(
  giorni integer default 7
)
returns table (
  slot_id uuid,
  data_slot date,
  ora_inizio time,
  ora_fine time,
  operatore text,
  tipologia text,
  posti_disponibili integer,
  gia_prenotato boolean
)
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
  v_oggi date := (now() at time zone 'Europe/Rome')::date;
  v_giorni integer := greatest(least(coalesce(giorni, 7), 10), 1);
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  return query
  select
    v.slot_id,
    v.data_slot,
    v.ora_inizio,
    v.ora_fine,
    v.operatore,
    v.tipologia,
    v.posti_disponibili,
    exists (
      select 1
      from gestionale_v2.prenotazioni p
      where p.cliente_id = v_accesso.cliente_id
        and p.data_prenotazione = v.data_slot
        and p.stato <> 'annullata'
        and p.ora_inizio < v.ora_fine
        and p.ora_fine > v.ora_inizio
    ) as gia_prenotato
  from gestionale_v2.vista_slot_app_cliente_operativa v
  where v.azienda_id = v_accesso.azienda_id
    and v.attivo = true
    and v.escluso = false
    and v.posti_disponibili > 0
    and v.data_slot between v_oggi and v_oggi + v_giorni
    and (
      v.data_slot > v_oggi
      or v.ora_inizio >
        (now() at time zone 'Europe/Rome')::time
    )
  order by v.data_slot, v.ora_inizio, v.operatore;
end;
$$;

grant execute
on function gestionale_v2.app_cliente_slot_disponibili(integer)
to authenticated;


-- ============================================================
-- DASHBOARD CLIENTE: NOME PACCHETTO
-- ============================================================

create or replace function gestionale_v2.app_cliente_dashboard()
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
  v_result jsonb;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  select jsonb_build_object(
    'cliente_id', c.id,
    'nome', c.nome,
    'cognome', c.cognome,
    'email', c.email,
    'telefono', c.telefono,
    'whatsapp', c.whatsapp,
    'pacchetto_nome', ab.pacchetto_nome,
    'disponibilita_principale', dl.disponibilita_principale,
    'disponibilita_secondaria', dl.disponibilita_secondaria,
    'prossima_prenotazione', (
      select jsonb_build_object(
        'data', to_char(p.data_prenotazione, 'DD/MM/YYYY'),
        'ora', left(p.ora_inizio::text, 5),
        'operatore', p.operatore,
        'stato', p.stato
      )
      from gestionale_v2.vista_prenotazioni_operativa p
      where p.azienda_id = v_accesso.azienda_id
        and p.cliente_id = v_accesso.cliente_id
        and p.data_prenotazione >=
          (now() at time zone 'Europe/Rome')::date
        and p.stato not in ('annullata', 'assente')
      order by p.data_prenotazione, p.ora_inizio
      limit 1
    )
  )
  into v_result
  from gestionale_v2.clienti c
  left join lateral (
    select *
    from gestionale_v2.vista_disponibilita_lezioni dl0
    where dl0.azienda_id = v_accesso.azienda_id
      and dl0.cliente_id = v_accesso.cliente_id
      and dl0.corrente = true
    order by dl0.data_inizio desc
    limit 1
  ) dl on true
  left join lateral (
    select p.nome as pacchetto_nome
    from gestionale_v2.abbonamenti a
    join gestionale_v2.pacchetti p
      on p.id = a.pacchetto_id
    where a.azienda_id = v_accesso.azienda_id
      and a.cliente_id = v_accesso.cliente_id
      and a.stato not in (
        'annullato',
        'terminato',
        'chiuso_anticipatamente'
      )
    order by
      case when a.stato = 'attivo' then 0 else 1 end,
      a.data_inizio desc
    limit 1
  ) ab on true
  where c.id = v_accesso.cliente_id
    and c.azienda_id = v_accesso.azienda_id;

  return coalesce(v_result, '{}'::jsonb);
end;
$$;

grant execute
on function gestionale_v2.app_cliente_dashboard()
to authenticated;

commit;

notify pgrst, 'reload schema';
