begin;

-- ============================================================
-- 1) MODELLO ABBONAMENTI: TEMPO vs LEZIONI
-- ============================================================

alter table gestionale_v2.pacchetti
  add column if not exists tipo_consumo text,
  add column if not exists max_lezioni_settimanali integer,
  add column if not exists recuperi_gestione text;

update gestionale_v2.pacchetti
set tipo_consumo = case
  when modalita_lezioni = 'Pacchetto lezioni' then 'lezioni'
  else 'tempo'
end
where tipo_consumo is null;

update gestionale_v2.pacchetti
set max_lezioni_settimanali = case
  when tipo_consumo = 'lezioni' then
    greatest(coalesce(nullif(lezioni_per_periodo, 0), 5), 1)
  else
    greatest(coalesce(nullif(lezioni_per_periodo, 0), 3), 1)
end
where max_lezioni_settimanali is null
   or max_lezioni_settimanali <= 0;

update gestionale_v2.pacchetti
set recuperi_gestione = 'operatore'
where recuperi_gestione is null;

alter table gestionale_v2.pacchetti
  alter column tipo_consumo set default 'tempo',
  alter column tipo_consumo set not null,
  alter column max_lezioni_settimanali set default 3,
  alter column max_lezioni_settimanali set not null,
  alter column recuperi_gestione set default 'operatore',
  alter column recuperi_gestione set not null;

alter table gestionale_v2.pacchetti
  drop constraint if exists pacchetti_tipo_consumo_check;

alter table gestionale_v2.pacchetti
  add constraint pacchetti_tipo_consumo_check
  check (tipo_consumo in ('tempo', 'lezioni'));

alter table gestionale_v2.pacchetti
  drop constraint if exists pacchetti_recuperi_gestione_check;

alter table gestionale_v2.pacchetti
  add constraint pacchetti_recuperi_gestione_check
  check (recuperi_gestione in ('operatore'));

alter table gestionale_v2.pacchetti
  drop constraint if exists pacchetti_max_lezioni_settimanali_check;

alter table gestionale_v2.pacchetti
  add constraint pacchetti_max_lezioni_settimanali_check
  check (max_lezioni_settimanali > 0);

-- Allineamento esplicito dei pacchetti KREO a tempo.
update gestionale_v2.pacchetti
set
  tipo_consumo = 'tempo',
  modalita_lezioni = 'Settimanale',
  max_lezioni_settimanali = coalesce(
    nullif(max_lezioni_settimanali, 0),
    3
  ),
  lezioni_per_periodo = coalesce(
    nullif(max_lezioni_settimanali, 0),
    3
  ),
  lezioni_totali = 0,
  lezioni_standard = 0,
  senza_scadenza = false,
  recuperi_gestione = 'operatore',
  consuma_lezione = false
where upper(trim(nome)) in (
  'VIP',
  'LUXURY',
  'GOLD',
  'COACHING IN SEDE'
);

-- Pacchetti a lezioni: nessuna scadenza temporale e max 5/settimana
-- come default operativo; il campo resta modificabile da catalogo.
update gestionale_v2.pacchetti
set
  tipo_consumo = 'lezioni',
  modalita_lezioni = 'Pacchetto lezioni',
  max_lezioni_settimanali = case
    when max_lezioni_settimanali is null
      or max_lezioni_settimanali <= 0
      or max_lezioni_settimanali = 3
    then 5
    else max_lezioni_settimanali
  end,
  lezioni_per_periodo = case
    when max_lezioni_settimanali is null
      or max_lezioni_settimanali <= 0
      or max_lezioni_settimanali = 3
    then 5
    else max_lezioni_settimanali
  end,
  senza_scadenza = true,
  consuma_lezione = true
where modalita_lezioni = 'Pacchetto lezioni'
   or upper(trim(nome)) like '%PERSONALIZZAT%'
   or upper(trim(nome)) like '%LEZION%';


-- ============================================================
-- RECUPERI AUTORIZZATI DALL'OPERATORE
-- Sono extra quota settimanale per gli abbonamenti A TEMPO.
-- Non diventano un monte lezioni permanente.
-- ============================================================

create table if not exists gestionale_v2.recuperi_settimanali (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  cliente_id uuid not null
    references gestionale_v2.clienti(id) on delete cascade,
  abbonamento_id uuid not null
    references gestionale_v2.abbonamenti(id) on delete cascade,
  settimana_origine date,
  settimana_destinazione date not null,
  quantita integer not null default 1 check (quantita > 0),
  motivo text not null,
  attivo boolean not null default true,
  created_by uuid,
  created_at timestamptz not null default now(),
  annullato_il timestamptz,
  motivo_annullamento text
);

create index if not exists idx_recuperi_settimanali_lookup
on gestionale_v2.recuperi_settimanali (
  azienda_id,
  abbonamento_id,
  settimana_destinazione
)
where attivo = true;

grant select, insert, update
on gestionale_v2.recuperi_settimanali
to service_role;


create or replace function gestionale_v2.registra_recupero_settimanale(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_abbonamento_id uuid := (payload->>'abbonamento_id')::uuid;
  v_azienda_id uuid := (payload->>'azienda_id')::uuid;
  v_cliente_id uuid;
  v_tipo_consumo text;
  v_settimana date;
  v_id uuid;
begin
  select a.cliente_id, pac.tipo_consumo
  into v_cliente_id, v_tipo_consumo
  from gestionale_v2.abbonamenti a
  join gestionale_v2.pacchetti pac
    on pac.id = a.pacchetto_id
  where a.id = v_abbonamento_id
    and a.azienda_id = v_azienda_id;

  if v_cliente_id is null then
    raise exception 'Abbonamento non trovato';
  end if;

  if v_tipo_consumo <> 'tempo' then
    raise exception 'I recuperi settimanali si applicano solo agli abbonamenti a tempo';
  end if;

  if nullif(trim(payload->>'motivo'), '') is null then
    raise exception 'Motivazione recupero obbligatoria';
  end if;

  v_settimana := date_trunc(
    'week',
    (payload->>'settimana_destinazione')::date
  )::date;

  insert into gestionale_v2.recuperi_settimanali (
    azienda_id,
    cliente_id,
    abbonamento_id,
    settimana_origine,
    settimana_destinazione,
    quantita,
    motivo,
    created_by
  )
  values (
    v_azienda_id,
    v_cliente_id,
    v_abbonamento_id,
    case
      when nullif(payload->>'settimana_origine', '') is null
      then null
      else date_trunc(
        'week',
        (payload->>'settimana_origine')::date
      )::date
    end,
    v_settimana,
    greatest(coalesce((payload->>'quantita')::integer, 1), 1),
    trim(payload->>'motivo'),
    nullif(payload->>'utente_id', '')::uuid
  )
  returning id into v_id;

  return jsonb_build_object(
    'recupero_id', v_id,
    'settimana_destinazione', v_settimana
  );
end;
$$;

grant execute
on function gestionale_v2.registra_recupero_settimanale(jsonb)
to service_role;


create or replace function gestionale_v2.elenco_recuperi_abbonamento(
  p_abbonamento_id uuid
)
returns setof gestionale_v2.recuperi_settimanali
language sql
stable
security definer
set search_path = gestionale_v2, public
as $$
  select r.*
  from gestionale_v2.recuperi_settimanali r
  where r.abbonamento_id = p_abbonamento_id
  order by r.settimana_destinazione desc, r.created_at desc;
$$;

grant execute
on function gestionale_v2.elenco_recuperi_abbonamento(uuid)
to service_role;


-- ============================================================
-- PACCHETTI: salvataggio con due soli motori contrattuali.
-- Manteniamo modalita_lezioni per compatibilità con PWA e viste legacy.
-- ============================================================

create or replace function gestionale_v2.salva_pacchetto(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_tipo text := coalesce(
    nullif(payload->>'tipo_consumo', ''),
    case
      when payload->>'modalita_lezioni' = 'Pacchetto lezioni'
      then 'lezioni'
      else 'tempo'
    end
  );
  v_total integer := coalesce((payload->>'lezioni_totali')::integer, 0);
  v_max_week integer := greatest(
    coalesce(
      (payload->>'max_lezioni_settimanali')::integer,
      case when v_tipo = 'lezioni' then 5 else 3 end
    ),
    1
  );
  v_duration integer := greatest(
    coalesce((payload->>'durata_numero')::integer, 1),
    1
  );
begin
  v_id := nullif(payload->>'pacchetto_id', '')::uuid;

  if nullif(trim(payload->>'nome'), '') is null then
    raise exception 'Nome pacchetto obbligatorio';
  end if;

  if v_tipo not in ('tempo', 'lezioni') then
    raise exception 'Tipo consumo non valido';
  end if;

  if v_tipo = 'lezioni' and v_total <= 0 then
    raise exception 'Il numero totale di lezioni deve essere maggiore di zero';
  end if;

  if v_id is null then
    insert into gestionale_v2.pacchetti (
      azienda_id,
      nome,
      periodicita,
      prezzo_standard,
      durata_numero,
      durata_unita,
      modalita_lezioni,
      lezioni_per_periodo,
      lezioni_totali,
      lezioni_standard,
      senza_scadenza,
      tipo_consumo,
      max_lezioni_settimanali,
      recuperi_gestione,
      consuma_lezione,
      attivo
    )
    values (
      (payload->>'azienda_id')::uuid,
      trim(payload->>'nome'),
      payload->>'periodicita',
      coalesce((payload->>'prezzo_standard')::numeric, 0),
      v_duration,
      'mesi',
      case when v_tipo = 'lezioni'
        then 'Pacchetto lezioni'
        else 'Settimanale'
      end,
      v_max_week,
      case when v_tipo = 'lezioni' then v_total else 0 end,
      case when v_tipo = 'lezioni' then v_total else 0 end,
      v_tipo = 'lezioni',
      v_tipo,
      v_max_week,
      'operatore',
      v_tipo = 'lezioni',
      coalesce((payload->>'attivo')::boolean, true)
    )
    returning id into v_id;
  else
    update gestionale_v2.pacchetti
    set
      nome = trim(payload->>'nome'),
      periodicita = payload->>'periodicita',
      prezzo_standard = coalesce((payload->>'prezzo_standard')::numeric, 0),
      durata_numero = v_duration,
      durata_unita = 'mesi',
      modalita_lezioni = case when v_tipo = 'lezioni'
        then 'Pacchetto lezioni'
        else 'Settimanale'
      end,
      lezioni_per_periodo = v_max_week,
      lezioni_totali = case when v_tipo = 'lezioni' then v_total else 0 end,
      lezioni_standard = case when v_tipo = 'lezioni' then v_total else 0 end,
      senza_scadenza = v_tipo = 'lezioni',
      tipo_consumo = v_tipo,
      max_lezioni_settimanali = v_max_week,
      recuperi_gestione = 'operatore',
      consuma_lezione = v_tipo = 'lezioni',
      attivo = coalesce((payload->>'attivo')::boolean, true),
      updated_at = now()
    where id = v_id
      and azienda_id = (payload->>'azienda_id')::uuid;

    if not found then
      raise exception 'Pacchetto non trovato';
    end if;
  end if;

  return jsonb_build_object('pacchetto_id', v_id);
end;
$$;

grant execute
on function gestionale_v2.salva_pacchetto(jsonb)
to service_role;


-- ============================================================
-- LEZIONI CONTRATTUALI
-- A TEMPO: nessun monte lezioni.
-- A LEZIONI: monte pari al pacchetto acquistato.
-- ============================================================

create or replace function gestionale_v2.calcola_lezioni_contrattuali(
  p_pacchetto_id uuid,
  p_data_inizio date,
  p_data_fine date
)
returns integer
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_tipo text;
  v_totale integer;
begin
  select
    p.tipo_consumo,
    coalesce(p.lezioni_totali, 0)
  into
    v_tipo,
    v_totale
  from gestionale_v2.pacchetti p
  where p.id = p_pacchetto_id;

  if v_tipo is null then
    raise exception 'Pacchetto non trovato';
  end if;

  if v_tipo = 'lezioni' then
    return v_totale;
  end if;

  if p_data_fine is null then
    raise exception 'Gli abbonamenti a tempo richiedono una data fine';
  end if;

  if p_data_fine < p_data_inizio then
    raise exception 'La data fine precede la data inizio';
  end if;

  return 0;
end;
$$;


create or replace function gestionale_v2.calcola_lezioni_contrattuali_rpc(
  payload jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_lessons integer;
begin
  v_lessons := gestionale_v2.calcola_lezioni_contrattuali(
    (payload->>'pacchetto_id')::uuid,
    (payload->>'data_inizio')::date,
    nullif(payload->>'data_fine', '')::date
  );

  return jsonb_build_object(
    'lezioni_contrattuali',
    v_lessons
  );
end;
$$;

grant execute
on function gestionale_v2.calcola_lezioni_contrattuali_rpc(jsonb)
to service_role;


-- Gli abbonamenti a tempo esistenti non devono più esporre un monte.
update gestionale_v2.abbonamenti a
set
  lezioni_iniziali = 0,
  updated_at = now()
from gestionale_v2.pacchetti p
where p.id = a.pacchetto_id
  and p.tipo_consumo = 'tempo'
  and a.lezioni_iniziali <> 0;


-- ============================================================
-- SALDO LEZIONI: significativo solo per tipo_consumo=lezioni.
-- ============================================================

create or replace view gestionale_v2.vista_saldi_lezioni
with (security_invoker = false)
as
select
  a.azienda_id,
  a.id as abbonamento_id,
  a.cliente_id,
  a.lezioni_iniziali,
  coalesce(
    sum(m.quantita) filter (where m.stato = 'valido'),
    0
  )::integer as movimenti_lezioni_netto,
  case
    when p.tipo_consumo = 'lezioni' then
      (
        a.lezioni_iniziali
        + coalesce(
            sum(m.quantita) filter (where m.stato = 'valido'),
            0
          )
      )::integer
    else 0
  end as saldo_lezioni
from gestionale_v2.abbonamenti a
join gestionale_v2.pacchetti p
  on p.id = a.pacchetto_id
left join gestionale_v2.movimenti_lezioni m
  on m.abbonamento_id = a.id
group by
  a.azienda_id,
  a.id,
  a.cliente_id,
  a.lezioni_iniziali,
  p.tipo_consumo;

grant select
on gestionale_v2.vista_saldi_lezioni
to service_role;


-- ============================================================
-- DISPONIBILITÀ UNICA
-- Per entrambi i motori il periodo organizzativo è settimanale.
-- TEMPO: limite base + recuperi autorizzati, nessun saldo.
-- LEZIONI: max settimanale + saldo residuo.
-- ============================================================

create or replace view gestionale_v2.vista_disponibilita_lezioni
with (security_invoker = false)
as
with base as (
  select
    a.azienda_id,
    a.id as abbonamento_id,
    a.cliente_id,
    a.pacchetto_id,
    p.nome as pacchetto,
    a.data_inizio,
    a.data_fine_prevista,
    a.stato,
    p.modalita_lezioni,
    p.tipo_consumo,
    p.max_lezioni_settimanali,
    a.lezioni_iniziali,
    date_trunc('week', current_date)::date as periodo_inizio,
    (date_trunc('week', current_date)::date + 6) as periodo_fine
  from gestionale_v2.abbonamenti a
  join gestionale_v2.pacchetti p
    on p.id = a.pacchetto_id
),
pren as (
  select
    b.abbonamento_id,
    count(*) filter (
      where pr.stato <> 'annullata'
        and pr.data_prenotazione between b.periodo_inizio and b.periodo_fine
    )::integer as prenotate_periodo,
    count(*) filter (
      where pr.stato = 'presente'
    )::integer as presenze_totali
  from base b
  left join gestionale_v2.prenotazioni pr
    on pr.abbonamento_id = b.abbonamento_id
  group by b.abbonamento_id
),
rec as (
  select
    b.abbonamento_id,
    coalesce(sum(r.quantita) filter (
      where r.attivo
        and r.settimana_destinazione = b.periodo_inizio
    ), 0)::integer as recuperi_autorizzati
  from base b
  left join gestionale_v2.recuperi_settimanali r
    on r.abbonamento_id = b.abbonamento_id
  group by b.abbonamento_id
),
mov as (
  select
    b.abbonamento_id,
    coalesce(sum(m.quantita) filter (
      where m.stato = 'valido'
    ), 0)::integer as movimenti_netto
  from base b
  left join gestionale_v2.movimenti_lezioni m
    on m.abbonamento_id = b.abbonamento_id
  group by b.abbonamento_id
)
select
  b.azienda_id,
  b.abbonamento_id,
  b.cliente_id,
  b.pacchetto_id,
  b.pacchetto,
  b.data_inizio,
  b.data_fine_prevista,
  b.stato,
  b.modalita_lezioni,

  (
    b.stato not in (
      'terminato',
      'chiuso_anticipatamente',
      'annullato'
    )
    and b.data_inizio <= current_date
    and (
      (b.tipo_consumo = 'tempo'
        and b.data_fine_prevista >= current_date)
      or
      (b.tipo_consumo = 'lezioni'
        and (
          b.lezioni_iniziali
          + coalesce(m.movimenti_netto, 0)
        ) > 0)
    )
  ) as corrente,

  b.periodo_inizio,
  b.periodo_fine,

  (
    b.max_lezioni_settimanali
    + case
      when b.tipo_consumo = 'tempo'
      then coalesce(r.recuperi_autorizzati, 0)
      else 0
    end
  )::integer as quota_periodo,

  coalesce(p.prenotate_periodo, 0)::integer as utilizzate_periodo,

  greatest(
    (
      b.max_lezioni_settimanali
      + case
        when b.tipo_consumo = 'tempo'
        then coalesce(r.recuperi_autorizzati, 0)
        else 0
      end
    )
    - coalesce(p.prenotate_periodo, 0),
    0
  )::integer as disponibili_periodo,

  case
    when b.tipo_consumo = 'lezioni'
    then b.lezioni_iniziali
    else 0
  end::integer as lezioni_contrattuali,

  coalesce(p.presenze_totali, 0)::integer as presenze_totali,

  case
    when b.tipo_consumo = 'lezioni'
    then (
      b.lezioni_iniziali
      + coalesce(m.movimenti_netto, 0)
    )
    else null
  end::integer as saldo_complessivo,

  case
    when b.tipo_consumo = 'tempo' then
      greatest(
        (
          b.max_lezioni_settimanali
          + coalesce(r.recuperi_autorizzati, 0)
        )
        - coalesce(p.prenotate_periodo, 0),
        0
      )::text
      || ' prenotabili su '
      || (
        b.max_lezioni_settimanali
        + coalesce(r.recuperi_autorizzati, 0)
      )::text
      || ' questa settimana'
    else
      (
        b.lezioni_iniziali
        + coalesce(m.movimenti_netto, 0)
      )::text
      || ' lezioni residue · max '
      || b.max_lezioni_settimanali::text
      || '/settimana'
  end as disponibilita_principale,

  case
    when b.tipo_consumo = 'tempo' then
      'Abbonamento a tempo · nessun monte lezioni'
      || case
        when coalesce(r.recuperi_autorizzati, 0) > 0
        then ' · recuperi autorizzati: '
          || r.recuperi_autorizzati::text
        else ''
      end
    else
      coalesce(p.presenze_totali, 0)::text
      || ' lezioni effettuate'
  end as disponibilita_secondaria,

  -- Nuovi campi, aggiunti in coda per compatibilità con la view esistente.
  b.tipo_consumo,
  b.max_lezioni_settimanali,
  coalesce(r.recuperi_autorizzati, 0)::integer
    as recuperi_autorizzati_periodo

from base b
left join pren p on p.abbonamento_id = b.abbonamento_id
left join rec r on r.abbonamento_id = b.abbonamento_id
left join mov m on m.abbonamento_id = b.abbonamento_id;
grant select
on gestionale_v2.vista_disponibilita_lezioni
to service_role;


-- ============================================================
-- LIMITE SETTIMANALE SULLE PRENOTAZIONI
-- Unico controllo per Reception e App Cliente.
-- ============================================================

create or replace function gestionale_v2.controlla_prenotazione_settimanale()
returns trigger
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_tipo text;
  v_max integer;
  v_extra integer := 0;
  v_usate integer := 0;
  v_week date;
  v_end date;
begin
  if new.abbonamento_id is null
     or new.stato = 'annullata' then
    return new;
  end if;

  select
    pac.tipo_consumo,
    pac.max_lezioni_settimanali
  into
    v_tipo,
    v_max
  from gestionale_v2.abbonamenti a
  join gestionale_v2.pacchetti pac
    on pac.id = a.pacchetto_id
  where a.id = new.abbonamento_id;

  if v_tipo is null then
    return new;
  end if;

  v_week := date_trunc('week', new.data_prenotazione)::date;
  v_end := v_week + 6;

  if v_tipo = 'tempo' then
    select coalesce(sum(r.quantita), 0)::integer
    into v_extra
    from gestionale_v2.recuperi_settimanali r
    where r.abbonamento_id = new.abbonamento_id
      and r.attivo
      and r.settimana_destinazione = v_week;
  end if;

  select count(*)::integer
  into v_usate
  from gestionale_v2.prenotazioni p
  where p.abbonamento_id = new.abbonamento_id
    and p.data_prenotazione between v_week and v_end
    and p.stato <> 'annullata'
    and p.id <> coalesce(new.id, gen_random_uuid());

  if v_usate >= (v_max + v_extra) then
    raise exception
      'Limite settimanale raggiunto: % lezioni%s',
      v_max,
      case
        when v_extra > 0
        then ' + ' || v_extra::text || ' recuperi autorizzati'
        else ''
      end;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_prenotazione_limite_settimanale
on gestionale_v2.prenotazioni;

create trigger trg_prenotazione_limite_settimanale
before insert or update of
  data_prenotazione,
  abbonamento_id,
  stato
on gestionale_v2.prenotazioni
for each row
execute function gestionale_v2.controlla_prenotazione_settimanale();


-- Il vecchio trigger sui movimenti non deve più governare il limite.
drop trigger if exists trg_limite_settimanale_lezioni
on gestionale_v2.movimenti_lezioni;


-- ============================================================
-- PRESENZA:
-- A TEMPO: nessuno scalaggio.
-- A LEZIONI: -1.
-- ============================================================

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
  v_cliente_id uuid;
  v_abbonamento_id uuid;
  v_tipologia text;
  v_data date;
  v_tipo_consumo text;
  v_delta integer := 0;
  v_booking_net integer := 0;
  v_saldo integer;
  v_movement_id uuid;
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

  select
    p.stato,
    to_jsonb(p),
    p.cliente_id,
    p.abbonamento_id,
    p.tipologia,
    p.data_prenotazione
  into
    v_old_state,
    v_before,
    v_cliente_id,
    v_abbonamento_id,
    v_tipologia,
    v_data
  from gestionale_v2.prenotazioni p
  where p.id = v_id
    and p.azienda_id = v_azienda_id;

  if v_before is null then
    raise exception 'Prenotazione non trovata';
  end if;

  if v_old_state = v_new_state then
    return jsonb_build_object(
      'prenotazione_id', v_id,
      'stato', v_new_state,
      'movimento_lezioni', 0
    );
  end if;

  if v_abbonamento_id is not null then
    select pac.tipo_consumo
    into v_tipo_consumo
    from gestionale_v2.abbonamenti a
    join gestionale_v2.pacchetti pac
      on pac.id = a.pacchetto_id
    where a.id = v_abbonamento_id;

    select coalesce(sum(m.quantita), 0)
    into v_booking_net
    from gestionale_v2.movimenti_lezioni m
    where m.prenotazione_id = v_id
      and m.stato = 'valido';
  end if;

  if v_old_state <> 'presente'
     and v_new_state = 'presente'
     and v_abbonamento_id is not null
     and v_tipo_consumo = 'lezioni' then

    if lower(trim(coalesce(v_tipologia, ''))) in (
      'lezione',
      'lezione ordinaria',
      'recupero',
      'lezione extra'
    ) then
      v_delta := -1;
    end if;

    if v_delta < 0 then
      select saldo_lezioni
      into v_saldo
      from gestionale_v2.vista_saldi_lezioni
      where abbonamento_id = v_abbonamento_id
        and azienda_id = v_azienda_id;

      if coalesce(v_saldo, 0) < abs(v_delta) then
        raise exception 'Nessuna lezione disponibile';
      end if;

      insert into gestionale_v2.movimenti_lezioni (
        azienda_id,
        cliente_id,
        abbonamento_id,
        prenotazione_id,
        data_movimento,
        tipo,
        quantita,
        causale,
        stato
      )
      values (
        v_azienda_id,
        v_cliente_id,
        v_abbonamento_id,
        v_id,
        v_data,
        'Presenza',
        v_delta,
        'Presenza: ' || coalesce(v_tipologia, 'Lezione'),
        'valido'
      )
      returning id into v_movement_id;
    end if;

  elsif v_old_state = 'presente'
        and v_new_state <> 'presente'
        and v_abbonamento_id is not null
        and v_booking_net <> 0 then

    v_delta := -v_booking_net;

    insert into gestionale_v2.movimenti_lezioni (
      azienda_id,
      cliente_id,
      abbonamento_id,
      prenotazione_id,
      data_movimento,
      tipo,
      quantita,
      causale,
      stato
    )
    values (
      v_azienda_id,
      v_cliente_id,
      v_abbonamento_id,
      v_id,
      current_date,
      'Storno presenza',
      v_delta,
      'Storno per cambio stato prenotazione',
      'valido'
    )
    returning id into v_movement_id;
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
    and azienda_id = v_azienda_id
  returning to_jsonb(prenotazioni.*)
  into v_after;

  return jsonb_build_object(
    'prenotazione_id', v_id,
    'stato', v_new_state,
    'movimento_lezioni', v_delta,
    'movimento_id', v_movement_id,
    'tipo_consumo', v_tipo_consumo
  );
end;
$$;

grant execute
on function gestionale_v2.cambia_stato_prenotazione(jsonb)
to service_role;


-- ============================================================
-- VISTA ABBONAMENTI OPERATIVA
-- Espone tipo consumo e limite settimanale.
-- ============================================================

create or replace view gestionale_v2.vista_abbonamenti_operativa
with (security_invoker = false)
as
select
  a.azienda_id,
  a.id as abbonamento_id,
  a.cliente_id,
  a.pacchetto_id,
  a.abbonamento_precedente_id,
  c.cognome || ' ' || c.nome as cliente,
  p.nome as pacchetto,
  a.data_inizio,
  coalesce(a.data_fine_prevista, date '9999-12-31')
    as data_fine_prevista,
  a.prezzo_concordato,
  a.lezioni_iniziali,
  a.tipologia_pagamento,
  a.stato,
  a.note,
  a.motivo_stato,
  a.data_sospensione,
  a.fine_sospensione_prevista,
  a.data_riattivazione,
  a.data_chiusura,
  coalesce(
    sum(i.importo) filter (where i.stato = 'valido'),
    0
  )::numeric(12,2) as pagato,
  greatest(
    a.prezzo_concordato
    - coalesce(
        sum(i.importo) filter (where i.stato = 'valido'),
        0
      ),
    0
  )::numeric(12,2) as residuo,
  nr.data_scadenza as prossima_rata_data,
  nr.residuo_rata::numeric(12,2) as prossima_rata_importo,
  case
    when a.stato = 'sospeso' then 'Sospeso'
    when a.stato = 'terminato' then 'Terminato'
    when a.stato = 'chiuso_anticipatamente' then 'Chiuso anticipatamente'
    when a.stato = 'annullato' then 'Annullato'
    when a.data_inizio > current_date then 'Da attivare'
    when p.tipo_consumo = 'lezioni'
      and coalesce(sl.saldo_lezioni, a.lezioni_iniziali) <= 0
      then 'Terminato'
    when p.tipo_consumo = 'tempo'
      and a.data_fine_prevista < current_date
      then 'Scaduto'
    when p.tipo_consumo = 'tempo'
      and a.data_fine_prevista <= current_date + 15
      then 'In scadenza'
    else 'Attivo'
  end as stato_visuale,
  coalesce(sl.movimenti_lezioni_netto, 0)
    as movimenti_lezioni_netto,
  case
    when p.tipo_consumo = 'lezioni'
    then coalesce(sl.saldo_lezioni, a.lezioni_iniziali)
    else null
  end as saldo_lezioni,
  p.senza_scadenza,
  a.data_fine_prevista as data_fine_reale,
  p.tipo_consumo,
  p.max_lezioni_settimanali,
  p.recuperi_gestione
from gestionale_v2.abbonamenti a
join gestionale_v2.clienti c
  on c.id = a.cliente_id
join gestionale_v2.pacchetti p
  on p.id = a.pacchetto_id
left join gestionale_v2.incassi i
  on i.abbonamento_id = a.id
left join gestionale_v2.vista_saldi_lezioni sl
  on sl.abbonamento_id = a.id
left join lateral (
  select
    vr.data_scadenza,
    vr.residuo_rata
  from gestionale_v2.vista_rate_operativa vr
  where vr.abbonamento_id = a.id
    and vr.residuo_rata > 0
  order by vr.data_scadenza, vr.numero_rata
  limit 1
) nr on true
group by
  a.azienda_id,
  a.id,
  a.cliente_id,
  a.pacchetto_id,
  a.abbonamento_precedente_id,
  c.cognome,
  c.nome,
  p.nome,
  p.senza_scadenza,
  p.tipo_consumo,
  p.max_lezioni_settimanali,
  p.recuperi_gestione,
  sl.movimenti_lezioni_netto,
  sl.saldo_lezioni,
  nr.data_scadenza,
  nr.residuo_rata;

grant select
on gestionale_v2.vista_abbonamenti_operativa
to service_role;



-- ============================================================
-- MOTORE ACCESSO CLIENTE ADEGUATO AL NUOVO MODELLO
-- Regole ON:
-- - cliente attivo
-- - abbonamento valido
-- - nessuna rata scaduta con residuo
-- - certificato valido
-- - prenotazione odierna
-- - per pacchetti a lezioni: saldo > 0
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
  v_tipo_consumo text;
  v_saldo integer;
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
    v.stato,
    v.tipo_consumo,
    v.saldo_lezioni
  into
    v_abbonamento_id,
    v_abbonamento_stato,
    v_tipo_consumo,
    v_saldo
  from gestionale_v2.vista_abbonamenti_operativa v
  where v.azienda_id = p_azienda_id
    and v.cliente_id = p_cliente_id
    and v.stato not in (
      'terminato',
      'chiuso_anticipatamente',
      'annullato'
    )
    and v.data_inizio <= current_date
    and (
      (v.tipo_consumo = 'tempo'
       and v.data_fine_reale >= current_date)
      or
      (v.tipo_consumo = 'lezioni'
       and coalesce(v.saldo_lezioni, 0) > 0)
    )
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

  if v_tipo_consumo = 'lezioni'
     and coalesce(v_saldo, 0) <= 0 then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Lezioni terminate',
      'cliente', v_cliente_nome,
      'abbonamento_id', v_abbonamento_id
    );
  end if;

  if exists (
    select 1
    from gestionale_v2.vista_rate_operativa r
    where r.abbonamento_id = v_abbonamento_id
      and r.data_scadenza < current_date
      and coalesce(r.residuo_rata, 0) > 0
  ) then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Pagamento scaduto',
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
    'prenotazione_id', v_prenotazione_id,
    'tipo_consumo', v_tipo_consumo
  );
end;
$$;

grant execute
on function gestionale_v2.valuta_accesso_cliente_tornello(uuid, uuid)
to service_role;


-- ============================================================
-- 2) INTERRUTTORE GENERALE REGOLE TORNELLO
-- OFF = badge KREO attivo/mappato entra; le regole amministrative
-- vengono calcolate solo a titolo informativo.
-- ============================================================

create table if not exists gestionale_v2.configurazione_tornello (
  azienda_id uuid primary key
    references gestionale_v2.aziende(id) on delete cascade,
  regole_accesso_attive boolean not null default true,
  motivo_modalita_libera text,
  modificato_da uuid,
  modificato_il timestamptz not null default now()
);

insert into gestionale_v2.configurazione_tornello (
  azienda_id,
  regole_accesso_attive
)
select a.id, true
from gestionale_v2.aziende a
on conflict (azienda_id) do nothing;

grant select, insert, update
on gestionale_v2.configurazione_tornello
to service_role;


create or replace function gestionale_v2.imposta_regole_accesso_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_attive boolean := coalesce(
    (payload->>'regole_accesso_attive')::boolean,
    true
  );
begin
  insert into gestionale_v2.configurazione_tornello (
    azienda_id,
    regole_accesso_attive,
    motivo_modalita_libera,
    modificato_da,
    modificato_il
  )
  values (
    v_azienda,
    v_attive,
    case
      when v_attive then null
      else coalesce(
        nullif(trim(payload->>'motivo'), ''),
        'Modalità libera attivata da operatore'
      )
    end,
    nullif(payload->>'utente_id', '')::uuid,
    now()
  )
  on conflict (azienda_id)
  do update set
    regole_accesso_attive = excluded.regole_accesso_attive,
    motivo_modalita_libera = excluded.motivo_modalita_libera,
    modificato_da = excluded.modificato_da,
    modificato_il = now();

  return jsonb_build_object(
    'regole_accesso_attive', v_attive
  );
end;
$$;

grant execute
on function gestionale_v2.imposta_regole_accesso_tornello(jsonb)
to service_role;


create or replace function gestionale_v2.get_configurazione_tornello(
  p_azienda_id uuid
)
returns jsonb
language sql
stable
security definer
set search_path = gestionale_v2, public
as $$
  select to_jsonb(c)
  from gestionale_v2.configurazione_tornello c
  where c.azienda_id = p_azienda_id;
$$;

grant execute
on function gestionale_v2.get_configurazione_tornello(uuid)
to service_role;


-- Aggiorniamo il motore canonico senza duplicare la logica cliente.
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

  v_regole_attive boolean := true;
  v_motivo_libero text;
  v_regola_teorica text;
begin
  if v_code is null or v_code = '' then
    raise exception 'Codice tornello mancante';
  end if;

  if v_modalita not in ('shadow', 'attivo') then
    raise exception 'Modalità tornello non valida';
  end if;

  select
    c.regole_accesso_attive,
    c.motivo_modalita_libera
  into
    v_regole_attive,
    v_motivo_libero
  from gestionale_v2.configurazione_tornello c
  where c.azienda_id = v_azienda;

  v_regole_attive := coalesce(v_regole_attive, true);

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

    insert into gestionale_v2.eventi_tornello_kreo (
      azienda_id, modalita, codice_tornello, tipo_badge,
      badge_staff_id, identita, decisione_kreo, motivo,
      perfectgym_idsocio, mappatura_appresa
    )
    values (
      v_azienda, v_modalita, v_code, v_tipo,
      v_staff.id, v_identita, v_decisione, v_motivo,
      v_idsocio, v_mappatura
    )
    returning id into v_evento_id;

    return jsonb_build_object(
      'evento_id', v_evento_id,
      'decisione_kreo', v_decisione,
      'motivo', v_motivo,
      'tipo_badge', v_tipo,
      'identita', v_identita,
      'regole_accesso_attive', v_regole_attive,
      'shadow_mode', v_modalita = 'shadow'
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
    v_motivo := 'Codice tornello non associato a un badge KREO attivo';

    insert into gestionale_v2.eventi_tornello_kreo (
      azienda_id, modalita, codice_tornello,
      decisione_kreo, motivo, perfectgym_idsocio,
      mappatura_appresa
    )
    values (
      v_azienda, v_modalita, v_code,
      v_decisione, v_motivo, v_idsocio,
      v_mappatura
    )
    returning id into v_evento_id;

    return jsonb_build_object(
      'evento_id', v_evento_id,
      'decisione_kreo', v_decisione,
      'motivo', v_motivo,
      'regole_accesso_attive', v_regole_attive,
      'shadow_mode', v_modalita = 'shadow'
    );
  end if;

  v_cliente_id := v_badge.cliente_id;

  select trim(c.cognome || ' ' || c.nome)
  into v_cliente_nome
  from gestionale_v2.clienti c
  where c.id = v_cliente_id;

  -- Calcoliamo sempre la regola teorica per audit.
  v_eval := gestionale_v2.valuta_accesso_cliente_tornello(
    v_azienda,
    v_cliente_id
  );
  v_regola_teorica := coalesce(
    nullif(v_eval->>'motivo', ''),
    'Decisione teorica non disponibile'
  );

  if not v_regole_attive then
    v_decisione := 'consentito';
    v_motivo := 'MODALITÀ LIBERA - controlli accesso globalmente disattivati'
      || case
        when nullif(v_motivo_libero, '') is not null
        then ' · ' || v_motivo_libero
        else ''
      end
      || ' · Regola teorica: ' || v_regola_teorica;
    v_tipo := 'cliente';
    v_identita := coalesce(v_cliente_nome, 'Cliente KREO');
    v_prenotazione_id := null;

  else
    if coalesce((v_eval->>'consentito')::boolean, false) then
      v_decisione := 'consentito';
    else
      v_decisione := 'negato';
    end if;

    v_motivo := v_regola_teorica;
    v_tipo := 'cliente';
    v_identita := coalesce(v_eval->>'cliente', v_cliente_nome);
    v_prenotazione_id := nullif(v_eval->>'prenotazione_id', '')::uuid;
  end if;

  insert into gestionale_v2.eventi_tornello_kreo (
    azienda_id, modalita, codice_tornello, tipo_badge,
    badge_cliente_id, cliente_id, identita,
    decisione_kreo, motivo, perfectgym_idsocio,
    mappatura_appresa, prenotazione_id
  )
  values (
    v_azienda, v_modalita, v_code, v_tipo,
    v_badge.id, v_cliente_id, v_identita,
    v_decisione, v_motivo, v_idsocio,
    v_mappatura, v_prenotazione_id
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
    'regole_accesso_attive', v_regole_attive,
    'regola_teorica', v_regola_teorica,
    'shadow_mode', v_modalita = 'shadow'
  );
end;
$$;

grant execute
on function gestionale_v2.valuta_evento_tornello_kreo(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
