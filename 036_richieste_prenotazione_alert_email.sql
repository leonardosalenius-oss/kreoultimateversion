begin;

create table if not exists gestionale_v2.alert_prenotazioni_cliente (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  prenotazione_id uuid not null
    references gestionale_v2.prenotazioni(id) on delete cascade,
  cliente_id uuid not null
    references gestionale_v2.clienti(id) on delete cascade,
  tipo text not null default 'richiesta_prenotazione',
  titolo text not null,
  messaggio text not null,
  letto boolean not null default false,
  risolto boolean not null default false,
  letto_da uuid,
  letto_at timestamptz,
  risolto_at timestamptz,
  created_at timestamptz not null default now(),
  unique (prenotazione_id, tipo)
);

create index if not exists idx_alert_prenotazioni_cliente_operativi
on gestionale_v2.alert_prenotazioni_cliente (
  azienda_id,
  risolto,
  letto,
  created_at desc
);

grant select, insert, update
on gestionale_v2.alert_prenotazioni_cliente
to service_role;


create or replace view gestionale_v2.vista_alert_prenotazioni_cliente
with (security_invoker = false)
as
select
  a.id as alert_id,
  a.azienda_id,
  a.prenotazione_id,
  a.cliente_id,
  concat(c.cognome, ' ', c.nome) as cliente,
  c.telefono,
  c.whatsapp,
  c.email,
  p.data_prenotazione,
  p.ora_inizio,
  p.ora_fine,
  p.tipologia,
  p.stato,
  p.motivo_ultimo_stato,
  p.origine,
  oa.nome_visualizzato as operatore,
  a.titolo,
  a.messaggio,
  a.letto,
  a.risolto,
  a.created_at
from gestionale_v2.alert_prenotazioni_cliente a
join gestionale_v2.prenotazioni p
  on p.id = a.prenotazione_id
join gestionale_v2.clienti c
  on c.id = a.cliente_id
left join gestionale_v2.operatori_agenda oa
  on oa.id = p.operatore_id;

grant select
on gestionale_v2.vista_alert_prenotazioni_cliente
to service_role;


create or replace function gestionale_v2.segna_alert_prenotazione_letto(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := (payload->>'alert_id')::uuid;
begin
  update gestionale_v2.alert_prenotazioni_cliente
  set
    letto = true,
    letto_da = nullif(payload->>'utente_id', '')::uuid,
    letto_at = now()
  where id = v_id
    and azienda_id = (payload->>'azienda_id')::uuid;

  if not found then
    raise exception 'Alert non trovato';
  end if;

  return jsonb_build_object(
    'alert_id', v_id,
    'letto', true
  );
end;
$$;

grant execute
on function gestionale_v2.segna_alert_prenotazione_letto(jsonb)
to service_role;


create or replace function gestionale_v2.risolvi_alert_prenotazione_trigger()
returns trigger
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
begin
  if new.stato is distinct from old.stato
     and new.stato <> 'prenotata' then
    update gestionale_v2.alert_prenotazioni_cliente
    set
      risolto = true,
      risolto_at = now(),
      letto = true,
      letto_at = coalesce(letto_at, now())
    where prenotazione_id = new.id
      and risolto = false;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_risolvi_alert_prenotazione
on gestionale_v2.prenotazioni;

create trigger trg_risolvi_alert_prenotazione
after update of stato
on gestionale_v2.prenotazioni
for each row
execute function gestionale_v2.risolvi_alert_prenotazione_trigger();


create or replace function gestionale_v2.app_cliente_prenota_slot(
  p_slot_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
  v_slot gestionale_v2.slot_app_cliente;
  v_abbonamento record;
  v_cliente record;
  v_prenotati integer;
  v_prenotazioni_periodo integer;
  v_future_prenotate integer;
  v_id uuid;
  v_periodo_inizio date;
  v_periodo_fine date;
  v_operatore text;
  v_cliente_nome text;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  select
    c.stato,
    c.prenotazioni_bloccate,
    c.motivo_blocco_prenotazioni,
    concat(c.cognome, ' ', c.nome) as cliente_nome
  into v_cliente
  from gestionale_v2.clienti c
  where c.id = v_accesso.cliente_id
    and c.azienda_id = v_accesso.azienda_id;

  if v_cliente.stato <> 'attivo' then
    raise exception 'Cliente non attivo';
  end if;

  if coalesce(v_cliente.prenotazioni_bloccate, false) then
    raise exception 'Prenotazioni bloccate: %',
      coalesce(
        v_cliente.motivo_blocco_prenotazioni,
        'rivolgersi alla reception'
      );
  end if;

  select * into v_slot
  from gestionale_v2.slot_app_cliente
  where id = p_slot_id
    and azienda_id = v_accesso.azienda_id
  for update;

  if v_slot.id is null or not v_slot.attivo then
    raise exception 'Slot non disponibile';
  end if;

  if (
    v_slot.data_slot + v_slot.ora_inizio
  ) <= (now() at time zone 'Europe/Rome') then
    raise exception 'Non è possibile prenotare uno slot già iniziato';
  end if;

  select *
  into v_abbonamento
  from gestionale_v2.vista_disponibilita_lezioni
  where azienda_id = v_accesso.azienda_id
    and cliente_id = v_accesso.cliente_id
    and corrente = true
  order by data_inizio desc
  limit 1;

  if v_abbonamento.abbonamento_id is null then
    raise exception 'Nessun abbonamento attivo';
  end if;

  if exists (
    select 1
    from gestionale_v2.prenotazioni p
    where p.cliente_id = v_accesso.cliente_id
      and p.slot_app_cliente_id = p_slot_id
      and p.stato <> 'annullata'
  ) then
    raise exception 'Hai già richiesto questo slot';
  end if;

  select count(*)::integer
  into v_prenotati
  from gestionale_v2.prenotazioni p
  where p.slot_app_cliente_id = p_slot_id
    and p.stato <> 'annullata';

  if v_prenotati >= v_slot.capienza then
    raise exception 'Lo slot non ha più posti disponibili';
  end if;

  if v_abbonamento.modalita_lezioni in ('Settimanale', 'Mensile') then
    if v_abbonamento.modalita_lezioni = 'Settimanale' then
      v_periodo_inizio := date_trunc('week', v_slot.data_slot)::date;
      v_periodo_fine := v_periodo_inizio + 6;
    else
      v_periodo_inizio := date_trunc('month', v_slot.data_slot)::date;
      v_periodo_fine := (
        date_trunc('month', v_slot.data_slot)
        + interval '1 month'
        - interval '1 day'
      )::date;
    end if;

    select count(*)::integer
    into v_prenotazioni_periodo
    from gestionale_v2.prenotazioni p
    where p.cliente_id = v_accesso.cliente_id
      and p.abbonamento_id = v_abbonamento.abbonamento_id
      and p.data_prenotazione between v_periodo_inizio and v_periodo_fine
      and p.stato <> 'annullata';

    if v_prenotazioni_periodo >=
       coalesce(v_abbonamento.quota_periodo, 0) then
      raise exception
        'Hai già utilizzato o prenotato tutta la disponibilità del periodo';
    end if;
  else
    select count(*)::integer
    into v_future_prenotate
    from gestionale_v2.prenotazioni p
    where p.cliente_id = v_accesso.cliente_id
      and p.abbonamento_id = v_abbonamento.abbonamento_id
      and p.data_prenotazione >=
        (now() at time zone 'Europe/Rome')::date
      and p.stato in ('prenotata', 'confermata');

    if coalesce(v_abbonamento.saldo_complessivo, 0)
       - v_future_prenotate <= 0 then
      raise exception 'Non hai lezioni residue disponibili';
    end if;
  end if;

  insert into gestionale_v2.prenotazioni (
    azienda_id,
    cliente_id,
    abbonamento_id,
    operatore_id,
    data_prenotazione,
    ora_inizio,
    ora_fine,
    tipologia,
    stato,
    note,
    slot_app_cliente_id,
    origine
  )
  values (
    v_accesso.azienda_id,
    v_accesso.cliente_id,
    v_abbonamento.abbonamento_id,
    v_slot.operatore_id,
    v_slot.data_slot,
    v_slot.ora_inizio,
    v_slot.ora_fine,
    v_slot.tipologia,
    'prenotata',
    'Richiesta dall''App Cliente · da confermare da Reception/Trainer',
    v_slot.id,
    'app_cliente'
  )
  returning id into v_id;

  select oa.nome_visualizzato
  into v_operatore
  from gestionale_v2.operatori_agenda oa
  where oa.id = v_slot.operatore_id;

  v_cliente_nome := v_cliente.cliente_nome;

  insert into gestionale_v2.alert_prenotazioni_cliente (
    azienda_id,
    prenotazione_id,
    cliente_id,
    titolo,
    messaggio
  )
  values (
    v_accesso.azienda_id,
    v_id,
    v_accesso.cliente_id,
    'Nuova richiesta di prenotazione',
    concat(
      v_cliente_nome,
      ' ha richiesto ',
      to_char(v_slot.data_slot, 'DD/MM/YYYY'),
      ' dalle ',
      to_char(v_slot.ora_inizio, 'HH24:MI'),
      ' alle ',
      to_char(v_slot.ora_fine, 'HH24:MI'),
      coalesce(' con ' || v_operatore, '')
    )
  )
  on conflict (prenotazione_id, tipo) do nothing;

  return jsonb_build_object(
    'prenotazione_id', v_id,
    'stato', 'prenotata',
    'messaggio', 'Richiesta inviata. Attendi la conferma di KREO.'
  );
end;
$$;


create or replace function gestionale_v2.app_cliente_dettaglio_notifica_prenotazione(
  p_prenotazione_id uuid
)
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
    'prenotazione_id', p.id,
    'cliente', concat(c.cognome, ' ', c.nome),
    'cliente_email', c.email,
    'cliente_telefono', c.telefono,
    'data_prenotazione', p.data_prenotazione,
    'ora_inizio', p.ora_inizio,
    'ora_fine', p.ora_fine,
    'tipologia', p.tipologia,
    'operatore', oa.nome_visualizzato,
    'stato', p.stato
  )
  into v_result
  from gestionale_v2.prenotazioni p
  join gestionale_v2.clienti c
    on c.id = p.cliente_id
  left join gestionale_v2.operatori_agenda oa
    on oa.id = p.operatore_id
  where p.id = p_prenotazione_id
    and p.azienda_id = v_accesso.azienda_id
    and p.cliente_id = v_accesso.cliente_id
    and p.origine = 'app_cliente';

  if v_result is null then
    raise exception 'Prenotazione non autorizzata';
  end if;

  return v_result;
end;
$$;

grant execute
on function gestionale_v2.app_cliente_dettaglio_notifica_prenotazione(uuid)
to authenticated;


drop function if exists gestionale_v2.app_cliente_prenotazioni();

create function gestionale_v2.app_cliente_prenotazioni()
returns table (
  prenotazione_id uuid,
  data_prenotazione date,
  ora_inizio time,
  ora_fine time,
  operatore text,
  tipologia text,
  stato text,
  motivo_stato text,
  origine text,
  annullabile boolean,
  termine_annullamento timestamp
)
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
  v_ore integer;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  select coalesce(ore_annullamento_cliente, 3)
  into v_ore
  from gestionale_v2.aziende
  where id = v_accesso.azienda_id;

  return query
  select
    p.id,
    p.data_prenotazione,
    p.ora_inizio,
    p.ora_fine,
    oa.nome_visualizzato,
    p.tipologia,
    p.stato,
    p.motivo_ultimo_stato,
    p.origine,
    (
      p.stato = 'prenotata'
      and (
        p.data_prenotazione + p.ora_inizio
        - make_interval(hours => v_ore)
      ) > (now() at time zone 'Europe/Rome')
    ) as annullabile,
    (
      p.data_prenotazione + p.ora_inizio
      - make_interval(hours => v_ore)
    )::timestamp as termine_annullamento
  from gestionale_v2.prenotazioni p
  left join gestionale_v2.operatori_agenda oa
    on oa.id = p.operatore_id
  where p.azienda_id = v_accesso.azienda_id
    and p.cliente_id = v_accesso.cliente_id
    and p.data_prenotazione >=
      ((now() at time zone 'Europe/Rome')::date - 30)
  order by p.data_prenotazione desc, p.ora_inizio desc;
end;
$$;

grant execute
on function gestionale_v2.app_cliente_prenotazioni()
to authenticated;

commit;

notify pgrst, 'reload schema';
