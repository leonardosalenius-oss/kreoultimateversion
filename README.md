# Gestionale KREO v0.9 — blocco Clienti, Rate e Incassi

Questa versione completa il primo blocco operativo persistente.

## Prima del deploy

Eseguire una sola volta in Supabase SQL Editor:

```text
sql/004_clienti_rate_incassi.sql
```

## Funzioni attive

### Reception

- Nuovo cliente
- Modifica cliente
- Registra incasso
- Stampa ricevuta
- Carica documento / Scheda cliente
- Storico cliente / Scheda cliente
- Situazione cliente

### Clienti

- elenco operativo;
- nuova registrazione completa;
- modifica anagrafica;
- scheda cliente con abbonamento, rate, incassi e documenti.

### Contabilità

- nuovo incasso;
- allocazione automatica alle rate più vecchie;
- pagamenti parziali;
- elenco incassi;
- annullamento incasso con motivo;
- ricalcolo automatico di rate e residuo;
- ricevuta progressiva;
- elenco rate con stato.

## Regole economiche

- residuo = prezzo concordato meno incassi validi;
- un incasso può coprire più rate;
- gli incassi vengono allocati cronologicamente;
- annullando un incasso, le allocazioni vengono ricostruite;
- gli incassi non vengono cancellati;
- le modifiche cliente e gli annullamenti finiscono nell'audit log.
