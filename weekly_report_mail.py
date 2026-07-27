from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from supabase import Client

from export_utils import ExportColumn, build_excel_bytes, build_pdf_bytes


ROME = ZoneInfo("Europe/Rome")


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    mime_type: str
    mime_subtype: str


def _money(value: Any) -> str:
    try:
        return (
            f"EUR {float(value):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except (TypeError, ValueError):
        return "EUR 0,00"


def _client_columns() -> list[ExportColumn]:
    return [
        ExportColumn("cliente", "Cliente", "text", 27),
        ExportColumn("telefono", "Telefono", "text", 15),
        ExportColumn("whatsapp", "WhatsApp", "text", 15),
        ExportColumn("pacchetto", "Pacchetto", "text", 25),
        ExportColumn("scadenza", "Scadenza", "date", 13),
        ExportColumn("lezioni_residue", "Lezioni residue", "number", 13),
        ExportColumn("prezzo", "Prezzo iniziale", "currency", 14),
        ExportColumn("pagato", "Pagato", "currency", 12),
        ExportColumn("residuo", "Residuo", "currency", 12),
        ExportColumn("prossima_rata", "Prossima rata", "date", 13),
        ExportColumn(
            "importo_prossima_rata",
            "Importo prossima rata",
            "currency",
            15,
        ),
        ExportColumn("certificato", "Certificato", "text", 16),
        ExportColumn("stato_cliente", "Stato cliente", "text", 13),
    ]


def _client_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "cliente": (
                f"{row.get('cognome') or ''} "
                f"{row.get('nome') or ''}"
            ).strip(),
            "telefono": row.get("telefono"),
            "whatsapp": row.get("whatsapp"),
            "pacchetto": row.get("pacchetto_nome"),
            "scadenza": (
                None
                if row.get("senza_scadenza")
                else row.get("data_fine_prevista")
            ),
            "lezioni_residue": row.get("saldo_lezioni"),
            "prezzo": float(row.get("prezzo_concordato") or 0),
            "pagato": float(row.get("pagato") or 0),
            "residuo": float(row.get("residuo") or 0),
            "prossima_rata": row.get("prossima_rata_data"),
            "importo_prossima_rata": float(
                row.get("prossima_rata_importo") or 0
            ),
            "certificato": row.get("certificato_stato") or "Mancante",
            "stato_cliente": (
                row.get("stato_cliente")
                or row.get("stato")
                or "attivo"
            ),
        }
        for row in rows
    ]


def _inventory_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        stock = float(row.get("giacenza") or 0)
        cost = float(row.get("costo_medio") or 0)
        minimum = float(row.get("scorta_minima") or 0)
        if not row.get("attivo"):
            state = "Inattivo"
        elif stock <= 0:
            state = "Esaurito"
        elif minimum > 0 and stock <= minimum:
            state = "Scorta bassa"
        else:
            state = "Disponibile"
        output.append({
            "codice": row.get("codice"),
            "prodotto": row.get("nome"),
            "categoria": row.get("categoria"),
            "marca": row.get("marca"),
            "giacenza": stock,
            "costo_medio": cost,
            "valore": stock * cost,
            "scorta_minima": minimum,
            "stato": state,
        })
    return output


def _movement_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "data": row.get("data_movimento"),
            "prodotto": row.get("prodotto"),
            "tipo": row.get("tipo"),
            "quantita": float(row.get("quantita") or 0),
            "costo_unitario": float(row.get("costo_unitario") or 0),
            "valore": abs(float(row.get("quantita") or 0))
            * float(row.get("costo_unitario") or 0),
            "fornitore": row.get("fornitore"),
            "documento": row.get("documento"),
            "causale": row.get("causale"),
            "stato": row.get("stato"),
        }
        for row in rows
    ]


INVENTORY_COLUMNS = [
    ExportColumn("codice", "Codice", "text", 13),
    ExportColumn("prodotto", "Prodotto", "text", 30),
    ExportColumn("categoria", "Categoria", "text", 15),
    ExportColumn("marca", "Marca", "text", 15),
    ExportColumn("giacenza", "Giacenza", "number", 12),
    ExportColumn("costo_medio", "Costo medio", "currency", 12),
    ExportColumn("valore", "Valore giacenza", "currency", 14),
    ExportColumn("scorta_minima", "Scorta minima", "number", 12),
    ExportColumn("stato", "Stato", "text", 13),
]

MOVEMENT_COLUMNS = [
    ExportColumn("data", "Data", "date", 12),
    ExportColumn("prodotto", "Prodotto", "text", 28),
    ExportColumn("tipo", "Tipo", "text", 17),
    ExportColumn("quantita", "Quantità", "number", 11),
    ExportColumn("costo_unitario", "Costo unitario", "currency", 13),
    ExportColumn("valore", "Valore", "currency", 13),
    ExportColumn("fornitore", "Fornitore", "text", 22),
    ExportColumn("documento", "Documento", "text", 15),
    ExportColumn("causale", "Causale", "text", 26),
    ExportColumn("stato", "Stato", "text", 11),
]


def _fetch_data(
    db: Client,
    company_id: str,
    start_date: date,
    end_date: date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    clients = (
        db.table("vista_clienti_operativa")
        .select("*")
        .eq("azienda_id", company_id)
        .order("cognome")
        .order("nome")
        .execute()
        .data
        or []
    )
    inventory = (
        db.table("vista_prodotti_magazzino")
        .select("*")
        .eq("azienda_id", company_id)
        .order("nome")
        .execute()
        .data
        or []
    )
    movements = (
        db.table("vista_movimenti_magazzino")
        .select("*")
        .eq("azienda_id", company_id)
        .gte("data_movimento", start_date.isoformat())
        .lte("data_movimento", end_date.isoformat())
        .order("data_movimento")
        .execute()
        .data
        or []
    )
    return clients, inventory, movements


def _write_sheet(
    workbook: xlsxwriter.Workbook,
    name: str,
    columns: list[ExportColumn],
    rows: list[dict[str, Any]],
) -> None:
    ws = workbook.add_worksheet(name[:31])
    header = workbook.add_format({
        "bold": True,
        "font_color": "#F6F2E8",
        "bg_color": "#171A1E",
        "border": 1,
        "border_color": "#BFA15A",
        "text_wrap": True,
        "align": "center",
    })
    text = workbook.add_format({"border": 1, "border_color": "#D8D1C0"})
    num = workbook.add_format({
        "border": 1,
        "border_color": "#D8D1C0",
        "num_format": "#,##0.###",
    })
    money = workbook.add_format({
        "border": 1,
        "border_color": "#D8D1C0",
        "num_format": 'EUR #,##0.00',
    })
    date_fmt = workbook.add_format({
        "border": 1,
        "border_color": "#D8D1C0",
        "num_format": "dd/mm/yyyy",
    })
    for col_idx, column in enumerate(columns):
        ws.write(0, col_idx, column.label, header)
        ws.set_column(col_idx, col_idx, min(max(column.width, 9), 38))
    for row_idx, row in enumerate(rows, start=1):
        for col_idx, column in enumerate(columns):
            value = row.get(column.key)
            if column.kind == "currency":
                ws.write_number(row_idx, col_idx, float(value or 0), money)
            elif column.kind == "number":
                ws.write_number(row_idx, col_idx, float(value or 0), num)
            elif column.kind == "date" and value:
                try:
                    parsed = datetime.fromisoformat(str(value)[:10])
                    ws.write_datetime(row_idx, col_idx, parsed, date_fmt)
                except ValueError:
                    ws.write(row_idx, col_idx, str(value), text)
            else:
                ws.write(row_idx, col_idx, "" if value is None else str(value), text)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(len(rows), 1), max(len(columns) - 1, 0))
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.hide_gridlines(2)


def _build_integrators_excel(
    inventory_rows: list[dict[str, Any]],
    purchase_rows: list[dict[str, Any]],
    movement_rows: list[dict[str, Any]],
) -> bytes:
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    _write_sheet(workbook, "Inventario valorizzato", INVENTORY_COLUMNS, inventory_rows)
    _write_sheet(workbook, "Acquisti settimana", MOVEMENT_COLUMNS, purchase_rows)
    _write_sheet(workbook, "Movimenti settimana", MOVEMENT_COLUMNS, movement_rows)
    workbook.close()
    output.seek(0)
    return output.getvalue()


def _pdf_table(
    columns: list[ExportColumn],
    rows: list[dict[str, Any]],
    width: float,
) -> Table:
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=6.5, leading=7.7)
    head = ParagraphStyle(
        "head", parent=cell, fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    data = [[Paragraph(c.label, head) for c in columns]]
    for row in rows:
        values = []
        for c in columns:
            value = row.get(c.key)
            if c.kind == "currency":
                shown = _money(value)
            elif c.kind == "date" and value:
                try:
                    shown = datetime.fromisoformat(str(value)[:10]).strftime("%d/%m/%Y")
                except ValueError:
                    shown = str(value)
            elif c.kind == "number":
                try:
                    n = float(value or 0)
                    shown = str(int(n)) if n.is_integer() else str(n).replace(".", ",")
                except (TypeError, ValueError):
                    shown = str(value or "")
            else:
                shown = str(value or "")
            values.append(Paragraph(shown.replace("&", "&amp;"), cell))
        data.append(values)
    total_weight = sum(c.width for c in columns)
    widths = [width * c.width / total_weight for c in columns]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#171A1E")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8B98D")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white, colors.HexColor("#F6F3EB")
        ]),
    ]))
    return table


def _build_integrators_pdf(
    company: dict[str, Any],
    inventory_rows: list[dict[str, Any]],
    purchase_rows: list[dict[str, Any]],
    movement_rows: list[dict[str, Any]],
    start_date: date,
    end_date: date,
) -> bytes:
    output = BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        output, pagesize=page_size,
        rightMargin=9 * mm, leftMargin=9 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "title", parent=styles["Title"], fontSize=16, leading=19,
        textColor=colors.HexColor("#171A1E"), alignment=TA_LEFT,
    )
    subtitle = ParagraphStyle(
        "subtitle", parent=styles["Normal"], fontSize=8.5, leading=10,
        textColor=colors.HexColor("#666666"),
    )
    section = ParagraphStyle(
        "section", parent=styles["Heading2"], fontSize=12, leading=14,
        textColor=colors.HexColor("#9B7E36"),
    )
    width = page_size[0] - 18 * mm
    company_name = company.get("nome_visualizzato") or company.get("ragione_sociale") or "KREO"
    story = [
        Paragraph("Report integratori", title),
        Paragraph(
            f"{company_name} · settimana {start_date.strftime('%d/%m/%Y')} - "
            f"{end_date.strftime('%d/%m/%Y')}",
            subtitle,
        ),
        Spacer(1, 5 * mm),
        Paragraph("Inventario valorizzato", section),
        _pdf_table(INVENTORY_COLUMNS, inventory_rows, width),
        PageBreak(),
        Paragraph("Acquisti della settimana", section),
        _pdf_table(MOVEMENT_COLUMNS, purchase_rows, width),
        PageBreak(),
        Paragraph("Movimenti della settimana", section),
        _pdf_table(MOVEMENT_COLUMNS, movement_rows, width),
    ]
    doc.build(story)
    output.seek(0)
    return output.getvalue()


def _already_sent(
    db: Client,
    company_id: str,
    scheduled_for: str,
) -> bool:
    response = (
        db.table("invii_report")
        .select("id")
        .eq("azienda_id", company_id)
        .eq("tipo_report", "settimanale_clienti_integratori")
        .eq("programmato_per", scheduled_for)
        .eq("stato", "inviato")
        .limit(1)
        .execute()
    )
    return bool(response.data)


def _log_send(
    db: Client,
    company_id: str,
    recipient: str,
    scheduled_for: str,
    status: str,
    source: str,
    error: str | None = None,
) -> None:
    db.table("invii_report").insert({
        "azienda_id": company_id,
        "tipo_report": "settimanale_clienti_integratori",
        "destinatario": recipient,
        "programmato_per": scheduled_for,
        "stato": status,
        "canale": "email",
        "origine": source,
        "errore": error,
    }).execute()


def send_weekly_reports_email(
    *,
    db: Client,
    company: dict[str, Any],
    smtp_host: str,
    smtp_port: int,
    username: str,
    app_password: str,
    sender_name: str,
    recipient: str,
    force: bool = False,
    source: str = "scheduler",
    now: datetime | None = None,
) -> dict[str, Any]:
    local_now = (now or datetime.now(ROME)).astimezone(ROME)
    scheduled_for = (
        local_now.date().isoformat()
        if local_now.weekday() == 4
        else f"manuale-{local_now.strftime('%Y-%m-%d-%H%M%S')}"
    )

    if not force:
        if local_now.weekday() != 4 or local_now.hour != 19:
            return {"sent": False, "reason": "outside_schedule"}
        if _already_sent(db, company["id"], scheduled_for):
            return {"sent": False, "reason": "already_sent"}

    end_date = local_now.date()
    start_date = end_date - timedelta(days=6)
    clients_raw, inventory_raw, movements_raw = _fetch_data(
        db, company["id"], start_date, end_date
    )

    clients = _client_rows(clients_raw)
    inventory = _inventory_rows(inventory_raw)
    movements = _movement_rows(movements_raw)
    purchases = [row for row in movements if row["tipo"] == "acquisto"]

    generated_at = local_now.replace(tzinfo=None)
    clients_pdf = build_pdf_bytes(
        title="Report clienti",
        company=company,
        columns=_client_columns(),
        rows=clients,
        filters=["Tutti i clienti"],
        totals={
            "Numero clienti": len(clients),
            "Residuo complessivo": sum(row["residuo"] for row in clients),
        },
        generated_at=generated_at,
        orientation="landscape",
    )
    clients_xlsx = build_excel_bytes(
        title="Report clienti",
        company=company,
        columns=_client_columns(),
        rows=clients,
        filters=["Tutti i clienti"],
        totals={
            "Numero clienti": len(clients),
            "Residuo complessivo": sum(row["residuo"] for row in clients),
        },
        generated_at=generated_at,
    )
    integrators_pdf = _build_integrators_pdf(
        company, inventory, purchases, movements, start_date, end_date
    )
    integrators_xlsx = _build_integrators_excel(
        inventory, purchases, movements
    )

    attachments = [
        Attachment("report_clienti.pdf", clients_pdf, "application", "pdf"),
        Attachment(
            "report_clienti.xlsx", clients_xlsx,
            "application",
            "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        Attachment(
            "report_integratori.pdf", integrators_pdf,
            "application", "pdf",
        ),
        Attachment(
            "report_integratori.xlsx", integrators_xlsx,
            "application",
            "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    ]

    company_name = (
        company.get("nome_visualizzato")
        or company.get("ragione_sociale")
        or "KREO"
    )
    message = EmailMessage()
    message["From"] = f"{sender_name} <{username}>"
    message["To"] = recipient
    message["Subject"] = (
        f"{company_name} · report settimanali "
        f"{end_date.strftime('%d/%m/%Y')}"
    )
    message.set_content(
        f"""Ciao Rosario,

in allegato trovi i report settimanali KREO:

1. Report clienti, PDF ed Excel;
2. Report integratori, PDF ed Excel, con:
   - inventario valorizzato attuale;
   - acquisti dal {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')};
   - movimenti dello stesso periodo.

Messaggio generato automaticamente dal Gestionale KREO.
"""
    )
    for item in attachments:
        message.add_attachment(
            item.content,
            maintype=item.mime_type,
            subtype=item.mime_subtype,
            filename=item.filename,
        )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(username, app_password.replace(" ", ""))
            smtp.send_message(message)
        _log_send(
            db, company["id"], recipient, scheduled_for,
            "inviato", source
        )
    except Exception as exc:
        try:
            _log_send(
                db, company["id"], recipient, scheduled_for,
                "errore", source, str(exc)[:1000]
            )
        except Exception:
            pass
        raise

    return {
        "sent": True,
        "attachment_count": len(attachments),
        "recipient": recipient,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
