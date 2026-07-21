begin;

create extension if not exists pgcrypto;

create table if not exists gestionale_v2.badge_clienti (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  cliente_id uuid not null
    references gestionale_v2.clienti(id) on delete cascade,
  codice_badge text not null,
  attivo boolean not null default true,
  assegnato_il timestamptz not null default now(),
  disattivato_il timestamptz,
  motivo_disattivazione text,
  note text,
  created_at timestamptz not null default now()
);

create unique index if not exists uq_badge_attivo_codice
  on gestionale_v2.badge_clienti(azienda_id, codice_badge)
  where attivo = true;

create index if not exists idx_badge_cliente
  on gestionale_v2.badge_clienti(azienda_id, cliente_id);

create table if not exists gestionale_v2.dispositivi_accesso (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  nome text not null,
  codice_dispositivo text not null unique,
  token_hash text not null,
  postazione text,
  tipo_collegamento text not null default 'keyboard_wedge',
  attivo boolean not null default true,
  ultimo_contatto timestamptz,
  versione_bridge text,
  created_at timestamptz not null default now()
);

create table if not exists gestionale_v2.accessi (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  cliente_id uuid
    references gestionale_v2.clienti(id) on delete set null,
  badge_id uuid
    references gestionale_v2.badge_clienti(id) on delete set null,
  dispositivo_id uuid
    references gestionale_v2.dispositivi_accesso(id) on delete set null,
  abbonamento_id uuid
    references gestionale_v2.abbonamenti(id) on delete set null,
  prenotazione_id uuid
    references gestionale_v2.prenotazioni(id) on delete set null,
  movimento_lezione_id uuid
    references gestionale_v2.movimenti_lezioni(id) on delete set null,
  codice_badge_letto text,
  data_accesso date not null default current_date,
  ora_accesso time not null default localtime,
  esito text not null,
  messaggio text,
  motivazione text,
  accesso_manuale boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_accessi_data
  on gestionale_v2.accessi(
    azienda_id,
    data_accesso,
    ora_accesso
  );

alter table gestionale_v2.badge_clienti enable row level security;
alter table gestionale_v2.dispositivi_accesso enable row level security;
alter table gestionale_v2.accessi enable row level security;

grant select, insert, update, delete
on
  gestionale_v2.badge_clienti,
  gestionale_v2.dispositivi_accesso,
  gestionale_v2.accessi
to service_role;

create or replace function gestionale_v2.associa_badge_cliente(
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
  v_cliente_id uuid;
  v_codice text;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_codice := trim(payload->>'codice_badge');

  if v_codice = '' then
    raise exception 'Codice badge obbligatorio';
  end if;

  if not exists (
    select 1
    from gestionale_v2.clienti c
    where c.id = v_cliente_id
      and c.azienda_id = v_azienda_id
      and c.stato = 'attivo'
  ) then
    raise exception 'Cliente non attivo o non trovato';
  end if;

  update gestionale_v2.badge_clienti
  set
    attivo = false,
    disattivato_il = now(),
    motivo_disattivazione = 'Sostituito da nuovo badge'
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id
    and attivo = true;

  if exists (
    select 1
    from gestionale_v2.badge_clienti b
    where b.azienda_id = v_azienda_id
      and b.codice_badge = v_codice
      and b.attivo = true
  ) then
    raise exception 'Badge già associato a un altro cliente';
  end if;

  insert into gestionale_v2.badge_clienti (
    azienda_id,
    cliente_id,
    codice_badge,
    note
  )
  values (
    v_azienda_id,
    v_cliente_id,
    v_codice,
    nullif(payload->>'note', '')
  )
  returning id into v_id;

  return jsonb_build_object('badge_id', v_id);
end;
$$;

create or replace function gestionale_v2.cambia_stato_badge(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_attivo boolean;
begin
  v_id := (payload->>'badge_id')::uuid;
  v_attivo := (payload->>'attivo')::boolean;

  update gestionale_v2.badge_clienti
  set
    attivo = v_attivo,
    disattivato_il = case when v_attivo then null else now() end,
    motivo_disattivazione = case
      when v_attivo then null
      else nullif(payload->>'motivo', '')
    end
  where id = v_id
    and azienda_id = (payload->>'azienda_id')::uuid;

  if not found then
    raise exception 'Badge non trovato';
  end if;

  return jsonb_build_object(
    'badge_id', v_id,
    'attivo', v_attivo
  );
end;
$$;

create or replace function gestionale_v2.crea_dispositivo_accesso(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_token text;
  v_code text;
begin
  v_token := encode(gen_random_bytes(32), 'hex');
  v_code := 'DEV-' || upper(substr(encode(gen_random_bytes(8), 'hex'), 1, 12));

  insert into gestionale_v2.dispositivi_accesso (
    azienda_id,
    nome,
    codice_dispositivo,
    token_hash,
    postazione,
    tipo_collegamento
  )
  values (
    (payload->>'azienda_id')::uuid,
    payload->>'nome',
    v_code,
    crypt(v_token, gen_salt('bf')),
    nullif(payload->>'postazione', ''),
    coalesce(
      nullif(payload->>'tipo_collegamento', ''),
      'keyboard_wedge'
    )
  )
  returning id into v_id;

  return jsonb_build_object(
    'dispositivo_id', v_id,
    'codice_dispositivo', v_code,
    'token', v_token
  );
end;
$$;

create or replace function gestionale_v2.rigenera_token_dispositivo(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_token text;
begin
  v_token := encode(gen_random_bytes(32), 'hex');

  update gestionale_v2.dispositivi_accesso
  set token_hash = crypt(v_token, gen_salt('bf'))
  where id = (payload->>'dispositivo_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if not found then
    raise exception 'Dispositivo non trovato';
  end if;

  return jsonb_build_object('token', v_token);
end;
$$;

create or replace function gestionale_v2.verifica_certificato_cliente(
  p_cliente_id uuid
)
returns boolean
language sql
security definer
set search_path = gestionale_v2, public
as $$
  select exists (
    select 1
    from gestionale_v2.documenti_clienti d
    join gestionale_v2.tipi_documento t
      on t.id = d.tipo_documento_id
    where d.cliente_id = p_cliente_id
      and d.stato = 'valido'
      and lower(t.nome) like '%certificato%'
      and (
        d.data_scadenza is null
        or d.data_scadenza >= current_date
      )
  );
$$;

create or replace function gestionale_v2.processa_accesso_badge(
  p_codice_dispositivo text,
  p_token text,
  p_codice_badge text,
  p_versione_bridge text default null
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_device record;
  v_badge record;
  v_cliente record;
  v_subscription record;
  v_booking record;
  v_movement_id uuid;
  v_access_id uuid;
  v_message text;
  v_allowed boolean := false;
  v_certificate_ok boolean;
begin
  select *
  into v_device
  from gestionale_v2.dispositivi_accesso d
  where d.codice_dispositivo = p_codice_dispositivo
    and d.attivo = true
    and d.token_hash = crypt(p_token, d.token_hash);

  if v_device.id is null then
    return jsonb_build_object(
      'consentito', false,
      'azione_tornello', 'nega',
      'messaggio', 'Dispositivo non autorizzato'
    );
  end if;

  update gestionale_v2.dispositivi_accesso
  set
    ultimo_contatto = now(),
    versione_bridge = p_versione_bridge
  where id = v_device.id;

  select
    b.id,
    b.azienda_id,
    b.cliente_id
  into v_badge
  from gestionale_v2.badge_clienti b
  where b.azienda_id = v_device.azienda_id
    and b.codice_badge = trim(p_codice_badge)
    and b.attivo = true
  limit 1;

  if v_badge.id is null then
    v_message := 'Badge non riconosciuto';

    insert into gestionale_v2.accessi (
      azienda_id,
      dispositivo_id,
      codice_badge_letto,
      esito,
      messaggio
    )
    values (
      v_device.azienda_id,
      v_device.id,
      trim(p_codice_badge),
      'negato',
      v_message
    )
    returning id into v_access_id;

    return jsonb_build_object(
      'consentito', false,
      'azione_tornello', 'nega',
      'messaggio', v_message,
      'accesso_id', v_access_id
    );
  end if;

  select *
  into v_cliente
  from gestionale_v2.clienti c
  where c.id = v_badge.cliente_id
    and c.azienda_id = v_device.azienda_id;

  if v_cliente.stato <> 'attivo' then
    v_message := 'Cliente inattivo';
  else
    select v.*
    into v_subscription
    from gestionale_v2.vista_abbonamenti_operativa v
    where v.azienda_id = v_device.azienda_id
      and v.cliente_id = v_cliente.id
      and v.stato not in (
        'terminato',
        'chiuso_anticipatamente',
        'annullato'
      )
      and v.data_inizio <= current_date
      and v.data_fine_prevista >= current_date
    order by v.data_inizio desc
    limit 1;

    if v_subscription.abbonamento_id is null then
      v_message := 'Nessun abbonamento valido';
    elsif v_subscription.stato = 'sospeso' then
      v_message := 'Abbonamento sospeso';
    else
      v_certificate_ok :=
        gestionale_v2.verifica_certificato_cliente(v_cliente.id);

      if not v_certificate_ok then
        v_message := 'Certificato medico mancante o scaduto';
      else
        select p.*
        into v_booking
        from gestionale_v2.prenotazioni p
        where p.azienda_id = v_device.azienda_id
          and p.cliente_id = v_cliente.id
          and p.abbonamento_id = v_subscription.abbonamento_id
          and p.data_prenotazione = current_date
          and p.stato in ('prenotata', 'confermata')
        order by
          abs(
            extract(
              epoch from (
                p.ora_inizio
                - localtime
              )
            )
          )
        limit 1;

        if v_booking.id is not null then
          perform gestionale_v2.cambia_stato_prenotazione(
            jsonb_build_object(
              'azienda_id', v_device.azienda_id,
              'prenotazione_id', v_booking.id,
              'stato', 'presente',
              'motivo', 'Presenza da badge'
            )
          );

          select m.id
          into v_movement_id
          from gestionale_v2.movimenti_lezioni m
          where m.prenotazione_id = v_booking.id
          order by m.created_at desc
          limit 1;

          v_allowed := true;
          v_message := 'Accesso consentito e presenza registrata';
        else
          v_message := 'Nessuna prenotazione odierna';
        end if;
      end if;
    end if;
  end if;

  insert into gestionale_v2.accessi (
    azienda_id,
    cliente_id,
    badge_id,
    dispositivo_id,
    abbonamento_id,
    prenotazione_id,
    movimento_lezione_id,
    codice_badge_letto,
    esito,
    messaggio
  )
  values (
    v_device.azienda_id,
    v_cliente.id,
    v_badge.id,
    v_device.id,
    v_subscription.abbonamento_id,
    v_booking.id,
    v_movement_id,
    trim(p_codice_badge),
    case when v_allowed then 'consentito' else 'negato' end,
    v_message
  )
  returning id into v_access_id;

  return jsonb_build_object(
    'consentito', v_allowed,
    'azione_tornello',
      case when v_allowed then 'apri' else 'nega' end,
    'messaggio', v_message,
    'cliente',
      trim(v_cliente.cognome || ' ' || v_cliente.nome),
    'prenotazione_id', v_booking.id,
    'abbonamento_id', v_subscription.abbonamento_id,
    'movimento_lezione_id', v_movement_id,
    'accesso_id', v_access_id
  );
end;
$$;

create or replace function gestionale_v2.gestisci_accesso_manuale(
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
  v_modalita text;
  v_subscription record;
  v_booking record;
  v_movement_id uuid;
  v_access_id uuid;
  v_message text;
  v_allowed boolean := false;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_modalita := payload->>'modalita';

  if not exists (
    select 1
    from gestionale_v2.clienti c
    where c.id = v_cliente_id
      and c.azienda_id = v_azienda_id
      and c.stato = 'attivo'
  ) then
    raise exception 'Cliente non attivo';
  end if;

  select v.*
  into v_subscription
  from gestionale_v2.vista_abbonamenti_operativa v
  where v.azienda_id = v_azienda_id
    and v.cliente_id = v_cliente_id
    and v.stato not in (
      'terminato',
      'chiuso_anticipatamente',
      'annullato'
    )
    and v.data_inizio <= current_date
    and v.data_fine_prevista >= current_date
  order by v.data_inizio desc
  limit 1;

  if v_subscription.abbonamento_id is null then
    v_message := 'Nessun abbonamento valido';
  elsif v_modalita = 'Accesso senza scalare' then
    v_allowed := true;
    v_message := 'Accesso manuale senza scalare';
  elsif v_modalita = 'Accesso extra con scalare' then
    if v_subscription.saldo_lezioni <= 0 then
      v_message := 'Nessuna lezione disponibile';
    else
      insert into gestionale_v2.movimenti_lezioni (
        azienda_id,
        cliente_id,
        abbonamento_id,
        data_movimento,
        tipo,
        quantita,
        causale
      )
      values (
        v_azienda_id,
        v_cliente_id,
        v_subscription.abbonamento_id,
        current_date,
        'Accesso extra',
        -1,
        payload->>'motivazione'
      )
      returning id into v_movement_id;

      v_allowed := true;
      v_message := 'Accesso extra con lezione scalata';
    end if;
  else
    if not gestionale_v2.verifica_certificato_cliente(v_cliente_id) then
      v_message := 'Certificato medico mancante o scaduto';
    else
      select p.*
      into v_booking
      from gestionale_v2.prenotazioni p
      where p.azienda_id = v_azienda_id
        and p.cliente_id = v_cliente_id
        and p.abbonamento_id = v_subscription.abbonamento_id
        and p.data_prenotazione = current_date
        and p.stato in ('prenotata', 'confermata')
      order by p.ora_inizio
      limit 1;

      if v_booking.id is null then
        v_message := 'Nessuna prenotazione odierna';
      else
        perform gestionale_v2.cambia_stato_prenotazione(
          jsonb_build_object(
            'azienda_id', v_azienda_id,
            'prenotazione_id', v_booking.id,
            'stato', 'presente',
            'motivo', 'Presenza manuale'
          )
        );

        select m.id
        into v_movement_id
        from gestionale_v2.movimenti_lezioni m
        where m.prenotazione_id = v_booking.id
        order by m.created_at desc
        limit 1;

        v_allowed := true;
        v_message := 'Accesso consentito e presenza registrata';
      end if;
    end if;
  end if;

  insert into gestionale_v2.accessi (
    azienda_id,
    cliente_id,
    abbonamento_id,
    prenotazione_id,
    movimento_lezione_id,
    esito,
    messaggio,
    motivazione,
    accesso_manuale
  )
  values (
    v_azienda_id,
    v_cliente_id,
    v_subscription.abbonamento_id,
    v_booking.id,
    v_movement_id,
    case when v_allowed then 'consentito_manuale' else 'negato' end,
    v_message,
    nullif(payload->>'motivazione', ''),
    true
  )
  returning id into v_access_id;

  return jsonb_build_object(
    'consentito', v_allowed,
    'messaggio', v_message,
    'accesso_id', v_access_id,
    'movimento_lezione_id', v_movement_id
  );
end;
$$;

create or replace view gestionale_v2.vista_badge_operativa
with (security_invoker = false)
as
select
  b.azienda_id,
  b.id as badge_id,
  b.cliente_id,
  c.cognome || ' ' || c.nome as cliente,
  b.codice_badge,
  b.attivo,
  b.assegnato_il,
  b.disattivato_il,
  b.motivo_disattivazione,
  b.note
from gestionale_v2.badge_clienti b
join gestionale_v2.clienti c
  on c.id = b.cliente_id;

create or replace view gestionale_v2.vista_dispositivi_accesso
with (security_invoker = false)
as
select
  d.azienda_id,
  d.id as dispositivo_id,
  d.nome,
  d.codice_dispositivo,
  d.postazione,
  d.tipo_collegamento,
  d.attivo,
  d.ultimo_contatto,
  d.versione_bridge,
  d.created_at
from gestionale_v2.dispositivi_accesso d;

create or replace view gestionale_v2.vista_accessi_operativa
with (security_invoker = false)
as
select
  a.azienda_id,
  a.id as accesso_id,
  a.cliente_id,
  a.badge_id,
  a.dispositivo_id,
  a.abbonamento_id,
  a.prenotazione_id,
  a.movimento_lezione_id,
  case
    when c.id is null then null
    else c.cognome || ' ' || c.nome
  end as cliente,
  b.codice_badge,
  d.nome as dispositivo,
  a.data_accesso,
  a.ora_accesso,
  a.esito,
  a.messaggio,
  a.motivazione,
  a.accesso_manuale,
  a.created_at
from gestionale_v2.accessi a
left join gestionale_v2.clienti c
  on c.id = a.cliente_id
left join gestionale_v2.badge_clienti b
  on b.id = a.badge_id
left join gestionale_v2.dispositivi_accesso d
  on d.id = a.dispositivo_id;

grant execute
on function gestionale_v2.associa_badge_cliente(jsonb)
to service_role;

grant execute
on function gestionale_v2.cambia_stato_badge(jsonb)
to service_role;

grant execute
on function gestionale_v2.crea_dispositivo_accesso(jsonb)
to service_role;

grant execute
on function gestionale_v2.rigenera_token_dispositivo(jsonb)
to service_role;

grant execute
on function gestionale_v2.gestisci_accesso_manuale(jsonb)
to service_role;

grant execute
on function gestionale_v2.processa_accesso_badge(text, text, text, text)
to anon, authenticated, service_role;

grant select
on gestionale_v2.vista_badge_operativa
to service_role;

grant select
on gestionale_v2.vista_dispositivi_accesso
to service_role;

grant select
on gestionale_v2.vista_accessi_operativa
to service_role;

commit;

notify pgrst, 'reload schema';
