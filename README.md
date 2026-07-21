# Gestionale v0.17.1 — Fix abbonamenti e gestione clienti

## Origine dell'errore

Le funzioni per gli abbonamenti erano presenti in `services.py`, ma non erano
state importate in `app.py`. Per questo Streamlit mostrava:

```text
NameError: elenco_abbonamenti_operativo
```

La v0.17.1 corregge l'importazione.

## Nuove funzioni clienti

Nella scheda `Modifica cliente` è presente la scheda `Gestione cliente`.

### Disattivazione

- conserva tutto lo storico;
- può essere annullata riattivando il cliente;
- il cliente è distinguibile nell'elenco;
- è disponibile un filtro Attivi/Inattivi.

### Eliminazione definitiva

Pensata esclusivamente per clienti test o inserimenti errati.

Richiede:

- frase di conferma con nome e cognome;
- checkbox esplicito;
- cancellazione di abbonamenti, rate, incassi, ricevute, documenti e audit collegato.

## Deploy

1. Eseguire una volta:

```text
sql/012_fix_abbonamenti_gestione_clienti.sql
```

2. Caricare tutti i file dello ZIP su GitHub.
