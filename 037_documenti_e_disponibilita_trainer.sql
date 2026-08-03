begin;

-- ============================================================
-- DOCUMENTI AREA CLIENTE: TIPI DINAMICI E ARCHIVIO UNICO
-- ============================================================

create or replace function gestionale_v2.app_cliente_tipi_documento()
returns table (
  tipo_documento_id uuid,
  nome text,
  ha_scadenza boolean,
  obbligatorio boolean
)
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  return query
  select
    td.id,
    td.nome,
    td.ha_scadenza,
    td.obbligatorio
  from gestionale_v2.tipi_documento td
  where td.azienda_id = v_accesso.azienda_id
    and td.attivo = true
  order by td.obbligatorio desc, td.nome;
end;
$$;

grant execute
on function gestionale_v2.app_cliente_tipi_documento()
to authenticated;


create or replace function gestionale_v2.app_cliente_documenti()
returns table (
  documento_id uuid,
  tipo_documento_id uuid,
  tipo text,
  nome_documento text,
  file_path text,
  data_documento date,
  data_caricamento timestamptz,
  data_scadenza date,
  stato text,
  note text,
  origine text
)
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  return query
  select
    d.id,
    d.tipo_documento_id,
    td.nome,
    d.nome_documento,
    d.file_path,
    d.data_documento,
    d.data_caricamento,
    d.data_scadenza,
    d.stato,
    d.note,
    case
      when coalesce(d.note, '') ilike '%caricato autonomamente dal cliente%'
        then 'cliente'
      else 'kreo'
    end
  from gestionale_v2.documenti_clienti d
  join gestionale_v2.tipi_documento td
    on td.id = d.tipo_documento_id
  where d.azienda_id = v_accesso.azienda_id
    and d.cliente_id = v_accesso.cliente_id
    and d.stato <> 'annullato'
  order by d.data_caricamento desc;
end;
$$;

grant execute
on function gestionale_v2.app_cliente_documenti()
to authenticated;


create or replace function gestionale_v2.app_cliente_salva_documento(
  payload jsonb
)
returns uuid
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_accesso gestionale_v2.accessi_clienti;
  v_tipo_id uuid := nullif(payload->>'tipo_documento_id', '')::uuid;
  v_file_path text := nullif(trim(payload->>'file_path'), '');
  v_id uuid;
begin
  select * into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  if v_file_path is null then
    raise exception 'File mancante';
  end if;

  if v_file_path not like (
    v_accesso.azienda_id::text || '/' ||
    v_accesso.cliente_id::text || '/%'
  ) then
    raise exception 'Percorso file non autorizzato';
  end if;

  if not exists (
    select 1
    from gestionale_v2.tipi_documento td
    where td.id = v_tipo_id
      and td.azienda_id = v_accesso.azienda_id
      and td.attivo = true
  ) then
    raise exception 'Tipo documento non valido';
  end if;

  insert into gestionale_v2.documenti_clienti (
    azienda_id,
    cliente_id,
    tipo_documento_id,
    nome_documento,
    file_path,
    data_documento,
    data_scadenza,
    stato,
    note
  )
  values (
    v_accesso.azienda_id,
    v_accesso.cliente_id,
    v_tipo_id,
    nullif(trim(payload->>'nome_documento'), ''),
    v_file_path,
    coalesce(
      nullif(payload->>'data_documento', '')::date,
      (now() at time zone 'Europe/Rome')::date
    ),
    nullif(payload->>'data_scadenza', '')::date,
    'da_verificare',
    'Caricato autonomamente dal cliente'
  )
  returning id into v_id;

  return v_id;
end;
$$;

grant execute
on function gestionale_v2.app_cliente_salva_documento(jsonb)
to authenticated;


-- ============================================================
-- DISPONIBILITÀ STANDARD TRAINER E INDISPONIBILITÀ
-- ============================================================

create table if not exists gestionale_v2.disponibilita_operatori_settimanale (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  operatore_id uuid not null
    references gestionale_v2.operatori_agenda(id) on delete cascade,
  giorno_settimana integer not null check (giorno_settimana between 1 and 7),
  ora_inizio time not null default '07:30',
  ora_fine time not null default '20:30',
  durata_slot_minuti integer not null default 60
    check (durata_slot_minuti between 15 and 240),
  attiva boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (operatore_id, giorno_settimana),
  check (ora_fine > ora_inizio)
);

create table if not exists gestionale_v2.indisponibilita_operatori (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  operatore_id uuid not null
    references gestionale_v2.operatori_agenda(id) on delete cascade,
  data_inizio date not null,
  data_fine date not null,
  ora_inizio time,
  ora_fine time,
  giornata_intera boolean not null default true,
  motivo text not null,
  note text,
  attiva boolean not null default true,
  inserito_da uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (data_fine >= data_inizio),
  check (
    giornata_intera
    or (
      ora_inizio is not null
      and ora_fine is not null
      and ora_fine > ora_inizio
    )
  )
);

create index if not exists idx_indisponibilita_operatore_periodo
on gestionale_v2.indisponibilita_operatori (
  azienda_id,
  operatore_id,
  data_inizio,
  data_fine,
  attiva
);

grant select, insert, update, delete
on gestionale_v2.disponibilita_operatori_settimanale,
   gestionale_v2.indisponibilita_operatori
to service_role;


-- Enzo e Federica: tutti i giorni 07:30-20:30, slot da 60 minuti.
insert into gestionale_v2.disponibilita_operatori_settimanale (
  azienda_id,
  operatore_id,
  giorno_settimana,
  ora_inizio,
  ora_fine,
  durata_slot_minuti,
  attiva
)
select
  oa.azienda_id,
  oa.id,
  gs,
  '07:30'::time,
  '20:30'::time,
  60,
  true
from gestionale_v2.operatori_agenda oa
cross join generate_series(1, 7) gs
where lower(oa.nome_visualizzato) like '%enzo%'
   or lower(oa.nome_visualizzato) like '%federica%'
on conflict (operatore_id, giorno_settimana)
do update set
  ora_inizio = excluded.ora_inizio,
  ora_fine = excluded.ora_fine,
  durata_slot_minuti = excluded.durata_slot_minuti,
  attiva = true,
  updated_at = now();


create or replace function gestionale_v2.rigenera_slot_operatori(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid := (payload->>'azienda_id')::uuid;
  v_operatore_id uuid := nullif(payload->>'operatore_id', '')::uuid;
  v_dal date := coalesce(
    nullif(payload->>'dal', '')::date,
    (now() at time zone 'Europe/Rome')::date
  );
  v_al date := coalesce(
    nullif(payload->>'al', '')::date,
    v_dal + 90
  );
  v_row record;
  v_start timestamp;
  v_last_start timestamp;
  v_count integer := 0;
begin
  for v_row in
    select
      d::date as giorno,
      dos.operatore_id,
      dos.ora_inizio,
      dos.ora_fine,
      dos.durata_slot_minuti
    from generate_series(v_dal, v_al, interval '1 day') d
    join gestionale_v2.disponibilita_operatori_settimanale dos
      on dos.azienda_id = v_azienda_id
     and dos.giorno_settimana = extract(isodow from d)::integer
     and dos.attiva = true
     and (v_operatore_id is null or dos.operatore_id = v_operatore_id)
  loop
    v_start := v_row.giorno + v_row.ora_inizio;
    v_last_start :=
      v_row.giorno + v_row.ora_fine
      - make_interval(mins => v_row.durata_slot_minuti);

    while v_start <= v_last_start loop
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
        v_row.operatore_id,
        v_row.giorno,
        v_start::time,
        (
          v_start
          + make_interval(mins => v_row.durata_slot_minuti)
        )::time,
        1,
        'Lezione',
        'Disponibilità standard automatica',
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
        attivo = true,
        updated_at = now();

      v_count := v_count + 1;
      v_start := v_start
        + make_interval(mins => v_row.durata_slot_minuti);
    end loop;
  end loop;

  return jsonb_build_object(
    'slot_generati_o_aggiornati', v_count,
    'dal', v_dal,
    'al', v_al
  );
end;
$$;

grant execute
on function gestionale_v2.rigenera_slot_operatori(jsonb)
to service_role;


create or replace function gestionale_v2.salva_indisponibilita_operatore(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_giornata_intera boolean :=
    coalesce((payload->>'giornata_intera')::boolean, true);
begin
  insert into gestionale_v2.indisponibilita_operatori (
    azienda_id,
    operatore_id,
    data_inizio,
    data_fine,
    ora_inizio,
    ora_fine,
    giornata_intera,
    motivo,
    note,
    attiva,
    inserito_da
  )
  values (
    (payload->>'azienda_id')::uuid,
    (payload->>'operatore_id')::uuid,
    (payload->>'data_inizio')::date,
    (payload->>'data_fine')::date,
    case
      when v_giornata_intera then null
      else (payload->>'ora_inizio')::time
    end,
    case
      when v_giornata_intera then null
      else (payload->>'ora_fine')::time
    end,
    v_giornata_intera,
    trim(payload->>'motivo'),
    nullif(trim(payload->>'note'), ''),
    true,
    nullif(payload->>'utente_id', '')::uuid
  )
  returning id into v_id;

  return jsonb_build_object(
    'indisponibilita_id', v_id
  );
end;
$$;

create or replace function gestionale_v2.elimina_indisponibilita_operatore(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := (payload->>'indisponibilita_id')::uuid;
begin
  update gestionale_v2.indisponibilita_operatori
  set
    attiva = false,
    updated_at = now()
  where id = v_id
    and azienda_id = (payload->>'azienda_id')::uuid;

  if not found then
    raise exception 'Indisponibilità non trovata';
  end if;

  return jsonb_build_object(
    'indisponibilita_id', v_id,
    'attiva', false
  );
end;
$$;

grant execute
on function gestionale_v2.salva_indisponibilita_operatore(jsonb)
to service_role;

grant execute
on function gestionale_v2.elimina_indisponibilita_operatore(jsonb)
to service_role;


create or replace view gestionale_v2.vista_indisponibilita_operatori
with (security_invoker = false)
as
select
  io.id as indisponibilita_id,
  io.azienda_id,
  io.operatore_id,
  oa.nome_visualizzato as operatore,
  io.data_inizio,
  io.data_fine,
  io.ora_inizio,
  io.ora_fine,
  io.giornata_intera,
  io.motivo,
  io.note,
  io.attiva,
  io.created_at
from gestionale_v2.indisponibilita_operatori io
join gestionale_v2.operatori_agenda oa
  on oa.id = io.operatore_id;

grant select
on gestionale_v2.vista_indisponibilita_operatori
to service_role;


-- La disponibilità residua considera TUTTE le prenotazioni del gestionale,
-- anche quelle create da Reception o trainer e prive di slot_app_cliente_id.
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
  (
    select count(*)::integer
    from gestionale_v2.prenotazioni p
    where p.azienda_id = s.azienda_id
      and p.operatore_id = s.operatore_id
      and p.data_prenotazione = s.data_slot
      and p.stato <> 'annullata'
      and p.ora_inizio < s.ora_fine
      and p.ora_fine > s.ora_inizio
  ) as prenotati,
  greatest(
    s.capienza - (
      select count(*)::integer
      from gestionale_v2.prenotazioni p
      where p.azienda_id = s.azienda_id
        and p.operatore_id = s.operatore_id
        and p.data_prenotazione = s.data_slot
        and p.stato <> 'annullata'
        and p.ora_inizio < s.ora_fine
        and p.ora_fine > s.ora_inizio
    ),
    0
  )::integer as posti_disponibili,
  exists (
    select 1
    from gestionale_v2.indisponibilita_operatori io
    where io.azienda_id = s.azienda_id
      and io.operatore_id = s.operatore_id
      and io.attiva = true
      and s.data_slot between io.data_inizio and io.data_fine
      and (
        io.giornata_intera
        or (
          s.ora_inizio < io.ora_fine
          and s.ora_fine > io.ora_inizio
        )
      )
  ) as escluso,
  s.created_at,
  s.updated_at
from gestionale_v2.slot_app_cliente s
join gestionale_v2.operatori_agenda oa
  on oa.id = s.operatore_id;


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
    and v.data_slot between
      v_oggi
      and v_oggi + greatest(least(giorni, 90), 1)
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


-- Generazione iniziale dei prossimi 90 giorni.
select gestionale_v2.rigenera_slot_operatori(
  jsonb_build_object(
    'azienda_id', a.id,
    'dal', (now() at time zone 'Europe/Rome')::date,
    'al', (now() at time zone 'Europe/Rome')::date + 90
  )
)
from gestionale_v2.aziende a
where exists (
  select 1
  from gestionale_v2.disponibilita_operatori_settimanale dos
  where dos.azienda_id = a.id
    and dos.attiva = true
);


-- Permesso per Admin, Direzione, Reception e Trainer.
insert into gestionale_v2.permessi_accesso (
  codice,
  descrizione,
  area
)
values (
  'agenda.indisponibilita',
  'Gestire disponibilità e indisponibilità dei trainer',
  'Reception'
)
on conflict (codice) do update set
  descrizione = excluded.descrizione,
  area = excluded.area;

insert into gestionale_v2.ruoli_permessi (
  ruolo_codice,
  permesso_codice
)
select
  r.codice,
  'agenda.indisponibilita'
from gestionale_v2.ruoli_accesso r
where r.codice in (
  'super_admin',
  'direzione',
  'reception',
  'trainer'
)
on conflict do nothing;

commit;

notify pgrst, 'reload schema';
