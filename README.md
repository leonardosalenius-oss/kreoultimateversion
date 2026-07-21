# Gestionale v0.17 — Abbonamenti

## Prima del deploy

Eseguire una sola volta in Supabase SQL Editor:

```text
sql/011_abbonamenti_rinnovi_sospensioni.sql
```

Poi caricare tutti i file dello ZIP su GitHub, perché cambiano:

- `app.py`
- `services.py`
- documentazione
- migrazione SQL

## Funzioni attive

### Elenco abbonamenti

- filtri per stato;
- ricerca cliente o pacchetto;
- indicatori attivi, in scadenza e sospesi;
- schede operative con valore, pagato, residuo e prossima rata.

### Nuovo abbonamento

Consente di assegnare un nuovo abbonamento a un cliente già registrato:

- pacchetto;
- date;
- prezzo;
- lezioni;
- piano rate;
- acconto iniziale.

### Sospensione e riattivazione

Ogni cambio di stato richiede una motivazione.

La riattivazione può prolungare la data finale per i giorni effettivi di sospensione.

### Chiusura

- terminazione ordinaria;
- chiusura anticipata;
- storico immutabile degli eventi.

### Rinnovo

Il rinnovo crea sempre un nuovo abbonamento.

L'abbonamento precedente non viene sovrascritto e può essere segnato come terminato.

## Logica

```text
cliente
→ abbonamento
→ rate
→ incassi
→ eventi di stato
→ rinnovo come nuovo record
```
