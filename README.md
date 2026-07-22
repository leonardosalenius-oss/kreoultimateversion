# Gestionale v0.20.1 — Frequenza settimanale reale

## Prima del deploy

Eseguire una sola volta in Supabase SQL Editor:

```text
sql/017_frequenza_settimanale_reale.sql
```

Poi sostituire su GitHub:

- `app.py`
- `services.py`
- `domain.py`

## Nuova regola

Per i pacchetti settimanali il gestionale non usa più:

```text
lezioni a settimana × mesi × 4
```

Usa invece:

```text
giorni effettivi inclusi × lezioni settimanali ÷ 7
```

Il risultato viene arrotondato all'intero più vicino dal database.

Esempio con 3 lezioni a settimana:

- 28 giorni → 12
- 30 giorni → 13
- 31 giorni → 13
- 365 giorni → 156

## Fonte unica

La funzione centrale è:

```text
calcola_lezioni_contrattuali()
```

Viene usata per:

- nuovo cliente;
- nuovo abbonamento;
- rinnovo;
- modifica date o pacchetto;
- anteprima dell'interfaccia;
- riallineamento degli abbonamenti esistenti.

## Limite settimanale

Per le lezioni ordinarie viene applicato anche il limite del pacchetto:

```text
3 lezioni a settimana
```

Recuperi, extra e valutazioni restano categorie distinte.

## Sospensioni

La sospensione può spostare la data finale, ma non ricalcola automaticamente
le lezioni già contrattualizzate durante la semplice riattivazione.
