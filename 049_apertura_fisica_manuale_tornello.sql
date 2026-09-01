begin;

create table if not exists gestionale_v2.richieste_apertura_tornello (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  stato text not null default 'in_attesa',
  motivazione text not null,
  richiesto_da uuid,
  richiesto_il timestamptz not null default now(),
  scade_il timestamptz not null default (now() + interval '20 seconds'),
  preso_in_carico_il timestamptz,
  completato_il timestamptz,
  risposta_controller text,
  errore text,
  updated_at timestamptz not null default now(),
  constraint richieste_apertura_tornello_stato_check
    check (
      stato in (
        'in_attesa',
        'in_esecuzione',
        'aperto',
        'errore',
        'scaduto'
      )
    )
);

create index if not exists idx_richieste_apertura_tornello_coda
on gestionale_v2.richieste_apertura_tornello (
  azienda_id,
  stato,
  richiesto_il
);

grant select, insert, update
on gestionale_v2.richieste_apertura_tornello
to service_role;


create or replace function gestionale_v2.crea_richiesta_apertura_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_motivazione text := nullif(trim(payload->>'motivazione'), '');
  v_user uuid := nullif(payload->>'utente_id', '')::uuid;
  v_id uuid;
  v_scade timestamptz;
begin
  if v_motivazione is null then
    raise exception 'Motivazione apertura manuale obbligatoria';
  end if;

  -- Chiudiamo eventuali richieste vecchie rimaste appese.
  update gestionale_v2.richieste_apertura_tornello
  set
    stato = 'scaduto',
    completato_il = now(),
    errore = coalesce(
      errore,
      'Richiesta scaduta prima della presa in carico'
    ),
    updated_at = now()
  where azienda_id = v_azienda
    and stato = 'in_attesa'
    and scade_il <= now();

  -- Evita doppi click/aperture duplicate.
  if exists (
    select 1
    from gestionale_v2.richieste_apertura_tornello
    where azienda_id = v_azienda
      and stato in ('in_attesa', 'in_esecuzione')
      and scade_il > now()
  ) then
    raise exception 'Esiste già una richiesta di apertura in corso';
  end if;

  insert into gestionale_v2.richieste_apertura_tornello (
    azienda_id,
    motivazione,
    richiesto_da,
    scade_il
  )
  values (
    v_azienda,
    v_motivazione,
    v_user,
    now() + interval '20 seconds'
  )
  returning id, scade_il
  into v_id, v_scade;

  return jsonb_build_object(
    'richiesta_id', v_id,
    'stato', 'in_attesa',
    'scade_il', v_scade
  );
end;
$$;

grant execute
on function gestionale_v2.crea_richiesta_apertura_tornello(jsonb)
to service_role;


create or replace function gestionale_v2.stato_richiesta_apertura_tornello(
  p_richiesta_id uuid,
  p_azienda_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_row gestionale_v2.richieste_apertura_tornello;
begin
  select *
  into v_row
  from gestionale_v2.richieste_apertura_tornello
  where id = p_richiesta_id
    and azienda_id = p_azienda_id;

  if v_row.id is null then
    raise exception 'Richiesta apertura non trovata';
  end if;

  if v_row.stato = 'in_attesa'
     and v_row.scade_il <= now() then
    update gestionale_v2.richieste_apertura_tornello
    set
      stato = 'scaduto',
      completato_il = now(),
      errore = coalesce(
        errore,
        'Agent KREO non ha preso in carico la richiesta in tempo'
      ),
      updated_at = now()
    where id = v_row.id
    returning * into v_row;
  end if;

  return jsonb_build_object(
    'richiesta_id', v_row.id,
    'stato', v_row.stato,
    'motivazione', v_row.motivazione,
    'richiesto_il', v_row.richiesto_il,
    'preso_in_carico_il', v_row.preso_in_carico_il,
    'completato_il', v_row.completato_il,
    'risposta_controller', v_row.risposta_controller,
    'errore', v_row.errore
  );
end;
$$;

grant execute
on function gestionale_v2.stato_richiesta_apertura_tornello(uuid, uuid)
to service_role;


create or replace function gestionale_v2.elenco_richieste_apertura_tornello(
  p_azienda_id uuid,
  p_limite integer default 20
)
returns setof gestionale_v2.richieste_apertura_tornello
language sql
stable
security definer
set search_path = gestionale_v2, public
as $$
  select r.*
  from gestionale_v2.richieste_apertura_tornello r
  where r.azienda_id = p_azienda_id
  order by r.richiesto_il desc
  limit greatest(1, least(coalesce(p_limite, 20), 100));
$$;

grant execute
on function gestionale_v2.elenco_richieste_apertura_tornello(uuid, integer)
to service_role;

commit;

notify pgrst, 'reload schema';
