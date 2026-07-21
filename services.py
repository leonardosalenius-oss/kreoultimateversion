from __future__ import annotations

from typing import Any

from supabase import Client


def elenco_aziende(db: Client) -> list[dict[str, Any]]:
    response = (
        db.table("aziende")
        .select("*")
        .eq("attiva", True)
        .order("nome_visualizzato")
        .execute()
    )
    return response.data or []


def get_azienda(
    db: Client,
    azienda_id: str,
) -> dict[str, Any]:
    response = (
        db.table("aziende")
        .select("*")
        .eq("id", azienda_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Azienda non trovata nel database.")
    return response.data[0]


def salva_azienda(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "salva_azienda",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Il database non ha restituito l'azienda.")
    return response.data


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



ASSET_COMPANY_BUCKET = "asset-aziende"
RECEIPT_BUCKET = "ricevute-pdf"


def carica_asset_azienda(
    db: Client,
    azienda_id: str,
    asset_type: str,
    nome_file: str,
    mime_type: str,
    contenuto: bytes,
) -> str:
    from uuid import uuid4

    if asset_type not in {"logo", "firma", "timbro"}:
        raise ValueError("Tipo asset non valido.")

    safe_name = _safe_filename(nome_file)
    path = (
        f"{azienda_id}/{asset_type}/"
        f"{uuid4().hex}_{safe_name}"
    )

    db.storage.from_(ASSET_COMPANY_BUCKET).upload(
        path=path,
        file=contenuto,
        file_options={
            "content-type": mime_type,
            "cache-control": "3600",
            "upsert": "false",
        },
    )
    return path


def elimina_asset_azienda(
    db: Client,
    file_path: str,
) -> None:
    db.storage.from_(ASSET_COMPANY_BUCKET).remove([file_path])


def crea_url_asset_azienda(
    db: Client,
    file_path: str,
    expires_in: int = 300,
) -> str:
    response = (
        db.storage
        .from_(ASSET_COMPANY_BUCKET)
        .create_signed_url(
            file_path,
            expires_in,
            {"download": False},
        )
    )
    return _extract_signed_url(response)


def scarica_asset_azienda(
    db: Client,
    file_path: str,
) -> bytes:
    return db.storage.from_(ASSET_COMPANY_BUCKET).download(file_path)


def salva_asset_azienda(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "salva_asset_azienda",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Il database non ha salvato l'asset.")
    return response.data


def get_ricevuta_dettaglio(
    db: Client,
    ricevuta_id: str,
) -> dict[str, Any]:
    response = db.rpc(
        "get_ricevuta_dettaglio",
        {"p_ricevuta_id": ricevuta_id},
    ).execute()
    if response.data is None:
        raise RuntimeError("Dettaglio ricevuta non disponibile.")
    return response.data


def carica_pdf_ricevuta(
    db: Client,
    azienda_id: str,
    anno: int,
    ricevuta_id: str,
    numero_documento: str,
    contenuto: bytes,
) -> str:
    import re

    safe_number = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        numero_documento,
    ).strip("_") or ricevuta_id

    path = (
        f"{azienda_id}/{anno}/"
        f"{ricevuta_id}/{safe_number}.pdf"
    )

    db.storage.from_(RECEIPT_BUCKET).upload(
        path=path,
        file=contenuto,
        file_options={
            "content-type": "application/pdf",
            "cache-control": "3600",
            "upsert": "true",
        },
    )
    return path


def collega_pdf_ricevuta(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "collega_pdf_ricevuta",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Il database non ha collegato il PDF.")
    return response.data


def crea_url_ricevuta(
    db: Client,
    file_path: str,
    expires_in: int = 300,
) -> str:
    response = (
        db.storage
        .from_(RECEIPT_BUCKET)
        .create_signed_url(
            file_path,
            expires_in,
            {"download": True},
        )
    )
    return _extract_signed_url(response)


def _extract_signed_url(response: Any) -> str:
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



EXPENSE_DOCUMENT_BUCKET = "documenti-spese"


def elenco_fornitori(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("fornitori")
        .select("*")
        .eq("azienda_id", azienda_id)
        .neq("stato", "annullato")
        .order("ragione_sociale")
        .execute()
    )
    return response.data or []


def crea_fornitore(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_fornitore",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Fornitore non salvato.")
    return response.data


def modifica_fornitore(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "modifica_fornitore",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Fornitore non aggiornato.")
    return response.data


def elenco_categorie_spesa(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("categorie_spesa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("nome")
        .execute()
    )
    return response.data or []


def crea_categoria_spesa(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_categoria_spesa",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Categoria non salvata.")
    return response.data


def crea_spesa_completa(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_spesa_completa",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Spesa non salvata.")
    return response.data


def elenco_spese(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_spese_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_spesa", desc=True)
        .execute()
    )
    return response.data or []


def elenco_scadenze_spesa(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_scadenze_spesa_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_scadenza")
        .execute()
    )
    return response.data or []


def elenco_pagamenti_spesa(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_pagamenti_spesa_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_pagamento", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def registra_pagamento_spesa(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "registra_pagamento_spesa",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Pagamento non registrato.")
    return response.data


def annulla_pagamento_spesa(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "annulla_pagamento_spesa",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Pagamento non annullato.")
    return response.data


def carica_documento_spesa(
    db: Client,
    azienda_id: str,
    fornitore_id: str,
    nome_file: str,
    mime_type: str,
    contenuto: bytes,
) -> str:
    from uuid import uuid4

    safe_name = _safe_filename(nome_file)
    path = (
        f"{azienda_id}/{fornitore_id}/"
        f"{uuid4().hex}_{safe_name}"
    )

    db.storage.from_(EXPENSE_DOCUMENT_BUCKET).upload(
        path=path,
        file=contenuto,
        file_options={
            "content-type": mime_type,
            "cache-control": "3600",
            "upsert": "false",
        },
    )
    return path


def elimina_documento_spesa(
    db: Client,
    file_path: str,
) -> None:
    db.storage.from_(EXPENSE_DOCUMENT_BUCKET).remove([file_path])


def crea_url_documento_spesa(
    db: Client,
    file_path: str,
    expires_in: int = 300,
) -> str:
    response = (
        db.storage
        .from_(EXPENSE_DOCUMENT_BUCKET)
        .create_signed_url(
            file_path,
            expires_in,
            {"download": False},
        )
    )
    return _extract_signed_url(response)



def elenco_abbonamenti_operativo(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_abbonamenti_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_inizio", desc=True)
        .execute()
    )
    return response.data or []


def get_abbonamento_dettaglio(
    db: Client,
    abbonamento_id: str,
) -> dict[str, Any]:
    response = db.rpc(
        "get_abbonamento_dettaglio",
        {"p_abbonamento_id": abbonamento_id},
    ).execute()
    if response.data is None:
        raise RuntimeError("Dettaglio abbonamento non disponibile.")
    return response.data


def crea_abbonamento_cliente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_abbonamento_cliente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Abbonamento non creato.")
    return response.data


def rinnova_abbonamento_cliente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "rinnova_abbonamento_cliente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Rinnovo non creato.")
    return response.data


def cambia_stato_abbonamento(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "cambia_stato_abbonamento",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Stato abbonamento non aggiornato.")
    return response.data



def elimina_cliente_definitivamente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "elimina_cliente_definitivamente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Il database non ha confermato l'eliminazione.")
    return response.data
