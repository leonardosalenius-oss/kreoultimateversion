begin;

create table if not exists gestionale_v2.regole_spese_ricorrenti (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null references gestionale_v2.aziende(id) on delete restrict,
  fornitore_id uuid references gestionale_v2.fornitori(id) on delete set null,
  categoria_spesa_id uuid references gestionale_v2.categorie_spesa(id) on delete set null,
  descrizione text not null,
  imponibile numeric(12,2) not null default 0 check (imponibile >= 0),
  iva numeric(12,2) not null default 0 check (iva >= 0),
  totale numeric(12,2) not null check (totale > 0),
  intervallo_mesi integer not null default 1 check (intervallo_mesi between 1 and 60),
  data_inizio date not null,
  data_fine date not null,
  giorno_scadenza integer not null default 1 check (giorno_scadenza between 1 and 31),
  tipo_documento text,
  note text,
  stato text not null default 'attiva' check (stato in ('attiva','disattivata')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (data_fine >= data_inizio)
);

alter table gestionale_v2.spese
  add column if not exists regola_ricorrente_id uuid
    references gestionale_v2.regole_spese_ricorrenti(id) on delete restrict;

create unique index if not exists uq_spesa_ricorrente_competenza
  on gestionale_v2.spese(regola_ricorrente_id, competenza_mese)
  where regola_ricorrente_id is not null;

create index if not exists idx_regole_spese_ricorrenti_azienda
  on gestionale_v2.regole_spese_ricorrenti(azienda_id, stato, data_inizio, data_fine);

alter table gestionale_v2.regole_spese_ricorrenti enable row level security;

grant select, insert, update, delete
on gestionale_v2.regole_spese_ricorrenti
to service_role;

create or replace function gestionale_v2.genera_spese_ricorrenti(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_regola gestionale_v2.regole_spese_ricorrenti%rowtype;
  v_competenza date;
  v_fine_mese date;
  v_scadenza date;
  v_spesa_id uuid;
  v_generate integer := 0;
begin
  select *
  into v_regola
  from gestionale_v2.regole_spese_ricorrenti
  where id = (payload->>'regola_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid
  for update;

  if v_regola.id is null then
    raise exception 'Regola ricorrente non trovata';
  end if;

  if v_regola.stato <> 'attiva' then
    raise exception 'La regola ricorrente non è attiva';
  end if;

  v_competenza := date_trunc('month', v_regola.data_inizio)::date;

  while v_competenza <= date_trunc('month', v_regola.data_fine)::date loop
    if not exists (
      select 1
      from gestionale_v2.spese s
      where s.regola_ricorrente_id = v_regola.id
        and s.competenza_mese = v_competenza
    ) then
      v_fine_mese := (
        date_trunc('month', v_competenza)
        + interval '1 month'
        - interval '1 day'
      )::date;
      v_scadenza := make_date(
        extract(year from v_competenza)::integer,
        extract(month from v_competenza)::integer,
        least(v_regola.giorno_scadenza, extract(day from v_fine_mese)::integer)
      );

      insert into gestionale_v2.spese (
        azienda_id,
        categoria_spesa_id,
        fornitore_id,
        data_spesa,
        descrizione,
        importo,
        imponibile,
        iva,
        totale,
        tipo_documento,
        data_documento,
        competenza_mese,
        note,
        stato,
        regola_ricorrente_id
      )
      values (
        v_regola.azienda_id,
        v_regola.categoria_spesa_id,
        v_regola.fornitore_id,
        v_competenza,
        v_regola.descrizione,
        v_regola.totale,
        v_regola.imponibile,
        v_regola.iva,
        v_regola.totale,
        coalesce(v_regola.tipo_documento, 'Costo ricorrente'),
        v_scadenza,
        v_competenza,
        v_regola.note,
        'registrata',
        v_regola.id
      )
      returning id into v_spesa_id;

      insert into gestionale_v2.scadenze_spesa (
        azienda_id,
        spesa_id,
        numero_scadenza,
        data_scadenza,
        importo_previsto
      )
      values (
        v_regola.azienda_id,
        v_spesa_id,
        1,
        v_scadenza,
        v_regola.totale
      );

      v_generate := v_generate + 1;
    end if;

    v_competenza := (
      v_competenza
      + make_interval(months => v_regola.intervallo_mesi)
    )::date;
  end loop;

  return jsonb_build_object(
    'regola_id', v_regola.id,
    'spese_generate', v_generate
  );
end;
$$;

create or replace function gestionale_v2.crea_regola_spesa_ricorrente(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_result jsonb;
begin
  if nullif(trim(payload->>'descrizione'), '') is null then
    raise exception 'Descrizione obbligatoria';
  end if;

  if (payload->>'totale')::numeric <= 0 then
    raise exception 'Il totale deve essere maggiore di zero';
  end if;

  if (payload->>'data_fine')::date < (payload->>'data_inizio')::date then
    raise exception 'Periodo ricorrente non valido';
  end if;

  insert into gestionale_v2.regole_spese_ricorrenti (
    azienda_id,
    fornitore_id,
    categoria_spesa_id,
    descrizione,
    imponibile,
    iva,
    totale,
    intervallo_mesi,
    data_inizio,
    data_fine,
    giorno_scadenza,
    tipo_documento,
    note,
    stato
  )
  values (
    (payload->>'azienda_id')::uuid,
    nullif(payload->>'fornitore_id', '')::uuid,
    nullif(payload->>'categoria_spesa_id', '')::uuid,
    trim(payload->>'descrizione'),
    coalesce((payload->>'imponibile')::numeric, 0),
    coalesce((payload->>'iva')::numeric, 0),
    (payload->>'totale')::numeric,
    coalesce((payload->>'intervallo_mesi')::integer, 1),
    (payload->>'data_inizio')::date,
    (payload->>'data_fine')::date,
    coalesce((payload->>'giorno_scadenza')::integer, 1),
    nullif(payload->>'tipo_documento', ''),
    nullif(payload->>'note', ''),
    'attiva'
  )
  returning id into v_id;

  v_result := gestionale_v2.genera_spese_ricorrenti(
    jsonb_build_object(
      'azienda_id', payload->>'azienda_id',
      'regola_id', v_id
    )
  );

  return jsonb_build_object(
    'regola_id', v_id,
    'spese_generate', coalesce((v_result->>'spese_generate')::integer, 0)
  );
end;
$$;

create or replace function gestionale_v2.cambia_stato_regola_spesa_ricorrente(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_stato text;
begin
  v_id := (payload->>'regola_id')::uuid;
  v_stato := payload->>'stato';

  if v_stato not in ('attiva','disattivata') then
    raise exception 'Stato regola non valido';
  end if;

  update gestionale_v2.regole_spese_ricorrenti
  set stato = v_stato,
      updated_at = now()
  where id = v_id
    and azienda_id = (payload->>'azienda_id')::uuid;

  if not found then
    raise exception 'Regola ricorrente non trovata';
  end if;

  return jsonb_build_object('regola_id', v_id, 'stato', v_stato);
end;
$$;

create or replace view gestionale_v2.vista_regole_spese_ricorrenti
with (security_invoker = false)
as
select
  r.azienda_id,
  r.id as regola_id,
  r.fornitore_id,
  r.categoria_spesa_id,
  coalesce(f.nome_commerciale, f.ragione_sociale) as fornitore,
  c.nome as categoria,
  r.descrizione,
  r.imponibile,
  r.iva,
  r.totale,
  r.intervallo_mesi,
  r.data_inizio,
  r.data_fine,
  r.giorno_scadenza,
  r.tipo_documento,
  r.note,
  r.stato,
  count(s.id)::integer as spese_generate,
  coalesce(sum(s.totale) filter (where s.stato <> 'annullata'), 0)::numeric(12,2)
    as totale_generato
from gestionale_v2.regole_spese_ricorrenti r
left join gestionale_v2.fornitori f on f.id = r.fornitore_id
left join gestionale_v2.categorie_spesa c on c.id = r.categoria_spesa_id
left join gestionale_v2.spese s on s.regola_ricorrente_id = r.id
group by
  r.azienda_id, r.id, r.fornitore_id, r.categoria_spesa_id,
  f.nome_commerciale, f.ragione_sociale, c.nome;

create or replace view gestionale_v2.vista_spese_operativa
with (security_invoker = false)
as
select
  s.azienda_id,
  s.id as spesa_id,
  s.fornitore_id,
  s.categoria_spesa_id,
  s.regola_ricorrente_id,
  (s.regola_ricorrente_id is not null) as ricorrente,
  coalesce(f.nome_commerciale, f.ragione_sociale) as fornitore,
  cs.nome as categoria,
  s.data_spesa,
  s.descrizione,
  s.imponibile,
  s.iva,
  s.totale,
  s.numero_documento,
  s.tipo_documento,
  s.data_documento,
  s.competenza_mese,
  s.allegato_path,
  s.note,
  s.stato,
  coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0)::numeric(12,2) as pagato,
  greatest(
    s.totale - coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0),
    0
  )::numeric(12,2) as residuo,
  case
    when s.stato = 'annullata' then 'Annullata'
    when greatest(
      s.totale - coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0),
      0
    ) = 0 then 'Pagata'
    when coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0) > 0
      then 'Parzialmente pagata'
    when exists (
      select 1
      from gestionale_v2.scadenze_spesa ss
      where ss.spesa_id = s.id
        and ss.annullata = false
        and ss.data_scadenza < current_date
    ) then 'Scaduta'
    else 'Da pagare'
  end as stato_pagamento
from gestionale_v2.spese s
left join gestionale_v2.fornitori f on f.id = s.fornitore_id
left join gestionale_v2.categorie_spesa cs on cs.id = s.categoria_spesa_id
left join gestionale_v2.pagamenti_spesa p on p.spesa_id = s.id
group by
  s.azienda_id, s.id, s.fornitore_id, s.categoria_spesa_id,
  s.regola_ricorrente_id,
  f.nome_commerciale, f.ragione_sociale, cs.nome;

grant execute on function gestionale_v2.genera_spese_ricorrenti(jsonb) to service_role;
grant execute on function gestionale_v2.crea_regola_spesa_ricorrente(jsonb) to service_role;
grant execute on function gestionale_v2.cambia_stato_regola_spesa_ricorrente(jsonb) to service_role;
grant select on gestionale_v2.vista_regole_spese_ricorrenti to service_role;
grant select on gestionale_v2.vista_spese_operativa to service_role;

commit;

notify pgrst, 'reload schema';
