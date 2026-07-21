begin;

-- La v0.17 aveva correttamente creato servizi e vista, ma l'app non li
-- importava. Questa migrazione aggiunge soltanto l'eliminazione definitiva.

create or replace function gestionale_v2.elimina_cliente_definitivamente(
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
  v_nome text;
  v_cognome text;
  v_conferma_attesa text;
  v_conferma_ricevuta text;
begin
  v_azienda_id := (payload->>'azienda_id')::uuid;
  v_cliente_id := (payload->>'cliente_id')::uuid;
  v_conferma_ricevuta := trim(payload->>'conferma');

  select c.nome, c.cognome
  into v_nome, v_cognome
  from gestionale_v2.clienti c
  where c.id = v_cliente_id
    and c.azienda_id = v_azienda_id;

  if v_nome is null then
    raise exception 'Cliente non trovato';
  end if;

  v_conferma_attesa := trim('ELIMINA ' || v_cognome || ' ' || v_nome);

  if v_conferma_ricevuta <> v_conferma_attesa then
    raise exception 'Conferma eliminazione non valida';
  end if;

  -- Allocazioni e ricevute dipendenti dagli incassi.
  delete from gestionale_v2.allocazioni_incassi_rate
  where incasso_id in (
    select id
    from gestionale_v2.incassi
    where cliente_id = v_cliente_id
      and azienda_id = v_azienda_id
  );

  delete from gestionale_v2.ricevute
  where cliente_id = v_cliente_id
    and azienda_id = v_azienda_id;

  delete from gestionale_v2.incassi
  where cliente_id = v_cliente_id
    and azienda_id = v_azienda_id;

  -- Documenti e rate/abbonamenti.
  delete from gestionale_v2.documenti_clienti
  where cliente_id = v_cliente_id
    and azienda_id = v_azienda_id;

  delete from gestionale_v2.eventi_stato_abbonamento
  where abbonamento_id in (
    select id
    from gestionale_v2.abbonamenti
    where cliente_id = v_cliente_id
      and azienda_id = v_azienda_id
  );

  delete from gestionale_v2.rate
  where abbonamento_id in (
    select id
    from gestionale_v2.abbonamenti
    where cliente_id = v_cliente_id
      and azienda_id = v_azienda_id
  );

  delete from gestionale_v2.abbonamenti
  where cliente_id = v_cliente_id
    and azienda_id = v_azienda_id;

  -- Lo storico audit del cliente test viene eliminato intenzionalmente.
  delete from gestionale_v2.audit_log
  where azienda_id = v_azienda_id
    and (
      (tabella = 'clienti' and record_id = v_cliente_id)
      or valore_precedente::text like '%' || v_cliente_id::text || '%'
      or valore_successivo::text like '%' || v_cliente_id::text || '%'
    );

  delete from gestionale_v2.clienti
  where id = v_cliente_id
    and azienda_id = v_azienda_id;

  if not found then
    raise exception 'Cliente non eliminato';
  end if;

  return jsonb_build_object(
    'cliente_id', v_cliente_id,
    'eliminato', true
  );
end;
$$;

grant execute
on function gestionale_v2.elimina_cliente_definitivamente(jsonb)
to service_role;

commit;

notify pgrst, 'reload schema';
