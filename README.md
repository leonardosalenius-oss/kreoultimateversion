# Gestionale v0.20.2

## Migliorie

- modifica pacchetto;
- correzione numero totale dei pacchetti da 20/30 o altro valore;
- modifica lezioni cliente tramite movimenti tracciati;
- ricevuta PDF anche per acconto iniziale;
- pacchetti a lezioni senza scadenza temporale.

## Regola unica pacchetti a lezioni

```text
lezioni iniziali = lezioni_totali del pacchetto
data fine = NULL
termine = saldo lezioni pari a zero
```

La normalizzazione avviene con un trigger sul database, quindi vale per:

- nuovo cliente;
- nuovo abbonamento;
- rinnovo;
- modifica abbonamento;
- operazioni future.

## Deploy

1. Eseguire:

```text
sql/018_pacchetti_lezioni_ricevute.sql
```

2. Sostituire su GitHub:

- `app.py`
- `services.py`
- `requirements.txt`

Non caricare il `requirements.txt` della cartella Bridge nella root.
