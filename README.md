# Gestionale KREO v0.8 — persistente

Versione costruita con logica unica e senza duplicazioni.

## Prima del deploy

Eseguire una sola volta nel SQL Editor:

```text
sql/003_pacchetti_periodici_e_acconto.sql
```

## Modello pacchetti

Ogni pacchetto ha:

- periodicità: mensile, semestrale o annuale;
- modalità lezioni:
  - settimanale;
  - mensile;
  - pacchetto lezioni;
- numero di lezioni calcolato automaticamente e modificabile nell'abbonamento.

Per la modalità settimanale il calcolo commerciale è:

```text
lezioni settimanali × 4 settimane × mesi del pacchetto
```

## Correzione errore data editor

L'errore precedente era causato da una colonna configurata come data che conteneva stringhe ISO.
Ora il piano rate usa veri oggetti `date` e viene convertito in ISO solo al salvataggio.

## Date

Tutti i campi data e le visualizzazioni usano formato italiano:

```text
GG/MM/AAAA
```

## Acconto

L'acconto iniziale:

- è inseribile durante la registrazione;
- aggiorna il residuo in tempo reale;
- viene salvato come incasso reale;
- viene sottratto automaticamente dal prezzo concordato.
