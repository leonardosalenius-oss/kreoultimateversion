begin;

-- ============================================================
-- KREO WELCOME
-- Messaggio visivo per app cliente + TTS locale dal PC Reception.
-- ============================================================

alter table gestionale_v2.configurazione_tornello
  add column if not exists benvenuto_attivo boolean not null default true,
  add column if not exists benvenuto_app_attivo boolean not null default true,
  add column if not exists benvenuto_audio_attivo boolean not null default true,
  add column if not exists benvenuto_testo_app text not null
    default 'Benvenuto/a {nome}! Buon allenamento.',
  add column if not exists benvenuto_testo_audio text not null
    default 'Benvenuto/a {nome}, buon allenamento.',
  add column if not exists benvenuto_durata_app_secondi integer not null default 8,
  add column if not exists benvenuto_volume integer not null default 100,
  add column if not exists benvenuto_velocita_voce integer not null default 0;

alter table gestionale_v2.configurazione_tornello
  drop constraint if exists configurazione_tornello_benvenuto_durata_check;

alter table gestionale_v2.configurazione_tornello
  add constraint configurazione_tornello_benvenuto_durata_check
  check (benvenuto_durata_app_secondi between 3 and 30);

alter table gestionale_v2.configurazione_tornello
  drop constraint if exists configurazione_tornello_benvenuto_volume_check;

alter table gestionale_v2.configurazione_tornello
  add constraint configurazione_tornello_benvenuto_volume_check
  check (benvenuto_volume between 0 and 100);

alter table gestionale_v2.configurazione_tornello
  drop constraint if exists configurazione_tornello_benvenuto_velocita_check;

alter table gestionale_v2.configurazione_tornello
  add constraint configurazione_tornello_benvenuto_velocita_check
  check (benvenuto_velocita_voce between -10 and 10);


create table if not exists gestionale_v2.eventi_benvenuto_cliente (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null,
  cliente_id uuid not null,
  evento_tornello_id uuid,
  testo text not null,
  created_at timestamptz not null default now(),

  constraint eventi_benvenuto_cliente_azienda_fk
    foreign key (azienda_id)
    references gestionale_v2.aziende(id)
    on delete cascade,

  constraint eventi_benvenuto_cliente_cliente_fk
    foreign key (cliente_id)
    references gestionale_v2.clienti(id)
    on delete cascade,

  constraint eventi_benvenuto_cliente_evento_fk
    foreign key (evento_tornello_id)
    references gestionale_v2.eventi_tornello_kreo(id)
    on delete set null
);

create index if not exists idx_eventi_benvenuto_cliente_lookup
  on gestionale_v2.eventi_benvenuto_cliente (
    azienda_id,
    cliente_id,
    created_at desc
  );


create or replace function gestionale_v2.imposta_benvenuto_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
begin
  insert into gestionale_v2.configurazione_tornello (
    azienda_id,
    benvenuto_attivo,
    benvenuto_app_attivo,
    benvenuto_audio_attivo,
    benvenuto_testo_app,
    benvenuto_testo_audio,
    benvenuto_durata_app_secondi,
    benvenuto_volume,
    benvenuto_velocita_voce,
    modificato_da,
    modificato_il
  )
  values (
    v_azienda,
    coalesce((payload->>'benvenuto_attivo')::boolean, true),
    coalesce((payload->>'benvenuto_app_attivo')::boolean, true),
    coalesce((payload->>'benvenuto_audio_attivo')::boolean, true),
    coalesce(
      nullif(trim(payload->>'benvenuto_testo_app'), ''),
      'Benvenuto/a {nome}! Buon allenamento.'
    ),
    coalesce(
      nullif(trim(payload->>'benvenuto_testo_audio'), ''),
      'Benvenuto/a {nome}, buon allenamento.'
    ),
    greatest(
      3,
      least(
        30,
        coalesce(
          nullif(payload->>'benvenuto_durata_app_secondi', '')::integer,
          8
        )
      )
    ),
    greatest(
      0,
      least(
        100,
        coalesce(
          nullif(payload->>'benvenuto_volume', '')::integer,
          100
        )
      )
    ),
    greatest(
      -10,
      least(
        10,
        coalesce(
          nullif(payload->>'benvenuto_velocita_voce', '')::integer,
          0
        )
      )
    ),
    nullif(payload->>'utente_id', '')::uuid,
    now()
  )
  on conflict (azienda_id)
  do update set
    benvenuto_attivo = excluded.benvenuto_attivo,
    benvenuto_app_attivo = excluded.benvenuto_app_attivo,
    benvenuto_audio_attivo = excluded.benvenuto_audio_attivo,
    benvenuto_testo_app = excluded.benvenuto_testo_app,
    benvenuto_testo_audio = excluded.benvenuto_testo_audio,
    benvenuto_durata_app_secondi =
      excluded.benvenuto_durata_app_secondi,
    benvenuto_volume = excluded.benvenuto_volume,
    benvenuto_velocita_voce = excluded.benvenuto_velocita_voce,
    modificato_da = excluded.modificato_da,
    modificato_il = now();

  return (
    select to_jsonb(c)
    from gestionale_v2.configurazione_tornello c
    where c.azienda_id = v_azienda
  );
end;
$$;

grant execute
on function gestionale_v2.imposta_benvenuto_tornello(jsonb)
to service_role;


-- Snapshot V4.1: oltre alla decisione porta al PC Reception anche
-- nome/cognome e configurazione del benvenuto.
drop function if exists gestionale_v2.snapshot_tornello_edge(uuid);

create function gestionale_v2.snapshot_tornello_edge(
  p_azienda_id uuid
)
returns table (
  codice_tornello text,
  tipo_badge text,
  badge_cliente_id uuid,
  badge_staff_id uuid,
  cliente_id uuid,
  nome text,
  cognome text,
  identita text,
  decisione_kreo text,
  motivo text,
  prenotazione_id uuid,
  benvenuto_attivo boolean,
  benvenuto_app_attivo boolean,
  benvenuto_audio_attivo boolean,
  benvenuto_testo_app text,
  benvenuto_testo_audio text,
  benvenuto_durata_app_secondi integer,
  benvenuto_volume integer,
  benvenuto_velocita_voce integer,
  generato_il timestamptz
)
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_cfg gestionale_v2.configurazione_tornello;
  v_master boolean := true;
  v_badge record;
  v_eval jsonb;
  v_code text;
begin
  select *
  into v_cfg
  from gestionale_v2.configurazione_tornello c
  where c.azienda_id = p_azienda_id;

  v_master := coalesce(v_cfg.regole_accesso_attive, true);

  for v_badge in
    select s.*
    from gestionale_v2.badge_staff s
    where s.azienda_id = p_azienda_id
      and s.attivo = true
  loop
    for v_code in
      select distinct upper(trim(x.code))
      from (
        values
          (v_badge.codice_tornello),
          (v_badge.rfid_uid_reale)
      ) as x(code)
      where nullif(trim(x.code), '') is not null
    loop
      codice_tornello := v_code;
      tipo_badge := 'staff';
      badge_cliente_id := null;
      badge_staff_id := v_badge.id;
      cliente_id := null;
      nome := null;
      cognome := null;
      identita := v_badge.nome;
      decisione_kreo := 'consentito';
      motivo := 'STAFF - accesso senza limitazioni';
      prenotazione_id := null;
      benvenuto_attivo := false;
      benvenuto_app_attivo := false;
      benvenuto_audio_attivo := false;
      benvenuto_testo_app := null;
      benvenuto_testo_audio := null;
      benvenuto_durata_app_secondi := 8;
      benvenuto_volume := 100;
      benvenuto_velocita_voce := 0;
      generato_il := now();
      return next;
    end loop;
  end loop;

  for v_badge in
    select
      b.*,
      c.nome as nome_cliente,
      c.cognome as cognome_cliente,
      trim(c.cognome || ' ' || c.nome) as nome_completo,
      c.stato as stato_cliente
    from gestionale_v2.badge_clienti b
    join gestionale_v2.clienti c
      on c.id = b.cliente_id
    where b.azienda_id = p_azienda_id
      and b.attivo = true
  loop
    if not v_master then
      if v_badge.stato_cliente = 'attivo' then
        v_eval := jsonb_build_object(
          'consentito', true,
          'motivo',
          'MODALITÀ LIBERA - controlli amministrativi disattivati',
          'cliente', v_badge.nome_completo
        );
      else
        v_eval := jsonb_build_object(
          'consentito', false,
          'motivo', 'Cliente inattivo',
          'cliente', v_badge.nome_completo
        );
      end if;
    else
      v_eval := gestionale_v2.valuta_accesso_cliente_tornello(
        p_azienda_id,
        v_badge.cliente_id
      );
    end if;

    for v_code in
      select distinct upper(trim(x.code))
      from (
        values
          (v_badge.codice_tornello),
          (v_badge.rfid_uid_reale),
          (v_badge.codice_badge),
          (v_badge.perfectgym_idsocio)
      ) as x(code)
      where nullif(trim(x.code), '') is not null
    loop
      codice_tornello := v_code;
      tipo_badge := 'cliente';
      badge_cliente_id := v_badge.id;
      badge_staff_id := null;
      cliente_id := v_badge.cliente_id;
      nome := v_badge.nome_cliente;
      cognome := v_badge.cognome_cliente;
      identita := coalesce(
        nullif(v_eval->>'cliente', ''),
        v_badge.nome_completo
      );
      decisione_kreo := case
        when coalesce((v_eval->>'consentito')::boolean, false)
        then 'consentito'
        else 'negato'
      end;
      motivo := coalesce(
        nullif(v_eval->>'motivo', ''),
        'Decisione KREO non disponibile'
      );
      prenotazione_id :=
        nullif(v_eval->>'prenotazione_id', '')::uuid;

      benvenuto_attivo :=
        coalesce(v_cfg.benvenuto_attivo, true);
      benvenuto_app_attivo :=
        coalesce(v_cfg.benvenuto_app_attivo, true);
      benvenuto_audio_attivo :=
        coalesce(v_cfg.benvenuto_audio_attivo, true);
      benvenuto_testo_app :=
        coalesce(
          nullif(v_cfg.benvenuto_testo_app, ''),
          'Benvenuto/a {nome}! Buon allenamento.'
        );
      benvenuto_testo_audio :=
        coalesce(
          nullif(v_cfg.benvenuto_testo_audio, ''),
          'Benvenuto/a {nome}, buon allenamento.'
        );
      benvenuto_durata_app_secondi :=
        coalesce(v_cfg.benvenuto_durata_app_secondi, 8);
      benvenuto_volume :=
        coalesce(v_cfg.benvenuto_volume, 100);
      benvenuto_velocita_voce :=
        coalesce(v_cfg.benvenuto_velocita_voce, 0);
      generato_il := now();
      return next;
    end loop;
  end loop;
end;
$$;

grant execute
on function gestionale_v2.snapshot_tornello_edge(uuid)
to service_role;


-- L'evento edge crea anche il benvenuto per la PWA solo quando
-- il controller ha confermato l'apertura.
create or replace function gestionale_v2.registra_evento_tornello_edge(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_decisione text := payload->>'decisione_kreo';
  v_cliente_id uuid :=
    nullif(payload->>'cliente_id', '')::uuid;
  v_apertura_ok boolean :=
    coalesce((payload->>'apertura_successo')::boolean, false);
  v_app_attiva boolean :=
    coalesce((payload->>'benvenuto_app_attivo')::boolean, false);
  v_testo_app text :=
    nullif(payload->>'benvenuto_testo_app_rendered', '');
begin
  if v_decisione not in ('consentito', 'negato', 'non_mappato') then
    raise exception 'Decisione edge non valida';
  end if;

  insert into gestionale_v2.eventi_tornello_kreo (
    azienda_id,
    modalita,
    codice_tornello,
    tipo_badge,
    badge_cliente_id,
    badge_staff_id,
    cliente_id,
    identita,
    decisione_kreo,
    motivo,
    prenotazione_id,
    origine_decisione,
    cache_generata_il,
    latenza_decisione_ms
  )
  values (
    (payload->>'azienda_id')::uuid,
    'attivo',
    upper(trim(payload->>'codice_tornello')),
    nullif(payload->>'tipo_badge', ''),
    nullif(payload->>'badge_cliente_id', '')::uuid,
    nullif(payload->>'badge_staff_id', '')::uuid,
    v_cliente_id,
    nullif(payload->>'identita', ''),
    v_decisione,
    coalesce(
      nullif(payload->>'motivo', ''),
      'Decisione locale KREO Edge'
    ),
    nullif(payload->>'prenotazione_id', '')::uuid,
    'edge',
    nullif(payload->>'cache_generata_il', '')::timestamptz,
    nullif(payload->>'latenza_decisione_ms', '')::numeric
  )
  returning id into v_id;

  if
    v_decisione = 'consentito'
    and v_apertura_ok
    and v_cliente_id is not null
    and v_app_attiva
    and v_testo_app is not null
  then
    insert into gestionale_v2.eventi_benvenuto_cliente (
      azienda_id,
      cliente_id,
      evento_tornello_id,
      testo
    )
    values (
      (payload->>'azienda_id')::uuid,
      v_cliente_id,
      v_id,
      v_testo_app
    );
  end if;

  return jsonb_build_object('evento_id', v_id);
end;
$$;

grant execute
on function gestionale_v2.registra_evento_tornello_edge(jsonb)
to service_role;


-- Ultimo benvenuto per l'utente autenticato della PWA.
create or replace function gestionale_v2.app_cliente_ultimo_benvenuto()
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
  select *
  into v_accesso
  from gestionale_v2.app_cliente_accesso_corrente();

  if v_accesso.id is null then
    raise exception 'Accesso cliente non autorizzato';
  end if;

  select jsonb_build_object(
    'id', e.id,
    'testo', e.testo,
    'created_at', e.created_at,
    'durata_secondi',
      coalesce(c.benvenuto_durata_app_secondi, 8)
  )
  into v_result
  from gestionale_v2.eventi_benvenuto_cliente e
  left join gestionale_v2.configurazione_tornello c
    on c.azienda_id = e.azienda_id
  where e.azienda_id = v_accesso.azienda_id
    and e.cliente_id = v_accesso.cliente_id
    and e.created_at >= now() - interval '2 minutes'
  order by e.created_at desc
  limit 1;

  return coalesce(v_result, '{}'::jsonb);
end;
$$;

grant execute
on function gestionale_v2.app_cliente_ultimo_benvenuto()
to authenticated;

commit;

notify pgrst, 'reload schema';
