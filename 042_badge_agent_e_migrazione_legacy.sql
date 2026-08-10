begin;

-- ============================================================
-- BADGE RFID REALE + COMPATIBILITÀ PERFECTGYM LEGACY
-- ============================================================

alter table gestionale_v2.badge_clienti
  add column if not exists rfid_uid_reale text,
  add column if not exists perfectgym_idsocio text,
  add column if not exists origine_badge text not null default 'legacy',
  add column if not exists associato_il timestamptz,
  add column if not exists disattivato_il timestamptz,
  add column if not exists motivo_disattivazione text;

create unique index if not exists uq_badge_uid_reale_attivo
on gestionale_v2.badge_clienti (
  azienda_id,
  upper(rfid_uid_reale)
)
where attivo = true
  and rfid_uid_reale is not null;

create index if not exists idx_badge_perfectgym_idsocio
on gestionale_v2.badge_clienti (
  azienda_id,
  perfectgym_idsocio
);

-- I badge esistenti restano validi e NON vengono sovrascritti.
update gestionale_v2.badge_clienti
set
  origine_badge = coalesce(nullif(origine_badge, ''), 'legacy'),
  associato_il = coalesce(associato_il, created_at)
where associato_il is null
   or origine_badge is null
   or origine_badge = '';


-- ============================================================
-- CODA LETTURE PER AGENT LOCALE RECEPTION
-- ============================================================

create table if not exists gestionale_v2.richieste_lettura_badge (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  cliente_id uuid not null
    references gestionale_v2.clienti(id) on delete cascade,
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

create index if not exists idx_richieste_badge_coda
on gestionale_v2.richieste_lettura_badge (
  stato,
  richiesto_il
);

grant select, insert, update
on gestionale_v2.richieste_lettura_badge
to service_role;


create or replace function gestionale_v2.crea_richiesta_lettura_badge(
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
  v_cliente uuid := (payload->>'cliente_id')::uuid;
begin
  if not exists (
    select 1
    from gestionale_v2.clienti c
    where c.id = v_cliente
      and c.azienda_id = v_azienda
  ) then
    raise exception 'Cliente non trovato';
  end if;

  update gestionale_v2.richieste_lettura_badge
  set
    stato = 'annullato',
    updated_at = now()
  where azienda_id = v_azienda
    and cliente_id = v_cliente
    and stato in ('in_attesa', 'in_lettura');

  insert into gestionale_v2.richieste_lettura_badge (
    azienda_id,
    cliente_id,
    richiesto_da
  )
  values (
    v_azienda,
    v_cliente,
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
on function gestionale_v2.crea_richiesta_lettura_badge(jsonb)
to service_role;


create or replace function gestionale_v2.stato_richiesta_lettura_badge(
  payload jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_row gestionale_v2.richieste_lettura_badge;
begin
  select *
  into v_row
  from gestionale_v2.richieste_lettura_badge
  where id = (payload->>'richiesta_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if v_row.id is null then
    raise exception 'Richiesta non trovata';
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
on function gestionale_v2.stato_richiesta_lettura_badge(jsonb)
to service_role;


create or replace function gestionale_v2.associa_badge_rfid_reale(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_cliente uuid := (payload->>'cliente_id')::uuid;
  v_uid text := upper(trim(payload->>'rfid_uid'));
  v_note text := nullif(trim(payload->>'note'), '');
  v_richiesta uuid := nullif(payload->>'richiesta_id', '')::uuid;
  v_result jsonb;
  v_badge_id uuid;
begin
  if v_uid is null or v_uid = '' then
    raise exception 'UID RFID mancante';
  end if;

  if exists (
    select 1
    from gestionale_v2.badge_clienti b
    where b.azienda_id = v_azienda
      and b.attivo = true
      and upper(coalesce(b.rfid_uid_reale, '')) = v_uid
      and b.cliente_id <> v_cliente
  ) then
    raise exception 'Questo badge è già associato a un altro cliente';
  end if;

  -- Riutilizza la logica già consolidata del gestionale.
  v_result := gestionale_v2.associa_badge_cliente(
    jsonb_build_object(
      'azienda_id', v_azienda,
      'cliente_id', v_cliente,
      'codice_badge', v_uid,
      'note', v_note
    )
  );

  -- Individua il badge appena associato / riattivato.
  select b.id
  into v_badge_id
  from gestionale_v2.badge_clienti b
  where b.azienda_id = v_azienda
    and b.cliente_id = v_cliente
    and b.attivo = true
    and upper(b.codice_badge) = v_uid
  order by b.updated_at desc nulls last, b.created_at desc
  limit 1;

  if v_badge_id is null then
    raise exception 'Associazione badge non trovata dopo il salvataggio';
  end if;

  update gestionale_v2.badge_clienti
  set
    rfid_uid_reale = v_uid,
    origine_badge = 'lettore_kreo',
    associato_il = coalesce(associato_il, now()),
    disattivato_il = null,
    motivo_disattivazione = null,
    updated_at = now()
  where id = v_badge_id;

  if v_richiesta is not null then
    update gestionale_v2.richieste_lettura_badge
    set
      stato = 'confermato',
      confermato_il = now(),
      updated_at = now()
    where id = v_richiesta
      and azienda_id = v_azienda;
  end if;

  return jsonb_build_object(
    'badge_id', v_badge_id,
    'rfid_uid', v_uid,
    'cliente_id', v_cliente
  );
end;
$$;

grant execute
on function gestionale_v2.associa_badge_rfid_reale(jsonb)
to service_role;


-- ============================================================
-- MIGRAZIONE LEGACY: funzione usata dall'agent Windows
-- ============================================================

create or replace function gestionale_v2.aggiorna_badge_legacy_perfectgym(
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
  v_uid text := upper(trim(payload->>'rfid_uid'));
  v_badge_id uuid;
begin
  if v_idsocio = '' or v_uid = '' then
    raise exception 'IDSocio o UID mancanti';
  end if;

  select b.id
  into v_badge_id
  from gestionale_v2.badge_clienti b
  where b.azienda_id = v_azienda
    and trim(b.codice_badge) = v_idsocio
  order by b.attivo desc, b.created_at desc
  limit 1;

  if v_badge_id is null then
    return jsonb_build_object(
      'aggiornato', false,
      'motivo', 'badge_kreo_non_trovato',
      'perfectgym_idsocio', v_idsocio
    );
  end if;

  if exists (
    select 1
    from gestionale_v2.badge_clienti b
    where b.azienda_id = v_azienda
      and b.id <> v_badge_id
      and b.attivo = true
      and upper(coalesce(b.rfid_uid_reale, '')) = v_uid
  ) then
    return jsonb_build_object(
      'aggiornato', false,
      'motivo', 'uid_gia_associato',
      'rfid_uid', v_uid
    );
  end if;

  update gestionale_v2.badge_clienti
  set
    perfectgym_idsocio = v_idsocio,
    rfid_uid_reale = v_uid,
    origine_badge = 'perfectgym_migrato',
    associato_il = coalesce(associato_il, created_at, now()),
    updated_at = now()
  where id = v_badge_id;

  return jsonb_build_object(
    'aggiornato', true,
    'badge_id', v_badge_id,
    'perfectgym_idsocio', v_idsocio,
    'rfid_uid', v_uid
  );
end;
$$;

grant execute
on function gestionale_v2.aggiorna_badge_legacy_perfectgym(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
