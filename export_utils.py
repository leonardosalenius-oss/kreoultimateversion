from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO, StringIO
from typing import Any

import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass(frozen=True)
class ExportColumn:
    key: str
    label: str
    kind: str = "text"
    width: float = 16


def _company_name(company: dict[str, Any]) -> str:
    return (
        company.get("nome_visualizzato")
        or company.get("ragione_sociale")
        or "Azienda"
    )


def _legal_lines(company: dict[str, Any]) -> list[str]:
    lines = []
    legal_name = company.get("ragione_sociale")
    if legal_name:
        lines.append(str(legal_name))

    fiscal_parts = []
    if company.get("partita_iva"):
        fiscal_parts.append(f"P. IVA {company['partita_iva']}")
    if company.get("codice_fiscale"):
        fiscal_parts.append(f"C.F. {company['codice_fiscale']}")
    if fiscal_parts:
        lines.append(" - ".join(fiscal_parts))

    address = (
        company.get("indirizzo")
        or company.get("sede_legale")
    )
    if address:
        lines.append(str(address))

    return lines


def _parse_date(value: Any) -> datetime | None:
    if value in (None, "", "-"):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    try:
        return datetime.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _display_value(value: Any, kind: str) -> str:
    if value is None:
        return ""
    if kind == "currency":
        try:
            return (
                f"EUR {float(value):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        except (TypeError, ValueError):
            return str(value)
    if kind == "number":
        try:
            number = float(value)
            if number.is_integer():
                return str(int(number))
            return (
                f"{number:,.3f}"
                .rstrip("0")
                .rstrip(".")
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        except (TypeError, ValueError):
            return str(value)
    if kind == "date":
        parsed = _parse_date(value)
        return parsed.strftime("%d/%m/%Y") if parsed else ""
    return str(value)


def build_csv_bytes(
    *,
    columns: list[ExportColumn],
    rows: list[dict[str, Any]],
) -> bytes:
    stream = StringIO()
    writer = csv.writer(stream, delimiter=";", lineterminator="\n")
    writer.writerow([column.label for column in columns])
    for row in rows:
        writer.writerow([
            _display_value(row.get(column.key), column.kind)
            for column in columns
        ])
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def build_excel_bytes(
    *,
    title: str,
    company: dict[str, Any],
    columns: list[ExportColumn],
    rows: list[dict[str, Any]],
    filters: list[str],
    totals: dict[str, Any],
    generated_at: datetime,
) -> bytes:
    output = BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {"in_memory": True},
    )
    worksheet = workbook.add_worksheet("Report")

    gold = "#BFA15A"
    dark = "#171A1E"
    light = "#F6F2E8"
    border = "#D8D1C0"

    title_format = workbook.add_format({
        "bold": True,
        "font_size": 18,
        "font_color": dark,
        "align": "left",
        "valign": "vcenter",
    })
    company_format = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "font_color": gold,
    })
    meta_format = workbook.add_format({
        "font_size": 9,
        "font_color": "#666666",
    })
    header_format = workbook.add_format({
        "bold": True,
        "font_color": light,
        "bg_color": dark,
        "border": 1,
        "border_color": gold,
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })
    text_format = workbook.add_format({
        "border": 1,
        "border_color": border,
        "valign": "top",
        "text_wrap": True,
    })
    number_format = workbook.add_format({
        "border": 1,
        "border_color": border,
        "num_format": "#,##0.###",
    })
    currency_format = workbook.add_format({
        "border": 1,
        "border_color": border,
        "num_format": 'EUR #,##0.00',
    })
    date_format = workbook.add_format({
        "border": 1,
        "border_color": border,
        "num_format": "dd/mm/yyyy",
    })
    blank_format = workbook.add_format({
        "border": 1,
        "border_color": border,
        "bg_color": "#FFFCEB",
    })
    total_label_format = workbook.add_format({
        "bold": True,
        "font_color": dark,
        "bg_color": "#EEE7D4",
        "border": 1,
        "border_color": gold,
    })
    total_value_format = workbook.add_format({
        "bold": True,
        "font_color": dark,
        "bg_color": "#EEE7D4",
        "border": 1,
        "border_color": gold,
    })

    last_column = max(len(columns) - 1, 0)
    worksheet.merge_range(
        0,
        0,
        0,
        last_column,
        title,
        title_format,
    )
    worksheet.merge_range(
        1,
        0,
        1,
        last_column,
        _company_name(company),
        company_format,
    )

    metadata = (
        f"Generato il {generated_at.strftime('%d/%m/%Y alle %H:%M')}"
    )
    worksheet.merge_range(
        2,
        0,
        2,
        last_column,
        metadata,
        meta_format,
    )

    current_row = 3
    legal_lines = _legal_lines(company)
    for line in legal_lines:
        worksheet.merge_range(
            current_row,
            0,
            current_row,
            last_column,
            line,
            meta_format,
        )
        current_row += 1

    for filter_text in filters:
        worksheet.merge_range(
            current_row,
            0,
            current_row,
            last_column,
            f"Filtro: {filter_text}",
            meta_format,
        )
        current_row += 1

    current_row += 1
    header_row = current_row
    for col_index, column in enumerate(columns):
        worksheet.write(
            header_row,
            col_index,
            column.label,
            header_format,
        )
        worksheet.set_column(
            col_index,
            col_index,
            min(max(column.width, 9), 38),
        )

    for row_index, row in enumerate(rows, start=header_row + 1):
        for col_index, column in enumerate(columns):
            value = row.get(column.key)
            if column.kind == "currency":
                worksheet.write_number(
                    row_index,
                    col_index,
                    float(value or 0),
                    currency_format,
                )
            elif column.kind == "number":
                worksheet.write_number(
                    row_index,
                    col_index,
                    float(value or 0),
                    number_format,
                )
            elif column.kind == "date":
                parsed = _parse_date(value)
                if parsed:
                    worksheet.write_datetime(
                        row_index,
                        col_index,
                        parsed,
                        date_format,
                    )
                else:
                    worksheet.write_blank(
                        row_index,
                        col_index,
                        None,
                        text_format,
                    )
            elif column.kind == "blank":
                worksheet.write_blank(
                    row_index,
                    col_index,
                    None,
                    blank_format,
                )
            else:
                worksheet.write(
                    row_index,
                    col_index,
                    "" if value is None else str(value),
                    text_format,
                )

    last_data_row = header_row + len(rows)
    worksheet.autofilter(
        header_row,
        0,
        max(last_data_row, header_row),
        last_column,
    )
    worksheet.freeze_panes(header_row + 1, 0)

    if totals:
        total_row = last_data_row + 2
        for label, value in totals.items():
            worksheet.write(
                total_row,
                0,
                str(label),
                total_label_format,
            )
            if isinstance(value, (int, float)):
                worksheet.write_number(
                    total_row,
                    1,
                    float(value),
                    total_value_format,
                )
            else:
                worksheet.write(
                    total_row,
                    1,
                    str(value),
                    total_value_format,
                )
            total_row += 1

    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)
    worksheet.set_margins(0.35, 0.35, 0.55, 0.55)
    worksheet.set_header(
        f"&L{_company_name(company)}&R{title}"
    )
    worksheet.set_footer(
        "&LGenerato dal Gestionale&RPagina &P di &N"
    )
    worksheet.hide_gridlines(2)

    workbook.close()
    output.seek(0)
    return output.getvalue()


def build_pdf_bytes(
    *,
    title: str,
    company: dict[str, Any],
    columns: list[ExportColumn],
    rows: list[dict[str, Any]],
    filters: list[str],
    totals: dict[str, Any],
    generated_at: datetime,
    orientation: str = "landscape",
) -> bytes:
    output = BytesIO()
    page_size = (
        landscape(A4)
        if orientation == "landscape"
        else portrait(A4)
    )
    document = SimpleDocTemplate(
        output,
        pagesize=page_size,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=title,
        author=_company_name(company),
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#171A1E"),
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    company_style = ParagraphStyle(
        "Company",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#9B7E36"),
        alignment=TA_LEFT,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#555555"),
        alignment=TA_LEFT,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontSize=6.7,
        leading=8,
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "Header",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    story = [
        Paragraph(title, title_style),
        Paragraph(_company_name(company), company_style),
    ]

    for line in _legal_lines(company):
        story.append(Paragraph(line, meta_style))

    story.append(
        Paragraph(
            (
                "Generato il "
                f"{generated_at.strftime('%d/%m/%Y alle %H:%M')}"
            ),
            meta_style,
        )
    )
    if filters:
        story.append(
            Paragraph(
                "Filtri: " + " | ".join(filters),
                meta_style,
            )
        )
    story.append(Spacer(1, 5 * mm))

    data = [[
        Paragraph(column.label, header_style)
        for column in columns
    ]]
    for row in rows:
        data.append([
            Paragraph(
                _display_value(
                    row.get(column.key),
                    column.kind,
                ).replace("&", "&amp;"),
                cell_style,
            )
            for column in columns
        ])

    available_width = page_size[0] - 20 * mm
    width_total = sum(max(column.width, 1) for column in columns)
    column_widths = [
        available_width * (max(column.width, 1) / width_total)
        for column in columns
    ]

    table = Table(
        data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#171A1E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8B98D")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F6F3EB"),
        ]),
    ]))
    story.append(table)

    if totals:
        story.append(Spacer(1, 5 * mm))
        total_data = [
            [
                Paragraph(str(label), company_style),
                Paragraph(
                    _display_value(
                        value,
                        (
                            "currency"
                            if isinstance(value, float)
                            else "text"
                        ),
                    ),
                    cell_style,
                ),
            ]
            for label, value in totals.items()
        ]
        totals_table = Table(
            total_data,
            colWidths=[55 * mm, 45 * mm],
            hAlign="LEFT",
        )
        totals_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEE7D4")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFA15A")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(KeepTogether(totals_table))

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(
            10 * mm,
            7 * mm,
            "Generato dal Gestionale",
        )
        canvas.drawRightString(
            page_size[0] - 10 * mm,
            7 * mm,
            f"Pagina {doc.page}",
        )
        canvas.restoreState()

    document.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )
    output.seek(0)
    return output.getvalue()
