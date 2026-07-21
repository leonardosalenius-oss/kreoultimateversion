# Architettura agenda v0.18

## Tabelle

- `operatori_agenda`
- `prenotazioni`
- `eventi_prenotazione`

## Stati prenotazione

- prenotata
- confermata
- presente
- assente
- annullata

## Separazione delle responsabilità

In questa versione l'agenda registra la realtà operativa.

La versione successiva collegherà lo stato `presente` a un movimento lezione immutabile:

```text
prenotazione
→ presenza
→ movimento lezione
→ saldo lezioni
```

Questo evita di modificare direttamente un contatore residuo.
