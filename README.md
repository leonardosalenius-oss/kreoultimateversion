# Gestionale v0.16 — Contabilità passiva

## Prima del deploy

Eseguire una sola volta in Supabase SQL Editor:

```text
sql/010_contabilita_passiva.sql
```

Poi caricare **tutti i file dello ZIP** su GitHub.

## Funzioni introdotte

### Fornitori

- elenco con ricerca;
- nuovo fornitore;
- modifica;
- stato attivo/inattivo;
- dati fiscali, contatti e IBAN.

### Categorie di spesa

Categorie standard create per ogni azienda:

- affitto;
- utenze;
- personale;
- consulenze;
- acquisto merci;
- integratori;
- manutenzioni;
- pubblicità;
- attrezzature;
- altro.

È possibile creare categorie personalizzate durante la registrazione della spesa.

### Spese

- fornitore e categoria;
- imponibile, IVA e totale;
- documento e competenza;
- upload fattura o ricevuta;
- piano di una o più scadenze;
- pagamento iniziale;
- calcolo del debito residuo.

### Pagamenti fornitori

- pagamenti parziali;
- allocazione automatica alle scadenze più vecchie;
- annullamento con motivazione;
- ricalcolo integrale delle allocazioni;
- storico pagamenti.

### Scadenziario

Stati calcolati dal database:

- da pagare;
- parzialmente pagata;
- pagata;
- scaduta;
- scaduta parziale.

## Logica unica

```text
spesa
→ scadenze
→ pagamenti
→ allocazioni
→ residuo
```

Il residuo non è salvato manualmente: viene sempre calcolato dai pagamenti validi.
