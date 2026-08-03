begin;

-- ============================================================
-- IMMAGINI PRODOTTI
-- ============================================================

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'immagini-prodotti',
  'immagini-prodotti',
  true,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Il caricamento avviene dal gestionale interno con service role.
-- Il bucket è pubblico soltanto in lettura per consentire la
-- visualizzazione stabile delle immagini nel catalogo cliente.


-- ============================================================
-- RILEVAZIONI FISICHE / IMPEDENZIOMETRICHE
-- ============================================================

create table if not exists gestionale_v2.rilevazioni_fisiche_cliente (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  cliente_id uuid not null
    references gestionale_v2.clienti(id) on delete cascade,
  data_rilevazione date not null,
  ora_rilevazione time,
  origine text not null default 'gestionale'
    check (origine in ('gestionale', 'app_cliente')),
  peso_kg numeric(6,2) check (peso_kg > 0),
  altezza_cm numeric(6,2) check (altezza_cm > 0),
  massa_grassa_percentuale numeric(5,2)
    check (
      massa_grassa_percentuale is null
      or massa_grassa_percentuale between 0 and 100
    ),
  massa_muscolare_kg numeric(6,2)
    check (massa_muscolare_kg is null or massa_muscolare_kg >= 0),
  massa_magra_kg numeric(6,2)
    check (massa_magra_kg is null or massa_magra_kg >= 0),
  acqua_percentuale numeric(5,2)
    check (
      acqua_percentuale is null
      or acqua_percentuale between 0 and 100
    ),
  grasso_viscerale numeric(6,2)
    check (grasso_viscerale is null or grasso_viscerale >= 0),
  massa_ossea_kg numeric(6,2)
    check (massa_ossea_kg is null or massa_ossea_kg >= 0),
  metabolismo_basale_kcal integer
    check (
      metabolismo_basale_kcal is null
      or metabolismo_basale_kcal > 0
    ),
  eta_metabolica integer
    check (eta_metabolica is null or eta_metabolica > 0),
  circonferenza_vita_cm numeric(6,2)
    check (
      circonferenza_vita_cm is null
      or circonferenza_vita_cm > 0
    ),
  circonferenza_fianchi_cm numeric(6,2)
    check (
      circonferenza_fianchi_cm is null
      or circonferenza_fianchi_cm > 0
    ),
  circonferenza_torace_cm numeric(6,2)
    check (
      circonferenza_torace_cm is null
      or circonferenza_torace_cm > 0
    ),
  circonferenza_braccio_cm numeric(6,2)
    check (
      circonferenza_braccio_cm is null
      or circonferenza_braccio_cm > 0
    ),
  circonferenza_coscia_cm numeric(6,2)
    check (
      circonferenza_coscia_cm is null
      or circonferenza_coscia_cm > 0
    ),
  pressione_sistolica integer
    check (
      pressione_sistolica is null
      or pressione_sistolica between 50 and 300
    ),
  pressione_diastolica integer
    check (
      pressione_diastolica is null
      or pressione_diastolica between 30 and 200
    ),
  frequenza_cardiaca integer
    check (
      frequenza_cardiaca is null
      or frequenza_cardiaca between 20 and 250
    ),
  note text,
  inserito_da uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_rilevazioni_cliente_data
on gestionale_v2.rilevazioni_fisiche_cliente (
  azienda_id,
  cliente_id,
  data_rilevazione desc,
  created_at desc
);

alter table gestionale_v2.rilevazioni_fisiche_cliente
enable row level security;

grant select, insert, update, delete
on gestionale_v2.rilevazioni_fisiche_cliente
to service_role;


create or replace view gestionale_v2.vista_rilevazioni_fisiche_cliente
with (security_invoker = false)
as
select
  r.id as rilevazione_id,
  r.azienda_id,
  r.cliente_id,
  concat(c.cognome, ' ', c.nome) as cliente,
  r.data_rilevazione,
  r.ora_rilevazione,
  r.origine,
  r.peso_kg,
  r.altezza_cm,
  case
    when r.peso_kg is not null
      and r.altezza_cm is not null
      and r.altezza_cm > 0
    then round(
      r.peso_kg
      / power(r.altezza_cm / 100.0, 2),
      2
    )
    else null
  end as bmi,
  r.massa_grassa_percentuale,
  r.massa_muscolare_kg,
  r.massa_magra_kg,
  r.acqua_percentuale,
  r.grasso_viscerale,
  r.massa_ossea_kg,
  r.metabolismo_basale_kcal,
  r.eta_metabolica,
  r.circonferenza_vita_cm,
  r.circonferenza_fianchi_cm,
  r.circonferenza_torace_cm,
  r.circonferenza_braccio_cm,
  r.circonferenza_coscia_cm,
  r.pressione_sistolica,
  r.pressione_diastolica,
  r.frequenza_cardiaca,
  r.note,
  r.created_at,
  r.updated_at
from gestionale_v2.rilevazioni_fisiche_cliente r
join gestionale_v2.clienti c
  on c.id = r.cliente_id;

grant select
on gestionale_v2.vista_rilevazioni_fisiche_cliente
to service_role;


create or replace function gestionale_v2.salva_rilevazione_fisica_cliente(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := nullif(payload->>'rilevazione_id', '')::uuid;
  v_azienda_id uuid := (payload->>'azienda_id')::uuid;
  v_cliente_id uuid := (payload->>'cliente_id')::uuid;
  v_origine text := coalesce(
    nullif(payload->>'origine', ''),
    'gestionale'
  );
begin
  if v_origine not in ('gestionale', 'app_cliente') then
    raise exception 'Origine rilevazione non valida';
  end if;

  if not exists (
    select 1
    from gestionale_v2.clienti c
    where c.id = v_cliente_id
      and c.azienda_id = v_azienda_id
  ) then
    raise exception 'Cliente non trovato';
  end if;

  if v_id is null then
    insert into gestionale_v2.rilevazioni_fisiche_cliente (
      azienda_id,
      cliente_id,
      data_rilevazione,
      ora_rilevazione,
      origine,
      peso_kg,
      altezza_cm,
      massa_grassa_percentuale,
      massa_muscolare_kg,
      massa_magra_kg,
      acqua_percentuale,
      grasso_viscerale,
      massa_ossea_kg,
      metabolismo_basale_kcal,
      eta_metabolica,
      circonferenza_vita_cm,
      circonferenza_fianchi_cm,
      circonferenza_torace_cm,
      circonferenza_braccio_cm,
      circonferenza_coscia_cm,
      pressione_sistolica,
      pressione_diastolica,
      frequenza_cardiaca,
      note,
      inserito_da
    )
    values (
      v_azienda_id,
      v_cliente_id,
      (payload->>'data_rilevazione')::date,
      nullif(payload->>'ora_rilevazione', '')::time,
      v_origine,
      nullif(payload->>'peso_kg', '')::numeric,
      nullif(payload->>'altezza_cm', '')::numeric,
      nullif(payload->>'massa_grassa_percentuale', '')::numeric,
      nullif(payload->>'massa_muscolare_kg', '')::numeric,
      nullif(payload->>'massa_magra_kg', '')::numeric,
      nullif(payload->>'acqua_percentuale', '')::numeric,
      nullif(payload->>'grasso_viscerale', '')::numeric,
      nullif(payload->>'massa_ossea_kg', '')::numeric,
      nullif(payload->>'metabolismo_basale_kcal', '')::integer,
      nullif(payload->>'eta_metabolica', '')::integer,
      nullif(payload->>'circonferenza_vita_cm', '')::numeric,
      nullif(payload->>'circonferenza_fianchi_cm', '')::numeric,
      nullif(payload->>'circonferenza_torace_cm', '')::numeric,
      nullif(payload->>'circonferenza_braccio_cm', '')::numeric,
      nullif(payload->>'circonferenza_coscia_cm', '')::numeric,
      nullif(payload->>'pressione_sistolica', '')::integer,
      nullif(payload->>'pressione_diastolica', '')::integer,
      nullif(payload->>'frequenza_cardiaca', '')::integer,
      nullif(trim(payload->>'note'), ''),
      nullif(payload->>'utente_id', '')::uuid
    )
    returning id into v_id;
  else
    update gestionale_v2.rilevazioni_fisiche_cliente
    set
      data_rilevazione = (payload->>'data_rilevazione')::date,
      ora_rilevazione =
        nullif(payload->>'ora_rilevazione', '')::time,
      peso_kg = nullif(payload->>'peso_kg', '')::numeric,
      altezza_cm = nullif(payload->>'altezza_cm', '')::numeric,
      massa_grassa_percentuale =
        nullif(payload->>'massa_grassa_percentuale', '')::numeric,
      massa_muscolare_kg =
        nullif(payload->>'massa_muscolare_kg', '')::numeric,
      massa_magra_kg =
        nullif(payload->>'massa_magra_kg', '')::numeric,
      acqua_percentuale =
        nullif(payload->>'acqua_percentuale', '')::numeric,
      grasso_viscerale =
        nullif(payload->>'grasso_viscerale', '')::numeric,
      massa_ossea_kg =
        nullif(payload->>'massa_ossea_kg', '')::numeric,
      metabolismo_basale_kcal =
        nullif(payload->>'metabolismo_basale_kcal', '')::integer,
      eta_metabolica =
        nullif(payload->>'eta_metabolica', '')::integer,
      circonferenza_vita_cm =
        nullif(payload->>'circonferenza_vita_cm', '')::numeric,
      circonferenza_fianchi_cm =
        nullif(payload->>'circonferenza_fianchi_cm', '')::numeric,
      circonferenza_torace_cm =
        nullif(payload->>'circonferenza_torace_cm', '')::numeric,
      circonferenza_braccio_cm =
        nullif(payload->>'circonferenza_braccio_cm', '')::numeric,
      circonferenza_coscia_cm =
        nullif(payload->>'circonferenza_coscia_cm', '')::numeric,
      pressione_sistolica =
        nullif(payload->>'pressione_sistolica', '')::integer,
      pressione_diastolica =
        nullif(payload->>'pressione_diastolica', '')::integer,
      frequenza_cardiaca =
        nullif(payload->>'frequenza_cardiaca', '')::integer,
      note = nullif(trim(payload->>'note'), ''),
      updated_at = now()
    where id = v_id
      and azienda_id = v_azienda_id
      and cliente_id = v_cliente_id;

    if not found then
      raise exception 'Rilevazione non trovata';
    end if;
  end if;

  return jsonb_build_object(
    'rilevazione_id', v_id
  );
end;
$$;

grant execute
on function gestionale_v2.salva_rilevazione_fisica_cliente(jsonb)
to service_role;


create or replace function gestionale_v2.elimina_rilevazione_fisica_cliente(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := (payload->>'rilevazione_id')::uuid;
begin
  delete from gestionale_v2.rilevazioni_fisiche_cliente
  where id = v_id
    and azienda_id = (payload->>'azienda_id')::uuid
    and cliente_id = (payload->>'cliente_id')::uuid;

  if not found then
    raise exception 'Rilevazione non trovata';
  end if;

  return jsonb_build_object(
    'rilevazione_id', v_id,
    'eliminata', true
  );
end;
$$;

grant execute
on function gestionale_v2.elimina_rilevazione_fisica_cliente(jsonb)
to service_role;


-- ============================================================
-- APP CLIENTE: LETTURA E INSERIMENTO NELLO STESSO ARCHIVIO
-- ============================================================

create or replace function gestionale_v2.app_cliente_rilevazioni_fisiche()
returns table (
  rilevazione_id uuid,
  data_rilevazione date,
  ora_rilevazione time,
  origine text,
  peso_kg numeric,
  altezza_cm numeric,
  bmi numeric,
  massa_grassa_percentuale numeric,
  massa_muscolare_kg numeric,
  massa_magra_kg numeric,
  acqua_percentuale numeric,
  grasso_viscerale numeric,
  massa_ossea_kg numeric,
  metabolismo_basale_kcal integer,
  eta_metabolica integer,
  circonferenza_vita_cm numeric,
  circonferenza_fianchi_cm numeric,
  circonferenza_torace_cm numeric,
  circonferenza_braccio_cm numeric,
  circonferenza_coscia_cm numeric,
  pressione_sistolica integer,
  pressione_diastolica integer,
  frequenza_cardiaca integer,
  note text,
  created_at timestamptz
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
    v.rilevazione_id,
    v.data_rilevazione,
    v.ora_rilevazione,
    v.origine,
    v.peso_kg,
    v.altezza_cm,
    v.bmi,
    v.massa_grassa_percentuale,
    v.massa_muscolare_kg,
    v.massa_magra_kg,
    v.acqua_percentuale,
    v.grasso_viscerale,
    v.massa_ossea_kg,
    v.metabolismo_basale_kcal,
    v.eta_metabolica,
    v.circonferenza_vita_cm,
    v.circonferenza_fianchi_cm,
    v.circonferenza_torace_cm,
    v.circonferenza_braccio_cm,
    v.circonferenza_coscia_cm,
    v.pressione_sistolica,
    v.pressione_diastolica,
    v.frequenza_cardiaca,
    v.note,
    v.created_at
  from gestionale_v2.vista_rilevazioni_fisiche_cliente v
  where v.azienda_id = v_accesso.azienda_id
    and v.cliente_id = v_accesso.cliente_id
  order by v.data_rilevazione desc, v.created_at desc;
end;
$$;

grant execute
on function gestionale_v2.app_cliente_rilevazioni_fisiche()
to authenticated;


create or replace function gestionale_v2.app_cliente_salva_rilevazione_fisica(
  payload jsonb
)
returns jsonb
language plpgsql
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

  return gestionale_v2.salva_rilevazione_fisica_cliente(
    payload
    || jsonb_build_object(
      'azienda_id', v_accesso.azienda_id,
      'cliente_id', v_accesso.cliente_id,
      'origine', 'app_cliente',
      'utente_id', auth.uid()
    )
  );
end;
$$;

grant execute
on function gestionale_v2.app_cliente_salva_rilevazione_fisica(jsonb)
to authenticated;

commit;

notify pgrst, 'reload schema';
