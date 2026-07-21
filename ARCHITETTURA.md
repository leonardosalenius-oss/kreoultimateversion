# Architettura abbonamenti v0.17

## Fonte unica

`vista_abbonamenti_operativa` calcola:

- pagato;
- residuo;
- prossima rata;
- stato visuale.

## Eventi di stato

`eventi_stato_abbonamento` conserva:

- sospensione;
- riattivazione;
- terminazione;
- chiusura anticipata;
- rinnovo.

## Rinnovi

`abbonamento_precedente_id` collega il nuovo abbonamento al precedente senza alterarne lo storico.

## Operazioni transazionali

- `crea_abbonamento_cliente`
- `rinnova_abbonamento_cliente`
- `cambia_stato_abbonamento`
