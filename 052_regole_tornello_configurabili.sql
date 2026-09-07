begin;

-- ============================================================
-- REGOLE TORNELLO CONFIGURABILI
-- Due controlli restano SEMPRE obbligatori e non sono disattivabili:
--   1) badge KREO attivo e riconosciuto
--   2) cliente anagrafico attivo
--
-- Tutte le regole amministrative/contrattuali sono invece selezionabili.
-- ============================================================

alter table gestionale_v2.configurazione_tornello
  add column if not exists controlla_certificato_medico boolean not null default true,
  add column if not exists controlla_rate_abbonamento boolean not null default true,
  add column if not exists controlla_prenotazione boolean not null default true,
  add column if not exists controlla_abbonamento_valido boolean not null default true,
  add column if not exists controlla_lezioni_residue boolean not null default true;

update gestionale_v2.configurazione_tornello
set
  controlla_certificato_medico = coalesce(controlla_certificato_medico, true),
  controlla_rate_abbonamento = coalesce(controlla_rate_abbonamento, true),
  controlla_prenotazione = coalesce(controlla_prenotazione, true),
  controlla_abbonamento_valido = coalesce(controlla_abbonamento_valido, true),
  controlla_lezioni_residue = coalesce(controlla_lezioni_residue, true);


create or replace function gestionale_v2.imposta_regole_accesso_tornello(
  payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_azienda uuid := (payload->>'azienda_id')::uuid;
  v_current gestionale_v2.configurazione_tornello;

  v_master boolean;
  v_cert boolean;
  v_rate boolean;
  v_booking boolean;
  v_sub boolean;
  v_balance boolean;
begin
  select *
  into v_current
  from gestionale_v2.configurazione_tornello
  where azienda_id = v_azienda;

  v_master := coalesce(
    nullif(payload->>'regole_accesso_attive', '')::boolean,
    v_current.regole_accesso_attive,
    true
  );
  v_cert := coalesce(
    nullif(payload->>'controlla_certificato_medico', '')::boolean,
    v_current.controlla_certificato_medico,
    true
  );
  v_rate := coalesce(
    nullif(payload->>'controlla_rate_abbonamento', '')::boolean,
    v_current.controlla_rate_abbonamento,
    true
  );
  v_booking := coalesce(
    nullif(payload->>'controlla_prenotazione', '')::boolean,
    v_current.controlla_prenotazione,
    true
  );
  v_sub := coalesce(
    nullif(payload->>'controlla_abbonamento_valido', '')::boolean,
    v_current.controlla_abbonamento_valido,
    true
  );
  v_balance := coalesce(
    nullif(payload->>'controlla_lezioni_residue', '')::boolean,
    v_current.controlla_lezioni_residue,
    true
  );

  insert into gestionale_v2.configurazione_tornello (
    azienda_id,
    regole_accesso_attive,
    motivo_modalita_libera,
    controlla_certificato_medico,
    controlla_rate_abbonamento,
    controlla_prenotazione,
    controlla_abbonamento_valido,
    controlla_lezioni_residue,
    modificato_da,
    modificato_il
  )
  values (
    v_azienda,
    v_master,
    case
      when v_master then null
      else coalesce(
        nullif(trim(payload->>'motivo'), ''),
        'Modalità libera attivata da operatore'
      )
    end,
    v_cert,
    v_rate,
    v_booking,
    v_sub,
    v_balance,
    nullif(payload->>'utente_id', '')::uuid,
    now()
  )
  on conflict (azienda_id)
  do update set
    regole_accesso_attive = excluded.regole_accesso_attive,
    motivo_modalita_libera = excluded.motivo_modalita_libera,
    controlla_certificato_medico = excluded.controlla_certificato_medico,
    controlla_rate_abbonamento = excluded.controlla_rate_abbonamento,
    controlla_prenotazione = excluded.controlla_prenotazione,
    controlla_abbonamento_valido = excluded.controlla_abbonamento_valido,
    controlla_lezioni_residue = excluded.controlla_lezioni_residue,
    modificato_da = excluded.modificato_da,
    modificato_il = now();

  return jsonb_build_object(
    'regole_accesso_attive', v_master,
    'controlla_certificato_medico', v_cert,
    'controlla_rate_abbonamento', v_rate,
    'controlla_prenotazione', v_booking,
    'controlla_abbonamento_valido', v_sub,
    'controlla_lezioni_residue', v_balance
  );
end;
$$;

grant execute
on function gestionale_v2.imposta_regole_accesso_tornello(jsonb)
to service_role;


create or replace function gestionale_v2.valuta_accesso_cliente_tornello(
  p_azienda_id uuid,
  p_cliente_id uuid
)
returns jsonb
language plpgsql
stable
security definer
set search_path = gestionale_v2, public
as $$
declare
  v_cliente_nome text;
  v_cfg gestionale_v2.configurazione_tornello;

  v_abbonamento_id uuid;
  v_tipo_consumo text;
  v_stato_abbonamento text;
  v_saldo integer;
  v_prenotazione_id uuid;

  v_cert_ok boolean := true;
  v_rate_ok boolean := true;
  v_booking_ok boolean := true;
  v_sub_ok boolean := true;
  v_balance_ok boolean := true;
begin
  -- ==========================================================
  -- BASELINE SEMPRE OBBLIGATORIA
  -- ==========================================================
  select trim(c.cognome || ' ' || c.nome)
  into v_cliente_nome
  from gestionale_v2.clienti c
  where c.id = p_cliente_id
    and c.azienda_id = p_azienda_id
    and c.stato = 'attivo';

  if v_cliente_nome is null then
    return jsonb_build_object(
      'consentito', false,
      'motivo', 'Cliente inattivo',
      'regola_bloccante', 'cliente_attivo'
    );
  end if;

  select *
  into v_cfg
  from gestionale_v2.configurazione_tornello
  where azienda_id = p_azienda_id;

  if v_cfg.azienda_id is null then
    -- Configurazione legacy/default: tutte le regole attive.
    v_cfg.controlla_certificato_medico := true;
    v_cfg.controlla_rate_abbonamento := true;
    v_cfg.controlla_prenotazione := true;
    v_cfg.controlla_abbonamento_valido := true;
    v_cfg.controlla_lezioni_residue := true;
  end if;

  -- Abbonamento "corrente" contrattualmente.
  -- Per un pacchetto a lezioni NON imponiamo qui il saldo > 0:
  -- il saldo è una regola autonoma e disattivabile.
  select
    a.id,
    p.tipo_consumo,
    a.stato
  into
    v_abbonamento_id,
    v_tipo_consumo,
    v_stato_abbonamento
  from gestionale_v2.abbonamenti a
  join gestionale_v2.pacchetti p
    on p.id = a.pacchetto_id
  where a.azienda_id = p_azienda_id
    and a.cliente_id = p_cliente_id
    and a.data_inizio <= current_date
    and a.stato not in (
      'terminato',
      'chiuso_anticipatamente',
      'annullato'
    )
    and (
      (
        p.tipo_consumo = 'tempo'
        and a.data_fine_prevista >= current_date
      )
      or
      p.tipo_consumo = 'lezioni'
    )
  order by a.data_inizio desc
  limit 1;

  -- ==========================================================
  -- 1) ABBONAMENTO VALIDO / NON SOSPESO
  -- ==========================================================
  if v_cfg.controlla_abbonamento_valido then
    v_sub_ok := (
      v_abbonamento_id is not null
      and coalesce(v_stato_abbonamento, '') <> 'sospeso'
    );

    if not v_sub_ok then
      return jsonb_build_object(
        'consentito', false,
        'motivo',
          case
            when v_stato_abbonamento = 'sospeso'
            then 'Abbonamento sospeso'
            else 'Nessun abbonamento valido'
          end,
        'cliente', v_cliente_nome,
        'regola_bloccante', 'abbonamento_valido'
      );
    end if;
  end if;

  -- ==========================================================
  -- 2) LEZIONI RESIDUE - SOLO PACCHETTI A LEZIONI
  -- ==========================================================
  if v_cfg.controlla_lezioni_residue
     and v_tipo_consumo = 'lezioni'
     and v_abbonamento_id is not null then

    select saldo_lezioni
    into v_saldo
    from gestionale_v2.vista_saldi_lezioni
    where azienda_id = p_azienda_id
      and abbonamento_id = v_abbonamento_id;

    v_balance_ok := coalesce(v_saldo, 0) > 0;

    if not v_balance_ok then
      return jsonb_build_object(
        'consentito', false,
        'motivo', 'Lezioni terminate',
        'cliente', v_cliente_nome,
        'abbonamento_id', v_abbonamento_id,
        'regola_bloccante', 'lezioni_residue'
      );
    end if;
  end if;

  -- ==========================================================
  -- 3) RATE / PAGAMENTI
  -- La regola è indipendente dal flag abbonamento:
  -- blocca se esiste una rata scaduta con residuo su un contratto
  -- non annullato/chiuso.
  -- ==========================================================
  if v_cfg.controlla_rate_abbonamento then
    v_rate_ok := not exists (
      select 1
      from gestionale_v2.vista_rate_operativa r
      join gestionale_v2.abbonamenti a
        on a.id = r.abbonamento_id
      where a.azienda_id = p_azienda_id
        and a.cliente_id = p_cliente_id
        and a.stato not in ('annullato', 'chiuso_anticipatamente')
        and r.data_scadenza < current_date
        and coalesce(r.residuo_rata, 0) > 0
    );

    if not v_rate_ok then
      return jsonb_build_object(
        'consentito', false,
        'motivo', 'Pagamento scaduto',
        'cliente', v_cliente_nome,
        'abbonamento_id', v_abbonamento_id,
        'regola_bloccante', 'rate_abbonamento'
      );
    end if;
  end if;

  -- ==========================================================
  -- 4) CERTIFICATO MEDICO
  -- ==========================================================
  if v_cfg.controlla_certificato_medico then
    v_cert_ok :=
      gestionale_v2.verifica_certificato_cliente(p_cliente_id);

    if not v_cert_ok then
      return jsonb_build_object(
        'consentito', false,
        'motivo', 'Certificato medico mancante o scaduto',
        'cliente', v_cliente_nome,
        'abbonamento_id', v_abbonamento_id,
        'regola_bloccante', 'certificato_medico'
      );
    end if;
  end if;

  -- ==========================================================
  -- 5) PRENOTAZIONE ODIERNA
  -- Indipendente dall'abbonamento se il relativo flag è disattivato.
  -- ==========================================================
  if v_cfg.controlla_prenotazione then
    select p.id
    into v_prenotazione_id
    from gestionale_v2.prenotazioni p
    where p.azienda_id = p_azienda_id
      and p.cliente_id = p_cliente_id
      and p.data_prenotazione = current_date
      and p.stato in ('prenotata', 'confermata', 'presente')
    order by abs(
      extract(epoch from (p.ora_inizio - localtime))
    )
    limit 1;

    v_booking_ok := v_prenotazione_id is not null;

    if not v_booking_ok then
      return jsonb_build_object(
        'consentito', false,
        'motivo', 'Nessuna prenotazione odierna',
        'cliente', v_cliente_nome,
        'abbonamento_id', v_abbonamento_id,
        'regola_bloccante', 'prenotazione'
      );
    end if;
  else
    -- Se non controlliamo la prenotazione, la cerchiamo comunque
    -- per poter registrare la presenza quando esiste.
    select p.id
    into v_prenotazione_id
    from gestionale_v2.prenotazioni p
    where p.azienda_id = p_azienda_id
      and p.cliente_id = p_cliente_id
      and p.data_prenotazione = current_date
      and p.stato in ('prenotata', 'confermata')
    order by abs(
      extract(epoch from (p.ora_inizio - localtime))
    )
    limit 1;
  end if;

  return jsonb_build_object(
    'consentito', true,
    'motivo', 'Accesso consentito dalle regole KREO selezionate',
    'cliente', v_cliente_nome,
    'abbonamento_id', v_abbonamento_id,
    'prenotazione_id', v_prenotazione_id,
    'tipo_consumo', v_tipo_consumo,
    'regole_applicate', jsonb_build_object(
      'abbonamento_valido', v_cfg.controlla_abbonamento_valido,
      'lezioni_residue', v_cfg.controlla_lezioni_residue,
      'rate_abbonamento', v_cfg.controlla_rate_abbonamento,
      'certificato_medico', v_cfg.controlla_certificato_medico,
      'prenotazione', v_cfg.controlla_prenotazione
    )
  );
end;
$$;

grant execute
on function gestionale_v2.valuta_accesso_cliente_tornello(uuid, uuid)
to service_role;

commit;

notify pgrst, 'reload schema';
