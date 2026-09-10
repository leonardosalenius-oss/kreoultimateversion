begin;

create table if not exists gestionale_v2.costi_fissi_bep (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id)
    on delete cascade,
  anno integer not null,
  descrizione text not null,
  categoria text,
  importo_annuo numeric(14,2) not null default 0,
  note text,
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by uuid,
  updated_by uuid
);

alter table gestionale_v2.costi_fissi_bep
  drop constraint if exists costi_fissi_bep_importo_check;

alter table gestionale_v2.costi_fissi_bep
  add constraint costi_fissi_bep_importo_check
  check (importo_annuo >= 0);

create index if not exists idx_costi_fissi_bep_azienda_anno
  on gestionale_v2.costi_fissi_bep (azienda_id, anno, attivo);


create or replace function gestionale_v2.salva_costo_fisso_bep(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := nullif(payload->>'id', '')::uuid;
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_anno integer := (payload->>'anno')::integer;
begin
  if v_id is null then
    insert into gestionale_v2.costi_fissi_bep (
      azienda_id,
      anno,
      descrizione,
      categoria,
      importo_annuo,
      note,
      attivo,
      created_by,
      updated_by
    )
    values (
      v_azienda,
      v_anno,
      trim(payload->>'descrizione'),
      nullif(trim(payload->>'categoria'), ''),
      greatest(
        0,
        coalesce(
          nullif(payload->>'importo_annuo', '')::numeric,
          0
        )
      ),
      nullif(trim(payload->>'note'), ''),
      coalesce((payload->>'attivo')::boolean, true),
      nullif(payload->>'utente_id', '')::uuid,
      nullif(payload->>'utente_id', '')::uuid
    )
    returning id into v_id;
  else
    update gestionale_v2.costi_fissi_bep
    set
      anno = v_anno,
      descrizione = trim(payload->>'descrizione'),
      categoria = nullif(trim(payload->>'categoria'), ''),
      importo_annuo = greatest(
        0,
        coalesce(
          nullif(payload->>'importo_annuo', '')::numeric,
          0
        )
      ),
      note = nullif(trim(payload->>'note'), ''),
      attivo = coalesce((payload->>'attivo')::boolean, true),
      updated_at = now(),
      updated_by = nullif(payload->>'utente_id', '')::uuid
    where id = v_id
      and azienda_id = v_azienda;
  end if;

  return (
    select to_jsonb(c)
    from gestionale_v2.costi_fissi_bep c
    where c.id = v_id
  );
end;
$$;

grant execute
on function gestionale_v2.salva_costo_fisso_bep(jsonb)
to service_role;


create or replace function gestionale_v2.elimina_costo_fisso_bep(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid := (payload->>'id')::uuid;
  v_azienda uuid := (payload->>'azienda_id')::uuid;
begin
  delete from gestionale_v2.costi_fissi_bep
  where id = v_id
    and azienda_id = v_azienda;

  return jsonb_build_object(
    'id', v_id,
    'eliminato', true
  );
end;
$$;

grant execute
on function gestionale_v2.elimina_costo_fisso_bep(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
