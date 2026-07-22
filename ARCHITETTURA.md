# Architettura presenze v0.19

## Registro immutabile

`movimenti_lezioni` contiene variazioni positive e negative.

Non viene salvato un contatore lezioni residue modificabile.

## Vista saldo

`vista_saldi_lezioni` calcola:

- lezioni iniziali;
- movimenti netti;
- saldo disponibile.

## Integrazione agenda

`cambia_stato_prenotazione` è l'unica funzione che trasforma una presenza in consumo lezione e genera lo storno quando la presenza viene corretta.
