begin;

-- ============================================================
-- KREO TORNELLO - MOTORE CANONICO
-- Unica logica per shadow e active.
-- Nessuna regola PerfectGym entra nella decisione KREO.
-- ============================================================

create table if not exists gestionale_v2.eventi_tornello_kreo (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  modalita text not null default 'shadow'
    check (modalita in ('shadow', 'attivo')),
  codice_tornello text not null,
  tipo_badge text
    check (tipo_badge is null or tipo_badge in ('cliente', 'staff')),
  badge_cliente_id uuid,
  badge_staff_id uuid,
  cliente_id uuid,
  identita text,
  decisione_kreo text not null
    check (decisione_kreo in ('consentito', 'negato', 'non_mappato')),
  motivo text not null,
  perfectgym_idsocio text,
  mappatura_appresa boolean not null default false,
  prenotazione_id uuid,
  apertura_richiesta boolean not null default false,
  apertura_eseguita boolean,
  risposta_controller text,
  errore_apertura text,
  presenza_registrata boolean,
  errore_presenza text,
  shadow_event_id uuid unique,
  created_at timestamptz not null default now(),
  apertura_il timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists idx_eventi_tornello_kreo_recenti
on gestionale_v2.eventi_tornello_kreo (
  azienda_id,
  created_at desc
);

create index if not exists idx_eventi_tornello_kreo_badge
on gestionale_v2.eventi_tornello_kreo (
  azienda_id,
  codice_tornello,
  created_at desc
);

grant select, insert, update
on gestionale_v2.eventi_tornello_kreo
to service_role;


-- Importa lo storico shadow esistente una sola volta.
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
  perfectgym_idsocio,
  mappatura_appresa,
  shadow_event_id,
  created_at,
  updated_at
)
select
  s.azienda_id,
  'shadow',
  s.codice_tornello,
  s.tipo_badge,
  s.badge_cliente_id,
  s.badge_staff_id,
  s.cliente_id,
  s.identita,
  s.decisione_kreo,
  s.motivo,
  s.perfectgym_idsocio,
  s.mappatura_appresa,
  s.id,
  s.created_at,
  s.created_at
from gestionale_v2.eventi_tornello_shadow s
where not exists (
  select 1
  from gestionale_v2.eventi_tornello_kreo k
  where k.shadow_event_id = s.id
);


-- ============================================================
-- VALUTAZIONE CLIENTE: funzione pura, senza scalaggi.
-- ============================================================

create or replace function gestionale_v2.valuta_accesso_cliente_tornello(
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
on function gestionale_v2.valuta_accesso_cliente_tornello(uuid, uuid)
to service_role;


-- Compatibilità: la vecchia funzione shadow usa il motore canonico.
create or replace function gestionale_v2.valuta_accesso_cliente_shadow(
  p_azienda_id uuid,
  p_cliente_id uuid
)
returns jsonb
language sql
stable
security definer
set search_path = gestionale_v2, public
as $$
  select gestionale_v2.valuta_accesso_cliente_tornello(
    p_azienda_id,
    p_cliente_id
  );
$$;

grant execute
on function gestionale_v2.valuta_accesso_cliente_shadow(uuid, uuid)
to service_role;


-- ============================================================
-- MOTORE UNICO EVENTO TORNELLO
-- Identifica staff/cliente, apprende legacy, decide e registra.
-- Non apre il tornello: l'apertura è responsabilità dell'Agent locale.
-- ============================================================

create or replace function gestionale_v2.valuta_evento_tornello_kreo(
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
  v_modalita text := coalesce(nullif(trim(payload->>'modalita'), ''), 'shadow');

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
  v_prenotazione_id uuid;
  v_evento_id uuid;
begin
  if v_code is null or v_code = '' then
    raise exception 'Codice tornello mancante';
  end if;

  if v_modalita not in ('shadow', 'attivo') then
    raise exception 'Modalità tornello non valida';
  end if;

  -- IDSocio serve solo per apprendere la mappatura di badge legacy.
  -- Non influenza mai CONSENTI/NEGA.
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

  -- STAFF: badge attivo = accesso sempre consentito.
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

    insert into gestionale_v2.eventi_tornello_kreo (
      azienda_id,
      modalita,
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
      v_modalita,
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
      'shadow_mode', v_modalita = 'shadow'
    );
  end if;

  -- CLIENTE
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

    insert into gestionale_v2.eventi_tornello_kreo (
      azienda_id,
      modalita,
      codice_tornello,
      decisione_kreo,
      motivo,
      perfectgym_idsocio,
      mappatura_appresa
    )
    values (
      v_azienda,
      v_modalita,
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
      'shadow_mode', v_modalita = 'shadow'
    );
  end if;

  v_cliente_id := v_badge.cliente_id;

  select trim(c.cognome || ' ' || c.nome)
  into v_cliente_nome
  from gestionale_v2.clienti c
  where c.id = v_cliente_id;

  v_eval := gestionale_v2.valuta_accesso_cliente_tornello(
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
  v_prenotazione_id := nullif(v_eval->>'prenotazione_id', '')::uuid;

  insert into gestionale_v2.eventi_tornello_kreo (
    azienda_id,
    modalita,
    codice_tornello,
    tipo_badge,
    badge_cliente_id,
    cliente_id,
    identita,
    decisione_kreo,
    motivo,
    perfectgym_idsocio,
    mappatura_appresa,
    prenotazione_id
  )
  values (
    v_azienda,
    v_modalita,
    v_code,
    v_tipo,
    v_badge.id,
    v_cliente_id,
    v_identita,
    v_decisione,
    v_motivo,
    v_idsocio,
    v_mappatura,
    v_prenotazione_id
  )
  returning id into v_evento_id;

  return jsonb_build_object(
    'evento_id', v_evento_id,
    'decisione_kreo', v_decisione,
    'motivo', v_motivo,
    'tipo_badge', v_tipo,
    'identita', v_identita,
    'cliente_id', v_cliente_id,
    'prenotazione_id', v_prenotazione_id,
    'shadow_mode', v_modalita = 'shadow'
  );
end;
$$;

grant execute
on function gestionale_v2.valuta_evento_tornello_kreo(jsonb)
to service_role;


-- ============================================================
-- ESITO FISICO DELL'APERTURA
-- Solo DOPO conferma del controller:
-- - aggiorna audit;
-- - per cliente marca la prenotazione "presente";
-- - usa la RPC centrale già esistente, quindi lo scalaggio lezioni
--   resta nella logica unica di cambia_stato_prenotazione.
-- ============================================================

create or replace function gestionale_v2.registra_esito_apertura_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_evento gestionale_v2.eventi_tornello_kreo;
  v_success boolean := coalesce((payload->>'successo')::boolean, false);
  v_presence_ok boolean;
  v_presence_error text;
begin
  select *
  into v_evento
  from gestionale_v2.eventi_tornello_kreo
  where id = (payload->>'evento_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid
  for update;

  if v_evento.id is null then
    raise exception 'Evento tornello non trovato';
  end if;

  update gestionale_v2.eventi_tornello_kreo
  set
    apertura_richiesta = true,
    apertura_eseguita = v_success,
    risposta_controller = nullif(payload->>'risposta_controller', ''),
    errore_apertura = case
      when v_success then null
      else coalesce(
        nullif(payload->>'errore_apertura', ''),
        'Apertura non confermata'
      )
    end,
    apertura_il = case when v_success then now() else apertura_il end,
    updated_at = now()
  where id = v_evento.id;

  if v_success
     and v_evento.tipo_badge = 'cliente'
     and v_evento.prenotazione_id is not null then
    begin
      perform gestionale_v2.cambia_stato_prenotazione(
        jsonb_build_object(
          'azienda_id', v_evento.azienda_id,
          'prenotazione_id', v_evento.prenotazione_id,
          'stato', 'presente'
        )
      );
      v_presence_ok := true;
      v_presence_error := null;
    exception when others then
      v_presence_ok := false;
      v_presence_error := sqlerrm;
    end;

    update gestionale_v2.eventi_tornello_kreo
    set
      presenza_registrata = v_presence_ok,
      errore_presenza = v_presence_error,
      updated_at = now()
    where id = v_evento.id;
  end if;

  return jsonb_build_object(
    'evento_id', v_evento.id,
    'apertura_eseguita', v_success,
    'presenza_registrata', v_presence_ok,
    'errore_presenza', v_presence_error
  );
end;
$$;

grant execute
on function gestionale_v2.registra_esito_apertura_tornello(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
