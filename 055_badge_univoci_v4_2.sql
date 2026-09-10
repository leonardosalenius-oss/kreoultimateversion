begin;

create or replace function gestionale_v2.verifica_collisione_badge(
  p_azienda_id uuid,
  p_codice text,
  p_escludi_tipo text default null,
  p_escludi_badge_id uuid default null
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_code text := upper(trim(p_codice));
  v_row record;
begin
  if v_code is null or v_code = '' then
    return jsonb_build_object('collisione', false, 'codice', v_code);
  end if;

  select *
  into v_row
  from (
    select
      'cliente'::text as tipo_soggetto,
      b.id as badge_id,
      b.cliente_id,
      trim(c.cognome || ' ' || c.nome) as nome,
      x.campo
    from gestionale_v2.badge_clienti b
    join gestionale_v2.clienti c on c.id = b.cliente_id
    cross join lateral (
      values
        ('codice_badge'::text, b.codice_badge::text),
        ('rfid_uid_reale'::text, b.rfid_uid_reale::text),
        ('codice_tornello'::text, b.codice_tornello::text),
        ('perfectgym_idsocio'::text, b.perfectgym_idsocio::text)
    ) x(campo, codice)
    where b.azienda_id = p_azienda_id
      and b.attivo = true
      and nullif(trim(x.codice), '') is not null
      and upper(trim(x.codice)) = v_code
      and not (
        p_escludi_tipo = 'cliente'
        and p_escludi_badge_id is not null
        and b.id = p_escludi_badge_id
      )

    union all

    select
      'staff'::text as tipo_soggetto,
      s.id as badge_id,
      null::uuid as cliente_id,
      s.nome,
      x.campo
    from gestionale_v2.badge_staff s
    cross join lateral (
      values
        ('rfid_uid_reale'::text, s.rfid_uid_reale::text),
        ('codice_tornello'::text, s.codice_tornello::text)
    ) x(campo, codice)
    where s.azienda_id = p_azienda_id
      and s.attivo = true
      and nullif(trim(x.codice), '') is not null
      and upper(trim(x.codice)) = v_code
      and not (
        p_escludi_tipo = 'staff'
        and p_escludi_badge_id is not null
        and s.id = p_escludi_badge_id
      )
  ) q
  limit 1;

  if v_row.badge_id is null then
    return jsonb_build_object('collisione', false, 'codice', v_code);
  end if;

  return jsonb_build_object(
    'collisione', true,
    'codice', v_code,
    'tipo_soggetto', v_row.tipo_soggetto,
    'badge_id', v_row.badge_id,
    'cliente_id', v_row.cliente_id,
    'nome', v_row.nome,
    'campo', v_row.campo
  );
end;
$$;

grant execute
on function gestionale_v2.verifica_collisione_badge(uuid, text, text, uuid)
to service_role;


create or replace function gestionale_v2.elenco_collisioni_badge(
  p_azienda_id uuid
)
returns table (
  codice text,
  soggetti integer,
  assegnazioni text
)
language sql
stable
security definer
set search_path = gestionale_v2, public
as $$
with tokens as (
  select
    upper(trim(x.codice)) as codice,
    'CLIENTE'::text as tipo,
    b.id as badge_id,
    trim(c.cognome || ' ' || c.nome) as nome,
    x.campo
  from gestionale_v2.badge_clienti b
  join gestionale_v2.clienti c on c.id = b.cliente_id
  cross join lateral (
    values
      ('codice_badge'::text, b.codice_badge::text),
      ('rfid_uid_reale'::text, b.rfid_uid_reale::text),
      ('codice_tornello'::text, b.codice_tornello::text),
      ('perfectgym_idsocio'::text, b.perfectgym_idsocio::text)
  ) x(campo, codice)
  where b.azienda_id = p_azienda_id
    and b.attivo = true
    and nullif(trim(x.codice), '') is not null

  union all

  select
    upper(trim(x.codice)) as codice,
    'STAFF'::text as tipo,
    s.id as badge_id,
    s.nome,
    x.campo
  from gestionale_v2.badge_staff s
  cross join lateral (
    values
      ('rfid_uid_reale'::text, s.rfid_uid_reale::text),
      ('codice_tornello'::text, s.codice_tornello::text)
  ) x(campo, codice)
  where s.azienda_id = p_azienda_id
    and s.attivo = true
    and nullif(trim(x.codice), '') is not null
),
owners as (
  select distinct codice, tipo, badge_id, nome, campo
  from tokens
)
select
  codice,
  count(distinct tipo || ':' || badge_id::text)::integer as soggetti,
  string_agg(
    tipo || ' · ' || nome || ' [' || campo || ']',
    ' | ' order by tipo, nome, campo
  ) as assegnazioni
from owners
group by codice
having count(distinct tipo || ':' || badge_id::text) > 1
order by codice;
$$;

grant execute
on function gestionale_v2.elenco_collisioni_badge(uuid)
to service_role;


create or replace function gestionale_v2.proteggi_badge_cliente_univoco()
returns trigger
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_code text;
  v_check jsonb;
begin
  if not coalesce(new.attivo, false) then
    return new;
  end if;

  for v_code in
    select distinct upper(trim(x.codice))
    from (
      values
        (new.codice_badge::text),
        (new.rfid_uid_reale::text),
        (new.codice_tornello::text),
        (new.perfectgym_idsocio::text)
    ) x(codice)
    where nullif(trim(x.codice), '') is not null
  loop
    v_check := gestionale_v2.verifica_collisione_badge(
      new.azienda_id, v_code, 'cliente', new.id
    );

    if coalesce((v_check->>'collisione')::boolean, false) then
      raise exception
        'BADGE AMBIGUO: codice % già assegnato a % (%)',
        v_code,
        coalesce(v_check->>'nome', 'altro soggetto'),
        coalesce(v_check->>'tipo_soggetto', 'sconosciuto');
    end if;
  end loop;

  return new;
end;
$$;


create or replace function gestionale_v2.proteggi_badge_staff_univoco()
returns trigger
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_code text;
  v_check jsonb;
begin
  if not coalesce(new.attivo, false) then
    return new;
  end if;

  for v_code in
    select distinct upper(trim(x.codice))
    from (
      values
        (new.rfid_uid_reale::text),
        (new.codice_tornello::text)
    ) x(codice)
    where nullif(trim(x.codice), '') is not null
  loop
    v_check := gestionale_v2.verifica_collisione_badge(
      new.azienda_id, v_code, 'staff', new.id
    );

    if coalesce((v_check->>'collisione')::boolean, false) then
      raise exception
        'BADGE AMBIGUO: codice % già assegnato a % (%)',
        v_code,
        coalesce(v_check->>'nome', 'altro soggetto'),
        coalesce(v_check->>'tipo_soggetto', 'sconosciuto');
    end if;
  end loop;

  return new;
end;
$$;


drop trigger if exists trg_badge_clienti_univoco
on gestionale_v2.badge_clienti;

create trigger trg_badge_clienti_univoco
before insert or update of
  codice_badge,
  rfid_uid_reale,
  codice_tornello,
  perfectgym_idsocio,
  attivo
on gestionale_v2.badge_clienti
for each row
execute function gestionale_v2.proteggi_badge_cliente_univoco();


drop trigger if exists trg_badge_staff_univoco
on gestionale_v2.badge_staff;

create trigger trg_badge_staff_univoco
before insert or update of
  rfid_uid_reale,
  codice_tornello,
  attivo
on gestionale_v2.badge_staff
for each row
execute function gestionale_v2.proteggi_badge_staff_univoco();

commit;

notify pgrst, 'reload schema';
