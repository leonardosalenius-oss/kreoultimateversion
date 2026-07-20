begin;

alter table gestionale_v2.aziende
  add column if not exists forma_giuridica text,
  add column if not exists indirizzo text,
  add column if not exists cap text,
  add column if not exists citta text,
  add column if not exists provincia text,
  add column if not exists pec text,
  add column if not exists codice_sdi text,
  add column if not exists sito_web text,
  add column if not exists iban text,
  add column if not exists banca text,
  add column if not exists intestazione_documenti text,
  add column if not exists dicitura_ricevuta text
    default 'Ricevuta non fiscale',
  add column if not exists footer_documenti text,
  add column if not exists prefisso_ricevute text,
  add column if not exists firma_path text,
  add column if not exists timbro_path text;

alter table gestionale_v2.ricevute
  add column if not exists pdf_path text,
  add column if not exists pdf_generato_il timestamptz,
  add column if not exists pdf_versione integer not null default 0,
  add column if not exists snapshot_dati jsonb;

create table if not exists gestionale_v2.utenti_aziende (
  id uuid primary key default gen_random_uuid(),
  utente_id uuid not null references auth.users(id) on delete cascade,
  azienda_id uuid not null references gestionale_v2.aziende(id) on delete cascade,
  ruolo text not null default 'operatore'
    check (ruolo in ('super_admin', 'admin', 'reception', 'operatore', 'lettura')),
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  unique (utente_id, azienda_id)
);

alter table gestionale_v2.utenti_aziende enable row level security;

grant select, insert, update, delete
on gestionale_v2.utenti_aziende
to service_role;

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values
(
  'asset-aziende',
  'asset-aziende',
  false,
  5242880,
  array['image/png', 'image/jpeg']
),
(
  'ricevute-pdf',
  'ricevute-pdf',
  false,
  10485760,
  array['application/pdf']
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

update gestionale_v2.aziende
set
  dicitura_ricevuta = coalesce(
    dicitura_ricevuta,
    'Ricevuta non fiscale'
  ),
  prefisso_ricevute = coalesce(
    nullif(prefisso_ricevute, ''),
    upper(left(regexp_replace(nome_visualizzato, '[^A-Za-z0-9]', '', 'g'), 6))
  )
where true;

create or replace function gestionale_v2.salva_azienda(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_is_new boolean;
begin
  v_azienda_id := nullif(payload->>'azienda_id', '')::uuid;
  v_is_new := v_azienda_id is null;

  if nullif(payload->>'nome_visualizzato', '') is null
     or nullif(payload->>'ragione_sociale', '') is null then
    raise exception 'Nome commerciale e ragione sociale sono obbligatori';
  end if;

  if v_is_new then
    insert into gestionale_v2.aziende (
      nome_visualizzato,
      ragione_sociale,
      partita_iva,
      codice_fiscale,
      forma_giuridica,
      indirizzo,
      cap,
      citta,
      provincia,
      telefono,
      email,
      pec,
      codice_sdi,
      sito_web,
      iban,
      banca,
      intestazione_documenti,
      dicitura_ricevuta,
      footer_documenti,
      prefisso_ricevute,
      attiva
    )
    values (
      payload->>'nome_visualizzato',
      payload->>'ragione_sociale',
      nullif(payload->>'partita_iva', ''),
      nullif(payload->>'codice_fiscale', ''),
      nullif(payload->>'forma_giuridica', ''),
      nullif(payload->>'indirizzo', ''),
      nullif(payload->>'cap', ''),
      nullif(payload->>'citta', ''),
      nullif(payload->>'provincia', ''),
      nullif(payload->>'telefono', ''),
      nullif(payload->>'email', ''),
      nullif(payload->>'pec', ''),
      nullif(payload->>'codice_sdi', ''),
      nullif(payload->>'sito_web', ''),
      nullif(payload->>'iban', ''),
      nullif(payload->>'banca', ''),
      nullif(payload->>'intestazione_documenti', ''),
      coalesce(
        nullif(payload->>'dicitura_ricevuta', ''),
        'Ricevuta non fiscale'
      ),
      nullif(payload->>'footer_documenti', ''),
      nullif(payload->>'prefisso_ricevute', ''),
      coalesce((payload->>'attiva')::boolean, true)
    )
    returning id into v_azienda_id;

    insert into gestionale_v2.tipi_documento (
      azienda_id,
      nome,
      obbligatorio,
      ha_scadenza,
      durata_standard_mesi,
      genera_alert,
      blocca_accesso,
      collegabile_abbonamento
    )
    select
      v_azienda_id,
      x.nome,
      x.obbligatorio,
      x.ha_scadenza,
      x.durata_standard_mesi,
      x.genera_alert,
      x.blocca_accesso,
      x.collegabile_abbonamento
    from (
      values
        ('Certificato medico', true, true, 12, true, true, false),
        ('Privacy', true, false, null, false, false, false),
        ('Contratto', true, false, null, false, false, true),
        ('Documento di identità', false, true, null, true, false, false),
        ('Codice fiscale', false, false, null, false, false, false),
        ('Altro', false, false, null, false, false, false)
    ) as x(
      nome,
      obbligatorio,
      ha_scadenza,
      durata_standard_mesi,
      genera_alert,
      blocca_accesso,
      collegabile_abbonamento
    );
  else
    update gestionale_v2.aziende
    set
      nome_visualizzato = payload->>'nome_visualizzato',
      ragione_sociale = payload->>'ragione_sociale',
      partita_iva = coalesce(
        nullif(payload->>'partita_iva', ''),
        partita_iva
      ),
      codice_fiscale = coalesce(
        nullif(payload->>'codice_fiscale', ''),
        codice_fiscale
      ),
      forma_giuridica = coalesce(
        nullif(payload->>'forma_giuridica', ''),
        forma_giuridica
      ),
      indirizzo = coalesce(
        nullif(payload->>'indirizzo', ''),
        indirizzo
      ),
      cap = coalesce(nullif(payload->>'cap', ''), cap),
      citta = coalesce(nullif(payload->>'citta', ''), citta),
      provincia = coalesce(
        nullif(payload->>'provincia', ''),
        provincia
      ),
      telefono = coalesce(
        nullif(payload->>'telefono', ''),
        telefono
      ),
      email = coalesce(nullif(payload->>'email', ''), email),
      pec = coalesce(nullif(payload->>'pec', ''), pec),
      codice_sdi = coalesce(
        nullif(payload->>'codice_sdi', ''),
        codice_sdi
      ),
      sito_web = coalesce(
        nullif(payload->>'sito_web', ''),
        sito_web
      ),
      iban = coalesce(nullif(payload->>'iban', ''), iban),
      banca = coalesce(nullif(payload->>'banca', ''), banca),
      intestazione_documenti = coalesce(
        nullif(payload->>'intestazione_documenti', ''),
        intestazione_documenti
      ),
      dicitura_ricevuta = coalesce(
        nullif(payload->>'dicitura_ricevuta', ''),
        dicitura_ricevuta
      ),
      footer_documenti = coalesce(
        nullif(payload->>'footer_documenti', ''),
        footer_documenti
      ),
      prefisso_ricevute = coalesce(
        nullif(payload->>'prefisso_ricevute', ''),
        prefisso_ricevute
      ),
      attiva = coalesce(
        (payload->>'attiva')::boolean,
        attiva
      )
    where id = v_azienda_id;

    if not found then
      raise exception 'Azienda non trovata';
    end if;
  end if;

  return jsonb_build_object(
    'azienda_id', v_azienda_id,
    'nuova', v_is_new
  );
end;
$$;

create or replace function gestionale_v2.salva_asset_azienda(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_tipo text;
  v_path text;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_tipo := payload->>'tipo_asset';
  v_path := payload->>'file_path';

  if v_tipo not in ('logo', 'firma', 'timbro') then
    raise exception 'Tipo asset non valido';
  end if;

  if nullif(v_path, '') is null then
    raise exception 'Percorso file obbligatorio';
  end if;

  update gestionale_v2.aziende
  set
    logo_path = case when v_tipo = 'logo' then v_path else logo_path end,
    firma_path = case when v_tipo = 'firma' then v_path else firma_path end,
    timbro_path = case when v_tipo = 'timbro' then v_path else timbro_path end
  where id = v_azienda_id;

  if not found then
    raise exception 'Azienda non trovata';
  end if;

  return jsonb_build_object(
    'azienda_id', v_azienda_id,
    'tipo_asset', v_tipo,
    'file_path', v_path
  );
end;
$$;

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
  v_snapshot jsonb;
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

    select jsonb_build_object(
      'azienda', to_jsonb(a),
      'cliente', to_jsonb(c),
      'incasso', jsonb_build_object(
        'id', v_incasso_id,
        'tipo_incasso', v_tipo_incasso,
        'causale', payload->>'causale',
        'importo', v_importo,
        'metodo_pagamento', payload->>'metodo_pagamento',
        'data_incasso', payload->>'data_incasso'
      )
    )
    into v_snapshot
    from gestionale_v2.aziende a
    cross join gestionale_v2.clienti c
    where a.id = v_azienda_id
      and c.id = v_cliente_id;

    insert into gestionale_v2.ricevute (
      azienda_id,
      cliente_id,
      incasso_id,
      anno,
      numero_progressivo,
      data_emissione,
      importo,
      metodo_pagamento,
      causale,
      snapshot_dati
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
      payload->>'causale',
      v_snapshot
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

create or replace function gestionale_v2.get_ricevuta_dettaglio(
  p_ricevuta_id uuid
)
returns jsonb
language sql
security definer
set search_path = gestionale_v2, public
as $$
  select jsonb_build_object(
    'ricevuta', to_jsonb(r),
    'azienda', coalesce(
      r.snapshot_dati->'azienda',
      to_jsonb(a)
    ),
    'cliente', coalesce(
      r.snapshot_dati->'cliente',
      to_jsonb(c)
    ),
    'incasso', coalesce(
      r.snapshot_dati->'incasso',
      to_jsonb(i)
    ),
    'numero_documento',
      concat_ws(
        '',
        case
          when nullif(a.prefisso_ricevute, '') is not null
          then a.prefisso_ricevute || '-'
          else ''
        end,
        lpad(r.numero_progressivo::text, 4, '0'),
        '/',
        r.anno::text
      )
  )
  from gestionale_v2.ricevute r
  join gestionale_v2.aziende a
    on a.id = r.azienda_id
  join gestionale_v2.clienti c
    on c.id = r.cliente_id
  join gestionale_v2.incassi i
    on i.id = r.incasso_id
  where r.id = p_ricevuta_id;
$$;

create or replace function gestionale_v2.collega_pdf_ricevuta(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_ricevuta_id uuid;
  v_path text;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_ricevuta_id := (payload->>'ricevuta_id')::uuid;
  v_path := payload->>'pdf_path';

  update gestionale_v2.ricevute
  set
    pdf_path = v_path,
    pdf_generato_il = now(),
    pdf_versione = pdf_versione + 1
  where id = v_ricevuta_id
    and azienda_id = v_azienda_id;

  if not found then
    raise exception 'Ricevuta non trovata';
  end if;

  return jsonb_build_object(
    'ricevuta_id', v_ricevuta_id,
    'pdf_path', v_path
  );
end;
$$;

create or replace function gestionale_v2.annulla_incasso(payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda_id uuid;
  v_incasso_id uuid;
  v_abbonamento_id uuid;
  v_ricevuta_id uuid;
  v_precedente jsonb;
  v_nuovo_residuo numeric;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_incasso_id := (payload->>'incasso_id')::uuid;

  select
    i.abbonamento_id,
    to_jsonb(i)
  into
    v_abbonamento_id,
    v_precedente
  from gestionale_v2.incassi i
  where i.id = v_incasso_id
    and i.azienda_id = v_azienda_id
    and i.stato = 'valido';

  if v_precedente is null then
    raise exception 'Incasso valido non trovato';
  end if;

  update gestionale_v2.incassi
  set
    stato = 'annullato',
    annullato_il = now(),
    motivo_annullamento = payload->>'motivo'
  where id = v_incasso_id;

  update gestionale_v2.ricevute
  set
    stato = 'annullata',
    annullata_il = now(),
    motivo_annullamento = payload->>'motivo',
    pdf_path = null
  where incasso_id = v_incasso_id
  returning id into v_ricevuta_id;

  if v_abbonamento_id is not null then
    perform gestionale_v2.ricalcola_allocazioni_abbonamento(
      v_abbonamento_id
    );

    select greatest(
      a.prezzo_concordato
      - coalesce(
          sum(i.importo)
          filter (where i.stato = 'valido'),
          0
        ),
      0
    )
    into v_nuovo_residuo
    from gestionale_v2.abbonamenti a
    left join gestionale_v2.incassi i
      on i.abbonamento_id = a.id
    where a.id = v_abbonamento_id
    group by a.prezzo_concordato;
  else
    v_nuovo_residuo := null;
  end if;

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
    'incassi',
    v_incasso_id,
    'annullamento',
    v_precedente,
    payload->>'motivo'
  );

  return jsonb_build_object(
    'incasso_id', v_incasso_id,
    'ricevuta_id', v_ricevuta_id,
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
  i.causale,
  i.note,
  i.stato,
  i.created_at,
  case
    when r.id is null then null
    else
      concat_ws(
        '',
        case
          when nullif(a.prefisso_ricevute, '') is not null
          then a.prefisso_ricevute || '-'
          else ''
        end,
        lpad(r.numero_progressivo::text, 4, '0'),
        '/',
        r.anno::text
      )
  end as ricevuta_numero,
  i.tipo_incasso,
  r.id as ricevuta_id,
  r.pdf_path,
  r.stato as ricevuta_stato
from gestionale_v2.incassi i
join gestionale_v2.clienti c
  on c.id = i.cliente_id
join gestionale_v2.aziende a
  on a.id = i.azienda_id
left join gestionale_v2.ricevute r
  on r.incasso_id = i.id;

grant execute
on function gestionale_v2.salva_azienda(jsonb)
to service_role;

grant execute
on function gestionale_v2.salva_asset_azienda(jsonb)
to service_role;

grant execute
on function gestionale_v2.registra_incasso_completo(jsonb)
to service_role;

grant execute
on function gestionale_v2.get_ricevuta_dettaglio(uuid)
to service_role;

grant execute
on function gestionale_v2.collega_pdf_ricevuta(jsonb)
to service_role;

grant execute
on function gestionale_v2.annulla_incasso(jsonb)
to service_role;

grant select
on gestionale_v2.vista_incassi_operativa
to service_role;

commit;

notify pgrst, 'reload schema';
