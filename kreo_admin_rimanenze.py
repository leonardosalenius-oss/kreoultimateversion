"""Valorizzazione delle chiusure di magazzino per il conto economico Admin."""

from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo


def closing_dates(start: date, end: date) -> list[date]:
    """Chiusura precedente al periodo, seguita dalle chiusure mensili incluse."""
    dates = [start - timedelta(days=1)]
    while dates[-1] < end:
        first = dates[-1] + timedelta(days=1)
        last = first.replace(day=monthrange(first.year, first.month)[1])
        dates.append(min(last, end))
    return dates


@dataclass
class StockBalance:
    quantity: Decimal = Decimal(0)
    priced_quantity: Decimal = Decimal(0)
    purchase_value: Decimal = Decimal(0)


def _standard_cost(product: dict | None, as_of: date) -> Decimal | None:
    if not product or product.get("costo_standard") is None:
        return None
    cost = Decimal(str(product["costo_standard"]))
    if not cost:
        return cost
    # Il catalogo conserva solo l'ultima versione del costo standard.
    if not product.get("updated_at"):
        return None
    timestamp = datetime.fromisoformat(str(product["updated_at"]))
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(ZoneInfo("Europe/Rome"))
    return cost if timestamp.date() <= as_of else None


def _closing_value(balances: dict[str, StockBalance], products: dict[str, dict],
                   as_of: date) -> Decimal | None:
    total = Decimal(0)
    for product_id, balance in balances.items():
        if not balance.quantity:
            continue
        if balance.priced_quantity:
            cost = (balance.purchase_value / balance.priced_quantity).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
        else:
            cost = _standard_cost(products.get(product_id), as_of)
            if cost is None:
                return None
        total += balance.quantity * cost
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def inventory_closings(products: list[dict[str, Any]], movements: list[dict[str, Any]],
                       dates: list[date]) -> dict[date, Decimal | None]:
    """Applica una volta il giornale, nell'ordine delle date di movimento."""
    catalog = {p["prodotto_id"]: p for p in products}
    by_id = {m["movimento_id"]: m for m in movements}
    reversed_ids = {m["movimento_origine_id"] for m in movements if m["tipo"] == "storno"}
    entries = iter(sorted(
        (m for m in movements if m["stato"] == "valido" or m["movimento_id"] in reversed_ids),
        key=lambda m: m["data_movimento"],
    ))
    movement = next(entries, None)
    balances = defaultdict(StockBalance)
    result = {}
    for as_of in dates:
        cutoff = as_of.isoformat()
        while movement is not None and movement["data_movimento"] <= cutoff:
            balance = balances[movement["prodotto_id"]]
            quantity = Decimal(str(movement["quantita"]))
            balance.quantity += quantity
            # Lo storno di un carico annulla anche il suo peso nel costo medio.
            # Lo storno di una vendita ripristina solo i pezzi.
            origin = movement
            while origin and origin["tipo"] == "storno":
                origin = by_id.get(origin["movimento_origine_id"])
            if (origin and origin["costo_unitario"] is not None
                    and Decimal(str(origin["quantita"])) > 0):
                balance.priced_quantity += quantity
                balance.purchase_value += quantity * Decimal(str(origin["costo_unitario"]))
            movement = next(entries, None)
        result[as_of] = _closing_value(balances, catalog, as_of)
    return result


def stock_change(opening: Decimal | None, closing: Decimal | None) -> float | None:
    if opening is None or closing is None:
        return None
    return float(closing - opening)
