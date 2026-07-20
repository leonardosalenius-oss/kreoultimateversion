# Architettura incassi v0.14

La funzione database `registra_incasso_completo` è l'unico ingresso per ogni ricavo.

Il campo `tipo_incasso` decide il comportamento:

- `abbonamento`: validazione residuo e allocazione rate;
- `vendita_prodotto`: sola registrazione ricavo;
- `servizio`: sola registrazione ricavo;
- `altro_ricavo`: sola registrazione ricavo.

Per i ricavi non riferiti all'abbonamento, `abbonamento_id` viene forzato a NULL dal database.
La descrizione resta libera, così la futura anagrafica prodotti e servizi potrà essere collegata senza riscrivere la logica contabile.
