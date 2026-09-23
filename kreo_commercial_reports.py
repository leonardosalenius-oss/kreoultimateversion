"""Commercial value and cash reports, with explicit cohort and price coverage.

The input is the current operational state, not a historical ledger snapshot.
Contract values belong to data_inizio; cash always belongs to data_incasso.
Legacy contracts without a price snapshot never inherit today's catalogue price.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, Mapping


ZERO = Decimal("0.00")
CENT = Decimal("0.01")
Row = Mapping[str, Any]


def _money(value: Any, field: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"Importo mancante o non valido: {field}.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Importo non valido: {field}.") from None
    if not number.is_finite() or number < ZERO:
        raise ValueError(f"Importo non valido: {field}.")
    return number.quantize(CENT, rounding=ROUND_HALF_UP)


def _date(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        raise ValueError(f"Data mancante o non valida: {field}.") from None


def _deduplicate(rows: Iterable[Row], id_field: str, company_id: str,
                 financial_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Reject mixed-tenant inputs and conflicting duplicate financial records."""
    found: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        if str(row.get("azienda_id") or "") != str(company_id):
            raise ValueError("Dati del report non coerenti con l'azienda selezionata.")
        record_id = str(row.get(id_field) or "")
        if not record_id:
            raise ValueError(f"Identificativo mancante: {id_field}.")
        if record_id in found:
            if any(found[record_id].get(k) != row.get(k) for k in financial_fields):
                raise ValueError(f"Dati discordanti per {id_field} {record_id}.")
            continue
        found[record_id] = row
    return list(found.values())


def _month_keys(start: date, end: date) -> list[str]:
    cursor = start.replace(day=1)
    result = []
    while cursor <= end:
        result.append(cursor.strftime("%Y-%m"))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return result


def _blank_month(key: str) -> dict[str, Any]:
    return {
        "mese": key, "contratti": 0, "contratti_con_listino": 0,
        "listino_documentato": ZERO, "concordato_con_listino": ZERO,
        "sconti_documentati": ZERO, "maggiorazioni_documentate": ZERO,
        "concordato_totale": ZERO, "incassi_abbonamenti": ZERO,
        "incassi_altri": ZERO, "incassi_totali": ZERO,
        "rate_previste": ZERO,
    }


def build_commercial_report(*, subscriptions: Iterable[Row], receipts: Iterable[Row],
                            installments: Iterable[Row] = (), company_id: str,
                            start_date: date, end_date: date) -> dict[str, Any]:
    """Compute independently dated sales, valid cash and the current rate schedule.

    Contract residuals apply to the selected start-date cohort and valid receipts
    up to end_date. Current cancellation state is respected, even for past dates;
    this is expressly not a reconstruction of the state as it existed then.
    """
    if not company_id:
        raise ValueError("Azienda obbligatoria per il report.")
    start = _date(start_date, "Dal")
    end = _date(end_date, "Al")
    if start > end:
        raise ValueError("La data iniziale è successiva alla data finale.")
    monthly = {key: _blank_month(key) for key in _month_keys(start, end)}
    contract_fields = ("data_inizio", "prezzo_concordato", "prezzo_standard_totale",
                       "prezzo_schema_versione", "stato", "cliente_id")
    contracts = _deduplicate(subscriptions, "abbonamento_id", company_id, contract_fields)
    receipt_fields = ("data_incasso", "importo", "tipo_incasso", "stato",
                      "abbonamento_id", "cliente_id")
    payments = _deduplicate(receipts, "incasso_id", company_id, receipt_fields)
    rate_fields = ("data_scadenza", "importo_previsto", "stato", "abbonamento_id")
    rates = _deduplicate(installments, "rata_id", company_id, rate_fields)
    paid_by_contract: dict[str, Decimal] = {}
    receipt_details = []
    for row in payments:
        state = str(row.get("stato") or "").strip().lower()
        if state == "annullato":
            continue
        if state != "valido":
            raise ValueError("Stato di un incasso non riconosciuto; report interrotto.")
        paid_on = _date(row.get("data_incasso"), "data_incasso")
        amount = _money(row.get("importo"), "importo incasso")
        if amount == ZERO:
            raise ValueError("Un incasso valido deve avere importo positivo.")
        kind = row.get("tipo_incasso")
        if kind not in {"abbonamento", "vendita_prodotto", "servizio", "altro_ricavo"}:
            raise ValueError("Tipo di incasso non riconosciuto; report interrotto.")
        if kind == "abbonamento" and row.get("abbonamento_id") and paid_on <= end:
            sid = str(row["abbonamento_id"])
            paid_by_contract[sid] = paid_by_contract.get(sid, ZERO) + amount
        if start <= paid_on <= end:
            bucket = monthly[paid_on.strftime("%Y-%m")]
            bucket["incassi_abbonamenti" if kind == "abbonamento" else "incassi_altri"] += amount
            bucket["incassi_totali"] += amount
            receipt_details.append({
                "incasso_id": row["incasso_id"], "data_incasso": paid_on.isoformat(),
                "cliente": row.get("cliente") or "", "tipo_incasso": kind,
                "abbonamento_id": row.get("abbonamento_id"), "importo": amount,
                "metodo_pagamento": row.get("metodo_pagamento") or "",
            })

    contract_details = []
    valid_contract_ids = set()
    for row in contracts:
        if str(row.get("stato") or "").strip().lower() == "annullato":
            continue
        valid_contract_ids.add(str(row["abbonamento_id"]))
        begins = _date(row.get("data_inizio"), "data_inizio abbonamento")
        if not start <= begins <= end:
            continue
        agreed = _money(row.get("prezzo_concordato"), "totale concordato")
        # Only versioned contract snapshots are documentary evidence of list price.
        standard = None
        if row.get("prezzo_schema_versione") == 2 and row.get("prezzo_standard_totale") is not None:
            standard = _money(row["prezzo_standard_totale"], "totale listino storico")
        discount = max(standard - agreed, ZERO) if standard is not None else None
        surcharge = max(agreed - standard, ZERO) if standard is not None else None
        paid = paid_by_contract.get(str(row["abbonamento_id"]), ZERO)
        bucket = monthly[begins.strftime("%Y-%m")]
        bucket["contratti"] += 1
        bucket["concordato_totale"] += agreed
        if standard is not None:
            bucket["contratti_con_listino"] += 1
            bucket["listino_documentato"] += standard
            bucket["concordato_con_listino"] += agreed
            bucket["sconti_documentati"] += discount
            bucket["maggiorazioni_documentate"] += surcharge
        contract_details.append({
            "abbonamento_id": row["abbonamento_id"], "cliente": row.get("cliente") or "",
            "pacchetto": row.get("pacchetto") or "", "data_inizio": begins.isoformat(),
            "mesi_contratto": row.get("mesi_contratto"), "listino_totale": standard,
            "concordato_totale": agreed, "sconto": discount, "maggiorazione": surcharge,
            "incassato_entro_fine_periodo": paid,
            "residuo_entro_fine_periodo": max(agreed - paid, ZERO),
            "eccedenza_incassi": max(paid - agreed, ZERO),
            "copertura_listino": "Documentato" if standard is not None else "Non disponibile",
        })

    for row in rates:
        if row.get("annullata") is True or str(row.get("stato") or "").strip().lower() == "annullata":
            continue
        if str(row.get("abbonamento_id") or "") not in valid_contract_ids:
            continue
        due_on = _date(row.get("data_scadenza"), "data_scadenza rata")
        if start <= due_on <= end:
            monthly[due_on.strftime("%Y-%m")]["rate_previste"] += _money(
                row.get("importo_previsto"), "importo previsto rata")

    totals = {key: sum((row[key] for row in monthly.values()), 0 if key.startswith("contratti") else ZERO)
              for key in _blank_month("") if key != "mese"}
    totals["contratti_senza_listino"] = totals["contratti"] - totals["contratti_con_listino"]
    totals["concordato_senza_listino"] = totals["concordato_totale"] - totals["concordato_con_listino"]
    totals["incassato_coorte_entro_fine_periodo"] = sum(
        (row["incassato_entro_fine_periodo"] for row in contract_details), ZERO)
    totals["residuo_coorte_entro_fine_periodo"] = sum(
        (row["residuo_entro_fine_periodo"] for row in contract_details), ZERO)
    totals["eccedenza_incassi_coorte"] = sum((row["eccedenza_incassi"] for row in contract_details), ZERO)
    return {
        "company_id": str(company_id), "start_date": start, "end_date": end,
        "totals": totals, "monthly": list(monthly.values()),
        "contracts": sorted(contract_details, key=lambda r: (r["data_inizio"], str(r["abbonamento_id"]))),
        "receipts": sorted(receipt_details, key=lambda r: (r["data_incasso"], str(r["incasso_id"]))),
    }


def _load_all(db: Any, table: str, id_field: str, company_id: str,
              page_size: int = 500) -> list[dict[str, Any]]:
    """Continue until empty, including when a server cap is below page_size."""
    if not company_id:
        raise ValueError("Azienda obbligatoria per il report.")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _ in range(10000):
        response = (db.table(table).select("*").eq("azienda_id", company_id)
                    .order(id_field).range(len(result), len(result) + page_size - 1).execute())
        if response.data is None:
            raise RuntimeError("Lettura report incompleta; riprovare.")
        page = response.data
        if not page:
            return result
        for row in page:
            rid = str(row.get(id_field) or "")
            if not rid or rid in seen or str(row.get("azienda_id") or "") != str(company_id):
                raise RuntimeError("Dati del report variati durante la lettura; aggiornare la pagina.")
            seen.add(rid)
        result.extend(page)
    raise RuntimeError("Report troppo esteso per una lettura completa.")


def load_commercial_report(db: Any, company_id: str, start_date: date,
                           end_date: date) -> dict[str, Any]:
    return build_commercial_report(
        subscriptions=_load_all(db, "vista_abbonamenti_operativa", "abbonamento_id", company_id),
        receipts=_load_all(db, "vista_incassi_operativa", "incasso_id", company_id),
        installments=_load_all(db, "vista_rate_operativa", "rata_id", company_id),
        company_id=company_id, start_date=start_date, end_date=end_date,
    )


MONTHLY_COLUMNS = [
    ("mese", "Mese", "text", 12), ("contratti", "Contratti avviati", "number", 12),
    ("contratti_con_listino", "Con listino storico", "number", 14),
    ("listino_documentato", "Listino documentato", "currency", 18),
    ("concordato_con_listino", "Concordato confrontabile", "currency", 20),
    ("sconti_documentati", "Sconti documentati", "currency", 18),
    ("maggiorazioni_documentate", "Maggiorazioni documentate", "currency", 20),
    ("concordato_totale", "Totale contratti avviati", "currency", 20),
    ("incassi_abbonamenti", "Incassi abbonamenti", "currency", 18),
    ("incassi_altri", "Altri incassi", "currency", 16),
    ("incassi_totali", "Incassi totali", "currency", 16),
    ("rate_previste", "Rate previste per scadenza", "currency", 22),
]


def _display_rows(rows: Iterable[Row]) -> list[dict[str, Any]]:
    return [{key: float(value) if isinstance(value, Decimal) else value
             for key, value in row.items()} for row in rows]


def commercial_csv(rows: Iterable[Row]) -> bytes:
    rows = list(rows)
    if not rows:
        return b""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=";")
    writer.writeheader()
    for row in rows:
        safe = {}
        for key, value in row.items():
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                value = "'" + value
            safe[key] = value
        writer.writerow(safe)
    return output.getvalue().encode("utf-8-sig")


def _euro(value: Decimal) -> str:
    return "€ " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def render_commercial_report(st: Any, report: Mapping[str, Any], *, key_prefix: str,
                              render_exports: Any = None, export_column: Any = None) -> None:
    """Inject Streamlit and optionally the app's common Excel/PDF export controls."""
    totals = report["totals"]
    st.subheader("Listino, sconti e incassi")
    st.caption(
        "Valori commerciali: abbonamenti con data di inizio nel periodo. "
        "Incassi: pagamenti validi registrati nel periodo, anche per abbonamenti precedenti. "
        "Rate previste: piano attuale, ripartito per scadenza."
    )
    metrics = st.columns(4)
    for col, (label, key) in zip(metrics, [
        ("Listino documentato", "listino_documentato"),
        ("Concordato confrontabile", "concordato_con_listino"),
        ("Sconti documentati", "sconti_documentati"),
        ("Incassi effettivi", "incassi_totali"),
    ]):
        col.metric(label, _euro(totals[key]))
    st.write(f"Valore totale dei {totals['contratti']} contratti avviati: "
             f"{_euro(totals['concordato_totale'])}.")
    if totals["contratti_senza_listino"]:
        st.info(
            f"Listino storico non disponibile per {totals['contratti_senza_listino']} contratti "
            f"({_euro(totals['concordato_senza_listino'])} concordati). "
            "Questi contratti sono inclusi nei totali concordati e negli incassi, "
            "ma esclusi dal confronto listino/sconti."
        )
    if totals["maggiorazioni_documentate"]:
        st.write("Maggiorazioni sul listino documentate: " + _euro(totals["maggiorazioni_documentate"]))
    monthly = _display_rows(report["monthly"])
    # Chart contains cash only. Commercial amounts remain in the distinct table.
    st.bar_chart([
        {"Mese": row["mese"], "Abbonamenti": row["incassi_abbonamenti"],
         "Altri incassi": row["incassi_altri"]} for row in monthly
    ], x="Mese", y=["Abbonamenti", "Altri incassi"])
    labels = {key: label for key, label, _, _ in MONTHLY_COLUMNS}
    st.dataframe([{labels[key]: value for key, value in row.items()} for row in monthly],
                 hide_index=True, use_container_width=True)
    filters = [
        f"Dal {report['start_date'].isoformat()} al {report['end_date'].isoformat()}",
        "Contratti per data inizio; incassi per data incasso; rate per scadenza.",
        f"Listino disponibile: {totals['contratti_con_listino']} su {totals['contratti']} contratti.",
        "Stato corrente di contratti e annullamenti; valori non ricostruiti alla data storica.",
    ]
    if render_exports is not None and export_column is not None:
        render_exports(
            report_key=key_prefix + "_monthly", title="Listino sconti e incassi mensili",
            columns=[export_column(*column) for column in MONTHLY_COLUMNS], rows=monthly,
            filters=filters, totals={
                "Listino documentato": float(totals["listino_documentato"]),
                "Concordato confrontabile": float(totals["concordato_con_listino"]),
                "Concordato totale": float(totals["concordato_totale"]),
                "Sconti documentati": float(totals["sconti_documentati"]),
                "Incassi effettivi": float(totals["incassi_totali"]),
                "Contratti senza listino storico": totals["contratti_senza_listino"],
            },
        )
    else:
        st.download_button("Esporta riepilogo CSV", commercial_csv(report["monthly"]),
                           file_name="kreo_incassi_mensili.csv", mime="text/csv",
                           key=key_prefix + "_monthly_csv")
    with st.expander("Dettaglio contratti e incassi"):
        st.caption(
            "Il residuo di ciascun contratto considera gli incassi validi fino alla fine "
            "del periodo. Annullamenti e prezzi sono quelli attualmente registrati: "
            "questa vista non ricostruisce lo stato del gestionale a una data passata."
        )
        contract_labels = {
            "cliente": "Cliente", "pacchetto": "Pacchetto", "data_inizio": "Inizio",
            "mesi_contratto": "Mesi", "listino_totale": "Listino storico",
            "concordato_totale": "Totale concordato", "sconto": "Sconto",
            "maggiorazione": "Maggiorazione", "copertura_listino": "Listino disponibile",
            "incassato_entro_fine_periodo": "Pagato entro fine periodo",
            "residuo_entro_fine_periodo": "Residuo entro fine periodo",
            "eccedenza_incassi": "Eccedenza incassi",
        }
        st.dataframe([{label: row.get(key) for key, label in contract_labels.items()}
                      for row in _display_rows(report["contracts"])],
                     hide_index=True, use_container_width=True)
        st.download_button("Esporta contratti CSV", commercial_csv(report["contracts"]),
                           file_name="kreo_confronto_contratti.csv", mime="text/csv",
                           key=key_prefix + "_contracts_csv")
        receipt_labels = {"data_incasso": "Data incasso", "cliente": "Cliente",
                          "tipo_incasso": "Tipo", "importo": "Importo",
                          "metodo_pagamento": "Metodo pagamento"}
        st.dataframe([{label: row.get(key) for key, label in receipt_labels.items()}
                      for row in _display_rows(report["receipts"])],
                     hide_index=True, use_container_width=True)
        st.download_button("Esporta incassi CSV", commercial_csv(report["receipts"]),
                           file_name="kreo_incassi_periodo.csv", mime="text/csv",
                           key=key_prefix + "_receipts_csv")
