from __future__ import annotations

from typing import Any

from supabase import Client


def get_azienda_kreo(db: Client) -> dict[str, Any]:
    response = (
        db.table("aziende")
        .select("*")
        .eq("nome_visualizzato", "KREO")
        .limit(1)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Azienda KREO non trovata nel database.")
    return response.data[0]


def elenco_pacchetti(db: Client, azienda_id: str) -> list[dict[str, Any]]:
    response = (
        db.table("pacchetti")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("nome")
        .execute()
    )
    return response.data or []


def crea_pacchetto(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.table("pacchetti").insert(payload).execute()
    if not response.data:
        raise RuntimeError("Il database non ha restituito il pacchetto creato.")
    return response.data[0]


def crea_cliente_completo(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("crea_cliente_completo", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def elenco_clienti_operativo(db: Client, azienda_id: str) -> list[dict[str, Any]]:
    response = (
        db.table("vista_clienti_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("cognome")
        .order("nome")
        .execute()
    )
    return response.data or []


def modifica_cliente(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("modifica_cliente", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def get_cliente_dettaglio(db: Client, cliente_id: str) -> dict[str, Any]:
    response = db.rpc("get_cliente_dettaglio", {"p_cliente_id": cliente_id}).execute()
    if response.data is None:
        raise RuntimeError("Dettaglio cliente non disponibile.")
    return response.data


def crea_incasso_completo(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("registra_incasso_completo", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def annulla_incasso(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("annulla_incasso", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def elenco_incassi_operativo(db: Client, azienda_id: str) -> list[dict[str, Any]]:
    response = (
        db.table("vista_incassi_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_incasso", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def elenco_rate_operativo(db: Client, azienda_id: str) -> list[dict[str, Any]]:
    response = (
        db.table("vista_rate_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_scadenza")
        .execute()
    )
    return response.data or []
