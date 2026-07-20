begin;

create or replace function gestionale_v2.modifica_anagrafica_cliente(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_precedente jsonb;
  v_successivo jsonb;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;

  select to_jsonb(c)
  into v_precedente
  from gestionale_v2.clienti c
  where c.id = v_cliente_id
    and c.azienda_id = v_azienda_id;

  if v_precedente is null then
    raise exception 'Cliente non trovato';
  end if;

  update gestionale_v2.clienti
  set
    nome = payload->>'nome',
    cognome = payload->>'cognome',
    telefono = nullif(payload->>'telefono', ''),
    whatsapp = nullif(payload->>'whatsapp', ''),
    email = nullif(payload->>'email', ''),
    codice_fiscale = nullif(payload->>'codice_fiscale', ''),
    partita_iva = nullif(payload->>'partita_iva', ''),
    indirizzo = nullif(payload->>'indirizzo', ''),
    stato = payload->>'stato',
    note = nullif(payload->>'note', '')
  where id = v_cliente_id
    and azienda_id = v_azienda_id;

  select to_jsonb(c)
  into v_successivo
  from gestionale_v2.clienti c
  where c.id = v_cliente_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    valore_successivo
  )
  values (
    v_azienda_id,
    'clienti',
    v_cliente_id,
    'modifica_anagrafica',
    v_precedente,
    v_successivo
  );

  return jsonb_build_object('cliente_id', v_cliente_id);
end;
$$;

create or replace function gestionale_v2.aggiorna_abbonamento_cliente(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_abbonamento_id uuid;
  v_precedente jsonb;
  v_successivo jsonb;
  v_pagato numeric;
  v_totale_rate_attive numeric;
  v_nuovo_prezzo numeric;
  v_gestione_rate text;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_abbonamento_id := (payload->>'abbonamento_id')::uuid;
  v_nuovo_prezzo := (payload->>'prezzo_concordato')::numeric;
  v_gestione_rate := payload->>'gestione_rate';

  select to_jsonb(a)
  into v_precedente
  from gestionale_v2.abbonamenti a
  where a.id = v_abbonamento_id
    and a.cliente_id = v_cliente_id
    and a.azienda_id = v_azienda_id;

  if v_precedente is null then
    raise exception 'Abbonamento non trovato';
  end if;

  select coalesce(sum(importo), 0)
  into v_pagato
  from gestionale_v2.incassi
  where abbonamento_id = v_abbonamento_id
    and stato = 'valido';

  if v_nuovo_prezzo < v_pagato then
    raise exception 'Il prezzo concordato non può essere inferiore al totale già pagato';
  end if;

  if v_gestione_rate = 'Lascia invariato' then
    select coalesce(sum(importo_previsto), 0)
    into v_totale_rate_attive
    from gestionale_v2.rate
    where abbonamento_id = v_abbonamento_id
      and annullata = false;

    if abs(v_totale_rate_attive - v_nuovo_prezzo) > 0.01 then
      raise exception 'Il nuovo prezzo non coincide con il piano rate attivo';
    end if;
  end if;

  update gestionale_v2.abbonamenti
  set
    pacchetto_id = (payload->>'pacchetto_id')::uuid,
    data_inizio = (payload->>'data_inizio')::date,
    data_fine_prevista = (payload->>'data_fine_prevista')::date,
    prezzo_concordato = v_nuovo_prezzo,
    lezioni_iniziali = (payload->>'lezioni_iniziali')::integer,
    tipologia_pagamento = payload->>'tipologia_pagamento',
    stato = payload->>'stato',
    note = nullif(payload->>'note', '')
  where id = v_abbonamento_id;

  if v_gestione_rate = 'Rigenera solo le rate aperte' then
    update gestionale_v2.rate r
    set annullata = true,
        motivo_annullamento = 'Rigenerazione piano rate'
    where r.abbonamento_id = v_abbonamento_id
      and r.annullata = false
      and coalesce((
        select sum(a.importo_allocato)
        from gestionale_v2.allocazioni_incassi_rate a
        where a.rata_id = r.id
      ), 0) = 0;
  end if;

  perform gestionale_v2.ricalcola_allocazioni_abbonamento(v_abbonamento_id);

  select to_jsonb(a)
  into v_successivo
  from gestionale_v2.abbonamenti a
  where a.id = v_abbonamento_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    valore_successivo
  )
  values (
    v_azienda_id,
    'abbonamenti',
    v_abbonamento_id,
    'modifica',
    v_precedente,
    v_successivo
  );

  return jsonb_build_object('abbonamento_id', v_abbonamento_id);
end;
$$;

create or replace function gestionale_v2.aggiorna_rate_abbonamento(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_abbonamento_id uuid;
  v_rata jsonb;
  v_importo_pagato numeric;
  v_totale_rate numeric;
  v_prezzo numeric;
  v_precedente jsonb;
  v_successivo jsonb;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_abbonamento_id := (payload->>'abbonamento_id')::uuid;

  select jsonb_agg(to_jsonb(r))
  into v_precedente
  from gestionale_v2.rate r
  where r.abbonamento_id = v_abbonamento_id;

  for v_rata in
    select value from jsonb_array_elements(payload->'rate')
  loop
    select coalesce(sum(a.importo_allocato), 0)
    into v_importo_pagato
    from gestionale_v2.allocazioni_incassi_rate a
    where a.rata_id = (v_rata->>'rata_id')::uuid;

    if (v_rata->>'importo_previsto')::numeric < v_importo_pagato then
      raise exception 'Una rata non può essere inferiore all''importo già pagato';
    end if;

    update gestionale_v2.rate
    set
      data_scadenza = (v_rata->>'data_scadenza')::date,
      importo_previsto = (v_rata->>'importo_previsto')::numeric,
      annullata = coalesce((v_rata->>'annullata')::boolean, false),
      motivo_annullamento = case
        when coalesce((v_rata->>'annullata')::boolean, false)
        then payload->>'motivo'
        else null
      end
    where id = (v_rata->>'rata_id')::uuid
      and abbonamento_id = v_abbonamento_id
      and azienda_id = v_azienda_id;
  end loop;

  select coalesce(sum(importo_previsto), 0)
  into v_totale_rate
  from gestionale_v2.rate
  where abbonamento_id = v_abbonamento_id
    and annullata = false;

  select prezzo_concordato
  into v_prezzo
  from gestionale_v2.abbonamenti
  where id = v_abbonamento_id
    and cliente_id = v_cliente_id
    and azienda_id = v_azienda_id;

  if abs(v_totale_rate - v_prezzo) > 0.01 then
    raise exception 'La somma delle rate attive deve coincidere con il prezzo concordato';
  end if;

  perform gestionale_v2.ricalcola_allocazioni_abbonamento(v_abbonamento_id);

  select jsonb_agg(to_jsonb(r))
  into v_successivo
  from gestionale_v2.rate r
  where r.abbonamento_id = v_abbonamento_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    valore_successivo,
    motivo
  )
  values (
    v_azienda_id,
    'rate',
    v_abbonamento_id,
    'modifica_piano_rate',
    v_precedente,
    v_successivo,
    payload->>'motivo'
  );

  return jsonb_build_object('abbonamento_id', v_abbonamento_id);
end;
$$;

create or replace function gestionale_v2.salva_documento_cliente(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_cliente_id uuid;
  v_tipo_id uuid;
  v_documento_id uuid;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;

  select id
  into v_tipo_id
  from gestionale_v2.tipi_documento
  where azienda_id = v_azienda_id
    and nome = payload->>'tipo'
  limit 1;

  if v_tipo_id is null then
    raise exception 'Tipo documento non trovato';
  end if;

  update gestionale_v2.documenti_clienti
  set
    stato = 'annullato',
    annullato_il = now(),
    motivo_annullamento = 'Sostituzione documento'
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id
    and tipo_documento_id = v_tipo_id
    and stato <> 'annullato';

  insert into gestionale_v2.documenti_clienti (
    azienda_id,
    cliente_id,
    abbonamento_id,
    tipo_documento_id,
    data_documento,
    data_scadenza,
    note,
    stato
  )
  values (
    v_azienda_id,
    v_cliente_id,
    nullif(payload->>'abbonamento_id', '')::uuid,
    v_tipo_id,
    (payload->>'data_documento')::date,
    nullif(payload->>'data_scadenza', '')::date,
    nullif(payload->>'note', ''),
    payload->>'stato'
  )
  returning id into v_documento_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo
  )
  values (
    v_azienda_id,
    'documenti_clienti',
    v_documento_id,
    'creazione_o_sostituzione',
    payload
  );

  return jsonb_build_object('documento_id', v_documento_id);
end;
$$;

create or replace function gestionale_v2.annulla_documento_cliente(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_documento_id uuid;
  v_precedente jsonb;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_documento_id := (payload->>'documento_id')::uuid;

  select to_jsonb(d)
  into v_precedente
  from gestionale_v2.documenti_clienti d
  where d.id = v_documento_id
    and d.azienda_id = v_azienda_id
    and d.stato <> 'annullato';

  if v_precedente is null then
    raise exception 'Documento non trovato';
  end if;

  update gestionale_v2.documenti_clienti
  set
    stato = 'annullato',
    annullato_il = now(),
    motivo_annullamento = payload->>'motivo'
  where id = v_documento_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_precedente,
    motivo
  )
  values (
    v_azienda_id,
    'documenti_clienti',
    v_documento_id,
    'annullamento',
    v_precedente,
    payload->>'motivo'
  );

  return jsonb_build_object('documento_id', v_documento_id);
end;
$$;

create or replace function gestionale_v2.get_cliente_dettaglio(p_cliente_id uuid)
returns jsonb
language sql
security definer
set search_path = gestionale_v2, public
as $$
  select jsonb_build_object(
    'cliente',
    (
      select to_jsonb(c)
      from gestionale_v2.clienti c
      where c.id = p_cliente_id
    ),
    'abbonamento',
    (
      select to_jsonb(x)
      from (
        select
          a.*,
          p.nome as pacchetto_nome,
          coalesce(sum(i.importo) filter (where i.stato = 'valido'), 0) as pagato,
          greatest(
            a.prezzo_concordato - coalesce(sum(i.importo) filter (where i.stato = 'valido'), 0),
            0
          ) as residuo
        from gestionale_v2.abbonamenti a
        join gestionale_v2.pacchetti p on p.id = a.pacchetto_id
        left join gestionale_v2.incassi i on i.abbonamento_id = a.id
        where a.cliente_id = p_cliente_id
          and a.stato <> 'annullato'
        group by a.id, p.nome
        order by a.data_inizio desc
        limit 1
      ) x
    ),
    'rate',
    coalesce((
      select jsonb_agg(
        to_jsonb(v) || jsonb_build_object('annullata', r.annullata)
        order by v.data_scadenza, v.numero_rata
      )
      from gestionale_v2.vista_rate_operativa v
      join gestionale_v2.rate r on r.id = v.rata_id
      where v.cliente_id = p_cliente_id
    ), '[]'::jsonb),
    'incassi',
    coalesce((
      select jsonb_agg(to_jsonb(v) order by v.data_incasso desc, v.created_at desc)
      from gestionale_v2.vista_incassi_operativa v
      where v.cliente_id = p_cliente_id
    ), '[]'::jsonb),
    'documenti',
    coalesce((
      select jsonb_agg(jsonb_build_object(
        'documento_id', dc.id,
        'tipo', td.nome,
        'data_documento', dc.data_documento,
        'data_scadenza', dc.data_scadenza,
        'stato', dc.stato,
        'note', dc.note
      ) order by td.nome, dc.created_at desc)
      from gestionale_v2.documenti_clienti dc
      join gestionale_v2.tipi_documento td on td.id = dc.tipo_documento_id
      where dc.cliente_id = p_cliente_id
    ), '[]'::jsonb),
    'audit',
    coalesce((
      select jsonb_agg(jsonb_build_object(
        'data', al.created_at,
        'tabella', al.tabella,
        'azione', al.azione,
        'motivo', al.motivo
      ) order by al.created_at desc)
      from gestionale_v2.audit_log al
      where al.record_id = p_cliente_id
         or al.record_id in (
           select a.id
           from gestionale_v2.abbonamenti a
           where a.cliente_id = p_cliente_id
         )
         or al.record_id in (
           select i.id
           from gestionale_v2.incassi i
           where i.cliente_id = p_cliente_id
         )
         or al.record_id in (
           select d.id
           from gestionale_v2.documenti_clienti d
           where d.cliente_id = p_cliente_id
         )
    ), '[]'::jsonb)
  );
$$;

grant execute on function gestionale_v2.modifica_anagrafica_cliente(jsonb) to service_role;
grant execute on function gestionale_v2.aggiorna_abbonamento_cliente(jsonb) to service_role;
grant execute on function gestionale_v2.aggiorna_rate_abbonamento(jsonb) to service_role;
grant execute on function gestionale_v2.salva_documento_cliente(jsonb) to service_role;
grant execute on function gestionale_v2.annulla_documento_cliente(jsonb) to service_role;
grant execute on function gestionale_v2.get_cliente_dettaglio(uuid) to service_role;

commit;

notify pgrst, 'reload schema';
