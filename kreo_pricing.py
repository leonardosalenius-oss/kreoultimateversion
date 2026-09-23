"""Contract price snapshots. Old prezzo_concordato always remains a TOTAL."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import calendar
import hashlib
import json
from typing import Any

CENT = Decimal('0.01')
PERIOD_MONTHS = {'Mensile': 1, 'Trimestrale': 3, 'Semestrale': 6, 'Annuale': 12}


def price_decimal(value: Any) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError('Prezzo mancante o non valido.')
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError('Il prezzo deve essere un importo positivo o zero.')
        return result.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Prezzo non valido.') from exc


def contract_months(value: Any) -> int:
    try:
        number = Decimal(str(value))
        if isinstance(value, bool) or not number.is_finite() or number != number.to_integral_value() or not 1 <= number <= 120:
            raise ValueError
        return int(number)
    except (ValueError, InvalidOperation, TypeError) as exc:
        raise ValueError('Indicare un numero intero di mesi da 1 a 120.') from exc


def package_consumption_kind(package: dict) -> str:
    return package.get('tipo_consumo') or ('lezioni' if package.get('modalita_lezioni') == 'Pacchetto lezioni' else 'tempo')


def package_default_months(package: dict) -> int:
    unit = str(package.get('durata_unita') or '').lower()
    if package.get('durata_numero') is not None and unit in ('mese', 'mesi', 'month', 'months'):
        return contract_months(package['durata_numero'])
    if package.get('durata_numero') is not None and unit in ('anno', 'anni', 'year', 'years'):
        return contract_months(Decimal(str(package['durata_numero'])) * 12)
    return contract_months(PERIOD_MONTHS.get(package.get('periodicita'), 1))


def contract_end_date(start: date, months: Any) -> date:
    offset = contract_months(months)
    year, month0 = divmod(start.year * 12 + start.month - 1 + offset, 12)
    anniversary = date(year, month0 + 1, min(start.day, calendar.monthrange(year, month0 + 1)[1]))
    return anniversary - timedelta(days=1)


def pricing_context(*values: Any) -> str:
    raw = json.dumps(values, sort_keys=True, default=str, ensure_ascii=True)
    return 'pricing_' + hashlib.sha256(raw.encode()).hexdigest()[:24]


def pricing_defaults(package: dict, *, existing: dict | None = None, renewal: dict | None = None) -> dict:
    """Never infer a historical monthly amount by dividing a stored total."""
    kind = package_consumption_kind(package)
    same_existing = existing and str(existing.get('pacchetto_id')) == str(package.get('id'))
    if existing and existing.get('prezzo_schema_versione') != 2:
        return {'legacy': True, 'total': float(price_decimal(existing['prezzo_concordato']))}
    standard = price_decimal(package.get('prezzo_standard'))
    agreed = standard
    months = package_default_months(package) if kind == 'tempo' else None
    source = existing if same_existing else None
    if source:
        standard = price_decimal(source.get('prezzo_standard_unitario'))
        agreed = price_decimal(source.get('prezzo_concordato_unitario'))
        months = contract_months(source.get('mesi_contratto')) if kind == 'tempo' else None
    elif renewal and renewal.get('prezzo_schema_versione') == 2 and str(renewal.get('pacchetto_id')) == str(package.get('id')):
        expected_unit = 'mese' if kind == 'tempo' else 'pacchetto'
        if renewal.get('prezzo_unita') == expected_unit:
            agreed = price_decimal(renewal.get('prezzo_concordato_unitario'))
            months = contract_months(renewal.get('mesi_contratto')) if kind == 'tempo' else None
    return {'legacy': False, 'standard': float(standard), 'agreed': float(agreed), 'months': months}


def contract_quote(package: dict, standard: Any, agreed: Any, months: Any = None) -> dict:
    kind = package_consumption_kind(package)
    if kind not in ('tempo', 'lezioni'):
        raise ValueError('Tipo di contratto non riconosciuto.')
    monthly = kind == 'tempo'
    count = contract_months(months) if monthly else None
    standard_amount, agreed_amount = price_decimal(standard), price_decimal(agreed)
    multiplier = count if monthly else 1
    return {
        'prezzo_schema_versione': 2,
        'prezzo_unita': 'mese' if monthly else 'pacchetto',
        'prezzo_standard_unitario': float(standard_amount),
        'prezzo_concordato_unitario': float(agreed_amount),
        'mesi_contratto': count,
        'prezzo_standard_totale': float(standard_amount * multiplier),
        'prezzo_concordato': float(agreed_amount * multiplier),
    }
