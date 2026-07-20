# Gestionale KREO v0.7 — persistente

Questa versione salva realmente i dati in Supabase.

## Prima di avviare

1. Eseguire in Supabase SQL Editor:

```text
sql/002_rpc_e_vista.sql
```

2. Inserire nei Secrets di Streamlit:

```toml
SUPABASE_URL = "https://..."
SUPABASE_SECRET_KEY = "sb_secret_..."
SUPABASE_SCHEMA = "gestionale_v2"
```

3. Installare le dipendenze:

```powershell
py -m pip install -r requirements.txt
```

4. Avviare:

```powershell
py -m streamlit run app.py
```

## Funzioni persistenti presenti

- lettura azienda KREO;
- creazione e lettura pacchetti;
- creazione transazionale di cliente, abbonamento, rate, incasso iniziale e metadati documenti;
- elenco clienti operativo;
- calcolo pagato, residuo e prossima rata dal database;
- registrazione di nuovi incassi.

I file dei documenti non vengono ancora caricati nello Storage: in questa fase vengono salvati i metadati.
