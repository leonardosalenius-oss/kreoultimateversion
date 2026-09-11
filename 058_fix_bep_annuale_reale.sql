begin;

-- ============================================================
-- BEP 2026 - modello annuale corretto
-- 1) import dei costi già registrati
-- 2) distinzione prezzo mensile / prezzo pacchetto
-- 3) unità annue per cliente
-- ============================================================

alter table gestionale_v2.costi_fissi_bep
  add column if not exists origine text not null default 'manuale',
  add column if not exists source_spesa_id uuid;

alter table gestionale_v2.costi_fissi_bep
  drop constraint if exists costi_fissi_bep_origine_check;

alter table gestionale_v2.costi_fissi_bep
  add constraint costi_fissi_bep_origine_check
  check (origine in ('manuale', 'spesa'));

create unique index if not exists uq_costi_fissi_bep_source_spesa
  on gestionale_v2.costi_fissi_bep (
    azienda_id,
    anno,
    source_spesa_id
  )
  where source_spesa_id is not null;


alter table gestionale_v2.configurazione_bep_pacchetti
  add column if not exists prezzo_unitario_bep numeric(14,2),
  add column if not exists costo_variabile_unitario_bep numeric(14,2),
  add column if not exists unita_annue_per_cliente numeric(10,3),
  add column if not exists modalita_bep text;

alter table gestionale_v2.configurazione_bep_pacchetti
  drop constraint if exists configurazione_bep_modalita_check;

alter table gestionale_v2.configurazione_bep_pacchetti
  add constraint configurazione_bep_modalita_check
  check (
    modalita_bep is null
    or modalita_bep in ('mensile', 'pacchetto')
  );

alter table gestionale_v2.configurazione_bep_pacchetti
  drop constraint if exists configurazione_bep_unita_check;

alter table gestionale_v2.configurazione_bep_pacchetti
  add constraint configurazione_bep_unita_check
  check (
    unita_annue_per_cliente is null
    or unita_annue_per_cliente >= 0
  );


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
  v_source_spesa_id uuid :=
    nullif(payload->>'source_spesa_id', '')::uuid;
  v_origine text :=
    coalesce(nullif(payload->>'origine', ''), 'manuale');
begin
  if v_origine not in ('manuale', 'spesa') then
    raise exception 'Origine costo fisso BEP non valida';
  end if;

  if v_id is null and v_source_spesa_id is not null then
    select c.id
    into v_id
    from gestionale_v2.costi_fissi_bep c
    where c.azienda_id = v_azienda
      and c.anno = v_anno
      and c.source_spesa_id = v_source_spesa_id
    limit 1;
  end if;

  if v_id is null then
    insert into gestionale_v2.costi_fissi_bep (
      azienda_id,
      anno,
      descrizione,
      categoria,
      importo_annuo,
      note,
      attivo,
      origine,
      source_spesa_id,
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
      v_origine,
      v_source_spesa_id,
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
      origine = v_origine,
      source_spesa_id = coalesce(
        v_source_spesa_id,
        source_spesa_id
      ),
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


create or replace function gestionale_v2.salva_configurazione_bep_pacchetto(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_pacchetto uuid := (payload->>'pacchetto_id')::uuid;
  v_prezzo numeric :=
    greatest(
      0,
      coalesce(
        nullif(payload->>'prezzo_unitario_bep', '')::numeric,
        0
      )
    );
  v_costo numeric :=
    greatest(
      0,
      coalesce(
        nullif(payload->>'costo_variabile_unitario_bep', '')::numeric,
        0
      )
    );
  v_unita numeric :=
    greatest(
      0,
      coalesce(
        nullif(payload->>'unita_annue_per_cliente', '')::numeric,
        0
      )
    );
  v_modalita text :=
    coalesce(
      nullif(payload->>'modalita_bep', ''),
      'pacchetto'
    );
begin
  if v_costo > v_prezzo then
    raise exception
      'Il costo variabile unitario non può superare il prezzo unitario';
  end if;

  if v_modalita not in ('mensile', 'pacchetto') then
    raise exception 'Modalità BEP non valida';
  end if;

  insert into gestionale_v2.configurazione_bep_pacchetti (
    azienda_id,
    pacchetto_id,
    ricavo_mensile_unitario,
    costo_variabile_unitario,
    peso_mix,
    attivo,
    prezzo_unitario_bep,
    costo_variabile_unitario_bep,
    unita_annue_per_cliente,
    modalita_bep,
    updated_at,
    updated_by
  )
  values (
    v_azienda,
    v_pacchetto,
    0,
    0,
    greatest(
      0,
      coalesce(
        nullif(payload->>'peso_mix', '')::numeric,
        1
      )
    ),
    coalesce((payload->>'attivo')::boolean, true),
    v_prezzo,
    v_costo,
    v_unita,
    v_modalita,
    now(),
    nullif(payload->>'utente_id', '')::uuid
  )
  on conflict (azienda_id, pacchetto_id)
  do update set
    ricavo_mensile_unitario = 0,
    costo_variabile_unitario = 0,
    peso_mix = excluded.peso_mix,
    attivo = excluded.attivo,
    prezzo_unitario_bep = excluded.prezzo_unitario_bep,
    costo_variabile_unitario_bep =
      excluded.costo_variabile_unitario_bep,
    unita_annue_per_cliente =
      excluded.unita_annue_per_cliente,
    modalita_bep = excluded.modalita_bep,
    updated_at = now(),
    updated_by = excluded.updated_by;

  return (
    select to_jsonb(c)
    from gestionale_v2.configurazione_bep_pacchetti c
    where c.azienda_id = v_azienda
      and c.pacchetto_id = v_pacchetto
  );
end;
$$;

grant execute
on function gestionale_v2.salva_configurazione_bep_pacchetto(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
