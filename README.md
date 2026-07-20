# Gestionale KREO v0.10 — Modifica cliente completa

La sezione **Modifica cliente** è ora una pagina completa articolata in:

- Anagrafica
- Abbonamento
- Rate
- Documenti
- Incassi
- Storico

## Prima del deploy

Eseguire una sola volta in Supabase SQL Editor:

```text
sql/005_modifica_cliente_completa.sql
```

## Regole

### Anagrafica

Le modifiche sono persistenti e tracciate.

### Abbonamento

È possibile modificare pacchetto, date, prezzo, lezioni, tipologia di pagamento, stato e note.

Il pacchetto generale non viene modificato.

### Rate

- le rate già pagate non possono essere ridotte sotto l'importo allocato;
- la somma delle rate attive deve coincidere con il prezzo concordato;
- dopo ogni modifica le allocazioni vengono ricalcolate;
- ogni modifica richiede una motivazione.

### Documenti

- aggiunta o sostituzione;
- date e scadenze;
- stato;
- annullamento con motivo;
- storico conservato.

### Incassi

Gli incassi non vengono modificati. Si annullano e si registrano nuovamente.

### Storico

La scheda raccoglie le operazioni registrate nell'audit log.
