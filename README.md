# Gestionale v0.18 — Reception, agenda e prenotazioni

## Prima del deploy

Eseguire una volta in Supabase SQL Editor:

```text
sql/013_reception_agenda_prenotazioni.sql
```

Poi caricare tutti i file dello ZIP su GitHub.

## Reception

La pagina Reception ora comprende:

- dashboard della giornata;
- agenda giornaliera;
- agenda settimanale;
- nuova prenotazione;
- modifica e annullamento;
- conferma prenotazione;
- registrazione presente o assente;
- gestione degli operatori;
- azioni rapide verso clienti e contabilità.

## Regole

- ogni prenotazione è collegata al cliente;
- normalmente è collegata anche a un abbonamento valido;
- l'operatore non può avere due prenotazioni sovrapposte;
- l'annullamento è logico, non cancella lo storico;
- ogni modifica e cambio di stato viene registrato;
- lo stato `presente` non scala ancora le lezioni.

Il movimento delle lezioni sarà introdotto nella v0.19, così agenda e conteggio lezioni useranno una sola logica.
