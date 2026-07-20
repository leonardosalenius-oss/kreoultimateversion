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


def modifica_anagrafica_cliente(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("modifica_anagrafica_cliente", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def aggiorna_abbonamento_cliente(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("aggiorna_abbonamento_cliente", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def aggiorna_rate_abbonamento(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("aggiorna_rate_abbonamento", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def salva_documento_cliente(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("salva_documento_cliente", {"payload": payload}).execute()
    if response.data is None:
        raise RuntimeError("La funzione non ha restituito alcun risultato.")
    return response.data


def annulla_documento_cliente(db: Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = db.rpc("annulla_documento_cliente", {"payload": payload}).execute()
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



DOCUMENT_BUCKET = "documenti-clienti"


def _safe_filename(value: str) -> str:
    import re
    from pathlib import Path

    original = Path(value).name
    stem = Path(original).stem
    suffix = Path(original).suffix.lower()

    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
    if not safe_stem:
        safe_stem = "documento"

    return f"{safe_stem}{suffix}"


def carica_file_documento(
    db: Client,
    azienda_id: str,
    cliente_id: str,
    tipo_documento: str,
    nome_file: str,
    mime_type: str,
    contenuto: bytes,
) -> str:
    import re
    from uuid import uuid4

    tipo_folder = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        tipo_documento.lower(),
    ).strip("_") or "altro"

    safe_name = _safe_filename(nome_file)
    path = (
        f"{azienda_id}/{cliente_id}/{tipo_folder}/"
        f"{uuid4().hex}_{safe_name}"
    )

    db.storage.from_(DOCUMENT_BUCKET).upload(
        path=path,
        file=contenuto,
        file_options={
            "content-type": mime_type,
            "cache-control": "3600",
            "upsert": "false",
        },
    )

    return path


def elimina_file_documento(db: Client, file_path: str) -> None:
    db.storage.from_(DOCUMENT_BUCKET).remove([file_path])


def crea_url_documento(
    db: Client,
    file_path: str,
    expires_in: int = 300,
) -> str:
    response = (
        db.storage
        .from_(DOCUMENT_BUCKET)
        .create_signed_url(
            file_path,
            expires_in,
            {"download": False},
        )
    )

    if isinstance(response, dict):
        url = (
            response.get("signedURL")
            or response.get("signedUrl")
            or response.get("signed_url")
        )
    else:
        url = getattr(response, "signed_url", None)

    if not url:
        raise RuntimeError("Supabase non ha restituito l'URL firmato.")

    return url
