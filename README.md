# Gestionale KREO v0.11 — Upload documenti

La gestione documenti ora salva sia i metadati nel database sia il file reale in Supabase Storage.

## Prima del deploy

Eseguire una sola volta nel SQL Editor:

```text
sql/006_storage_documenti.sql
```

Lo script:

- crea/aggiorna il bucket privato `documenti-clienti`;
- limita i file a 10 MB;
- ammette PDF, PNG e JPEG;
- aggiorna la funzione database dei documenti;
- include nome file e percorso Storage nel dettaglio cliente.

## Flusso documento

1. L'utente seleziona un file.
2. Il backend Streamlit lo carica nel bucket privato.
3. Il database registra metadati e percorso.
4. In caso di errore database, il file appena caricato viene rimosso.
5. I file vengono aperti tramite URL firmato temporaneo.
6. La sostituzione conserva il documento precedente come annullato.
7. L'annullamento non elimina fisicamente il file, preservando lo storico.
