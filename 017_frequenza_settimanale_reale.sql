begin;

create or replace function gestionale_v2.calcola_lezioni_contrattuali(
  p_pacchetto_id uuid,
  p_data_inizio date,
  p_data_fine date
)
returns integer
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_modalita text;
  v_lezioni_per_periodo integer;
  v_lezioni_totali integer;
  v_durata_numero integer;
  v_giorni integer;
begin
  if p_data_fine < p_data_inizio then
    raise exception 'La data fine precede la data inizio';
  end if;

  select
    p.modalita_lezioni,
    coalesce(p.lezioni_per_periodo, 0),
    coalesce(p.lezioni_totali, 0),
    coalesce(p.durata_numero, 1)
  into
    v_modalita,
    v_lezioni_per_periodo,
    v_lezioni_totali,
    v_durata_numero
  from gestionale_v2.pacchetti p
  where p.id = p_pacchetto_id;

  if v_modalita is null then
    raise exception 'Pacchetto non trovato';
  end if;

  if v_modalita = 'Pacchetto lezioni' then
    return v_lezioni_totali;
  end if;

  if v_modalita = 'Settimanale' then
    v_giorni := (p_data_fine - p_data_inizio) + 1;

    return round(
      (
        v_giorni::numeric
        * v_lezioni_per_periodo::numeric
      ) / 7
    )::integer;
  end if;

  if v_modalita = 'Mensile' then
    return v_lezioni_per_periodo * v_durata_numero;
  end if;

  raise exception 'Modalità lezioni non valida';
end;
$$;


create or replace function gestionale_v2.calcola_lezioni_contrattuali_rpc(
  payload jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_lessons integer;
begin
  v_lessons := gestionale_v2.calcola_lezioni_contrattuali(
    (payload->>'pacchetto_id')::uuid,
    (payload->>'data_inizio')::date,
    (payload->>'data_fine')::date
  );

  return jsonb_build_object(
    'lezioni_contrattuali',
    v_lessons
  );
end;
$$;


create or replace function gestionale_v2.crea_cliente_completo(
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
  v_abbonamento_id uuid;
  v_incasso_id uuid;
  v_doc jsonb;
  v_rata jsonb;
  v_tipo_documento_id uuid;
  v_pacchetto_id uuid;
  v_data_inizio date;
  v_data_fine date;
  v_lezioni_contrattuali integer;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_pacchetto_id :=
    (payload->'abbonamento'->>'pacchetto_id')::uuid;
  v_data_inizio :=
    (payload->'abbonamento'->>'data_inizio')::date;
  v_data_fine :=
    (payload->'abbonamento'->>'data_fine_prevista')::date;

  v_lezioni_contrattuali :=
    gestionale_v2.calcola_lezioni_contrattuali(
      v_pacchetto_id,
      v_data_inizio,
      v_data_fine
    );

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
    v_pacchetto_id,
    v_data_inizio,
    v_data_fine,
    (payload->'abbonamento'->>'prezzo_concordato')::numeric,
    v_lezioni_contrattuali,
    payload->'abbonamento'->>'tipologia_pagamento',
    case
      when v_data_inizio > current_date then 'da_attivare'
      else 'attivo'
    end
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
    'incasso_id', v_incasso_id,
    'lezioni_contrattuali', v_lezioni_contrattuali
  );
end;
$$;


create or replace function gestionale_v2.crea_abbonamento_cliente(
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
  v_abbonamento_id uuid;
  v_rata jsonb;
  v_incasso_id uuid;
  v_totale_rate numeric;
  v_prezzo numeric;
  v_pacchetto_id uuid;
  v_data_inizio date;
  v_data_fine date;
  v_lezioni_contrattuali integer;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_prezzo := (payload->>'prezzo_concordato')::numeric;
  v_pacchetto_id := (payload->>'pacchetto_id')::uuid;
  v_data_inizio := (payload->>'data_inizio')::date;
  v_data_fine := (payload->>'data_fine_prevista')::date;

  v_lezioni_contrattuali :=
    gestionale_v2.calcola_lezioni_contrattuali(
      v_pacchetto_id,
      v_data_inizio,
      v_data_fine
    );

  if not exists (
    select 1
    from gestionale_v2.clienti c
    where c.id = v_cliente_id
      and c.azienda_id = v_azienda_id
      and c.stato <> 'annullato'
  ) then
    raise exception 'Cliente non trovato';
  end if;

  select coalesce(
    sum((value->>'importo_previsto')::numeric),
    0
  )
  into v_totale_rate
  from jsonb_array_elements(payload->'rate');

  if abs(v_totale_rate - v_prezzo) > 0.01 then
    raise exception 'La somma delle rate non coincide con il prezzo';
  end if;

  insert into gestionale_v2.abbonamenti (
    azienda_id,
    cliente_id,
    pacchetto_id,
    abbonamento_precedente_id,
    data_inizio,
    data_fine_prevista,
    prezzo_concordato,
    lezioni_iniziali,
    tipologia_pagamento,
    note,
    stato
  )
  values (
    v_azienda_id,
    v_cliente_id,
    v_pacchetto_id,
    nullif(payload->>'abbonamento_precedente_id', '')::uuid,
    v_data_inizio,
    v_data_fine,
    v_prezzo,
    v_lezioni_contrattuali,
    payload->>'tipologia_pagamento',
    nullif(payload->>'note', ''),
    case
      when v_data_inizio > current_date then 'da_attivare'
      else 'attivo'
    end
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

  if payload->'pagamento_iniziale' is not null then
    insert into gestionale_v2.incassi (
      azienda_id,
      cliente_id,
      abbonamento_id,
      data_incasso,
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
      (payload->'pagamento_iniziale'->>'data_incasso')::date,
      (payload->'pagamento_iniziale'->>'importo')::numeric,
      payload->'pagamento_iniziale'->>'metodo_pagamento',
      'abbonamento',
      coalesce(
        payload->'pagamento_iniziale'->>'causale',
        'Acconto abbonamento'
      ),
      'valido'
    )
    returning id into v_incasso_id;
  end if;

  perform gestionale_v2.ricalcola_allocazioni_abbonamento(
    v_abbonamento_id
  );

  insert into gestionale_v2.eventi_stato_abbonamento (
    azienda_id,
    abbonamento_id,
    stato_precedente,
    stato_successivo,
    azione,
    data_evento,
    motivo
  )
  select
    v_azienda_id,
    v_abbonamento_id,
    null,
    a.stato,
    'Creazione',
    a.data_inizio,
    'Creazione abbonamento'
  from gestionale_v2.abbonamenti a
  where a.id = v_abbonamento_id;

  insert into gestionale_v2.audit_log (
    azienda_id,
    tabella,
    record_id,
    azione,
    valore_successivo
  )
  values (
    v_azienda_id,
    'abbonamenti',
    v_abbonamento_id,
    'creazione',
    payload
  );

  return jsonb_build_object(
    'abbonamento_id', v_abbonamento_id,
    'incasso_id', v_incasso_id,
    'lezioni_contrattuali', v_lezioni_contrattuali
  );
end;
$$;


create or replace function gestionale_v2.aggiorna_abbonamento_cliente(
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
  v_abbonamento_id uuid;
  v_precedente jsonb;
  v_successivo jsonb;
  v_pagato numeric;
  v_totale_rate_attive numeric;
  v_nuovo_prezzo numeric;
  v_gestione_rate text;
  v_pacchetto_id uuid;
  v_data_inizio date;
  v_data_fine date;
  v_lezioni_contrattuali integer;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_abbonamento_id := (payload->>'abbonamento_id')::uuid;
  v_nuovo_prezzo := (payload->>'prezzo_concordato')::numeric;
  v_gestione_rate := payload->>'gestione_rate';
  v_pacchetto_id := (payload->>'pacchetto_id')::uuid;
  v_data_inizio := (payload->>'data_inizio')::date;
  v_data_fine := (payload->>'data_fine_prevista')::date;

  v_lezioni_contrattuali :=
    gestionale_v2.calcola_lezioni_contrattuali(
      v_pacchetto_id,
      v_data_inizio,
      v_data_fine
    );

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
    raise exception 'Il prezzo non può essere inferiore al pagato';
  end if;

  if v_gestione_rate = 'Lascia invariato' then
    select coalesce(sum(importo_previsto), 0)
    into v_totale_rate_attive
    from gestionale_v2.rate
    where abbonamento_id = v_abbonamento_id
      and annullata = false;

    if abs(v_totale_rate_attive - v_nuovo_prezzo) > 0.01 then
      raise exception 'Il prezzo non coincide con il piano rate';
    end if;
  end if;

  update gestionale_v2.abbonamenti
  set
    pacchetto_id = v_pacchetto_id,
    data_inizio = v_data_inizio,
    data_fine_prevista = v_data_fine,
    prezzo_concordato = v_nuovo_prezzo,
    lezioni_iniziali = v_lezioni_contrattuali,
    tipologia_pagamento = payload->>'tipologia_pagamento',
    stato = payload->>'stato',
    note = nullif(payload->>'note', '')
  where id = v_abbonamento_id;

  if v_gestione_rate = 'Rigenera solo le rate aperte' then
    update gestionale_v2.rate r
    set
      annullata = true,
      motivo_annullamento = 'Rigenerazione piano rate'
    where r.abbonamento_id = v_abbonamento_id
      and r.annullata = false
      and coalesce((
        select sum(a.importo_allocato)
        from gestionale_v2.allocazioni_incassi_rate a
        where a.rata_id = r.id
      ), 0) = 0;
  end if;

  perform gestionale_v2.ricalcola_allocazioni_abbonamento(
    v_abbonamento_id
  );

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

  return jsonb_build_object(
    'abbonamento_id', v_abbonamento_id,
    'lezioni_contrattuali', v_lezioni_contrattuali
  );
end;
$$;


create or replace function gestionale_v2.controlla_limite_settimanale_lezioni()
returns trigger
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_modalita text;
  v_limite integer;
  v_tipologia text;
  v_data date;
  v_usate integer;
begin
  if new.stato <> 'valido'
     or new.quantita >= 0
     or new.prenotazione_id is null
     or new.tipo <> 'Presenza' then
    return new;
  end if;

  select
    p.tipologia,
    p.data_prenotazione,
    pac.modalita_lezioni,
    pac.lezioni_per_periodo
  into
    v_tipologia,
    v_data,
    v_modalita,
    v_limite
  from gestionale_v2.prenotazioni p
  join gestionale_v2.abbonamenti a
    on a.id = p.abbonamento_id
  join gestionale_v2.pacchetti pac
    on pac.id = a.pacchetto_id
  where p.id = new.prenotazione_id;

  if v_modalita <> 'Settimanale'
     or v_tipologia <> 'Lezione ordinaria' then
    return new;
  end if;

  select count(*)
  into v_usate
  from gestionale_v2.movimenti_lezioni m
  join gestionale_v2.prenotazioni p
    on p.id = m.prenotazione_id
  where m.abbonamento_id = new.abbonamento_id
    and m.stato = 'valido'
    and m.tipo = 'Presenza'
    and m.quantita < 0
    and p.tipologia = 'Lezione ordinaria'
    and date_trunc('week', p.data_prenotazione::timestamp)
      = date_trunc('week', v_data::timestamp);

  if v_usate >= v_limite then
    raise exception
      'Limite settimanale raggiunto: % lezioni ordinarie',
      v_limite;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_limite_settimanale_lezioni
on gestionale_v2.movimenti_lezioni;

create trigger trg_limite_settimanale_lezioni
before insert on gestionale_v2.movimenti_lezioni
for each row
execute function gestionale_v2.controlla_limite_settimanale_lezioni();


-- Riallineamento degli abbonamenti settimanali esistenti.
-- Il saldo si aggiorna automaticamente perché deriva da lezioni_iniziali
-- più i movimenti già registrati.
update gestionale_v2.abbonamenti a
set lezioni_iniziali =
  gestionale_v2.calcola_lezioni_contrattuali(
    a.pacchetto_id,
    a.data_inizio,
    a.data_fine_prevista
  )
from gestionale_v2.pacchetti p
where p.id = a.pacchetto_id
  and p.modalita_lezioni = 'Settimanale'
  and a.stato <> 'annullato';


grant execute
on function gestionale_v2.calcola_lezioni_contrattuali(
  uuid,
  date,
  date
)
to service_role;

grant execute
on function gestionale_v2.calcola_lezioni_contrattuali_rpc(jsonb)
to service_role;

grant execute
on function gestionale_v2.crea_cliente_completo(jsonb)
to service_role;

grant execute
on function gestionale_v2.crea_abbonamento_cliente(jsonb)
to service_role;

grant execute
on function gestionale_v2.aggiorna_abbonamento_cliente(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
