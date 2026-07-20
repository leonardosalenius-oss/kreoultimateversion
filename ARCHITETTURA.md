# Architettura contabilità passiva v0.16

## Aggregati

- `fornitori`: anagrafica controparte.
- `spese`: documento/costo originario.
- `scadenze_spesa`: piano delle obbligazioni.
- `pagamenti_spesa`: movimenti finanziari reali.
- `allocazioni_pagamenti_spesa`: collegamento tra pagamenti e scadenze.

## Regole

- La somma delle scadenze deve coincidere con il totale della spesa.
- Un pagamento non può superare il residuo.
- Ogni pagamento valido viene allocato alle scadenze più vecchie.
- L'annullamento non cancella il movimento e ricostruisce tutte le allocazioni.
- Le viste operative calcolano pagato, residuo e stato.
