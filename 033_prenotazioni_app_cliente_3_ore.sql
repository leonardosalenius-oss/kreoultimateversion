begin;

alter table gestionale_v2.aziende
  add column if not exists ore_annullamento_cliente integer not null default 3
  check (ore_annullamento_cliente between 0 and 72);

create table if not exists gestionale_v2.slot_app_cliente (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  operatore_id uuid not null
    references gestionale_v2.operatori_agenda(id) on delete restrict,
  data_slot date not null,
  ora_inizio time not null,
  ora_fine time not null,
  capienza integer not null default 1 check (capienza > 0),
  tipologia text not null default 'Lezione',
  note text,
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (ora_fine > ora_inizio)
);

create unique index if not exists uq_slot_app_cliente
on gestionale_v2.slot_app_cliente (
  azienda_id,
  operatore_id,
  data_slot,
  ora_inizio
);

create index if not exists idx_slot_app_cliente_periodo
on gestionale_v2.slot_app_cliente (
  azienda_id,
  data_slot,
  attivo
);

alter table gestionale_v2.prenotazioni
  add column if not exists slot_app_cliente_id uuid
    references gestionale_v2.slot_app_cliente(id) on delete set null,
  add column if not exists origine text not null default 'interno';

create index if not exists idx_prenotazioni_slot_app
on gestionale_v2.prenotazioni(slot_app_cliente_id);

create unique index if not exists uq_prenotazione_cliente_slot_attiva
on gestionale_v2.prenotazioni(cliente_id, slot_app_cliente_id)
where slot_app_cliente_id is not null
  and stato <> 'annullata';

create or replace function gestionale_v2.salva_slot_app_cliente(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid := (payload->>'azienda_id')::uuid;
  v_operatore_id uuid := (payload->>'operatore_id')::uuid;
  v_data date := (payload->>'data_slot')::date;
  v_ora_inizio time := (payload->>'ora_inizio')::time;
  v_ora_fine time := (payload->>'ora_fine')::time;
  v_capienza integer := greatest(coalesce((payload->>'capienza')::integer, 1), 1);
  v_tipologia text := coalesce(nullif(trim(payload->>'tipologia'), ''), 'Lezione');
  v_note text := nullif(trim(payload->>'note'), '');
  v_ripetizioni integer := greatest(coalesce((payload->>'ripetizioni_settimanali')::integer, 1), 1);
  v_i integer;
  v_count integer := 0;
begin
  if v_ora_fine <= v_ora_inizio then
    raise exception 'L''ora finale deve essere successiva all''ora iniziale';
  end if;

  if not exists (
    select 1
    from gestionale_v2.operatori_agenda oa
    where oa.id = v_operatore_id
      and oa.azienda_id = v_azienda_id
      and coalesce(oa.attivo, true) = true
  ) then
    raise exception 'Operatore non valido o non attivo';
  end if;

  for v_i in 0..least(v_ripetizioni - 1, 51) loop
    insert into gestionale_v2.slot_app_cliente (
      azienda_id,
      operatore_id,
      data_slot,
      ora_inizio,
      ora_fine,
      capienza,
      tipologia,
      note,
      attivo
    )
    values (
      v_azienda_id,
      v_operatore_id,
      v_data + (v_i * 7),
      v_ora_inizio,
      v_ora_fine,
      v_capienza,
      v_tipologia,
      v_note,
      true
    )
    on conflict (
      azienda_id,
      operatore_id,
      data_slot,
      ora_inizio
    )
    do update set
      ora_fine = excluded.ora_fine,
      capienza = excluded.capienza,
      tipologia = excluded.tipologia,
      note = excluded.note,
      attivo = true,
      updated_at = now();

    v_count := v_count + 1;
  end loop;

  return jsonb_build_object(
    'slot_generati_o_aggiornati', v_count
  );
end;
$$;

create or replace function gestionale_v2.cambia_stato_slot_app_cliente(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := (payload->>'slot_id')::uuid;
  v_attivo boolean := coalesce((payload->>'attivo')::boolean, false);
begin
  update gestionale_v2.slot_app_cliente
  set
    attivo = v_attivo,
    updated_at = now()
  where id = v_id;

  if not found then
    raise exception 'Slot non trovato';
  end if;

  return jsonb_build_object(
    'slot_id', v_id,
    'attivo', v_attivo
  );
end;
$$;

create or replace view gestionale_v2.vista_slot_app_cliente_operativa
with (security_invoker = false)
as
select
  s.id as slot_id,
  s.azienda_id,
  s.operatore_id,
  oa.nome_visualizzato as operatore,
  s.data_slot,
  s.ora_inizio,
  s.ora_fine,
  s.capienza,
  s.tipologia,
  s.note,
  s.attivo,
  count(p.id) filter (
    where p.stato <> 'annullata'
  )::integer as prenotati,
  greatest(
    s.capienza - count(p.id) filter (
      where p.stato <> 'annullata'
    ),
    0
  )::integer as posti_disponibili,
  s.created_at,
  s.updated_at
from gestionale_v2.slot_app_cliente s
join gestionale_v2.operatori_agenda oa
  on oa.id = s.operatore_id
left join gestionale_v2.prenotazioni p
  on p.slot_app_cliente_id = s.id
group by
  s.id,
  s.azienda_id,
  s.operatore_id,
  oa.nome_visualizzato,
  s.data_slot,
  s.ora_inizio,
  s.ora_fine,
  s.capienza,
  s.tipologia,
  s.note,
  s.attivo,
  s.created_at,
  s.updated_at;

create or replace function gestionale_v2.app_cliente_slot_disponibili(
  giorni integer default 30
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
      where p.slot_app_cliente_id = v.slot_id
        and p.cliente_id = v_accesso.cliente_id
        and p.stato <> 'annullata'
    ) as gia_prenotato
  from gestionale_v2.vista_slot_app_cliente_operativa v
  where v.azienda_id = v_accesso.azienda_id
    and v.attivo = true
    and v.data_slot between v_oggi and v_oggi + greatest(least(giorni, 60), 1)
    and (
      v.data_slot > v_oggi
      or v.ora_inizio > (now() at time zone 'Europe/Rome')::time
    )
  order by v.data_slot, v.ora_inizio, v.operatore;
end;
$$;

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
  v_certificato text;
  v_prenotati integer;
  v_prenotazioni_periodo integer;
  v_future_prenotate integer;
  v_id uuid;
  v_periodo_inizio date;
  v_periodo_fine date;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
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

  select coalesce(certificato_stato, 'Mancante')
  into v_certificato
  from gestionale_v2.vista_clienti_operativa
  where azienda_id = v_accesso.azienda_id
    and cliente_id = v_accesso.cliente_id
  limit 1;

  if lower(coalesce(v_certificato, 'mancante')) like '%mancant%'
     or lower(coalesce(v_certificato, 'mancante')) like '%scadut%' then
    raise exception 'Certificato medico mancante o scaduto';
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
    raise exception 'Hai già prenotato questo slot';
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

    if v_prenotazioni_periodo >= coalesce(v_abbonamento.quota_periodo, 0) then
      raise exception 'Hai già utilizzato o prenotato tutta la disponibilità del periodo';
    end if;
  else
    select count(*)::integer
    into v_future_prenotate
    from gestionale_v2.prenotazioni p
    where p.cliente_id = v_accesso.cliente_id
      and p.abbonamento_id = v_abbonamento.abbonamento_id
      and p.data_prenotazione >= (now() at time zone 'Europe/Rome')::date
      and p.stato = 'prenotata';

    if coalesce(v_abbonamento.saldo_complessivo, 0) - v_future_prenotate <= 0 then
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
    'Prenotazione effettuata dall''App Cliente',
    v_slot.id,
    'app_cliente'
  )
  returning id into v_id;

  return jsonb_build_object(
    'prenotazione_id', v_id,
    'messaggio', 'Prenotazione confermata'
  );
end;
$$;

create or replace function gestionale_v2.app_cliente_prenotazioni()
returns table (
  prenotazione_id uuid,
  data_prenotazione date,
  ora_inizio time,
  ora_fine time,
  operatore text,
  tipologia text,
  stato text,
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
    and p.data_prenotazione >= (
      (now() at time zone 'Europe/Rome')::date - 30
    )
  order by p.data_prenotazione desc, p.ora_inizio desc;
end;
$$;

create or replace function gestionale_v2.app_cliente_annulla_prenotazione(
  p_prenotazione_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
  v_booking gestionale_v2.prenotazioni;
  v_ore integer;
  v_limite timestamp;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  select * into v_booking
  from gestionale_v2.prenotazioni
  where id = p_prenotazione_id
    and azienda_id = v_accesso.azienda_id
    and cliente_id = v_accesso.cliente_id
  for update;

  if v_booking.id is null then
    raise exception 'Prenotazione non trovata';
  end if;

  if v_booking.stato <> 'prenotata' then
    raise exception 'La prenotazione non è annullabile';
  end if;

  select coalesce(ore_annullamento_cliente, 3)
  into v_ore
  from gestionale_v2.aziende
  where id = v_accesso.azienda_id;

  v_limite := (
    v_booking.data_prenotazione + v_booking.ora_inizio
    - make_interval(hours => v_ore)
  );

  if (now() at time zone 'Europe/Rome') >= v_limite then
    raise exception
      'La cancellazione gratuita è consentita fino a % ore prima',
      v_ore;
  end if;

  update gestionale_v2.prenotazioni
  set
    stato = 'annullata',
    motivo_ultimo_stato = 'Annullata dal cliente entro i termini',
    updated_at = now()
  where id = v_booking.id;

  return jsonb_build_object(
    'prenotazione_id', v_booking.id,
    'stato', 'annullata',
    'messaggio', 'Prenotazione annullata'
  );
end;
$$;

grant select on gestionale_v2.vista_slot_app_cliente_operativa to service_role;
grant select, insert, update on gestionale_v2.slot_app_cliente to service_role;
grant execute on function gestionale_v2.salva_slot_app_cliente(jsonb) to service_role;
grant execute on function gestionale_v2.cambia_stato_slot_app_cliente(jsonb) to service_role;

grant execute on function gestionale_v2.app_cliente_slot_disponibili(integer) to authenticated;
grant execute on function gestionale_v2.app_cliente_prenota_slot(uuid) to authenticated;
grant execute on function gestionale_v2.app_cliente_prenotazioni() to authenticated;
grant execute on function gestionale_v2.app_cliente_annulla_prenotazione(uuid) to authenticated;

commit;

notify pgrst, 'reload schema';
