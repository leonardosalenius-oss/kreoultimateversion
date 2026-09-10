begin;

create table if not exists gestionale_v2.configurazione_bep (
  azienda_id uuid primary key
    references gestionale_v2.aziende(id)
    on delete cascade,
  costi_fissi_mensili numeric(14,2) not null default 0,
  margine_sicurezza_pct numeric(7,3) not null default 0,
  note text,
  updated_at timestamptz not null default now(),
  updated_by uuid
);

alter table gestionale_v2.configurazione_bep
  drop constraint if exists configurazione_bep_costi_check;

alter table gestionale_v2.configurazione_bep
  add constraint configurazione_bep_costi_check
  check (costi_fissi_mensili >= 0);

alter table gestionale_v2.configurazione_bep
  drop constraint if exists configurazione_bep_margine_check;

alter table gestionale_v2.configurazione_bep
  add constraint configurazione_bep_margine_check
  check (margine_sicurezza_pct between 0 and 100);


create table if not exists gestionale_v2.configurazione_bep_pacchetti (
  azienda_id uuid not null
    references gestionale_v2.aziende(id)
    on delete cascade,
  pacchetto_id uuid not null
    references gestionale_v2.pacchetti(id)
    on delete cascade,
  ricavo_mensile_unitario numeric(14,2) not null default 0,
  costo_variabile_unitario numeric(14,2) not null default 0,
  peso_mix numeric(10,4) not null default 1,
  attivo boolean not null default true,
  updated_at timestamptz not null default now(),
  updated_by uuid,
  primary key (azienda_id, pacchetto_id)
);

alter table gestionale_v2.configurazione_bep_pacchetti
  drop constraint if exists configurazione_bep_pacchetti_valori_check;

alter table gestionale_v2.configurazione_bep_pacchetti
  add constraint configurazione_bep_pacchetti_valori_check
  check (
    ricavo_mensile_unitario >= 0
    and costo_variabile_unitario >= 0
    and costo_variabile_unitario <= ricavo_mensile_unitario
    and peso_mix >= 0
  );


create or replace function gestionale_v2.salva_configurazione_bep(
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
  insert into gestionale_v2.configurazione_bep (
    azienda_id,
    costi_fissi_mensili,
    margine_sicurezza_pct,
    note,
    updated_at,
    updated_by
  )
  values (
    v_azienda,
    greatest(
      0,
      coalesce(
        nullif(payload->>'costi_fissi_mensili', '')::numeric,
        0
      )
    ),
    greatest(
      0,
      least(
        100,
        coalesce(
          nullif(payload->>'margine_sicurezza_pct', '')::numeric,
          0
        )
      )
    ),
    nullif(payload->>'note', ''),
    now(),
    nullif(payload->>'utente_id', '')::uuid
  )
  on conflict (azienda_id)
  do update set
    costi_fissi_mensili = excluded.costi_fissi_mensili,
    margine_sicurezza_pct = excluded.margine_sicurezza_pct,
    note = excluded.note,
    updated_at = now(),
    updated_by = excluded.updated_by;

  return (
    select to_jsonb(c)
    from gestionale_v2.configurazione_bep c
    where c.azienda_id = v_azienda
  );
end;
$$;

grant execute
on function gestionale_v2.salva_configurazione_bep(jsonb)
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
  v_ricavo numeric;
  v_costo numeric;
begin
  v_ricavo := greatest(
    0,
    coalesce(
      nullif(payload->>'ricavo_mensile_unitario', '')::numeric,
      0
    )
  );
  v_costo := greatest(
    0,
    coalesce(
      nullif(payload->>'costo_variabile_unitario', '')::numeric,
      0
    )
  );

  if v_costo > v_ricavo then
    raise exception
      'Il costo variabile unitario non può superare il ricavo mensile unitario';
  end if;

  insert into gestionale_v2.configurazione_bep_pacchetti (
    azienda_id,
    pacchetto_id,
    ricavo_mensile_unitario,
    costo_variabile_unitario,
    peso_mix,
    attivo,
    updated_at,
    updated_by
  )
  values (
    v_azienda,
    v_pacchetto,
    v_ricavo,
    v_costo,
    greatest(
      0,
      coalesce(
        nullif(payload->>'peso_mix', '')::numeric,
        1
      )
    ),
    coalesce((payload->>'attivo')::boolean, true),
    now(),
    nullif(payload->>'utente_id', '')::uuid
  )
  on conflict (azienda_id, pacchetto_id)
  do update set
    ricavo_mensile_unitario = excluded.ricavo_mensile_unitario,
    costo_variabile_unitario = excluded.costo_variabile_unitario,
    peso_mix = excluded.peso_mix,
    attivo = excluded.attivo,
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
