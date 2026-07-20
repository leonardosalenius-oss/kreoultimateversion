from __future__ import annotations

from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta


PERIODICITA_MESI = {
    "Mensile": 1,
    "Semestrale": 6,
    "Annuale": 12,
}


def money(value: float) -> str:
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_date_it(value: Any) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return value.strftime("%d/%m/%Y")


def calculate_package_end(start: date, periodicita: str) -> date:
    if periodicita not in PERIODICITA_MESI:
        raise ValueError("Periodicità pacchetto non valida.")
    return start + relativedelta(months=PERIODICITA_MESI[periodicita]) - relativedelta(days=1)


def calculate_package_lessons(
    periodicita: str,
    modalita: str,
    lezioni_per_periodo: int,
    lezioni_totali: int,
) -> int:
    if periodicita not in PERIODICITA_MESI:
        raise ValueError("Periodicità pacchetto non valida.")

    if modalita == "Pacchetto lezioni":
        return int(lezioni_totali)

    months = PERIODICITA_MESI[periodicita]

    if modalita == "Settimanale":
        return int(lezioni_per_periodo) * months * 4

    if modalita == "Mensile":
        return int(lezioni_per_periodo) * months

    raise ValueError("Modalità lezioni non valida.")


def build_installment_plan(
    total: float,
    count: int,
    first_due: date,
    month_step: int,
) -> list[dict]:
    count = max(int(count), 1)
    base = round(total / count, 2)
    amounts = [base] * count
    amounts[-1] = round(amounts[-1] + round(total - sum(amounts), 2), 2)

    return [
        {
            "numero_rata": idx + 1,
            "data_scadenza": first_due + relativedelta(months=idx * month_step),
            "importo_previsto": float(amounts[idx]),
        }
        for idx in range(count)
    ]
