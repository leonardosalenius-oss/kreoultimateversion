begin;

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'documenti-clienti',
  'documenti-clienti',
  false,
  10485760,
  array[
    'application/pdf',
    'image/png',
    'image/jpeg'
  ]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

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

  if nullif(payload->>'file_path', '') is null then
    raise exception 'Il percorso del file è obbligatorio';
  end if;

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
    nome_documento,
    file_path,
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
    nullif(payload->>'nome_documento', ''),
    payload->>'file_path',
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
    'caricamento_o_sostituzione_file',
    jsonb_build_object(
      'cliente_id', v_cliente_id,
      'tipo', payload->>'tipo',
      'nome_documento', payload->>'nome_documento',
      'file_path', payload->>'file_path'
    )
  );

  return jsonb_build_object(
    'documento_id', v_documento_id,
    'file_path', payload->>'file_path'
  );
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
            a.prezzo_concordato
            - coalesce(sum(i.importo) filter (where i.stato = 'valido'), 0),
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
      select jsonb_agg(
        to_jsonb(v)
        order by v.data_incasso desc, v.created_at desc
      )
      from gestionale_v2.vista_incassi_operativa v
      where v.cliente_id = p_cliente_id
    ), '[]'::jsonb),
    'documenti',
    coalesce((
      select jsonb_agg(jsonb_build_object(
        'documento_id', dc.id,
        'tipo', td.nome,
        'nome_documento', dc.nome_documento,
        'file_path', dc.file_path,
        'data_documento', dc.data_documento,
        'data_scadenza', dc.data_scadenza,
        'stato', dc.stato,
        'note', dc.note,
        'created_at', dc.created_at
      ) order by td.nome, dc.created_at desc)
      from gestionale_v2.documenti_clienti dc
      join gestionale_v2.tipi_documento td
        on td.id = dc.tipo_documento_id
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

grant execute
on function gestionale_v2.salva_documento_cliente(jsonb)
to service_role;

grant execute
on function gestionale_v2.get_cliente_dettaglio(uuid)
to service_role;

commit;

notify pgrst, 'reload schema';
