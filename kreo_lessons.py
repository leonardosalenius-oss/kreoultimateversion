"""Read-only lesson detail, scoped to an exact company, client and contract.

No writes, RPC calls, permissions or changes to the database's counting rules.
Database summaries describe the current database week; historical tables keep
the individual records instead of inferring workouts from turnstile events.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID


def _scope(azienda_id: str, cliente_id: str, abbonamento_id: str) -> dict[str, str]:
    return {
        "azienda_id": str(UUID(str(azienda_id))),
        "cliente_id": str(UUID(str(cliente_id))),
        "abbonamento_id": str(UUID(str(abbonamento_id))),
    }


def _scoped_query(db: Any, table: str, scope: dict[str, str]) -> Any:
    query = db.table(table).select("*")
    for name, value in scope.items():
        query = query.eq(name, value)
    return query


def _validated_rows(response: Any, scope: dict[str, str]) -> list[dict[str, Any]]:
    rows = response.data
    if not isinstance(rows, list):
        raise RuntimeError("La lettura non ha restituito un elenco valido.")
    for row in rows:
        if not isinstance(row, dict) or any(
            str(row.get(key)) != value for key, value in scope.items()
        ):
            raise RuntimeError("La lettura non corrisponde al contratto selezionato.")
    return rows


def read_lesson_summary(
    db: Any, azienda_id: str, cliente_id: str, abbonamento_id: str,
    *, include_time_quota: bool,
) -> dict[str, Any]:
    """Missing/unreadable rows remain None, never fabricated zero balances."""
    scope = _scope(azienda_id, cliente_id, abbonamento_id)
    result: dict[str, Any] = {"quota": None, "availability": None, "errors": []}
    sources = [("availability", "vista_disponibilita_lezioni", "Disponibilità agenda")]
    if include_time_quota:
        sources.insert(0, ("quota", "vista_quota_settimanale_tempo", "Consumi settimanali"))
    for key, table, label in sources:
        try:
            rows = _validated_rows(_scoped_query(db, table, scope).limit(2).execute(), scope)
            if len(rows) != 1:
                raise RuntimeError("Riepilogo non univoco o assente.")
            result[key] = dict(rows[0])
        except Exception:
            result["errors"].append(f"{label}: dati non disponibili per questo abbonamento.")
    return result


def read_time_lesson_history(
    db: Any, azienda_id: str, cliente_id: str, abbonamento_id: str,
    week_day: date, *, page_size: int = 200,
) -> dict[str, Any]:
    """All rows in one week; bounded by date and paginated with stable ordering.

    An unreadable/incomplete source is None, while a successful empty read is [].
    Advance by the received row count to also tolerate a smaller server row cap.
    """
    if not 1 <= page_size <= 1000:
        raise ValueError("Dimensione pagina non valida.")
    scope = _scope(azienda_id, cliente_id, abbonamento_id)
    start = week_day - timedelta(days=week_day.weekday())
    end = start + timedelta(days=6)
    result: dict[str, Any] = {
        "week_start": start.isoformat(), "week_end": end.isoformat(),
        "uses": None, "bookings": None, "recoveries": None, "errors": [],
    }
    sources = (
        ("uses", "utilizzi_settimanali_tempo", "data_utilizzo", "Accessi senza prenotazione"),
        ("bookings", "prenotazioni", "data_prenotazione", "Prenotazioni e presenze"),
        ("recoveries", "recuperi_settimanali", "settimana_destinazione", "Recuperi"),
    )
    for key, table, date_field, label in sources:
        try:
            collected: list[dict[str, Any]] = []
            seen: set[str] = set()
            offset = 0
            # A bounded week cannot reasonably need 1000 pages. Refuse to present
            # a partial result if a server ignores range/order or data changes.
            for _ in range(1000):
                query = _scoped_query(db, table, scope)
                query = query.gte(date_field, start.isoformat()).lte(date_field, end.isoformat())
                query = query.order(date_field).order("id").range(offset, offset + page_size - 1)
                rows = _validated_rows(query.execute(), scope)
                if not rows:
                    result[key] = collected
                    break
                for row in rows:
                    identity = str(row.get("id") or "")
                    if not identity or identity in seen:
                        raise RuntimeError("Paginazione incompleta o ripetuta.")
                    row_day = date.fromisoformat(str(row[date_field]))
                    if not start <= row_day <= end:
                        raise RuntimeError("Registrazione fuori dalla settimana richiesta.")
                    seen.add(identity)
                    collected.append(dict(row))
                offset += len(rows)
            else:
                raise RuntimeError("Storico troppo esteso per una lettura completa.")
        except Exception:
            result[key] = None
            result["errors"].append(f"{label}: storico non disponibile; non equivale a zero registrazioni.")
    return result


def metric_value(row: dict[str, Any] | None, field: str) -> Any:
    """Preserve meaningful zero and show missing values explicitly."""
    if row is None or row.get(field) is None:
        return "Non disponibile"
    return row[field]
