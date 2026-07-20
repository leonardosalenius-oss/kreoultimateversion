# Gestionale KREO v0.15 - Multi-azienda e ricevute PDF

Questa versione elimina il riferimento fisso a KREO dalla logica applicativa.

## Prima del deploy

Eseguire una sola volta in Supabase SQL Editor:

```text
sql/009_multiazienda_ricevute_pdf.sql
```

Poi caricare su GitHub tutti i file della v0.15, perché cambiano:

- `app.py`
- `services.py`
- `requirements.txt`
- nuovo file `receipts.py`

## Multi-azienda

Il Super Admin può:

- selezionare l'azienda attiva dal menu laterale;
- configurare i dati aziendali;
- configurare intestazione e diciture dei documenti;
- caricare logo, firma e timbro;
- creare nuove aziende clienti.

Tutte le aree operative continuano a filtrare tramite `azienda_id`.

## Ricevute PDF

Quando viene registrato un incasso con ricevuta:

1. il database assegna numero e anno;
2. salva uno snapshot dei dati azienda, cliente e incasso;
3. Streamlit genera un PDF;
4. il PDF viene salvato nel bucket privato `ricevute-pdf`;
5. il percorso viene collegato alla ricevuta;
6. il PDF può essere aperto, scaricato o rigenerato.

Se la generazione fallisce, l'incasso resta valido e il PDF può essere rigenerato dalla sezione Ricevute.

## Storage

Bucket privati:

- `asset-aziende`
- `ricevute-pdf`

L'accesso ai file avviene tramite URL firmati temporanei.


## Predisposizione utenti per azienda

La migrazione crea anche `utenti_aziende`, che collegherà gli account Supabase Auth alle aziende e ai ruoli. In questa fase, non essendo ancora attivo il login nuovo, il Super Admin può selezionare tutte le aziende attive. Le nuove aziende ricevono automaticamente i tipi documento iniziali.
