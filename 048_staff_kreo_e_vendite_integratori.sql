begin;

-- ============================================================
-- CLIENTE TECNICO STAFF KREO
-- ============================================================

alter table gestionale_v2.clienti
  add column if not exists tipo_soggetto text not null default 'cliente',
  add column if not exists escludi_da_report_clienti boolean not null default false,
  add column if not exists escludi_da_crm boolean not null default false,
  add column if not exists escludi_da_abbonamenti boolean not null default false;

alter table gestionale_v2.clienti
  drop constraint if exists clienti_tipo_soggetto_check;

alter table gestionale_v2.clienti
  add constraint clienti_tipo_soggetto_check
  check (tipo_soggetto in ('cliente', 'staff_tecnico'));

do $$
declare
  v_azienda uuid;
  v_staff_id uuid;
begin
  for v_azienda in
    select id from gestionale_v2.aziende
  loop
    select c.id
    into v_staff_id
    from gestionale_v2.clienti c
    where c.azienda_id = v_azienda
      and c.tipo_soggetto = 'staff_tecnico'
    order by c.created_at
    limit 1;

    if v_staff_id is null then
      insert into gestionale_v2.clienti (
        azienda_id,
        nome,
        cognome,
        note,
        stato,
        tipo_soggetto,
        escludi_da_report_clienti,
        escludi_da_crm,
        escludi_da_abbonamenti
      )
      values (
        v_azienda,
        '',
        'STAFF KREO',
        'Soggetto tecnico interno per test e operazioni staff.',
        'attivo',
        'staff_tecnico',
        true,
        true,
        true
      )
      returning id into v_staff_id;
    else
      update gestionale_v2.clienti
      set
        cognome = 'STAFF KREO',
        nome = '',
        stato = 'attivo',
        tipo_soggetto = 'staff_tecnico',
        escludi_da_report_clienti = true,
        escludi_da_crm = true,
        escludi_da_abbonamenti = true,
        updated_at = now()
      where id = v_staff_id;
    end if;
  end loop;
end $$;

create unique index if not exists uq_cliente_staff_tecnico_azienda
on gestionale_v2.clienti (azienda_id)
where tipo_soggetto = 'staff_tecnico';


-- ============================================================
-- METADATI STAFF SUI MOVIMENTI MAGAZZINO
-- ============================================================

alter table gestionale_v2.movimenti_magazzino
  add column if not exists staff_badge_id uuid
    references gestionale_v2.badge_staff(id) on delete set null,
  add column if not exists nominativo_staff text,
  add column if not exists tipo_operazione_staff text,
  add column if not exists note_staff text;

alter table gestionale_v2.movimenti_magazzino
  drop constraint if exists movimenti_magazzino_tipo_operazione_staff_check;

alter table gestionale_v2.movimenti_magazzino
  add constraint movimenti_magazzino_tipo_operazione_staff_check
  check (
    tipo_operazione_staff is null
    or tipo_operazione_staff in (
      'prezzo_normale',
      'prezzo_staff',
      'omaggio',
      'uso_interno',
      'test_rettifica'
    )
  );

create index if not exists idx_movimenti_magazzino_staff
on gestionale_v2.movimenti_magazzino (
  azienda_id,
  staff_badge_id,
  data_movimento desc
);


-- ============================================================
-- VIEW MOVIMENTI: aggiunge i nuovi campi in coda
-- ============================================================

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
    else trim(c.cognome || ' ' || c.nome)
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
  m.created_at,
  m.staff_badge_id,
  m.nominativo_staff,
  m.tipo_operazione_staff,
  m.note_staff
from gestionale_v2.movimenti_magazzino m
join gestionale_v2.prodotti_magazzino p
  on p.id = m.prodotto_id
left join gestionale_v2.clienti c
  on c.id = m.cliente_id
left join gestionale_v2.fornitori f
  on f.id = m.fornitore_id;

grant select
on gestionale_v2.vista_movimenti_magazzino
to service_role;


create or replace function gestionale_v2.get_cliente_staff_tecnico(
  p_azienda_id uuid
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_row gestionale_v2.clienti;
begin
  select *
  into v_row
  from gestionale_v2.clienti
  where azienda_id = p_azienda_id
    and tipo_soggetto = 'staff_tecnico'
    and stato = 'attivo'
  limit 1;

  if v_row.id is null then
    raise exception 'Cliente tecnico STAFF KREO non trovato';
  end if;

  return jsonb_build_object(
    'id', v_row.id,
    'cliente_id', v_row.id,
    'nome', 'STAFF KREO',
    'tipo_soggetto', 'staff_tecnico'
  );
end;
$$;

grant execute
on function gestionale_v2.get_cliente_staff_tecnico(uuid)
to service_role;


-- ============================================================
-- VENDITA MAGAZZINO ESTESA:
-- normale cliente -> comportamento invariato
-- STAFF KREO -> richiede nominativo staff e tipo operazione
-- ============================================================

create or replace function gestionale_v2.registra_vendita_magazzino(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_righe jsonb;
  v_riga jsonb;
  v_prodotto_id uuid;
  v_quantita numeric(12,3);
  v_prezzo_unitario numeric(12,4);
  v_giacenza numeric(12,3);
  v_nome_prodotto text;
  v_totale_lordo numeric(12,2) := 0;
  v_sconto numeric(12,2) := 0;
  v_totale_netto numeric(12,2);
  v_numero_righe integer := 0;
  v_descrizione text := '';
  v_incasso_result jsonb;
  v_incasso_id uuid;
  v_ricevuta_id uuid;

  v_tipo_soggetto text;
  v_is_staff boolean := false;
  v_staff_badge_id uuid;
  v_staff_nome text;
  v_staff_tipo text;
  v_staff_note text;
  v_zero_value boolean := false;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_sconto := coalesce((payload->>'sconto')::numeric, 0);

  select c.tipo_soggetto
  into v_tipo_soggetto
  from gestionale_v2.clienti c
  where c.id = v_cliente_id
    and c.azienda_id = v_azienda_id
    and c.stato = 'attivo';

  if v_tipo_soggetto is null then
    raise exception 'Cliente non attivo o non trovato';
  end if;

  v_is_staff := v_tipo_soggetto = 'staff_tecnico';

  if v_is_staff then
    v_staff_badge_id := nullif(payload->>'staff_badge_id', '')::uuid;
    v_staff_tipo := coalesce(
      nullif(trim(payload->>'tipo_operazione_staff'), ''),
      'prezzo_normale'
    );
    v_staff_note := nullif(trim(payload->>'note_staff'), '');

    select s.nome
    into v_staff_nome
    from gestionale_v2.badge_staff s
    where s.id = v_staff_badge_id
      and s.azienda_id = v_azienda_id
      and s.attivo = true;

    if v_staff_nome is null then
      raise exception 'Per STAFF KREO devi indicare chi ha effettuato l''acquisto/uscita';
    end if;

    if v_staff_tipo not in (
      'prezzo_normale',
      'prezzo_staff',
      'omaggio',
      'uso_interno',
      'test_rettifica'
    ) then
      raise exception 'Tipo operazione staff non valido';
    end if;

    v_zero_value := v_staff_tipo in (
      'omaggio',
      'uso_interno',
      'test_rettifica'
    );

    if v_staff_note is null then
      raise exception 'Per le operazioni STAFF la nota è obbligatoria';
    end if;
  end if;

  if jsonb_typeof(payload->'righe') = 'array' then
    v_righe := payload->'righe';
  else
    v_righe := jsonb_build_array(
      jsonb_build_object(
        'prodotto_id', payload->>'prodotto_id',
        'quantita', payload->>'quantita',
        'prezzo_unitario', payload->>'prezzo_unitario'
      )
    );
  end if;

  if jsonb_array_length(v_righe) = 0 then
    raise exception 'La vendita non contiene prodotti';
  end if;

  create temporary table if not exists tmp_vendita_magazzino (
    prodotto_id uuid,
    nome text,
    quantita numeric(12,3),
    prezzo_unitario numeric(12,4),
    totale numeric(12,2)
  ) on commit drop;

  truncate table tmp_vendita_magazzino;

  for v_riga in
    select value
    from jsonb_array_elements(v_righe)
  loop
    v_prodotto_id := (v_riga->>'prodotto_id')::uuid;
    v_quantita := (v_riga->>'quantita')::numeric;
    v_prezzo_unitario :=
      case
        when v_zero_value then 0
        else (v_riga->>'prezzo_unitario')::numeric
      end;

    if v_quantita <= 0 then
      raise exception 'Quantità non valida';
    end if;
    if not v_zero_value and v_prezzo_unitario <= 0 then
      raise exception 'Prezzo unitario non valido';
    end if;

    select p.nome
    into v_nome_prodotto
    from gestionale_v2.prodotti_magazzino p
    where p.id = v_prodotto_id
      and p.azienda_id = v_azienda_id
      and p.attivo = true
    for update;

    if v_nome_prodotto is null then
      raise exception 'Prodotto non trovato o inattivo';
    end if;

    select coalesce(sum(m.quantita), 0)
    into v_giacenza
    from gestionale_v2.movimenti_magazzino m
    where m.azienda_id = v_azienda_id
      and m.prodotto_id = v_prodotto_id
      and m.stato = 'valido';

    if v_quantita > v_giacenza then
      raise exception
        'Giacenza insufficiente per %: disponibile %, richiesta %',
        v_nome_prodotto,
        v_giacenza,
        v_quantita;
    end if;

    insert into tmp_vendita_magazzino (
      prodotto_id,
      nome,
      quantita,
      prezzo_unitario,
      totale
    )
    values (
      v_prodotto_id,
      v_nome_prodotto,
      v_quantita,
      v_prezzo_unitario,
      round(v_quantita * v_prezzo_unitario, 2)
    );

    v_totale_lordo :=
      v_totale_lordo
      + round(v_quantita * v_prezzo_unitario, 2);
    v_numero_righe := v_numero_righe + 1;

    v_descrizione := concat_ws(
      ', ',
      nullif(v_descrizione, ''),
      v_nome_prodotto || ' x ' || v_quantita
    );
  end loop;

  if not v_zero_value then
    if v_sconto < 0 or v_sconto >= v_totale_lordo then
      raise exception 'Sconto non valido';
    end if;

    if v_sconto > 0
       and nullif(trim(payload->>'motivo_sconto'), '') is null then
      raise exception 'Motivazione sconto obbligatoria';
    end if;

    v_totale_netto := round(v_totale_lordo - v_sconto, 2);

    v_incasso_result :=
      gestionale_v2.registra_incasso_completo(
        jsonb_build_object(
          'azienda_id', v_azienda_id,
          'cliente_id', v_cliente_id,
          'abbonamento_id', null,
          'tipo_incasso', 'vendita_prodotto',
          'data_incasso', payload->>'data_vendita',
          'importo', v_totale_netto,
          'metodo_pagamento', payload->>'metodo_pagamento',
          'causale',
            case
              when v_is_staff
              then 'Vendita STAFF KREO - ' || v_staff_nome || ': ' || v_descrizione
              else 'Vendita prodotti: ' || v_descrizione
            end,
          'note',
            concat_ws(
              E'\n',
              nullif(payload->>'note', ''),
              case
                when v_is_staff
                then 'Staff: ' || v_staff_nome
                     || ' · Tipo: ' || v_staff_tipo
                     || ' · ' || v_staff_note
                else null
              end,
              case
                when v_sconto > 0
                then 'Motivo sconto: ' || (payload->>'motivo_sconto')
                else null
              end
            ),
          'genera_ricevuta',
            coalesce(
              (payload->>'genera_ricevuta')::boolean,
              false
            )
        )
      );

    v_incasso_id := (v_incasso_result->>'incasso_id')::uuid;
    v_ricevuta_id :=
      nullif(v_incasso_result->>'ricevuta_id', '')::uuid;

    insert into gestionale_v2.righe_vendita_prodotti (
      azienda_id,
      incasso_id,
      prodotto_id,
      quantita,
      prezzo_unitario,
      totale
    )
    select
      v_azienda_id,
      v_incasso_id,
      t.prodotto_id,
      t.quantita,
      t.prezzo_unitario,
      t.totale
    from tmp_vendita_magazzino t;
  else
    v_sconto := 0;
    v_totale_netto := 0;
    v_incasso_id := null;
    v_ricevuta_id := null;
  end if;

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
    note,
    staff_badge_id,
    nominativo_staff,
    tipo_operazione_staff,
    note_staff
  )
  select
    v_azienda_id,
    t.prodotto_id,
    v_cliente_id,
    v_incasso_id,
    (payload->>'data_vendita')::date,
    'vendita',
    -t.quantita,
    t.prezzo_unitario,
    case
      when v_is_staff
      then 'STAFF KREO - ' || v_staff_nome
      else 'Vendita multiprodotto'
    end,
    nullif(payload->>'note', ''),
    case when v_is_staff then v_staff_badge_id else null end,
    case when v_is_staff then v_staff_nome else null end,
    case when v_is_staff then v_staff_tipo else null end,
    case when v_is_staff then v_staff_note else null end
  from tmp_vendita_magazzino t;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo,
    motivo
  )
  values (
    v_azienda_id,
    'vendite_prodotti',
    coalesce(v_incasso_id, gen_random_uuid()),
    case
      when v_is_staff then 'vendita_staff'
      else 'vendita_multiprodotto'
    end,
    payload,
    case
      when v_is_staff then v_staff_note
      else nullif(payload->>'motivo_sconto', '')
    end
  );

  return jsonb_build_object(
    'incasso_id', v_incasso_id,
    'ricevuta_id', v_ricevuta_id,
    'numero_righe', v_numero_righe,
    'totale_lordo', v_totale_lordo,
    'sconto', v_sconto,
    'totale', v_totale_netto,
    'staff', case when v_is_staff then v_staff_nome else null end,
    'tipo_operazione_staff',
      case when v_is_staff then v_staff_tipo else null end
  );
end;
$$;

grant execute
on function gestionale_v2.registra_vendita_magazzino(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
