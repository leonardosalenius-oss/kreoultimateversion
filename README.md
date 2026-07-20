# Gestionale KREO v0.12 — Allocazioni coerenti

Correzione strutturale della logica rate/incassi.

## Problema risolto

L'acconto iniziale veniva salvato come incasso valido e sottratto dal residuo generale,
ma non veniva passato al motore di allocazione rate.

Per questo poteva comparire:

- residuo abbonamento: € 250;
- due rate da € 250 ancora entrambe da pagare.

## Regola unica

Ogni incasso valido, incluso l'acconto iniziale, viene sempre elaborato da:

```text
ricalcola_allocazioni_abbonamento
```

Il motore assegna gli importi alle rate più vecchie.

## Prima del deploy

Eseguire una sola volta:

```text
sql/007_allineamento_acconti_rate.sql
```

Lo script:

- aggiorna la funzione `crea_cliente_completo`;
- alloca automaticamente gli acconti dei nuovi clienti;
- ricalcola le allocazioni per tutti gli abbonamenti già esistenti.
