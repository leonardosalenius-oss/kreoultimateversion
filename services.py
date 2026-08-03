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


def modifica_spesa(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "modifica_spesa",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Spesa non modificata.")
    return response.data


def annulla_spesa(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "annulla_spesa",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Spesa non eliminata.")
    return response.data


def modifica_regola_spesa_ricorrente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "modifica_regola_spesa_ricorrente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Regola ricorrente non modificata.")
    return response.data


def elimina_regola_spesa_ricorrente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "elimina_regola_spesa_ricorrente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Regola ricorrente non eliminata.")
    return response.data


def crea_regola_spesa_ricorrente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_regola_spesa_ricorrente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Regola ricorrente non salvata.")
    return response.data


def genera_spese_ricorrenti(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "genera_spese_ricorrenti",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Spese ricorrenti non generate.")
    return response.data


def cambia_stato_regola_spesa_ricorrente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "cambia_stato_regola_spesa_ricorrente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Stato della regola non aggiornato.")
    return response.data


def elenco_regole_spese_ricorrenti(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_regole_spese_ricorrenti")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_inizio", desc=True)
        .execute()
    )
    return response.data or []


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



def elenco_operatori_agenda(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("operatori_agenda")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("nome_visualizzato")
        .execute()
    )
    return response.data or []


def crea_operatore_agenda(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_operatore_agenda",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Operatore non salvato.")
    return response.data


def elenco_prenotazioni(
    db: Client,
    azienda_id: str,
    data_inizio: str,
    data_fine: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_prenotazioni_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .gte("data_prenotazione", data_inizio)
        .lte("data_prenotazione", data_fine)
        .order("data_prenotazione")
        .order("ora_inizio")
        .execute()
    )
    return response.data or []


def elenco_slot_app_cliente(
    db: Client,
    azienda_id: str,
    data_inizio: str,
    data_fine: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_slot_app_cliente_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .gte("data_slot", data_inizio)
        .lte("data_slot", data_fine)
        .order("data_slot")
        .order("ora_inizio")
        .execute()
    )
    return response.data or []


def salva_slot_app_cliente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "salva_slot_app_cliente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Slot App Cliente non salvato.")
    return response.data


def cambia_stato_slot_app_cliente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "cambia_stato_slot_app_cliente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Stato slot non aggiornato.")
    return response.data


def imposta_blocco_prenotazioni_cliente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "imposta_blocco_prenotazioni_cliente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Blocco prenotazioni non aggiornato.")
    return response.data


def elenco_ordini_cliente(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_ordini_cliente_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def aggiorna_stato_ordine_cliente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "aggiorna_stato_ordine_cliente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Ordine non aggiornato.")
    return response.data


def elenco_alert_prenotazioni_cliente(
    db: Client,
    azienda_id: str,
    *,
    solo_aperti: bool = True,
) -> list[dict[str, Any]]:
    query = (
        db.table("vista_alert_prenotazioni_cliente")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("created_at", desc=True)
    )
    if solo_aperti:
        query = query.eq("risolto", False)
    response = query.execute()
    return response.data or []


def segna_alert_prenotazione_letto(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "segna_alert_prenotazione_letto",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Alert non aggiornato.")
    return response.data


def crea_prenotazione(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_prenotazione",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Prenotazione non salvata.")
    return response.data


def modifica_prenotazione(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "modifica_prenotazione",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Prenotazione non aggiornata.")
    return response.data


def cambia_stato_prenotazione(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "cambia_stato_prenotazione",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Stato prenotazione non aggiornato.")
    return response.data


def annulla_prenotazione(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = {
        **payload,
        "stato": "annullata",
    }
    return cambia_stato_prenotazione(db, normalized)



def elenco_movimenti_lezioni(
    db: Client,
    azienda_id: str,
    abbonamento_id: str | None = None,
) -> list[dict[str, Any]]:
    query = (
        db.table("vista_movimenti_lezioni_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_movimento", desc=True)
        .order("created_at", desc=True)
    )

    if abbonamento_id:
        query = query.eq("abbonamento_id", abbonamento_id)

    response = query.execute()
    return response.data or []


def registra_movimento_lezioni(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "registra_movimento_lezioni",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Movimento lezioni non registrato.")
    return response.data



def elenco_badge(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_badge_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("cliente")
        .execute()
    )
    return response.data or []


def associa_badge_cliente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "associa_badge_cliente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Badge non associato.")
    return response.data


def cambia_stato_badge(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "cambia_stato_badge",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Stato badge non aggiornato.")
    return response.data


def elenco_dispositivi_accesso(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_dispositivi_accesso")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("nome")
        .execute()
    )
    return response.data or []


def crea_dispositivo_accesso(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "crea_dispositivo_accesso",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Dispositivo non creato.")
    return response.data


def rigenera_token_dispositivo(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "rigenera_token_dispositivo",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Token non rigenerato.")
    return response.data


def elenco_accessi(
    db: Client,
    azienda_id: str,
    data_inizio: str,
    data_fine: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_accessi_operativa")
        .select("*")
        .eq("azienda_id", azienda_id)
        .gte("data_accesso", data_inizio)
        .lte("data_accesso", data_fine)
        .order("data_accesso", desc=True)
        .order("ora_accesso", desc=True)
        .execute()
    )
    return response.data or []


def gestisci_accesso_manuale(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "gestisci_accesso_manuale",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Accesso manuale non registrato.")
    return response.data



def calcola_lezioni_contrattuali(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "calcola_lezioni_contrattuali_rpc",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError(
            "Il database non ha calcolato le lezioni contrattuali."
        )
    return response.data



def salva_pacchetto(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "salva_pacchetto",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Pacchetto non salvato.")
    return response.data


def genera_ricevuta_incasso(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "genera_ricevuta_incasso",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Ricevuta non generata.")
    return response.data



def rimodula_rate_residue(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "rimodula_rate_residue",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError(
            "Il database non ha confermato la rimodulazione."
        )
    return response.data



def elenco_prodotti_magazzino(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_prodotti_magazzino")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("nome")
        .execute()
    )
    return response.data or []


def salva_prodotto_magazzino(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "salva_prodotto_magazzino",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Prodotto non salvato.")
    return response.data


def registra_vendita_magazzino(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "registra_vendita_magazzino",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Vendita non registrata.")
    return response.data


def registra_acquisto_magazzino(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "registra_acquisto_magazzino",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Acquisto non registrato.")
    return response.data


def registra_rettifica_magazzino(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "registra_rettifica_magazzino",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Rettifica non registrata.")
    return response.data


def elenco_movimenti_magazzino(
    db: Client,
    azienda_id: str,
    prodotto_id: str | None = None,
) -> list[dict[str, Any]]:
    query = (
        db.table("vista_movimenti_magazzino")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("data_movimento", desc=True)
        .order("created_at", desc=True)
    )
    if prodotto_id:
        query = query.eq("prodotto_id", prodotto_id)

    response = query.execute()
    return response.data or []


def annulla_movimento_magazzino(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "annulla_movimento_magazzino",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Movimento non annullato.")
    return response.data


# ============================================================
# ACCESSI, RUOLI E PERMESSI
# ============================================================


def elenco_accessi_utente(
    db: Client,
    email: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_accesso_utente")
        .select("*")
        .eq("email", email.strip().lower())
        .eq("attivo", True)
        .order("azienda_nome")
        .execute()
    )
    return response.data or []


def elenco_ruoli_accesso(db: Client) -> list[dict[str, Any]]:
    response = (
        db.table("ruoli_accesso")
        .select("codice,nome,descrizione,livello")
        .eq("attivo", True)
        .order("livello", desc=True)
        .execute()
    )
    return response.data or []


def elenco_utenti_azienda(
    db: Client,
    azienda_id: str,
) -> list[dict[str, Any]]:
    response = (
        db.table("vista_utenti_accessi")
        .select("*")
        .eq("azienda_id", azienda_id)
        .order("nome_visualizzato")
        .execute()
    )
    return response.data or []


def salva_accesso_utente(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "salva_accesso_utente",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Accesso utente non salvato.")
    return response.data


def bootstrap_super_admin(
    db: Client,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = db.rpc(
        "bootstrap_super_admin",
        {"payload": payload},
    ).execute()
    if response.data is None:
        raise RuntimeError("Bootstrap Super Admin non completato.")
    return response.data


def registra_audit_accesso(
    db: Client,
    payload: dict[str, Any],
) -> None:
    db.rpc("registra_audit_accesso", {"payload": payload}).execute()


def get_accesso_app_cliente(
    db: Client,
    *,
    azienda_id: str,
    cliente_id: str,
) -> dict[str, Any] | None:
    response = (
        db.table("accessi_clienti")
        .select("*")
        .eq("azienda_id", azienda_id)
        .eq("cliente_id", cliente_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def crea_accesso_app_cliente(
    db: Client,
    *,
    azienda_id: str,
    cliente_id: str,
    email: str,
    password: str,
    nome_visualizzato: str,
) -> dict[str, Any]:
    existing = get_accesso_app_cliente(
        db,
        azienda_id=azienda_id,
        cliente_id=cliente_id,
    )
    if existing:
        raise ValueError(
            "Questo cliente possiede già un accesso App Cliente."
        )

    auth_user_id = crea_utente_auth_con_password(
        db,
        email=email,
        password=password,
        nome_visualizzato=nome_visualizzato,
    )

    try:
        response = (
            db.table("accessi_clienti")
            .insert({
                "azienda_id": azienda_id,
                "cliente_id": cliente_id,
                "auth_user_id": auth_user_id,
                "attivo": True,
            })
            .execute()
        )
    except Exception:
        try:
            db.auth.admin.delete_user(auth_user_id)
        except Exception:
            pass
        raise

    rows = response.data or []
    if not rows:
        try:
            db.auth.admin.delete_user(auth_user_id)
        except Exception:
            pass
        raise RuntimeError("Collegamento App Cliente non creato.")

    return rows[0]


def aggiorna_accesso_app_cliente(
    db: Client,
    *,
    accesso_id: str,
    attivo: bool,
) -> dict[str, Any]:
    response = (
        db.table("accessi_clienti")
        .update({"attivo": attivo})
        .eq("id", accesso_id)
        .execute()
    )
    rows = response.data or []
    if not rows:
        raise RuntimeError("Accesso App Cliente non aggiornato.")
    return rows[0]


def reimposta_password_utente_auth(
    db: Client,
    *,
    auth_user_id: str,
    nuova_password: str,
) -> None:
    if len(nuova_password) < 8:
        raise ValueError(
            "La password deve contenere almeno 8 caratteri."
        )
    db.auth.admin.update_user_by_id(
        auth_user_id,
        {"password": nuova_password},
    )


def crea_utente_auth_con_password(
    db: Client,
    *,
    email: str,
    password: str,
    nome_visualizzato: str,
) -> str:
    """
    Crea direttamente l'utente in Supabase Auth.

    Nessuna email viene inviata. La password non viene salvata
    nelle tabelle del gestionale e l'indirizzo viene confermato
    amministrativamente per consentire l'accesso immediato.
    """
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("L'email è obbligatoria.")
    if len(password) < 8:
        raise ValueError(
            "La password deve contenere almeno 8 caratteri."
        )

    result = db.auth.admin.create_user({
        "email": normalized_email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "nome_visualizzato": (
                nome_visualizzato.strip()
                or normalized_email
            ),
        },
    })

    user = getattr(result, "user", None)
    user_id = str(getattr(user, "id", "") or "")
    if not user_id:
        raise RuntimeError(
            "Utente Auth creato senza identificativo."
        )

    return user_id
