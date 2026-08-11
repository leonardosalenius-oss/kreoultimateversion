begin;

-- ============================================================
-- KREO TORNELLO - SHADOW MODE
-- - badge staff senza limitazioni
-- - codice letto dal lettore del tornello
-- - pairing badge <-> codice tornello
-- - log decisioni KREO senza apertura fisica
-- ============================================================

alter table gestionale_v2.badge_clienti
  add column if not exists codice_tornello text;

create unique index if not exists uq_badge_cliente_codice_tornello_attivo
on gestionale_v2.badge_clienti (
  azienda_id,
  upper(codice_tornello)
)
where attivo = true
  and codice_tornello is not null;


create table if not exists gestionale_v2.badge_staff (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  nome text not null,
  ruolo text,
  rfid_uid_reale text,
  codice_tornello text,
  attivo boolean not null default true,
  note text,
  associato_il timestamptz not null default now(),
  disattivato_il timestamptz,
  motivo_disattivazione text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uq_badge_staff_uid_attivo
on gestionale_v2.badge_staff (
  azienda_id,
  upper(rfid_uid_reale)
)
where attivo = true
  and rfid_uid_reale is not null;

create unique index if not exists uq_badge_staff_codice_tornello_attivo
on gestionale_v2.badge_staff (
  azienda_id,
  upper(codice_tornello)
)
where attivo = true
  and codice_tornello is not null;


create table if not exists gestionale_v2.richieste_lettura_badge_staff (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  nome_staff text not null,
  ruolo_staff text,
  note text,
  stato text not null default 'in_attesa'
    check (
      stato in (
        'in_attesa',
        'in_lettura',
        'letto',
        'confermato',
        'errore',
        'scaduto',
        'annullato'
      )
    ),
  lettore text not null default 'RECEPTION_ST_FH320',
  rfid_uid text,
  errore text,
  richiesto_da uuid,
  richiesto_il timestamptz not null default now(),
  preso_in_carico_il timestamptz,
  letto_il timestamptz,
  confermato_il timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists idx_richieste_badge_staff_coda
on gestionale_v2.richieste_lettura_badge_staff (
  stato,
  richiesto_il
);


create table if not exists gestionale_v2.richieste_abbinamento_tornello (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  tipo_badge text not null
    check (tipo_badge in ('cliente', 'staff')),
  badge_id uuid not null,
  stato text not null default 'in_attesa'
    check (
      stato in (
        'in_attesa',
        'abbinato',
        'errore',
        'scaduto',
        'annullato'
      )
    ),
  codice_tornello text,
  errore text,
  richiesto_da uuid,
  richiesto_il timestamptz not null default now(),
  abbinato_il timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists idx_abbinamento_tornello_coda
on gestionale_v2.richieste_abbinamento_tornello (
  azienda_id,
  stato,
  richiesto_il
);


create table if not exists gestionale_v2.eventi_tornello_shadow (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  codice_tornello text not null,
  tipo_badge text,
  badge_cliente_id uuid,
  badge_staff_id uuid,
  cliente_id uuid,
  identita text,
  decisione_kreo text not null
    check (
      decisione_kreo in (
        'consentito',
        'negato',
        'non_mappato'
      )
    ),
  motivo text not null,
  perfectgym_idsocio text,
  mappatura_appresa boolean not null default false,
  shadow_mode boolean not null default true,
  sorgente text not null default 'KREO_TURNSTILE_AGENT',
  created_at timestamptz not null default now()
);

create index if not exists idx_eventi_tornello_shadow_recenti
on gestionale_v2.eventi_tornello_shadow (
  azienda_id,
  created_at desc
);


grant select, insert, update
on gestionale_v2.badge_staff,
   gestionale_v2.richieste_lettura_badge_staff,
   gestionale_v2.richieste_abbinamento_tornello,
   gestionale_v2.eventi_tornello_shadow
to service_role;


-- ============================================================
-- LETTURA BADGE STAFF DAL LETTORE RECEPTION
-- ============================================================

create or replace function gestionale_v2.crea_richiesta_lettura_badge_staff(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_nome text := trim(payload->>'nome_staff');
begin
  if v_nome is null or v_nome = '' then
    raise exception 'Nome staff obbligatorio';
  end if;

  update gestionale_v2.richieste_lettura_badge_staff
  set
    stato = 'annullato',
    updated_at = now()
  where azienda_id = v_azienda
    and stato in ('in_attesa', 'in_lettura');

  insert into gestionale_v2.richieste_lettura_badge_staff (
    azienda_id,
    nome_staff,
    ruolo_staff,
    note,
    richiesto_da
  )
  values (
    v_azienda,
    v_nome,
    nullif(trim(payload->>'ruolo_staff'), ''),
    nullif(trim(payload->>'note'), ''),
    nullif(payload->>'utente_id', '')::uuid
  )
  returning id into v_id;

  return jsonb_build_object(
    'richiesta_id', v_id,
    'stato', 'in_attesa'
  );
end;
$$;

grant execute
on function gestionale_v2.crea_richiesta_lettura_badge_staff(jsonb)
to service_role;


create or replace function gestionale_v2.stato_richiesta_lettura_badge_staff(
  payload jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_row gestionale_v2.richieste_lettura_badge_staff;
begin
  select *
  into v_row
  from gestionale_v2.richieste_lettura_badge_staff
  where id = (payload->>'richiesta_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if v_row.id is null then
    raise exception 'Richiesta staff non trovata';
  end if;

  return jsonb_build_object(
    'richiesta_id', v_row.id,
    'stato', v_row.stato,
    'rfid_uid', v_row.rfid_uid,
    'errore', v_row.errore,
    'letto_il', v_row.letto_il
  );
end;
$$;

grant execute
on function gestionale_v2.stato_richiesta_lettura_badge_staff(jsonb)
to service_role;


create or replace function gestionale_v2.associa_badge_staff_rfid(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_uid text := upper(trim(payload->>'rfid_uid'));
  v_nome text := trim(payload->>'nome_staff');
  v_richiesta uuid := nullif(payload->>'richiesta_id', '')::uuid;
  v_id uuid;
begin
  if v_uid is null or v_uid = '' then
    raise exception 'UID RFID mancante';
  end if;

  if v_nome is null or v_nome = '' then
    raise exception 'Nome staff mancante';
  end if;

  if exists (
    select 1
    from gestionale_v2.badge_clienti b
    where b.azienda_id = v_azienda
      and b.attivo = true
      and upper(coalesce(b.rfid_uid_reale, '')) = v_uid
  ) or exists (
    select 1
    from gestionale_v2.badge_staff s
    where s.azienda_id = v_azienda
      and s.attivo = true
      and upper(coalesce(s.rfid_uid_reale, '')) = v_uid
  ) then
    raise exception 'Questo badge RFID è già associato';
  end if;

  insert into gestionale_v2.badge_staff (
    azienda_id,
    nome,
    ruolo,
    rfid_uid_reale,
    note
  )
  values (
    v_azienda,
    v_nome,
    nullif(trim(payload->>'ruolo_staff'), ''),
    v_uid,
    nullif(trim(payload->>'note'), '')
  )
  returning id into v_id;

  if v_richiesta is not null then
    update gestionale_v2.richieste_lettura_badge_staff
    set
      stato = 'confermato',
      confermato_il = now(),
      updated_at = now()
    where id = v_richiesta
      and azienda_id = v_azienda;
  end if;

  return jsonb_build_object(
    'badge_staff_id', v_id,
    'rfid_uid', v_uid,
    'nome_staff', v_nome
  );
end;
$$;

grant execute
on function gestionale_v2.associa_badge_staff_rfid(jsonb)
to service_role;


create or replace function gestionale_v2.cambia_stato_badge_staff(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_attivo boolean := coalesce((payload->>'attivo')::boolean, false);
begin
  update gestionale_v2.badge_staff
  set
    attivo = v_attivo,
    disattivato_il = case when v_attivo then null else now() end,
    motivo_disattivazione = case
      when v_attivo then null
      else nullif(trim(payload->>'motivo'), '')
    end,
    updated_at = now()
  where id = (payload->>'badge_staff_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if not found then
    raise exception 'Badge staff non trovato';
  end if;

  return jsonb_build_object('attivo', v_attivo);
end;
$$;

grant execute
on function gestionale_v2.cambia_stato_badge_staff(jsonb)
to service_role;


-- ============================================================
-- ABBINAMENTO CODICE LETTO DAL TORNELLO
-- ============================================================

create or replace function gestionale_v2.crea_richiesta_abbinamento_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_tipo text := trim(payload->>'tipo_badge');
  v_badge uuid := (payload->>'badge_id')::uuid;
begin
  if v_tipo not in ('cliente', 'staff') then
    raise exception 'Tipo badge non valido';
  end if;

  if v_tipo = 'cliente' and not exists (
    select 1
    from gestionale_v2.badge_clienti b
    where b.id = v_badge
      and b.azienda_id = v_azienda
      and b.attivo = true
  ) then
    raise exception 'Badge cliente non trovato';
  end if;

  if v_tipo = 'staff' and not exists (
    select 1
    from gestionale_v2.badge_staff s
    where s.id = v_badge
      and s.azienda_id = v_azienda
      and s.attivo = true
  ) then
    raise exception 'Badge staff non trovato';
  end if;

  update gestionale_v2.richieste_abbinamento_tornello
  set
    stato = 'annullato',
    updated_at = now()
  where azienda_id = v_azienda
    and stato = 'in_attesa';

  insert into gestionale_v2.richieste_abbinamento_tornello (
    azienda_id,
    tipo_badge,
    badge_id,
    richiesto_da
  )
  values (
    v_azienda,
    v_tipo,
    v_badge,
    nullif(payload->>'utente_id', '')::uuid
  )
  returning id into v_id;

  return jsonb_build_object(
    'richiesta_id', v_id,
    'stato', 'in_attesa'
  );
end;
$$;

grant execute
on function gestionale_v2.crea_richiesta_abbinamento_tornello(jsonb)
to service_role;


create or replace function gestionale_v2.stato_richiesta_abbinamento_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_row gestionale_v2.richieste_abbinamento_tornello;
begin
  select *
  into v_row
  from gestionale_v2.richieste_abbinamento_tornello
  where id = (payload->>'richiesta_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if v_row.id is null then
    raise exception 'Richiesta abbinamento non trovata';
  end if;

  return jsonb_build_object(
    'richiesta_id', v_row.id,
    'stato', v_row.stato,
    'codice_tornello', v_row.codice_tornello,
    'errore', v_row.errore,
    'abbinato_il', v_row.abbinato_il
  );
end;
$$;

grant execute
on function gestionale_v2.stato_richiesta_abbinamento_tornello(jsonb)
to service_role;


create or replace function gestionale_v2.completa_abbinamento_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_row gestionale_v2.richieste_abbinamento_tornello;
  v_code text := upper(trim(payload->>'codice_tornello'));
begin
  select *
  into v_row
  from gestionale_v2.richieste_abbinamento_tornello
  where id = (payload->>'richiesta_id')::uuid
    and stato = 'in_attesa'
  for update;

  if v_row.id is null then
    raise exception 'Richiesta abbinamento non disponibile';
  end if;

  if v_code is null or v_code = '' then
    raise exception 'Codice tornello mancante';
  end if;

  if exists (
    select 1
    from gestionale_v2.badge_clienti b
    where b.azienda_id = v_row.azienda_id
      and b.attivo = true
      and upper(coalesce(b.codice_tornello, '')) = v_code
      and not (
        v_row.tipo_badge = 'cliente'
        and b.id = v_row.badge_id
      )
  ) or exists (
    select 1
    from gestionale_v2.badge_staff s
    where s.azienda_id = v_row.azienda_id
      and s.attivo = true
      and upper(coalesce(s.codice_tornello, '')) = v_code
      and not (
        v_row.tipo_badge = 'staff'
        and s.id = v_row.badge_id
      )
  ) then
    raise exception 'Codice tornello già associato a un altro badge';
  end if;

  if v_row.tipo_badge = 'cliente' then
    update gestionale_v2.badge_clienti
    set
      codice_tornello = v_code,
      updated_at = now()
    where id = v_row.badge_id
      and azienda_id = v_row.azienda_id;
  else
    update gestionale_v2.badge_staff
    set
      codice_tornello = v_code,
      updated_at = now()
    where id = v_row.badge_id
      and azienda_id = v_row.azienda_id;
  end if;

  update gestionale_v2.richieste_abbinamento_tornello
  set
    stato = 'abbinato',
    codice_tornello = v_code,
    abbinato_il = now(),
    updated_at = now()
  where id = v_row.id;

  return jsonb_build_object(
    'abbinato', true,
    'tipo_badge', v_row.tipo_badge,
    'badge_id', v_row.badge_id,
    'codice_tornello', v_code
  );
end;
$$;

grant execute
on function gestionale_v2.completa_abbinamento_tornello(jsonb)
to service_role;


-- ============================================================
-- APPRENDIMENTO AUTOMATICO LEGACY PERFECTGYM
-- ============================================================

create or replace function gestionale_v2.apprendi_codice_tornello_legacy(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_idsocio text := trim(payload->>'perfectgym_idsocio');
  v_code text := upper(trim(payload->>'codice_tornello'));
  v_badge_id uuid;
begin
  if v_idsocio is null or v_idsocio = ''
     or v_code is null or v_code = '' then
    return jsonb_build_object('aggiornato', false);
  end if;

  select b.id
  into v_badge_id
  from gestionale_v2.badge_clienti b
  where b.azienda_id = v_azienda
    and b.attivo = true
    and trim(coalesce(b.perfectgym_idsocio, '')) = v_idsocio
  order by b.updated_at desc nulls last
  limit 1;

  if v_badge_id is null then
    return jsonb_build_object(
      'aggiornato', false,
      'motivo', 'IDSocio non presente tra i badge KREO'
    );
  end if;

  if exists (
    select 1
    from gestionale_v2.badge_clienti b
    where b.azienda_id = v_azienda
      and b.attivo = true
      and b.id <> v_badge_id
      and upper(coalesce(b.codice_tornello, '')) = v_code
  ) or exists (
    select 1
    from gestionale_v2.badge_staff s
    where s.azienda_id = v_azienda
      and s.attivo = true
      and upper(coalesce(s.codice_tornello, '')) = v_code
  ) then
    return jsonb_build_object(
      'aggiornato', false,
      'motivo', 'Codice tornello già utilizzato'
    );
  end if;

  update gestionale_v2.badge_clienti
  set
    codice_tornello = v_code,
    updated_at = now()
  where id = v_badge_id;

  return jsonb_build_object(
    'aggiornato', true,
    'badge_id', v_badge_id,
    'perfectgym_idsocio', v_idsocio,
    'codice_tornello', v_code
  );
end;
$$;

grant execute
on function gestionale_v2.apprendi_codice_tornello_legacy(jsonb)
to service_role;


-- ============================================================
-- VALUTAZIONE KREO PURA - NESSUN EFFETTO COLLATERALE
-- Replica le regole KREO già usate dal tornello:
-- cliente attivo, abbonamento valido, non sospeso,
-- certificato valido, prenotazione odierna.
-- NON controlla la "data iscrizione" di PerfectGym.
-- NON scala lezioni e NON cambia presenze in shadow mode.
-- ============================================================

create or replace function gestionale_v2.valuta_accesso_cliente_shadow(
  p_azienda_id uuid,
  p_cliente_id uuid
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_cliente_nome text;
  v_abbonamento_id uuid;
  v_abbonamento_stato text;
  v_prenotazione_id uuid;
begin
  select trim(c.cognome || ' ' || c.nome)
  into v_cliente_nome
  from gestionale_v2.clienti c
  where c.id = p_cliente_id
    and c.azienda_id = p_azienda_id
    and c.stato = 'attivo';

  if v_cliente_nome is null then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Cliente inattivo'
    );
  end if;

  select
    v.abbonamento_id,
    v.stato
  into
    v_abbonamento_id,
    v_abbonamento_stato
  from gestionale_v2.vista_abbonamenti_operativa v
  where v.azienda_id = p_azienda_id
    and v.cliente_id = p_cliente_id
    and v.stato not in (
      'terminato',
      'chiuso_anticipatamente',
      'annullato'
    )
    and v.data_inizio <= current_date
    and v.data_fine_prevista >= current_date
  order by v.data_inizio desc
  limit 1;

  if v_abbonamento_id is null then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Nessun abbonamento valido',
      'cliente', v_cliente_nome
    );
  end if;

  if v_abbonamento_stato = 'sospeso' then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Abbonamento sospeso',
      'cliente', v_cliente_nome,
      'abbonamento_id', v_abbonamento_id
    );
  end if;

  if not gestionale_v2.verifica_certificato_cliente(p_cliente_id) then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Certificato medico mancante o scaduto',
      'cliente', v_cliente_nome,
      'abbonamento_id', v_abbonamento_id
    );
  end if;

  select p.id
  into v_prenotazione_id
  from gestionale_v2.prenotazioni p
  where p.azienda_id = p_azienda_id
    and p.cliente_id = p_cliente_id
    and p.abbonamento_id = v_abbonamento_id
    and p.data_prenotazione = current_date
    and p.stato in ('prenotata', 'confermata')
  order by abs(
    extract(epoch from (p.ora_inizio - localtime))
  )
  limit 1;

  if v_prenotazione_id is null then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Nessuna prenotazione odierna',
      'cliente', v_cliente_nome,
      'abbonamento_id', v_abbonamento_id
    );
  end if;

  return jsonb_build_object(
    'consentito', true,
    'motivo', 'Accesso consentito da regole KREO',
    'cliente', v_cliente_nome,
    'abbonamento_id', v_abbonamento_id,
    'prenotazione_id', v_prenotazione_id
  );
end;
$$;

grant execute
on function gestionale_v2.valuta_accesso_cliente_shadow(uuid, uuid)
to service_role;


create or replace function gestionale_v2.registra_evento_tornello_shadow(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_code text := upper(trim(payload->>'codice_tornello'));
  v_idsocio text := nullif(trim(payload->>'perfectgym_idsocio'), '');

  v_staff gestionale_v2.badge_staff;
  v_badge gestionale_v2.badge_clienti;
  v_cliente_id uuid;
  v_cliente_nome text;

  v_eval jsonb;
  v_decisione text;
  v_motivo text;
  v_tipo text;
  v_identita text;
  v_mappatura boolean := false;
  v_evento_id uuid;
begin
  if v_code is null or v_code = '' then
    raise exception 'Codice tornello mancante';
  end if;

  -- Se il bridge legacy ha dato un IDSocio, usalo solo per apprendere
  -- il codice hardware del tornello; la decisione resta interamente KREO.
  if v_idsocio is not null then
    v_eval := gestionale_v2.apprendi_codice_tornello_legacy(
      jsonb_build_object(
        'azienda_id', v_azienda,
        'perfectgym_idsocio', v_idsocio,
        'codice_tornello', v_code
      )
    );
    v_mappatura := coalesce((v_eval->>'aggiornato')::boolean, false);
  end if;

  select *
  into v_staff
  from gestionale_v2.badge_staff s
  where s.azienda_id = v_azienda
    and s.attivo = true
    and (
      upper(coalesce(s.codice_tornello, '')) = v_code
      or upper(coalesce(s.rfid_uid_reale, '')) = v_code
    )
  order by s.updated_at desc
  limit 1;

  if v_staff.id is not null then
    v_decisione := 'consentito';
    v_motivo := 'STAFF - accesso senza limitazioni';
    v_tipo := 'staff';
    v_identita := v_staff.nome;

    insert into gestionale_v2.eventi_tornello_shadow (
      azienda_id,
      codice_tornello,
      tipo_badge,
      badge_staff_id,
      identita,
      decisione_kreo,
      motivo,
      perfectgym_idsocio,
      mappatura_appresa
    )
    values (
      v_azienda,
      v_code,
      v_tipo,
      v_staff.id,
      v_identita,
      v_decisione,
      v_motivo,
      v_idsocio,
      v_mappatura
    )
    returning id into v_evento_id;

    return jsonb_build_object(
      'evento_id', v_evento_id,
      'decisione_kreo', v_decisione,
      'motivo', v_motivo,
      'tipo_badge', v_tipo,
      'identita', v_identita,
      'shadow_mode', true
    );
  end if;

  select b.*
  into v_badge
  from gestionale_v2.badge_clienti b
  where b.azienda_id = v_azienda
    and b.attivo = true
    and (
      upper(coalesce(b.codice_tornello, '')) = v_code
      or upper(coalesce(b.rfid_uid_reale, '')) = v_code
      or upper(coalesce(b.codice_badge, '')) = v_code
      or trim(coalesce(b.perfectgym_idsocio, '')) = v_code
    )
  order by b.updated_at desc nulls last, b.created_at desc
  limit 1;

  if v_badge.id is null then
    v_decisione := 'non_mappato';
    v_motivo := 'Codice tornello non ancora associato a un badge KREO';

    insert into gestionale_v2.eventi_tornello_shadow (
      azienda_id,
      codice_tornello,
      decisione_kreo,
      motivo,
      perfectgym_idsocio,
      mappatura_appresa
    )
    values (
      v_azienda,
      v_code,
      v_decisione,
      v_motivo,
      v_idsocio,
      v_mappatura
    )
    returning id into v_evento_id;

    return jsonb_build_object(
      'evento_id', v_evento_id,
      'decisione_kreo', v_decisione,
      'motivo', v_motivo,
      'shadow_mode', true
    );
  end if;

  v_cliente_id := v_badge.cliente_id;

  select trim(c.cognome || ' ' || c.nome)
  into v_cliente_nome
  from gestionale_v2.clienti c
  where c.id = v_cliente_id;

  v_eval := gestionale_v2.valuta_accesso_cliente_shadow(
    v_azienda,
    v_cliente_id
  );

  if coalesce((v_eval->>'consentito')::boolean, false) then
    v_decisione := 'consentito';
  else
    v_decisione := 'negato';
  end if;

  v_motivo := coalesce(
    nullif(v_eval->>'motivo', ''),
    'Decisione KREO non disponibile'
  );
  v_tipo := 'cliente';
  v_identita := coalesce(v_eval->>'cliente', v_cliente_nome);

  insert into gestionale_v2.eventi_tornello_shadow (
    azienda_id,
    codice_tornello,
    tipo_badge,
    badge_cliente_id,
    cliente_id,
    identita,
    decisione_kreo,
    motivo,
    perfectgym_idsocio,
    mappatura_appresa
  )
  values (
    v_azienda,
    v_code,
    v_tipo,
    v_badge.id,
    v_cliente_id,
    v_identita,
    v_decisione,
    v_motivo,
    v_idsocio,
    v_mappatura
  )
  returning id into v_evento_id;

  return jsonb_build_object(
    'evento_id', v_evento_id,
    'decisione_kreo', v_decisione,
    'motivo', v_motivo,
    'tipo_badge', v_tipo,
    'identita', v_identita,
    'cliente_id', v_cliente_id,
    'shadow_mode', true
  );
end;
$$;

grant execute
on function gestionale_v2.registra_evento_tornello_shadow(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
