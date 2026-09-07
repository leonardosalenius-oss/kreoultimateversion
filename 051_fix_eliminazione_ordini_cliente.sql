begin;

-- L'ordine cliente è dato dipendente dal cliente: per l'eliminazione
-- definitiva di un cliente di prova deve seguire il cliente.
alter table gestionale_v2.ordini_cliente
  drop constraint if exists ordini_cliente_cliente_id_fkey;

alter table gestionale_v2.ordini_cliente
  add constraint ordini_cliente_cliente_id_fkey
  foreign key (cliente_id)
  references gestionale_v2.clienti(id)
  on delete cascade;


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

  v_conferma_attesa :=
    trim('ELIMINA ' || v_cognome || ' ' || v_nome);

  if v_conferma_ricevuta <> v_conferma_attesa then
    raise exception 'Conferma eliminazione non valida';
  end if;

  -- Ordini e righe ordine (le righe hanno cascade sull'ordine).
  delete from gestionale_v2.ordini_cliente
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.accessi
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.movimenti_lezioni
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.eventi_prenotazione
  where azienda_id = v_azienda_id
    and prenotazione_id in (
      select p.id
      from gestionale_v2.prenotazioni p
      where p.azienda_id = v_azienda_id
        and p.cliente_id = v_cliente_id
    );

  delete from gestionale_v2.prenotazioni
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.badge_clienti
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.allocazioni_incassi_rate
  where azienda_id = v_azienda_id
    and (
      incasso_id in (
        select i.id
        from gestionale_v2.incassi i
        where i.azienda_id = v_azienda_id
          and i.cliente_id = v_cliente_id
      )
      or rata_id in (
        select r.id
        from gestionale_v2.rate r
        join gestionale_v2.abbonamenti a
          on a.id = r.abbonamento_id
        where a.azienda_id = v_azienda_id
          and a.cliente_id = v_cliente_id
      )
    );

  delete from gestionale_v2.ricevute
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.incassi
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.documenti_clienti
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.eventi_stato_abbonamento
  where azienda_id = v_azienda_id
    and abbonamento_id in (
      select a.id
      from gestionale_v2.abbonamenti a
      where a.azienda_id = v_azienda_id
        and a.cliente_id = v_cliente_id
    );

  delete from gestionale_v2.rate
  where azienda_id = v_azienda_id
    and abbonamento_id in (
      select a.id
      from gestionale_v2.abbonamenti a
      where a.azienda_id = v_azienda_id
        and a.cliente_id = v_cliente_id
    );

  delete from gestionale_v2.abbonamenti
  where azienda_id = v_azienda_id
    and cliente_id = v_cliente_id;

  delete from gestionale_v2.audit_log
  where azienda_id = v_azienda_id
    and (
      (tabella = 'clienti' and record_id = v_cliente_id)
      or valore_precedente::text like
        '%' || v_cliente_id::text || '%'
      or valore_successivo::text like
        '%' || v_cliente_id::text || '%'
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
