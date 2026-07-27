begin;

create table if not exists gestionale_v2.prodotti_magazzino (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  codice text not null,
  barcode text,
  nome text not null,
  categoria text,
  marca text,
  unita_misura text not null default 'pz',
  prezzo_vendita numeric(12,2) not null default 0,
  costo_standard numeric(12,2) not null default 0,
  scorta_minima numeric(12,3) not null default 0,
  attivo boolean not null default true,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (azienda_id, codice)
);

create unique index if not exists uq_prodotto_barcode_azienda
  on gestionale_v2.prodotti_magazzino(azienda_id, barcode)
  where barcode is not null;

create table if not exists gestionale_v2.movimenti_magazzino (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  prodotto_id uuid not null
    references gestionale_v2.prodotti_magazzino(id)
    on delete restrict,
  cliente_id uuid
    references gestionale_v2.clienti(id) on delete set null,
  fornitore_id uuid
    references gestionale_v2.fornitori(id) on delete set null,
  incasso_id uuid
    references gestionale_v2.incassi(id) on delete set null,
  spesa_id uuid
    references gestionale_v2.spese(id) on delete set null,
  movimento_origine_id uuid
    references gestionale_v2.movimenti_magazzino(id)
    on delete set null,
  data_movimento date not null default current_date,
  tipo text not null
    check (
      tipo in (
        'giacenza_iniziale',
        'acquisto',
        'vendita',
        'rettifica_positiva',
        'rettifica_negativa',
        'storno'
      )
    ),
  quantita numeric(12,3) not null
    check (quantita <> 0),
  costo_unitario numeric(12,4),
  prezzo_unitario numeric(12,4),
  documento text,
  lotto text,
  data_scadenza_lotto date,
  causale text not null,
  stato text not null default 'valido'
    check (stato in ('valido', 'annullato')),
  note text,
  created_at timestamptz not null default now()
);

create index if not exists idx_movimenti_magazzino_prodotto
  on gestionale_v2.movimenti_magazzino(
    azienda_id,
    prodotto_id,
    data_movimento
  );

create table if not exists gestionale_v2.righe_vendita_prodotti (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete restrict,
  incasso_id uuid not null
    references gestionale_v2.incassi(id) on delete restrict,
  prodotto_id uuid not null
    references gestionale_v2.prodotti_magazzino(id)
    on delete restrict,
  quantita numeric(12,3) not null check (quantita > 0),
  prezzo_unitario numeric(12,4) not null check (prezzo_unitario >= 0),
  totale numeric(12,2) not null check (totale >= 0),
  created_at timestamptz not null default now()
);

alter table gestionale_v2.prodotti_magazzino
  enable row level security;
alter table gestionale_v2.movimenti_magazzino
  enable row level security;
alter table gestionale_v2.righe_vendita_prodotti
  enable row level security;

grant select, insert, update, delete
on
  gestionale_v2.prodotti_magazzino,
  gestionale_v2.movimenti_magazzino,
  gestionale_v2.righe_vendita_prodotti
to service_role;


create or replace view gestionale_v2.vista_prodotti_magazzino
with (security_invoker = false)
as
select
  p.azienda_id,
  p.id as prodotto_id,
  p.codice,
  p.barcode,
  p.nome,
  p.categoria,
  p.marca,
  p.unita_misura,
  p.prezzo_vendita,
  p.costo_standard,
  p.scorta_minima,
  p.attivo,
  p.note,
  coalesce(
    sum(m.quantita) filter (
      where m.stato = 'valido'
        and m.tipo = 'giacenza_iniziale'
    ),
    0
  )::numeric(12,3) as giacenza_iniziale,
  coalesce(
    sum(m.quantita) filter (
      where m.stato = 'valido'
    ),
    0
  )::numeric(12,3) as giacenza,
  coalesce(
    (
      sum(
        m.quantita * m.costo_unitario
      ) filter (
        where m.stato = 'valido'
          and m.quantita > 0
          and m.costo_unitario is not null
      )
      /
      nullif(
        sum(m.quantita) filter (
          where m.stato = 'valido'
            and m.quantita > 0
            and m.costo_unitario is not null
        ),
        0
      )
    ),
    p.costo_standard
  )::numeric(12,4) as costo_medio,
  p.created_at,
  p.updated_at
from gestionale_v2.prodotti_magazzino p
left join gestionale_v2.movimenti_magazzino m
  on m.prodotto_id = p.id
group by p.id;


create or replace view gestionale_v2.vista_movimenti_magazzino
with (security_invoker = false)
as
select
  m.azienda_id,
  m.id as movimento_id,
  m.prodotto_id,
  p.codice,
  p.nome as prodotto,
  p.unita_misura,
  m.cliente_id,
  case
    when c.id is null then null
    else c.cognome || ' ' || c.nome
  end as cliente,
  m.fornitore_id,
  coalesce(f.nome_commerciale, f.ragione_sociale)
    as fornitore,
  m.incasso_id,
  m.spesa_id,
  m.movimento_origine_id,
  m.data_movimento,
  m.tipo,
  m.quantita,
  m.costo_unitario,
  m.prezzo_unitario,
  m.documento,
  m.lotto,
  m.data_scadenza_lotto,
  m.causale,
  m.stato,
  m.note,
  m.created_at
from gestionale_v2.movimenti_magazzino m
join gestionale_v2.prodotti_magazzino p
  on p.id = m.prodotto_id
left join gestionale_v2.clienti c
  on c.id = m.cliente_id
left join gestionale_v2.fornitori f
  on f.id = m.fornitore_id;


create or replace function gestionale_v2.salva_prodotto_magazzino(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_id uuid;
  v_initial numeric(12,3);
begin
  v_id := nullif(payload->>'prodotto_id', '')::uuid;
  v_initial :=
    nullif(payload->>'giacenza_iniziale', '')::numeric;

  if nullif(trim(payload->>'codice'), '') is null
     or nullif(trim(payload->>'nome'), '') is null then
    raise exception 'Codice e nome prodotto sono obbligatori';
  end if;

  if v_id is null then
    insert into gestionale_v2.prodotti_magazzino (
      azienda_id,
      codice,
      barcode,
      nome,
      categoria,
      marca,
      unita_misura,
      prezzo_vendita,
      costo_standard,
      scorta_minima,
      attivo,
      note
    )
    values (
      (payload->>'azienda_id')::uuid,
      trim(payload->>'codice'),
      nullif(trim(payload->>'barcode'), ''),
      trim(payload->>'nome'),
      nullif(trim(payload->>'categoria'), ''),
      nullif(trim(payload->>'marca'), ''),
      coalesce(nullif(payload->>'unita_misura', ''), 'pz'),
      coalesce((payload->>'prezzo_vendita')::numeric, 0),
      coalesce((payload->>'costo_standard')::numeric, 0),
      coalesce((payload->>'scorta_minima')::numeric, 0),
      coalesce((payload->>'attivo')::boolean, true),
      nullif(payload->>'note', '')
    )
    returning id into v_id;

    if coalesce(v_initial, 0) > 0 then
      insert into gestionale_v2.movimenti_magazzino (
        azienda_id,
        prodotto_id,
        data_movimento,
        tipo,
        quantita,
        costo_unitario,
        causale
      )
      values (
        (payload->>'azienda_id')::uuid,
        v_id,
        current_date,
        'giacenza_iniziale',
        v_initial,
        coalesce(
          (payload->>'costo_standard')::numeric,
          0
        ),
        'Giacenza iniziale'
      );
    end if;
  else
    update gestionale_v2.prodotti_magazzino
    set
      codice = trim(payload->>'codice'),
      barcode = nullif(trim(payload->>'barcode'), ''),
      nome = trim(payload->>'nome'),
      categoria = nullif(trim(payload->>'categoria'), ''),
      marca = nullif(trim(payload->>'marca'), ''),
      unita_misura =
        coalesce(nullif(payload->>'unita_misura', ''), 'pz'),
      prezzo_vendita =
        coalesce((payload->>'prezzo_vendita')::numeric, 0),
      costo_standard =
        coalesce((payload->>'costo_standard')::numeric, 0),
      scorta_minima =
        coalesce((payload->>'scorta_minima')::numeric, 0),
      attivo = coalesce((payload->>'attivo')::boolean, true),
      note = nullif(payload->>'note', ''),
      updated_at = now()
    where id = v_id
      and azienda_id = (payload->>'azienda_id')::uuid;

    if not found then
      raise exception 'Prodotto non trovato';
    end if;
  end if;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo
  )
  values (
    (payload->>'azienda_id')::uuid,
    'prodotti_magazzino',
    v_id,
    case
      when nullif(payload->>'prodotto_id', '') is null
        then 'creazione'
      else 'modifica'
    end,
    payload
  );

  return jsonb_build_object('prodotto_id', v_id);
end;
$$;


create or replace function gestionale_v2.registra_vendita_magazzino(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_product record;
  v_quantity numeric(12,3);
  v_price numeric(12,4);
  v_total numeric(12,2);
  v_stock numeric(12,3);
  v_income_result jsonb;
  v_income_id uuid;
  v_receipt_id uuid;
  v_movement_id uuid;
  v_new_stock numeric(12,3);
begin
  v_quantity := (payload->>'quantita')::numeric;
  v_price := (payload->>'prezzo_unitario')::numeric;

  if v_quantity <= 0 then
    raise exception 'Quantità non valida';
  end if;

  select p.*
  into v_product
  from gestionale_v2.vista_prodotti_magazzino p
  where p.prodotto_id = (payload->>'prodotto_id')::uuid
    and p.azienda_id = (payload->>'azienda_id')::uuid
    and p.attivo = true
  for update;

  if v_product.prodotto_id is null then
    raise exception 'Prodotto non trovato o inattivo';
  end if;

  v_stock := v_product.giacenza;

  if v_quantity > v_stock then
    raise exception
      'Giacenza insufficiente: disponibile %',
      v_stock;
  end if;

  v_total := round(v_quantity * v_price, 2);

  v_income_result :=
    gestionale_v2.registra_incasso_completo(
      jsonb_build_object(
        'azienda_id', payload->>'azienda_id',
        'cliente_id', payload->>'cliente_id',
        'abbonamento_id', null,
        'tipo_incasso', 'vendita_prodotto',
        'data_incasso', payload->>'data_vendita',
        'importo', v_total,
        'metodo_pagamento', payload->>'metodo_pagamento',
        'causale',
          'Vendita ' || v_product.nome
          || ' x ' || v_quantity,
        'note', payload->>'note',
        'genera_ricevuta',
          coalesce(
            (payload->>'genera_ricevuta')::boolean,
            false
          )
      )
    );

  v_income_id := (v_income_result->>'incasso_id')::uuid;
  v_receipt_id :=
    nullif(v_income_result->>'ricevuta_id', '')::uuid;

  insert into gestionale_v2.righe_vendita_prodotti (
    azienda_id,
    incasso_id,
    prodotto_id,
    quantita,
    prezzo_unitario,
    totale
  )
  values (
    (payload->>'azienda_id')::uuid,
    v_income_id,
    v_product.prodotto_id,
    v_quantity,
    v_price,
    v_total
  );

  insert into gestionale_v2.movimenti_magazzino (
    azienda_id,
    prodotto_id,
    cliente_id,
    incasso_id,
    data_movimento,
    tipo,
    quantita,
    prezzo_unitario,
    causale,
    note
  )
  values (
    (payload->>'azienda_id')::uuid,
    v_product.prodotto_id,
    (payload->>'cliente_id')::uuid,
    v_income_id,
    (payload->>'data_vendita')::date,
    'vendita',
    -v_quantity,
    v_price,
    'Vendita prodotto',
    nullif(payload->>'note', '')
  )
  returning id into v_movement_id;

  v_new_stock := v_stock - v_quantity;

  return jsonb_build_object(
    'incasso_id', v_income_id,
    'ricevuta_id', v_receipt_id,
    'movimento_id', v_movement_id,
    'totale', v_total,
    'nuova_giacenza', v_new_stock
  );
end;
$$;


create or replace function gestionale_v2.registra_acquisto_magazzino(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_stock numeric(12,3);
  v_quantity numeric(12,3);
  v_id uuid;
begin
  v_quantity := (payload->>'quantita')::numeric;

  if v_quantity <= 0 then
    raise exception 'Quantità non valida';
  end if;

  select giacenza
  into v_stock
  from gestionale_v2.vista_prodotti_magazzino
  where prodotto_id = (payload->>'prodotto_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if v_stock is null then
    raise exception 'Prodotto non trovato';
  end if;

  insert into gestionale_v2.movimenti_magazzino (
    azienda_id,
    prodotto_id,
    fornitore_id,
    data_movimento,
    tipo,
    quantita,
    costo_unitario,
    documento,
    lotto,
    data_scadenza_lotto,
    causale,
    note
  )
  values (
    (payload->>'azienda_id')::uuid,
    (payload->>'prodotto_id')::uuid,
    nullif(payload->>'fornitore_id', '')::uuid,
    (payload->>'data_movimento')::date,
    'acquisto',
    v_quantity,
    coalesce((payload->>'costo_unitario')::numeric, 0),
    nullif(payload->>'documento', ''),
    nullif(payload->>'lotto', ''),
    nullif(payload->>'data_scadenza_lotto', '')::date,
    'Acquisto prodotto',
    nullif(payload->>'note', '')
  )
  returning id into v_id;

  return jsonb_build_object(
    'movimento_id', v_id,
    'nuova_giacenza', v_stock + v_quantity
  );
end;
$$;


create or replace function gestionale_v2.registra_rettifica_magazzino(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_stock numeric(12,3);
  v_quantity numeric(12,3);
  v_id uuid;
begin
  v_quantity := (payload->>'quantita')::numeric;

  if v_quantity = 0 then
    raise exception 'Quantità non valida';
  end if;

  if nullif(trim(payload->>'causale'), '') is null then
    raise exception 'La motivazione è obbligatoria';
  end if;

  select giacenza
  into v_stock
  from gestionale_v2.vista_prodotti_magazzino
  where prodotto_id = (payload->>'prodotto_id')::uuid
    and azienda_id = (payload->>'azienda_id')::uuid;

  if v_stock is null then
    raise exception 'Prodotto non trovato';
  end if;

  if v_quantity < 0 and abs(v_quantity) > v_stock then
    raise exception 'La rettifica porterebbe la giacenza sotto zero';
  end if;

  insert into gestionale_v2.movimenti_magazzino (
    azienda_id,
    prodotto_id,
    data_movimento,
    tipo,
    quantita,
    causale
  )
  values (
    (payload->>'azienda_id')::uuid,
    (payload->>'prodotto_id')::uuid,
    (payload->>'data_movimento')::date,
    case
      when v_quantity > 0
        then 'rettifica_positiva'
      else 'rettifica_negativa'
    end,
    v_quantity,
    trim(payload->>'causale')
  )
  returning id into v_id;

  return jsonb_build_object(
    'movimento_id', v_id,
    'nuova_giacenza', v_stock + v_quantity
  );
end;
$$;


create or replace function gestionale_v2.annulla_movimento_magazzino(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_original record;
  v_storno_id uuid;
begin
  if nullif(trim(payload->>'motivo'), '') is null then
    raise exception 'Il motivo è obbligatorio';
  end if;

  select *
  into v_original
  from gestionale_v2.movimenti_magazzino m
  where m.id = (payload->>'movimento_id')::uuid
    and m.azienda_id = (payload->>'azienda_id')::uuid
    and m.stato = 'valido'
  for update;

  if v_original.id is null then
    raise exception 'Movimento non trovato o già annullato';
  end if;

  update gestionale_v2.movimenti_magazzino
  set stato = 'annullato'
  where id = v_original.id;

  insert into gestionale_v2.movimenti_magazzino (
    azienda_id,
    prodotto_id,
    cliente_id,
    fornitore_id,
    incasso_id,
    spesa_id,
    movimento_origine_id,
    data_movimento,
    tipo,
    quantita,
    costo_unitario,
    prezzo_unitario,
    documento,
    lotto,
    data_scadenza_lotto,
    causale,
    note
  )
  values (
    v_original.azienda_id,
    v_original.prodotto_id,
    v_original.cliente_id,
    v_original.fornitore_id,
    v_original.incasso_id,
    v_original.spesa_id,
    v_original.id,
    current_date,
    'storno',
    -v_original.quantita,
    v_original.costo_unitario,
    v_original.prezzo_unitario,
    v_original.documento,
    v_original.lotto,
    v_original.data_scadenza_lotto,
    'Storno: ' || trim(payload->>'motivo'),
    v_original.note
  )
  returning id into v_storno_id;

  return jsonb_build_object(
    'movimento_annullato_id', v_original.id,
    'storno_id', v_storno_id
  );
end;
$$;


create or replace function gestionale_v2.storna_magazzino_incasso_annullato()
returns trigger
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_movement record;
begin
  if old.stato = 'valido'
     and new.stato = 'annullato'
     and new.tipo_incasso = 'vendita_prodotto' then

    for v_movement in
      select *
      from gestionale_v2.movimenti_magazzino m
      where m.incasso_id = new.id
        and m.stato = 'valido'
        and m.tipo = 'vendita'
    loop
      update gestionale_v2.movimenti_magazzino
      set stato = 'annullato'
      where id = v_movement.id;

      insert into gestionale_v2.movimenti_magazzino (
        azienda_id,
        prodotto_id,
        cliente_id,
        incasso_id,
        movimento_origine_id,
        data_movimento,
        tipo,
        quantita,
        prezzo_unitario,
        causale
      )
      values (
        v_movement.azienda_id,
        v_movement.prodotto_id,
        v_movement.cliente_id,
        new.id,
        v_movement.id,
        current_date,
        'storno',
        -v_movement.quantita,
        v_movement.prezzo_unitario,
        'Storno automatico per annullamento incasso'
      );
    end loop;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_storno_magazzino_incasso
on gestionale_v2.incassi;

create trigger trg_storno_magazzino_incasso
after update of stato on gestionale_v2.incassi
for each row
execute function gestionale_v2.storna_magazzino_incasso_annullato();


grant execute
on function gestionale_v2.salva_prodotto_magazzino(jsonb)
to service_role;

grant execute
on function gestionale_v2.registra_vendita_magazzino(jsonb)
to service_role;

grant execute
on function gestionale_v2.registra_acquisto_magazzino(jsonb)
to service_role;

grant execute
on function gestionale_v2.registra_rettifica_magazzino(jsonb)
to service_role;

grant execute
on function gestionale_v2.annulla_movimento_magazzino(jsonb)
to service_role;

grant select
on gestionale_v2.vista_prodotti_magazzino
to service_role;

grant select
on gestionale_v2.vista_movimenti_magazzino
to service_role;

commit;

notify pgrst, 'reload schema';
