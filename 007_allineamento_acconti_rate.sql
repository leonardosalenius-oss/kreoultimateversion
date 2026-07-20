begin;

create or replace function gestionale_v2.crea_cliente_completo(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_abbonamento_id uuid;
  v_incasso_id uuid;
  v_doc jsonb;
  v_rata jsonb;
  v_tipo_documento_id uuid;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;

  insert into gestionale_v2.clienti (
    azienda_id,
    nome,
    cognome,
    telefono,
    whatsapp,
    email,
    codice_fiscale,
    partita_iva,
    indirizzo,
    note
  )
  values (
    v_azienda_id,
    payload->'cliente'->>'nome',
    payload->'cliente'->>'cognome',
    nullif(payload->'cliente'->>'telefono', ''),
    nullif(payload->'cliente'->>'whatsapp', ''),
    nullif(payload->'cliente'->>'email', ''),
    nullif(payload->'cliente'->>'codice_fiscale', ''),
    nullif(payload->'cliente'->>'partita_iva', ''),
    nullif(payload->'cliente'->>'indirizzo', ''),
    nullif(payload->'cliente'->>'note', '')
  )
  returning id into v_cliente_id;

  insert into gestionale_v2.abbonamenti (
    azienda_id,
    cliente_id,
    pacchetto_id,
    data_inizio,
    data_fine_prevista,
    prezzo_concordato,
    lezioni_iniziali,
    tipologia_pagamento,
    stato
  )
  values (
    v_azienda_id,
    v_cliente_id,
    (payload->'abbonamento'->>'pacchetto_id')::uuid,
    (payload->'abbonamento'->>'data_inizio')::date,
    (payload->'abbonamento'->>'data_fine_prevista')::date,
    (payload->'abbonamento'->>'prezzo_concordato')::numeric,
    coalesce(
      (payload->'abbonamento'->>'lezioni_iniziali')::integer,
      0
    ),
    payload->'abbonamento'->>'tipologia_pagamento',
    'attivo'
  )
  returning id into v_abbonamento_id;

  for v_rata in
    select value
    from jsonb_array_elements(payload->'rate')
  loop
    insert into gestionale_v2.rate (
      azienda_id,
      abbonamento_id,
      numero_rata,
      data_scadenza,
      importo_previsto
    )
    values (
      v_azienda_id,
      v_abbonamento_id,
      (v_rata->>'numero_rata')::integer,
      (v_rata->>'data_scadenza')::date,
      (v_rata->>'importo_previsto')::numeric
    );
  end loop;

  if payload->'incasso_iniziale' is not null then
    insert into gestionale_v2.incassi (
      azienda_id,
      cliente_id,
      abbonamento_id,
      importo,
      metodo_pagamento,
      tipo_incasso,
      causale,
      stato
    )
    values (
      v_azienda_id,
      v_cliente_id,
      v_abbonamento_id,
      (payload->'incasso_iniziale'->>'importo')::numeric,
      payload->'incasso_iniziale'->>'metodo_pagamento',
      'abbonamento',
      coalesce(
        payload->'incasso_iniziale'->>'causale',
        'Acconto iniziale'
      ),
      'valido'
    )
    returning id into v_incasso_id;
  end if;

  -- Unica logica economica:
  -- ogni incasso valido, compreso l'acconto iniziale,
  -- viene allocato alle rate tramite lo stesso motore.
  perform gestionale_v2.ricalcola_allocazioni_abbonamento(
    v_abbonamento_id
  );

  for v_doc in
    select value
    from jsonb_array_elements(
      coalesce(payload->'documenti', '[]'::jsonb)
    )
  loop
    select id
    into v_tipo_documento_id
    from gestionale_v2.tipi_documento
    where azienda_id = v_azienda_id
      and nome = v_doc->>'tipo'
    limit 1;

    if v_tipo_documento_id is not null then
      insert into gestionale_v2.documenti_clienti (
        azienda_id,
        cliente_id,
        abbonamento_id,
        tipo_documento_id,
        data_documento,
        data_scadenza,
        stato
      )
      values (
        v_azienda_id,
        v_cliente_id,
        case
          when v_doc->>'tipo' = 'Contratto'
          then v_abbonamento_id
          else null
        end,
        v_tipo_documento_id,
        nullif(v_doc->>'data_documento', '')::date,
        nullif(v_doc->>'data_scadenza', '')::date,
        'da_verificare'
      );
    end if;
  end loop;

  return jsonb_build_object(
    'cliente_id', v_cliente_id,
    'abbonamento_id', v_abbonamento_id,
    'incasso_id', v_incasso_id
  );
end;
$$;

grant execute
on function gestionale_v2.crea_cliente_completo(jsonb)
to service_role;

-- Riallinea tutti gli abbonamenti già esistenti.
do $$
declare
  v_abbonamento_id uuid;
begin
  for v_abbonamento_id in
    select id
    from gestionale_v2.abbonamenti
    where stato <> 'annullato'
  loop
    perform gestionale_v2.ricalcola_allocazioni_abbonamento(
      v_abbonamento_id
    );
  end loop;
end;
$$;

commit;

notify pgrst, 'reload schema';
