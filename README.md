# Gestionale KREO v0.14 — Incassi generici

La contabilità utilizza ora un solo flusso per quattro tipologie di ricavo:

- abbonamento;
- vendita prodotto / integratori;
- servizio extra;
- altro ricavo.

## Regola economica unica

### Incasso abbonamento

- richiede un abbonamento;
- non può superare il residuo;
- riduce il residuo;
- aggiorna le rate;
- ricalcola le allocazioni.

### Altri incassi

- non sono collegati a un abbonamento;
- non riducono il residuo;
- non modificano rate o scadenze;
- vengono comunque registrati come ricavi;
- possono generare una ricevuta;
- richiedono una descrizione libera.

## Prima del deploy

Eseguire una sola volta:

```text
sql/008_incassi_generici.sql
```
