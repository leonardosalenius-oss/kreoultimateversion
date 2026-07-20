begin;

alter table gestionale_v2.incassi
  drop constraint if exists incassi_tipo_incasso_check;

alter table gestionale_v2.incassi
  add constraint incassi_tipo_incasso_check
  check (
    tipo_incasso in (
      'abbonamento',
      'vendita_prodotto',
      'servizio',
      'altro_ricavo'
    )
  );

create or replace function gestionale_v2.registra_incasso_completo(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_abbonamento_id uuid;
  v_tipo_incasso text;
  v_importo numeric;
  v_residuo numeric;
  v_nuovo_residuo numeric;
  v_incasso_id uuid;
  v_ricevuta_id uuid;
  v_numero integer;
  v_anno integer;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_tipo_incasso := payload->>'tipo_incasso';
  v_importo := (payload->>'importo')::numeric;

  if v_tipo_incasso not in (
    'abbonamento',
    'vendita_prodotto',
    'servizio',
    'altro_ricavo'
  ) then
    raise exception 'Tipo incasso non valido';
  end if;

  if v_importo <= 0 then
    raise exception 'Importo non valido';
  end if;

  if nullif(payload->>'causale', '') is null then
    raise exception 'La descrizione dell''incasso è obbligatoria';
  end if;

  if not exists (
    select 1
    from gestionale_v2.clienti c
    where c.id = v_cliente_id
      and c.azienda_id = v_azienda_id
      and c.stato <> 'annullato'
  ) then
    raise exception 'Cliente non trovato';
  end if;

  if v_tipo_incasso = 'abbonamento' then
    v_abbonamento_id := nullif(
      payload->>'abbonamento_id',
      ''
    )::uuid;

    if v_abbonamento_id is null then
      raise exception 'Abbonamento obbligatorio';
    end if;

    select greatest(
      a.prezzo_concordato
      - coalesce(
          sum(i.importo)
          filter (where i.stato = 'valido'),
          0
        ),
      0
    )
    into v_residuo
    from gestionale_v2.abbonamenti a
    left join gestionale_v2.incassi i
      on i.abbonamento_id = a.id
    where a.id = v_abbonamento_id
      and a.cliente_id = v_cliente_id
      and a.azienda_id = v_azienda_id
    group by a.prezzo_concordato;

    if v_residuo is null then
      raise exception 'Abbonamento non trovato';
    end if;

    if v_importo > v_residuo then
      raise exception 'L''incasso supera il residuo';
    end if;

  else
    -- I ricavi autonomi non devono mai essere collegati
    -- accidentalmente a un abbonamento.
    v_abbonamento_id := null;
    v_residuo := null;
  end if;

  insert into gestionale_v2.incassi (
    azienda_id,
    cliente_id,
    abbonamento_id,
    data_incasso,
    importo,
    metodo_pagamento,
    tipo_incasso,
    causale,
    note,
    stato
  )
  values (
    v_azienda_id,
    v_cliente_id,
    v_abbonamento_id,
    (payload->>'data_incasso')::date,
    v_importo,
    payload->>'metodo_pagamento',
    v_tipo_incasso,
    payload->>'causale',
    nullif(payload->>'note', ''),
    'valido'
  )
  returning id into v_incasso_id;

  if v_tipo_incasso = 'abbonamento' then
    perform gestionale_v2.ricalcola_allocazioni_abbonamento(
      v_abbonamento_id
    );
    v_nuovo_residuo := v_residuo - v_importo;
  else
    v_nuovo_residuo := null;
  end if;

  if coalesce(
    (payload->>'genera_ricevuta')::boolean,
    false
  ) then
    v_anno := extract(
      year from (payload->>'data_incasso')::date
    )::integer;

    select coalesce(max(numero_progressivo), 0) + 1
    into v_numero
    from gestionale_v2.ricevute
    where azienda_id = v_azienda_id
      and anno = v_anno;

    insert into gestionale_v2.ricevute (
      azienda_id,
      cliente_id,
      incasso_id,
      anno,
      numero_progressivo,
      data_emissione,
      importo,
      metodo_pagamento,
      causale
    )
    values (
      v_azienda_id,
      v_cliente_id,
      v_incasso_id,
      v_anno,
      v_numero,
      (payload->>'data_incasso')::date,
      v_importo,
      payload->>'metodo_pagamento',
      payload->>'causale'
    )
    returning id into v_ricevuta_id;
  end if;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo
  )
  values (
    v_azienda_id,
    'incassi',
    v_incasso_id,
    'creazione',
    jsonb_build_object(
      'cliente_id', v_cliente_id,
      'abbonamento_id', v_abbonamento_id,
      'tipo_incasso', v_tipo_incasso,
      'importo', v_importo,
      'causale', payload->>'causale'
    )
  );

  return jsonb_build_object(
    'incasso_id', v_incasso_id,
    'ricevuta_id', v_ricevuta_id,
    'tipo_incasso', v_tipo_incasso,
    'nuovo_residuo', v_nuovo_residuo
  );
end;
$$;

create or replace view gestionale_v2.vista_incassi_operativa
with (security_invoker = false)
as
select
  i.azienda_id,
  i.id as incasso_id,
  i.cliente_id,
  i.abbonamento_id,
  c.cognome || ' ' || c.nome as cliente,
  i.data_incasso,
  i.importo,
  i.metodo_pagamento,
  i.tipo_incasso,
  i.causale,
  i.note,
  i.stato,
  i.created_at,
  case
    when r.id is null then null
    else
      lpad(r.numero_progressivo::text, 4, '0')
      || '/'
      || r.anno::text
  end as ricevuta_numero
from gestionale_v2.incassi i
join gestionale_v2.clienti c
  on c.id = i.cliente_id
left join gestionale_v2.ricevute r
  on r.incasso_id = i.id;

grant execute
on function gestionale_v2.registra_incasso_completo(jsonb)
to service_role;

grant select
on gestionale_v2.vista_incassi_operativa
to service_role;

commit;

notify pgrst, 'reload schema';
