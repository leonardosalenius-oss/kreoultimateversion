# Gestionale KREO — nuova base

Questa repository contiene un nuovo `app.py` scritto da zero.

## Funzioni già presenti

- tema scuro con bordi dorati;
- menu Reception, Pacchetti, Abbonamenti, Clienti, Contabilità, Admin e Azienda;
- correzione visibilità testo dei pulsanti al passaggio del mouse;
- gestione pacchetti in memoria;
- data fine abbonamento proposta automaticamente in base al pacchetto;
- piano rate automatico e modificabile prima del salvataggio;
- registrazione cliente con possibilità di assegnare subito un abbonamento;
- caricamento documenti durante la registrazione;
- calcolo automatico del residuo;
- nuovo incasso;
- nuova spesa;
- nuovo fornitore;
- caricamento logo aziendale nella sessione.

## Importante

Questa versione usa `st.session_state` per verificare interfaccia e logiche.
I dati non sono ancora persistenti: il collegamento a Supabase verrà aggiunto nella fase successiva.

## Avvio

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Oppure:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Deploy Streamlit Cloud

File principale:

```text
app.py
```
