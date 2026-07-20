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


def crea_incasso(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.table("incassi").insert(payload).execute()
    if not response.data:
        raise RuntimeError("Il database non ha restituito l'incasso creato.")
    return response.data[0]


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
