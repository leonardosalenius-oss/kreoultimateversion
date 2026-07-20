begin;

alter table gestionale_v2.spese
  add column if not exists imponibile numeric(12,2) not null default 0,
  add column if not exists iva numeric(12,2) not null default 0,
  add column if not exists totale numeric(12,2),
  add column if not exists annullata_il timestamptz,
  add column if not exists motivo_annullamento text;

update gestionale_v2.spese
set totale = coalesce(totale, importo)
where totale is null;

alter table gestionale_v2.spese
  alter column totale set not null;

create table if not exists gestionale_v2.scadenze_spesa (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null references gestionale_v2.aziende(id) on delete restrict,
  spesa_id uuid not null references gestionale_v2.spese(id) on delete restrict,
  numero_scadenza integer not null check (numero_scadenza > 0),
  data_scadenza date not null,
  importo_previsto numeric(12,2) not null check (importo_previsto > 0),
  annullata boolean not null default false,
  motivo_annullamento text,
  created_at timestamptz not null default now(),
  unique (spesa_id, numero_scadenza)
);

create table if not exists gestionale_v2.pagamenti_spesa (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null references gestionale_v2.aziende(id) on delete restrict,
  spesa_id uuid not null references gestionale_v2.spese(id) on delete restrict,
  fornitore_id uuid references gestionale_v2.fornitori(id) on delete set null,
  data_pagamento date not null default current_date,
  ora_pagamento time not null default localtime,
  importo numeric(12,2) not null check (importo > 0),
  metodo_pagamento text not null
    check (metodo_pagamento in ('Contanti','Carta','Bonifico','Assegno','Altro')),
  causale text,
  note text,
  stato text not null default 'valido'
    check (stato in ('valido','annullato')),
  annullato_il timestamptz,
  motivo_annullamento text,
  created_at timestamptz not null default now()
);

create table if not exists gestionale_v2.allocazioni_pagamenti_spesa (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null references gestionale_v2.aziende(id) on delete restrict,
  pagamento_id uuid not null references gestionale_v2.pagamenti_spesa(id) on delete cascade,
  scadenza_spesa_id uuid not null references gestionale_v2.scadenze_spesa(id) on delete cascade,
  importo_allocato numeric(12,2) not null check (importo_allocato > 0),
  created_at timestamptz not null default now(),
  unique (pagamento_id, scadenza_spesa_id)
);

create index if not exists idx_scadenze_spesa_data
  on gestionale_v2.scadenze_spesa(azienda_id, data_scadenza);

create index if not exists idx_pagamenti_spesa_data
  on gestionale_v2.pagamenti_spesa(azienda_id, data_pagamento);

alter table gestionale_v2.scadenze_spesa enable row level security;
alter table gestionale_v2.pagamenti_spesa enable row level security;
alter table gestionale_v2.allocazioni_pagamenti_spesa enable row level security;

grant select, insert, update, delete
on
  gestionale_v2.scadenze_spesa,
  gestionale_v2.pagamenti_spesa,
  gestionale_v2.allocazioni_pagamenti_spesa
to service_role;

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'documenti-spese',
  'documenti-spese',
  false,
  10485760,
  array[
    'application/pdf',
    'image/png',
    'image/jpeg'
  ]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

insert into gestionale_v2.categorie_spesa (
  azienda_id,
  nome,
  descrizione
)
select
  a.id,
  c.nome,
  c.descrizione
from gestionale_v2.aziende a
cross join (
  values
    ('Affitto', 'Canoni di locazione'),
    ('Utenze', 'Energia, acqua, telefonia e connettività'),
    ('Personale', 'Costi del personale'),
    ('Consulenze', 'Consulenze professionali'),
    ('Acquisto merci', 'Merci e materiali destinati alla vendita'),
    ('Integratori', 'Prodotti e integratori'),
    ('Manutenzioni', 'Manutenzioni ordinarie e straordinarie'),
    ('Pubblicità', 'Marketing e comunicazione'),
    ('Attrezzature', 'Macchinari e attrezzature'),
    ('Altro', 'Altre spese')
) as c(nome, descrizione)
on conflict (azienda_id, nome) do nothing;

create or replace function gestionale_v2.ricalcola_allocazioni_spesa(
  p_spesa_id uuid
)
returns void
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_pagamento record;
  v_scadenza record;
  v_residuo_pagamento numeric;
  v_allocabile numeric;
begin
  select azienda_id
  into v_azienda_id
  from gestionale_v2.spese
  where id = p_spesa_id;

  if v_azienda_id is null then
    raise exception 'Spesa non trovata';
  end if;

  delete from gestionale_v2.allocazioni_pagamenti_spesa aps
  using gestionale_v2.pagamenti_spesa ps
  where aps.pagamento_id = ps.id
    and ps.spesa_id = p_spesa_id;

  for v_pagamento in
    select *
    from gestionale_v2.pagamenti_spesa
    where spesa_id = p_spesa_id
      and stato = 'valido'
    order by data_pagamento, ora_pagamento, created_at, id
  loop
    v_residuo_pagamento := v_pagamento.importo;

    for v_scadenza in
      select
        s.id,
        s.importo_previsto,
        coalesce((
          select sum(a.importo_allocato)
          from gestionale_v2.allocazioni_pagamenti_spesa a
          where a.scadenza_spesa_id = s.id
        ), 0) as gia_allocato
      from gestionale_v2.scadenze_spesa s
      where s.spesa_id = p_spesa_id
        and s.annullata = false
      order by s.data_scadenza, s.numero_scadenza, s.id
    loop
      exit when v_residuo_pagamento <= 0;

      v_allocabile := least(
        v_residuo_pagamento,
        greatest(
          v_scadenza.importo_previsto - v_scadenza.gia_allocato,
          0
        )
      );

      if v_allocabile > 0 then
        insert into gestionale_v2.allocazioni_pagamenti_spesa (
          azienda_id,
          pagamento_id,
          scadenza_spesa_id,
          importo_allocato
        )
        values (
          v_azienda_id,
          v_pagamento.id,
          v_scadenza.id,
          v_allocabile
        );

        v_residuo_pagamento := v_residuo_pagamento - v_allocabile;
      end if;
    end loop;
  end loop;
end;
$$;

create or replace function gestionale_v2.crea_fornitore(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
begin
  if nullif(payload->>'ragione_sociale', '') is null then
    raise exception 'Ragione sociale obbligatoria';
  end if;

  insert into gestionale_v2.fornitori (
    azienda_id,
    ragione_sociale,
    nome_commerciale,
    partita_iva,
    codice_fiscale,
    indirizzo,
    citta,
    cap,
    provincia,
    telefono,
    email,
    pec,
    codice_sdi,
    iban,
    referente,
    note,
    stato
  )
  values (
    (payload->>'azienda_id')::uuid,
    payload->>'ragione_sociale',
    nullif(payload->>'nome_commerciale', ''),
    nullif(payload->>'partita_iva', ''),
    nullif(payload->>'codice_fiscale', ''),
    nullif(payload->>'indirizzo', ''),
    nullif(payload->>'citta', ''),
    nullif(payload->>'cap', ''),
    nullif(payload->>'provincia', ''),
    nullif(payload->>'telefono', ''),
    nullif(payload->>'email', ''),
    nullif(payload->>'pec', ''),
    nullif(payload->>'codice_sdi', ''),
    nullif(payload->>'iban', ''),
    nullif(payload->>'referente', ''),
    nullif(payload->>'note', ''),
    coalesce(nullif(payload->>'stato', ''), 'attivo')
  )
  returning id into v_id;

  return jsonb_build_object('fornitore_id', v_id);
end;
$$;

create or replace function gestionale_v2.modifica_fornitore(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_before jsonb;
  v_after jsonb;
begin
  v_id := (payload->>'fornitore_id')::uuid;

  select to_jsonb(f)
  into v_before
  from gestionale_v2.fornitori f
  where f.id = v_id
    and f.azienda_id = (payload->>'azienda_id')::uuid;

  if v_before is null then
    raise exception 'Fornitore non trovato';
  end if;

  update gestionale_v2.fornitori
  set
    ragione_sociale = payload->>'ragione_sociale',
    nome_commerciale = nullif(payload->>'nome_commerciale', ''),
    telefono = nullif(payload->>'telefono', ''),
    email = nullif(payload->>'email', ''),
    iban = nullif(payload->>'iban', ''),
    stato = payload->>'stato',
    note = nullif(payload->>'note', '')
  where id = v_id;

  select to_jsonb(f)
  into v_after
  from gestionale_v2.fornitori f
  where f.id = v_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    valore_successivo
  )
  values (
    (payload->>'azienda_id')::uuid,
    'fornitori',
    v_id,
    'modifica',
    v_before,
    v_after
  );

  return jsonb_build_object('fornitore_id', v_id);
end;
$$;

create or replace function gestionale_v2.crea_categoria_spesa(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
begin
  insert into gestionale_v2.categorie_spesa (
    azienda_id,
    nome,
    descrizione,
    attiva
  )
  values (
    (payload->>'azienda_id')::uuid,
    payload->>'nome',
    nullif(payload->>'descrizione', ''),
    true
  )
  on conflict (azienda_id, nome)
  do update set attiva = true
  returning id into v_id;

  return jsonb_build_object('categoria_id', v_id);
end;
$$;

create or replace function gestionale_v2.crea_spesa_completa(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_spesa_id uuid;
  v_scadenza jsonb;
  v_pagamento_id uuid;
  v_totale numeric;
  v_somma_scadenze numeric;
begin
  v_totale := (payload->>'totale')::numeric;

  select coalesce(sum((value->>'importo_previsto')::numeric), 0)
  into v_somma_scadenze
  from jsonb_array_elements(payload->'scadenze');

  if abs(v_somma_scadenze - v_totale) > 0.01 then
    raise exception 'La somma delle scadenze non coincide con il totale';
  end if;

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
    numero_documento,
    tipo_documento,
    data_documento,
    competenza_mese,
    allegato_path,
    note,
    stato
  )
  values (
    (payload->>'azienda_id')::uuid,
    (payload->>'categoria_spesa_id')::uuid,
    (payload->>'fornitore_id')::uuid,
    (payload->>'data_spesa')::date,
    payload->>'descrizione',
    v_totale,
    coalesce((payload->>'imponibile')::numeric, 0),
    coalesce((payload->>'iva')::numeric, 0),
    v_totale,
    nullif(payload->>'numero_documento', ''),
    nullif(payload->>'tipo_documento', ''),
    nullif(payload->>'data_documento', '')::date,
    nullif(payload->>'competenza_mese', '')::date,
    nullif(payload->>'allegato_path', ''),
    nullif(payload->>'note', ''),
    'registrata'
  )
  returning id into v_spesa_id;

  for v_scadenza in
    select value
    from jsonb_array_elements(payload->'scadenze')
  loop
    insert into gestionale_v2.scadenze_spesa (
      azienda_id,
      spesa_id,
      numero_scadenza,
      data_scadenza,
      importo_previsto
    )
    values (
      (payload->>'azienda_id')::uuid,
      v_spesa_id,
      (v_scadenza->>'numero_scadenza')::integer,
      (v_scadenza->>'data_scadenza')::date,
      (v_scadenza->>'importo_previsto')::numeric
    );
  end loop;

  if payload->'pagamento_iniziale' is not null then
    insert into gestionale_v2.pagamenti_spesa (
      azienda_id,
      spesa_id,
      fornitore_id,
      data_pagamento,
      importo,
      metodo_pagamento,
      causale,
      stato
    )
    values (
      (payload->>'azienda_id')::uuid,
      v_spesa_id,
      (payload->>'fornitore_id')::uuid,
      (payload->'pagamento_iniziale'->>'data_pagamento')::date,
      (payload->'pagamento_iniziale'->>'importo')::numeric,
      payload->'pagamento_iniziale'->>'metodo_pagamento',
      payload->'pagamento_iniziale'->>'causale',
      'valido'
    )
    returning id into v_pagamento_id;
  end if;

  perform gestionale_v2.ricalcola_allocazioni_spesa(v_spesa_id);

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo
  )
  values (
    (payload->>'azienda_id')::uuid,
    'spese',
    v_spesa_id,
    'creazione',
    payload
  );

  return jsonb_build_object(
    'spesa_id', v_spesa_id,
    'pagamento_id', v_pagamento_id
  );
end;
$$;

create or replace function gestionale_v2.registra_pagamento_spesa(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_spesa_id uuid;
  v_importo numeric;
  v_residuo numeric;
  v_pagamento_id uuid;
begin
  v_spesa_id := (payload->>'spesa_id')::uuid;
  v_importo := (payload->>'importo')::numeric;

  select greatest(
    s.totale
    - coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0),
    0
  )
  into v_residuo
  from gestionale_v2.spese s
  left join gestionale_v2.pagamenti_spesa p
    on p.spesa_id = s.id
  where s.id = v_spesa_id
    and s.azienda_id = (payload->>'azienda_id')::uuid
    and s.stato <> 'annullata'
  group by s.totale;

  if v_residuo is null then
    raise exception 'Spesa non trovata';
  end if;

  if v_importo <= 0 or v_importo > v_residuo then
    raise exception 'Importo pagamento non valido';
  end if;

  insert into gestionale_v2.pagamenti_spesa (
    azienda_id,
    spesa_id,
    fornitore_id,
    data_pagamento,
    importo,
    metodo_pagamento,
    causale,
    note,
    stato
  )
  values (
    (payload->>'azienda_id')::uuid,
    v_spesa_id,
    nullif(payload->>'fornitore_id', '')::uuid,
    (payload->>'data_pagamento')::date,
    v_importo,
    payload->>'metodo_pagamento',
    nullif(payload->>'causale', ''),
    nullif(payload->>'note', ''),
    'valido'
  )
  returning id into v_pagamento_id;

  perform gestionale_v2.ricalcola_allocazioni_spesa(v_spesa_id);

  return jsonb_build_object(
    'pagamento_id', v_pagamento_id,
    'nuovo_residuo', v_residuo - v_importo
  );
end;
$$;

create or replace function gestionale_v2.annulla_pagamento_spesa(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_pagamento_id uuid;
  v_spesa_id uuid;
  v_before jsonb;
  v_residuo numeric;
begin
  v_pagamento_id := (payload->>'pagamento_id')::uuid;

  select p.spesa_id, to_jsonb(p)
  into v_spesa_id, v_before
  from gestionale_v2.pagamenti_spesa p
  where p.id = v_pagamento_id
    and p.azienda_id = (payload->>'azienda_id')::uuid
    and p.stato = 'valido';

  if v_before is null then
    raise exception 'Pagamento valido non trovato';
  end if;

  update gestionale_v2.pagamenti_spesa
  set
    stato = 'annullato',
    annullato_il = now(),
    motivo_annullamento = payload->>'motivo'
  where id = v_pagamento_id;

  perform gestionale_v2.ricalcola_allocazioni_spesa(v_spesa_id);

  select greatest(
    s.totale
    - coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0),
    0
  )
  into v_residuo
  from gestionale_v2.spese s
  left join gestionale_v2.pagamenti_spesa p
    on p.spesa_id = s.id
  where s.id = v_spesa_id
  group by s.totale;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    motivo
  )
  values (
    (payload->>'azienda_id')::uuid,
    'pagamenti_spesa',
    v_pagamento_id,
    'annullamento',
    v_before,
    payload->>'motivo'
  );

  return jsonb_build_object(
    'pagamento_id', v_pagamento_id,
    'nuovo_residuo', v_residuo
  );
end;
$$;

create or replace view gestionale_v2.vista_spese_operativa
with (security_invoker = false)
as
select
  s.azienda_id,
  s.id as spesa_id,
  s.fornitore_id,
  s.categoria_spesa_id,
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
    s.totale
    - coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0),
    0
  )::numeric(12,2) as residuo,
  case
    when s.stato = 'annullata' then 'Annullata'
    when greatest(
      s.totale
      - coalesce(sum(p.importo) filter (where p.stato = 'valido'), 0),
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
  f.nome_commerciale, f.ragione_sociale, cs.nome;

create or replace view gestionale_v2.vista_scadenze_spesa_operativa
with (security_invoker = false)
as
select
  ss.azienda_id,
  ss.id as scadenza_spesa_id,
  ss.spesa_id,
  s.fornitore_id,
  coalesce(f.nome_commerciale, f.ragione_sociale) as fornitore,
  s.descrizione,
  ss.numero_scadenza,
  ss.data_scadenza,
  ss.importo_previsto,
  coalesce(sum(a.importo_allocato), 0)::numeric(12,2) as importo_pagato,
  greatest(
    ss.importo_previsto - coalesce(sum(a.importo_allocato), 0),
    0
  )::numeric(12,2) as residuo_scadenza,
  case
    when ss.annullata then 'Annullata'
    when greatest(
      ss.importo_previsto - coalesce(sum(a.importo_allocato), 0),
      0
    ) = 0 then 'Pagata'
    when coalesce(sum(a.importo_allocato), 0) > 0
      and ss.data_scadenza < current_date then 'Scaduta parziale'
    when coalesce(sum(a.importo_allocato), 0) > 0
      then 'Parzialmente pagata'
    when ss.data_scadenza < current_date then 'Scaduta'
    else 'Da pagare'
  end as stato
from gestionale_v2.scadenze_spesa ss
join gestionale_v2.spese s on s.id = ss.spesa_id
left join gestionale_v2.fornitori f on f.id = s.fornitore_id
left join gestionale_v2.allocazioni_pagamenti_spesa a
  on a.scadenza_spesa_id = ss.id
group by
  ss.azienda_id, ss.id, ss.spesa_id, s.fornitore_id,
  f.nome_commerciale, f.ragione_sociale, s.descrizione,
  ss.numero_scadenza, ss.data_scadenza,
  ss.importo_previsto, ss.annullata;

create or replace view gestionale_v2.vista_pagamenti_spesa_operativa
with (security_invoker = false)
as
select
  p.azienda_id,
  p.id as pagamento_id,
  p.spesa_id,
  p.fornitore_id,
  coalesce(f.nome_commerciale, f.ragione_sociale) as fornitore,
  s.descrizione as descrizione_spesa,
  p.data_pagamento,
  p.importo,
  p.metodo_pagamento,
  p.causale,
  p.note,
  p.stato,
  p.created_at
from gestionale_v2.pagamenti_spesa p
join gestionale_v2.spese s on s.id = p.spesa_id
left join gestionale_v2.fornitori f on f.id = p.fornitore_id;

grant execute on function gestionale_v2.ricalcola_allocazioni_spesa(uuid) to service_role;
grant execute on function gestionale_v2.crea_fornitore(jsonb) to service_role;
grant execute on function gestionale_v2.modifica_fornitore(jsonb) to service_role;
grant execute on function gestionale_v2.crea_categoria_spesa(jsonb) to service_role;
grant execute on function gestionale_v2.crea_spesa_completa(jsonb) to service_role;
grant execute on function gestionale_v2.registra_pagamento_spesa(jsonb) to service_role;
grant execute on function gestionale_v2.annulla_pagamento_spesa(jsonb) to service_role;

grant select on gestionale_v2.vista_spese_operativa to service_role;
grant select on gestionale_v2.vista_scadenze_spesa_operativa to service_role;
grant select on gestionale_v2.vista_pagamenti_spesa_operativa to service_role;

commit;

notify pgrst, 'reload schema';
