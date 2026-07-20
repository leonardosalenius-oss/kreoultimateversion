# Architettura v0.15

## Azienda attiva

`active_company_id` è uno stato di navigazione. La fonte dati resta Supabase.

Non esiste più alcuna query basata sul nome KREO.

## Snapshot ricevuta

La tabella `ricevute` conserva `snapshot_dati`, così una ricevuta storica non cambia se successivamente vengono modificati:

- ragione sociale;
- indirizzo;
- dati fiscali;
- anagrafica cliente.

## Generazione PDF

- `receipts.py`: generatore puro ReportLab.
- `services.py`: Storage e RPC.
- `app.py`: orchestra generazione e archiviazione.
- `registra_incasso_completo`: unica funzione per la registrazione economica.
