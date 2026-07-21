begin;

create table if not exists gestionale_v2.operatori_agenda (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  nome_visualizzato text not null,
  ruolo text,
  telefono text,
  colore_agenda text,
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  unique (azienda_id, nome_visualizzato)
);

create table if not exists gestionale_v2.prenotazioni (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  cliente_id uuid not null
    references gestionale_v2.clienti(id) on delete restrict,
  abbonamento_id uuid
    references gestionale_v2.abbonamenti(id) on delete set null,
  operatore_id uuid
    references gestionale_v2.operatori_agenda(id) on delete set null,
  data_prenotazione date not null,
  ora_inizio time not null,
  ora_fine time not null,
  tipologia text not null default 'Lezione ordinaria',
  stato text not null default 'prenotata'
    check (
      stato in (
        'prenotata',
        'confermata',
        'presente',
        'assente',
        'annullata'
      )
    ),
  note text,
  motivo_ultimo_stato text,
  annullata_il timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (ora_fine > ora_inizio)
);

create table if not exists gestionale_v2.eventi_prenotazione (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  prenotazione_id uuid not null
    references gestionale_v2.prenotazioni(id) on delete cascade,
  azione text not null,
  stato_precedente text,
  stato_successivo text,
  dati_precedenti jsonb,
  dati_successivi jsonb,
  motivo text,
  created_at timestamptz not null default now()
);

create index if not exists idx_prenotazioni_agenda
  on gestionale_v2.prenotazioni(
    azienda_id,
    data_prenotazione,
    ora_inizio
  );

create index if not exists idx_prenotazioni_operatore
  on gestionale_v2.prenotazioni(
    azienda_id,
    operatore_id,
    data_prenotazione
  );

alter table gestionale_v2.operatori_agenda enable row level security;
alter table gestionale_v2.prenotazioni enable row level security;
alter table gestionale_v2.eventi_prenotazione enable row level security;

grant select, insert, update, delete
on
  gestionale_v2.operatori_agenda,
  gestionale_v2.prenotazioni,
  gestionale_v2.eventi_prenotazione
to service_role;

create or replace function gestionale_v2.crea_operatore_agenda(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
begin
  if nullif(trim(payload->>'nome_visualizzato'), '') is null then
    raise exception 'Nome operatore obbligatorio';
  end if;

  insert into gestionale_v2.operatori_agenda (
    azienda_id,
    nome_visualizzato,
    ruolo,
    telefono,
    colore_agenda,
    attivo
  )
  values (
    (payload->>'azienda_id')::uuid,
    trim(payload->>'nome_visualizzato'),
    nullif(trim(payload->>'ruolo'), ''),
    nullif(trim(payload->>'telefono'), ''),
    nullif(trim(payload->>'colore_agenda'), ''),
    coalesce((payload->>'attivo')::boolean, true)
  )
  on conflict (azienda_id, nome_visualizzato)
  do update set
    ruolo = excluded.ruolo,
    telefono = excluded.telefono,
    attivo = true
  returning id into v_id;

  return jsonb_build_object('operatore_id', v_id);
end;
$$;

create or replace function gestionale_v2.crea_prenotazione(
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
  v_abbonamento_id uuid;
  v_operatore_id uuid;
  v_data date;
  v_inizio time;
  v_fine time;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_abbonamento_id :=
    nullif(payload->>'abbonamento_id', '')::uuid;
  v_operatore_id :=
    nullif(payload->>'operatore_id', '')::uuid;
  v_data := (payload->>'data_prenotazione')::date;
  v_inizio := (payload->>'ora_inizio')::time;
  v_fine := (payload->>'ora_fine')::time;

  if v_fine <= v_inizio then
    raise exception 'L''ora fine deve essere successiva all''ora inizio';
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

  if v_abbonamento_id is not null
     and not exists (
       select 1
       from gestionale_v2.abbonamenti a
       where a.id = v_abbonamento_id
         and a.cliente_id = v_cliente_id
         and a.azienda_id = v_azienda_id
         and a.stato not in (
           'terminato',
           'chiuso_anticipatamente',
           'annullato'
         )
     ) then
    raise exception 'Abbonamento non valido per il cliente';
  end if;

  if v_operatore_id is not null
     and exists (
       select 1
       from gestionale_v2.prenotazioni p
       where p.azienda_id = v_azienda_id
         and p.operatore_id = v_operatore_id
         and p.data_prenotazione = v_data
         and p.stato <> 'annullata'
         and p.ora_inizio < v_fine
         and p.ora_fine > v_inizio
     ) then
    raise exception 'Operatore già occupato nella fascia oraria';
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
    motivo_ultimo_stato
  )
  values (
    v_azienda_id,
    v_cliente_id,
    v_abbonamento_id,
    v_operatore_id,
    v_data,
    v_inizio,
    v_fine,
    coalesce(
      nullif(payload->>'tipologia', ''),
      'Lezione ordinaria'
    ),
    coalesce(
      nullif(payload->>'stato', ''),
      'prenotata'
    ),
    nullif(payload->>'note', ''),
    'Creazione prenotazione'
  )
  returning id into v_id;

  insert into gestionale_v2.eventi_prenotazione (
    azienda_id,
    prenotazione_id,
    azione,
    stato_successivo,
    dati_successivi,
    motivo
  )
  select
    v_azienda_id,
    v_id,
    'creazione',
    p.stato,
    to_jsonb(p),
    'Creazione prenotazione'
  from gestionale_v2.prenotazioni p
  where p.id = v_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo
  )
  values (
    v_azienda_id,
    'prenotazioni',
    v_id,
    'creazione',
    payload
  );

  return jsonb_build_object('prenotazione_id', v_id);
end;
$$;

create or replace function gestionale_v2.modifica_prenotazione(
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
  v_before jsonb;
  v_after jsonb;
  v_operatore_id uuid;
  v_data date;
  v_inizio time;
  v_fine time;
begin
  v_id := (payload->>'prenotazione_id')::uuid;
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_operatore_id :=
    nullif(payload->>'operatore_id', '')::uuid;
  v_data := (payload->>'data_prenotazione')::date;
  v_inizio := (payload->>'ora_inizio')::time;
  v_fine := (payload->>'ora_fine')::time;

  if v_fine <= v_inizio then
    raise exception 'L''ora fine deve essere successiva all''ora inizio';
  end if;

  select to_jsonb(p)
  into v_before
  from gestionale_v2.prenotazioni p
  where p.id = v_id
    and p.azienda_id = v_azienda_id;

  if v_before is null then
    raise exception 'Prenotazione non trovata';
  end if;

  if exists (
    select 1
    from gestionale_v2.prenotazioni p
    where p.azienda_id = v_azienda_id
      and p.operatore_id = v_operatore_id
      and p.data_prenotazione = v_data
      and p.id <> v_id
      and p.stato <> 'annullata'
      and p.ora_inizio < v_fine
      and p.ora_fine > v_inizio
  ) then
    raise exception 'Operatore già occupato nella fascia oraria';
  end if;

  update gestionale_v2.prenotazioni
  set
    operatore_id = v_operatore_id,
    data_prenotazione = v_data,
    ora_inizio = v_inizio,
    ora_fine = v_fine,
    tipologia = payload->>'tipologia',
    note = nullif(payload->>'note', ''),
    updated_at = now()
  where id = v_id
    and azienda_id = v_azienda_id;

  select to_jsonb(p)
  into v_after
  from gestionale_v2.prenotazioni p
  where p.id = v_id;

  insert into gestionale_v2.eventi_prenotazione (
    azienda_id,
    prenotazione_id,
    azione,
    stato_precedente,
    stato_successivo,
    dati_precedenti,
    dati_successivi,
    motivo
  )
  values (
    v_azienda_id,
    v_id,
    'modifica',
    v_before->>'stato',
    v_after->>'stato',
    v_before,
    v_after,
    'Modifica prenotazione'
  );

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    valore_successivo
  )
  values (
    v_azienda_id,
    'prenotazioni',
    v_id,
    'modifica',
    v_before,
    v_after
  );

  return jsonb_build_object('prenotazione_id', v_id);
end;
$$;

create or replace function gestionale_v2.cambia_stato_prenotazione(
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
  v_new_state text;
  v_old_state text;
  v_before jsonb;
  v_after jsonb;
begin
  v_id := (payload->>'prenotazione_id')::uuid;
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_new_state := payload->>'stato';

  if v_new_state not in (
    'prenotata',
    'confermata',
    'presente',
    'assente',
    'annullata'
  ) then
    raise exception 'Stato prenotazione non valido';
  end if;

  select p.stato, to_jsonb(p)
  into v_old_state, v_before
  from gestionale_v2.prenotazioni p
  where p.id = v_id
    and p.azienda_id = v_azienda_id;

  if v_before is null then
    raise exception 'Prenotazione non trovata';
  end if;

  update gestionale_v2.prenotazioni
  set
    stato = v_new_state,
    motivo_ultimo_stato = nullif(payload->>'motivo', ''),
    annullata_il = case
      when v_new_state = 'annullata' then now()
      else annullata_il
    end,
    updated_at = now()
  where id = v_id
    and azienda_id = v_azienda_id;

  select to_jsonb(p)
  into v_after
  from gestionale_v2.prenotazioni p
  where p.id = v_id;

  insert into gestionale_v2.eventi_prenotazione (
    azienda_id,
    prenotazione_id,
    azione,
    stato_precedente,
    stato_successivo,
    dati_precedenti,
    dati_successivi,
    motivo
  )
  values (
    v_azienda_id,
    v_id,
    'cambio_stato',
    v_old_state,
    v_new_state,
    v_before,
    v_after,
    nullif(payload->>'motivo', '')
  );

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    valore_successivo,
    motivo
  )
  values (
    v_azienda_id,
    'prenotazioni',
    v_id,
    'cambio_stato',
    v_before,
    v_after,
    nullif(payload->>'motivo', '')
  );

  return jsonb_build_object(
    'prenotazione_id', v_id,
    'stato', v_new_state
  );
end;
$$;

create or replace view gestionale_v2.vista_prenotazioni_operativa
with (security_invoker = false)
as
select
  p.azienda_id,
  p.id as prenotazione_id,
  p.cliente_id,
  p.abbonamento_id,
  p.operatore_id,
  c.cognome || ' ' || c.nome as cliente,
  pac.nome as pacchetto,
  oa.nome_visualizzato as operatore,
  p.data_prenotazione,
  p.ora_inizio,
  p.ora_fine,
  p.tipologia,
  p.stato,
  p.note,
  p.motivo_ultimo_stato,
  p.created_at,
  p.updated_at
from gestionale_v2.prenotazioni p
join gestionale_v2.clienti c
  on c.id = p.cliente_id
left join gestionale_v2.abbonamenti a
  on a.id = p.abbonamento_id
left join gestionale_v2.pacchetti pac
  on pac.id = a.pacchetto_id
left join gestionale_v2.operatori_agenda oa
  on oa.id = p.operatore_id;

grant execute
on function gestionale_v2.crea_operatore_agenda(jsonb)
to service_role;

grant execute
on function gestionale_v2.crea_prenotazione(jsonb)
to service_role;

grant execute
on function gestionale_v2.modifica_prenotazione(jsonb)
to service_role;

grant execute
on function gestionale_v2.cambia_stato_prenotazione(jsonb)
to service_role;

grant select
on gestionale_v2.vista_prenotazioni_operativa
to service_role;

commit;

notify pgrst, 'reload schema';
