from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


def _money(value: Any) -> str:
    number = float(value or 0)
    return f"EUR {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _date_it(value: Any) -> str:
    if not value:
        return "-"
    text = str(value)
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text


def _safe(value: Any, default: str = "-") -> str:
    text = str(value or "").strip()
    return text or default


def build_receipt_pdf(
    detail: dict[str, Any],
    logo_bytes: bytes | None = None,
) -> bytes:
    receipt = detail["ricevuta"]
    company = detail["azienda"]
    client = detail["cliente"]
    payment = detail["incasso"]
    number = detail["numero_documento"]

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 18 * mm
    top = height - 18 * mm
    gold = colors.HexColor("#BFA15A")
    dark = colors.HexColor("#121416")
    muted = colors.HexColor("#666666")
    light = colors.HexColor("#F4F1E8")
    danger = colors.HexColor("#B42318")

    # Header background
    pdf.setFillColor(dark)
    pdf.roundRect(
        margin_x,
        top - 38 * mm,
        width - 2 * margin_x,
        38 * mm,
        4 * mm,
        fill=1,
        stroke=0,
    )

    logo_drawn = False
    if logo_bytes:
        try:
            image = ImageReader(BytesIO(logo_bytes))
            pdf.drawImage(
                image,
                margin_x + 6 * mm,
                top - 31 * mm,
                width=32 * mm,
                height=24 * mm,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
            logo_drawn = True
        except Exception:
            logo_drawn = False

    header_x = margin_x + (43 * mm if logo_drawn else 7 * mm)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(
        header_x,
        top - 12 * mm,
        _safe(company.get("nome_visualizzato"), "Azienda"),
    )

    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(
        header_x,
        top - 19 * mm,
        _safe(company.get("ragione_sociale")),
    )

    tax_parts = []
    if company.get("partita_iva"):
        tax_parts.append(f"P. IVA {company['partita_iva']}")
    if company.get("codice_fiscale"):
        tax_parts.append(f"C.F. {company['codice_fiscale']}")
    pdf.drawString(
        header_x,
        top - 25 * mm,
        " - ".join(tax_parts) or "Dati fiscali non configurati",
    )

    address_parts = [
        company.get("indirizzo") or company.get("sede_legale"),
        " ".join(
            part for part in [
                company.get("cap"),
                company.get("citta"),
                company.get("provincia"),
            ] if part
        ),
    ]
    pdf.drawString(
        header_x,
        top - 31 * mm,
        " - ".join(part for part in address_parts if part)
        or "Sede non configurata",
    )

    # Receipt title
    y = top - 51 * mm
    pdf.setFillColor(dark)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin_x, y, _safe(company.get("dicitura_ricevuta"), "Ricevuta non fiscale"))

    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(gold)
    number_text = f"N. {number}"
    pdf.drawRightString(width - margin_x, y + 1 * mm, number_text)

    y -= 10 * mm
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1)
    pdf.line(margin_x, y, width - margin_x, y)

    # Data cards
    y -= 14 * mm
    card_width = (width - 2 * margin_x - 8 * mm) / 3
    cards = [
        ("DATA", _date_it(receipt.get("data_emissione"))),
        ("IMPORTO", _money(receipt.get("importo"))),
        ("METODO", _safe(receipt.get("metodo_pagamento"))),
    ]

    for index, (label, value) in enumerate(cards):
        x = margin_x + index * (card_width + 4 * mm)
        pdf.setFillColor(light)
        pdf.roundRect(x, y - 18 * mm, card_width, 18 * mm, 3 * mm, fill=1, stroke=0)
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(x + 5 * mm, y - 6 * mm, label)
        pdf.setFillColor(dark)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x + 5 * mm, y - 13 * mm, value)

    y -= 31 * mm

    # Client section
    pdf.setFillColor(dark)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin_x, y, "Ricevuto da")

    y -= 8 * mm
    client_name = " ".join(
        part for part in [
            client.get("nome"),
            client.get("cognome"),
        ] if part
    )
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin_x, y, _safe(client_name, "Cliente"))

    y -= 7 * mm
    pdf.setFont("Helvetica", 9.5)
    client_details = []
    if client.get("codice_fiscale"):
        client_details.append(f"C.F. {client['codice_fiscale']}")
    if client.get("partita_iva"):
        client_details.append(f"P. IVA {client['partita_iva']}")
    if client.get("indirizzo"):
        client_details.append(client["indirizzo"])
    pdf.setFillColor(muted)
    pdf.drawString(
        margin_x,
        y,
        " - ".join(client_details) or "Dati identificativi non inseriti",
    )

    # Reason box
    y -= 17 * mm
    pdf.setFillColor(light)
    pdf.roundRect(
        margin_x,
        y - 35 * mm,
        width - 2 * margin_x,
        35 * mm,
        3 * mm,
        fill=1,
        stroke=0,
    )
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(margin_x + 6 * mm, y - 7 * mm, "CAUSALE")

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "receipt_body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=dark,
        alignment=TA_LEFT,
    )
    type_map = {
        "abbonamento": "Abbonamento",
        "vendita_prodotto": "Vendita prodotto / integratori",
        "servizio": "Servizio extra",
        "altro_ricavo": "Altro ricavo",
    }
    reason = (
        f"<b>{type_map.get(payment.get('tipo_incasso'), 'Incasso')}</b><br/>"
        f"{_safe(payment.get('causale'), 'Pagamento')}"
    )
    paragraph = Paragraph(reason, body_style)
    paragraph.wrapOn(pdf, width - 2 * margin_x - 12 * mm, 23 * mm)
    paragraph.drawOn(pdf, margin_x + 6 * mm, y - 29 * mm)

    # Banking/contact information
    y -= 49 * mm
    pdf.setFillColor(dark)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(margin_x, y, "Informazioni aziendali")

    y -= 7 * mm
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(muted)
    contact_lines = []
    if company.get("telefono"):
        contact_lines.append(f"Tel. {company['telefono']}")
    if company.get("email"):
        contact_lines.append(company["email"])
    if company.get("pec"):
        contact_lines.append(f"PEC {company['pec']}")
    if company.get("iban"):
        contact_lines.append(f"IBAN {company['iban']}")
    if company.get("banca"):
        contact_lines.append(company["banca"])

    for line in contact_lines[:4]:
        pdf.drawString(margin_x, y, line)
        y -= 5 * mm

    # Status watermark
    if receipt.get("stato") == "annullata":
        pdf.saveState()
        pdf.setFillColor(danger)
        pdf.setFillAlpha(0.16)
        pdf.setFont("Helvetica-Bold", 48)
        pdf.translate(width / 2, height / 2)
        pdf.rotate(32)
        text_width = stringWidth("ANNULLATA", "Helvetica-Bold", 48)
        pdf.drawString(-text_width / 2, 0, "ANNULLATA")
        pdf.restoreState()

    # Footer
    footer_text = _safe(
        company.get("footer_documenti"),
        "Documento generato dal gestionale.",
    )
    footer_style = ParagraphStyle(
        "footer",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=muted,
        alignment=TA_CENTER,
    )
    footer = Paragraph(footer_text, footer_style)
    footer.wrapOn(pdf, width - 2 * margin_x, 18 * mm)
    footer.drawOn(pdf, margin_x, 13 * mm)

    pdf.setStrokeColor(gold)
    pdf.line(margin_x, 27 * mm, width - margin_x, 27 * mm)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
