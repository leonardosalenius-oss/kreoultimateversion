import streamlit as st
import os
import uuid
import math
import time
import copy
from decimal import Decimal, InvalidOperation
import hmac
import zipfile
import posixpath
import xml.etree.ElementTree as ET
from contextvars import ContextVar
import base64
import requests
import pandas as pd
from io import BytesIO
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from html import escape
from urllib.parse import quote_plus

st.set_page_config(page_title="DIVISPACK Analytics Platform", layout="wide")
APP_BUILD = "2026.09.11-RISERVATA1"

# ======================================================
# SCHERMO RISERVATO — SOLO NEL BROWSER, NON È AUTENTICAZIONE
# ======================================================
# Ctrl+Alt+H: nasconde. Ctrl+Alt+R: ripristina. Nessuna richiesta storage.
# Il flag persistito in sessionStorage contiene solo uno stato 0/1 per scheda.
# Il DOM rimane in memoria: non sostituisce logout, password o blocco del PC.
# Inserire PRIMA di branding/login/dati per ripristinare una copertura già attiva.
SSC_PRIVACY_GUARD = '<style>\n/* Niente dati visibili prima dell\'inizializzazione del controllo browser.\n   Sul rerun l\'attributo ready del documento resta presente. */\nhtml:not([data-ssc-screen-ready="1"]) body > * {visibility:hidden !important;}\nhtml:not([data-ssc-screen-ready="1"]) body::after {\n content:"Avvio interfaccia…";position:fixed;inset:0;display:grid;place-items:center;\n background:#f6f7f9;color:#66717f;font:15px system-ui;z-index:2147483647;\n}\n</style>'

SSC_PRIVACY_HTML = r'''
<!doctype html><html lang="it"><head><meta charset="utf-8">
<style>
body{margin:0;background:transparent;font-family:system-ui,-apple-system,'Segoe UI',sans-serif}
button{box-sizing:border-box;width:100%;min-height:36px;padding:6px 10px;border:1px solid #cfd5de;
  border-radius:8px;background:#fff;color:#243143;font:inherit;font-size:13px;cursor:pointer}
button:hover{background:#f1f3f6}button:focus-visible{outline:2px solid #5877a5;outline-offset:-2px}
button:disabled{color:#697586;cursor:wait}
</style></head><body>
<button id="ssc-hide-screen" type="button" title="Nascondi i dati (Ctrl+Alt+H)" disabled>Schermo neutro</button>
<script>(() => {
  "use strict";
  const button = document.getElementById("ssc-hide-screen");
  try {
    const host = window.parent;
    const doc = host.document;
    if (!host.__divispackPrivateScreenV1) {
      // Esegue il controller nel documento principale, NON nel frame temporaneo.
      // In questo modo i listener sopravvivono ai rerun che rimontano il componente.
      const installer = doc.createElement("script");
      installer.textContent = "(() => {\n  \"use strict\";\n  const host = window;\n  const doc = host.document;\n    const KEY = \"divispack.ssc.screen.hidden.v1:\" + host.location.pathname;\n    const ATTR = \"data-ssc-screen-hidden\";\n    const READY = \"data-ssc-screen-ready\";\n    const COVER_ID = \"ssc-private-cover\";\n    const STYLE_ID = \"ssc-private-style\";\n    const GLOBAL = \"__divispackPrivateScreenV1\";\n\n    if (!host[GLOBAL]) {\n      let hidden = false;\n      let oldTitle = \"\";\n      let previousFocus = null;\n      let recovering = false;\n      const savedNodes = new Map();\n      const attachedWindows = new WeakSet();\n      let cover;\n      const style = doc.createElement(\"style\");\n      style.id = STYLE_ID;\n      style.textContent = `\n        html[${ATTR}=\"1\"] { background: #f6f7f9 !important; }\n        html[${ATTR}=\"1\"] body { overflow: hidden !important; background: #f6f7f9 !important; }\n        html[${ATTR}=\"1\"] body > :not(#${COVER_ID}),\n        html[${ATTR}=\"1\"] body > :not(#${COVER_ID}) * {\n          visibility: hidden !important; pointer-events: none !important;\n          user-select: none !important;\n        }\n        #${COVER_ID} {\n          position: fixed !important; inset: 0 !important; margin: 0 !important;\n          width: 100vw !important; height: 100vh !important;\n          max-width: none !important; max-height: none !important;\n          box-sizing: border-box !important; padding: 32px !important;\n          border: 0 !important; border-radius: 0 !important;\n          background: #f6f7f9 !important; color: #3c4655 !important;\n          font-family: system-ui, -apple-system, 'Segoe UI', sans-serif !important;\n          z-index: 2147483647 !important; outline: none !important;\n          overflow: hidden !important; visibility: visible !important;\n          pointer-events: auto !important;\n        }\n        #${COVER_ID}:not([open]) { display: none !important; }\n        #${COVER_ID}[open] { display: grid !important; place-items: center !important; }\n        #${COVER_ID}::backdrop { background: #f6f7f9 !important; }\n        #${COVER_ID} * { visibility: visible !important; }\n        #${COVER_ID} .ssc-neutral-card {\n          box-sizing: border-box; width: min(440px, 100%); padding: 42px 32px;\n          background: #ffffff; border: 1px solid #e4e8ed; border-radius: 16px;\n          text-align: center; box-shadow: 0 8px 36px rgba(25, 40, 60, 0.045);\n        }\n        #${COVER_ID} .ssc-neutral-mark {\n          width: 36px; height: 36px; margin: 0 auto 20px; border-radius: 10px;\n          background: #edf0f5; border: 1px solid #e2e7ee;\n        }\n        #${COVER_ID} h1 { margin: 0; font-size: 24px; font-weight: 550; line-height: 1.3; }\n        #${COVER_ID} p { margin: 14px 0 0; color: #788391; font-size: 14px; line-height: 1.5; }\n        @media print {\n          html[${ATTR}=\"1\"] body > :not(#${COVER_ID}) { display: none !important; }\n          #${COVER_ID}[open] { position: static !important; height: 95vh !important; }\n        }\n      `;\n      doc.head.appendChild(style);\n      cover = doc.createElement(\"dialog\");\n      cover.id = COVER_ID;\n      cover.setAttribute(\"aria-label\", \"Area di lavoro\");\n      cover.tabIndex = -1;\n      // Questa schermata non contiene moduli, link o dati aziendali.\n      cover.innerHTML = '<section class=\"ssc-neutral-card\"><div class=\"ssc-neutral-mark\" aria-hidden=\"true\"></div><h1>Area di lavoro</h1><p>Nessuna attivit\u00e0 da visualizzare.</p></section>';\n      doc.body.appendChild(cover);\n\n      function readFlag() {\n        try { return host.sessionStorage.getItem(KEY) === \"1\"; }\n        catch (_) { return false; }\n      }\n      function writeFlag(value) {\n        try {\n          if (value) host.sessionStorage.setItem(KEY, \"1\");\n          else host.sessionStorage.removeItem(KEY);\n        } catch (_) { /* Lo schermo funziona comunque nella pagina corrente. */ }\n      }\n      function makeUnderlyingInert() {\n        for (const node of doc.body.children) {\n          if (node === cover || [\"SCRIPT\", \"STYLE\", \"LINK\"].includes(node.tagName)) continue;\n          if (!savedNodes.has(node)) savedNodes.set(node, {\n            inert: node.inert, ariaHidden: node.getAttribute(\"aria-hidden\")\n          });\n          node.inert = true;\n          node.setAttribute(\"aria-hidden\", \"true\");\n        }\n      }\n      function ensureCover() {\n        if (!hidden || recovering) return;\n        recovering = true;\n        try {\n          if (!style.isConnected) doc.head.appendChild(style);\n          if (!cover.isConnected) doc.body.appendChild(cover);\n          doc.documentElement.setAttribute(ATTR, \"1\");\n          makeUnderlyingInert();\n          if (doc.title !== \"Area di lavoro\") doc.title = \"Area di lavoro\";\n          if (!cover.open) {\n            if (typeof cover.showModal === \"function\") cover.showModal();\n            else cover.setAttribute(\"open\", \"\");\n          }\n        } finally { recovering = false; }\n      }\n      // Osservatori attivi SOLO mentre lo schermo \u00e8 coperto; nessun polling.\n      const bodyObserver = new host.MutationObserver(ensureCover);\n      const titleObserver = new host.MutationObserver(ensureCover);\n\n      function hide() {\n        if (hidden) { ensureCover(); return; }\n        oldTitle = doc.title;\n        previousFocus = doc.activeElement;\n        hidden = true;\n        writeFlag(true);\n        // CSS applicato prima del dialogo: niente dissolvenza dei dati.\n        doc.documentElement.setAttribute(ATTR, \"1\");\n        ensureCover();\n        cover.focus({preventScroll: true});\n        bodyObserver.observe(doc.body, {childList: true});\n        titleObserver.observe(doc.head, {childList: true, subtree: true, characterData: true});\n      }\n      function show() {\n        if (!hidden) return;\n        hidden = false;\n        writeFlag(false);\n        bodyObserver.disconnect();\n        titleObserver.disconnect();\n        for (const [node, saved] of savedNodes) {\n          if (!node.isConnected) continue;\n          node.inert = saved.inert;\n          if (saved.ariaHidden === null) node.removeAttribute(\"aria-hidden\");\n          else node.setAttribute(\"aria-hidden\", saved.ariaHidden);\n        }\n        savedNodes.clear();\n        doc.title = oldTitle || \"DIVISPACK Analytics Platform\";\n        if (cover.open && typeof cover.close === \"function\") cover.close();\n        else cover.removeAttribute(\"open\");\n        doc.documentElement.removeAttribute(ATTR);\n        // Il DOM dell'app non viene smontato: filtri, form e scroll restano l\u00ec.\n        if (previousFocus && previousFocus.isConnected && typeof previousFocus.focus === \"function\") {\n          try { previousFocus.focus({preventScroll: true}); } catch (_) {}\n        }\n      }\n      function consume(event) {\n        event.preventDefault();\n        event.stopImmediatePropagation();\n      }\n      function onKey(event) {\n        const shortcut = event.ctrlKey && event.altKey && !event.shiftKey && !event.metaKey;\n        const key = String(event.key || \"\").toLowerCase();\n        if (shortcut && (event.code === \"KeyH\" || key === \"h\")) {\n          consume(event);\n          if (event.type === \"keydown\" && !event.repeat) hide();\n          return;\n        }\n        if (shortcut && (event.code === \"KeyR\" || key === \"r\")) {\n          consume(event);\n          if (event.type === \"keydown\" && !event.repeat) show();\n          return;\n        }\n        if (hidden) consume(event);\n      }\n      function attachTo(w) {\n        if (!w || attachedWindows.has(w)) return;\n        try {\n          // Capture anche se il focus \u00e8 su un campo o un componente iframe.\n          w.addEventListener(\"keydown\", onKey, true);\n          w.addEventListener(\"keyup\", onKey, true);\n          for (const type of [\"copy\", \"cut\", \"paste\", \"contextmenu\", \"dragstart\", \"submit\"]) {\n            w.addEventListener(type, e => { if (hidden) consume(e); }, true);\n          }\n          attachedWindows.add(w);\n        } catch (_) {}\n      }\n      cover.addEventListener(\"cancel\", e => { if (hidden) e.preventDefault(); });\n      cover.addEventListener(\"close\", () => { if (hidden) ensureCover(); });\n      host.addEventListener(\"pageshow\", ensureCover);\n      host.addEventListener(\"beforeprint\", ensureCover);\n      attachTo(host);\n      host[GLOBAL] = { hide, show, attachTo, ensureCover };\n      if (readFlag()) hide();\n    }\n\n  doc.documentElement.setAttribute(READY,\"1\");\n})();";
      doc.head.appendChild(installer);
      installer.remove();
    }
    const controller = host.__divispackPrivateScreenV1;
    if (!controller) throw new Error("Controller non installato");
    controller.attachTo(window);
    controller.ensureCover();
    doc.documentElement.setAttribute("data-ssc-screen-ready", "1");
    button.addEventListener("click", () => controller.hide());
    button.disabled = false;
  } catch (_) {
    button.textContent = "Schermo neutro non disponibile";
    button.disabled = true;
  }
})();
</script></body></html>
'''


def render_schermo_riservato():
    """Installa un solo controller browser, riutilizzato su tutti i rerun.

    HTML/JS sono costanti del codice: non inserire mai input utente qui.
    L'iframe controlla il documento contenitore same-origin, come supportato
    dai componenti HTML Streamlit. Nessuna dipendenza esterna o polling.
    """
    from streamlit.components.v1 import html as component_html
    st.html(SSC_PRIVACY_GUARD)
    with st.sidebar:
        component_html(SSC_PRIVACY_HTML, height=40, scrolling=False, tab_index=0)


render_schermo_riservato()

_SSC_PARSE_YEAR = ContextVar("ssc_parse_year", default=None)
_RUN_BUNDLE = None
_RUN_START = time.perf_counter()
_RUN_HTTP = []
_RUN_PHASES = []
_DATASET_USED_THIS_RUN = False

# ======================================================
# DIVISPACK STORAGE API — GOOGLE APPS SCRIPT
# ======================================================
# GitHub contiene il codice; Drive/Sheets contengono i dati operativi.
# L'endpoint e il token restano esclusivamente nei Secrets di Streamlit.

def get_storage_api_config():
    try:
        cfg = st.secrets.get("apps_script", {})
        return (
            str(cfg.get("url", "")).strip(),
            str(cfg.get("token", "")).strip(),
        )
    except Exception:
        return "", ""


def storage_api_configured():
    url, token = get_storage_api_config()
    return bool(url and token)


def storage_api_call(action, payload=None, timeout=60, quiet=False):
    url, token = get_storage_api_config()
    if not url or not token:
        raise StorageError("Archivio non configurato nei Secrets.")
    _call_start = time.perf_counter()
    try:
        r = requests.post(url, json={"token": token, "action": action, "payload": payload or {}},
                          timeout=(15, timeout), allow_redirects=True)
        r.raise_for_status()
        result = r.json()
    except Exception as exc:
        raise StorageError("Archivio condiviso non raggiungibile. Nessuna modifica confermata.") from exc
    if not isinstance(result, dict) or not result.get("ok"):
        code = result.get("code", "STORAGE_ERROR") if isinstance(result, dict) else "STORAGE_ERROR"
        messages = {
            "CONFLICT": "Un altro utente ha aggiornato i dati. Premi Aggiorna situazione condivisa, controlla il saldo e ripeti la modifica.",
            "BASELINE_CHANGED": "È cambiata la situazione ufficiale. Aggiorna i dati prima di salvare.",
            "UPGRADE_REQUIRED": "Aggiornare anche il deployment Code.gs a NAVIGAZIONE1.",
            "AUDIT_CHANGED": "La cronologia è cambiata. Premi Aggiorna cronologia per ripartire dalla prima pagina.",
        }
        text = str(result.get("error", "")) if isinstance(result, dict) else ""
        if "non autorizzato" in text.lower():
            raise StorageError("Non autorizzato: verificare token e deployment Apps Script.")
        raise StorageError(messages.get(code, "Operazione rifiutata dall'archivio. Verifica configurazione e permessi; nessun salvataggio locale sostitutivo."))
    _RUN_HTTP.append({"operazione": action, "secondi": round(time.perf_counter()-_call_start, 3)})
    return result





@st.cache_data(ttl=45, show_spinner=False)
def storage_health_cached(url, token):
    if not url or not token:
        return False, "Archivio non configurato"
    try:
        result = storage_api_call("health", timeout=30)
        if int(result.get("protocol", 0)) < 2:
            return False, "Aggiornare anche Code.gs e pubblicare una Nuova versione del deployment esistente."
        return True, "Dati nell'archivio condiviso"
    except StorageError as exc:
        return False, str(exc)



def storage_health():
    url, token = get_storage_api_config()
    return storage_health_cached(url, token)


@st.cache_data(ttl=60, max_entries=96, show_spinner=False)
def remote_state_get_cached(url, token, key):
    return storage_api_call("state_get_v2", {"key": str(key)})



def remote_state_get(key, default=None):
    url, token = get_storage_api_config()
    if not url or not token:
        raise StorageError("Archivio condiviso non configurato.")
    # Il pacchetto di questo ciclo contiene dati e revisioni letti insieme.
    if isinstance(_RUN_BUNDLE, dict) and key in _RUN_BUNDLE.get("states", {}):
        result = _RUN_BUNDLE["states"][key]
    else:
        result = remote_state_get_cached(url, token, str(key))
    st.session_state.setdefault("__state_versions", {})[str(key)] = int(result.get("version", 0))
    return result.get("value") if result.get("found") else default




def remote_state_set(key, value, updated_by="", bootstrap=False):
    global _RUN_BUNDLE
    if key in {"payment_history", "manual_clients", "deleted_clients", "quadrature_corrections"} and not can_edit():
        st.error("Scrittura bloccata: profilo o vista in sola lettura.")
        return False
    try:
        versions = st.session_state.setdefault("__state_versions", {})
        if key not in versions:
            remote_state_get(key)
        user = st.session_state.get("current_user", {}) or {}
        p = {"key": key, "value": value, "expected_version": versions[key],
             "actor": updated_by or user.get("username", ""), "bootstrap": bool(bootstrap),
             "request_id": str(uuid.uuid4())}
        if key in {"payment_history", "manual_clients", "deleted_clients", "quadrature_corrections"}:
            p["active_hash"] = st.session_state.get("current_baseline_hash", "")
            dependencies = ("payment_history", "quadrature_corrections", "manual_clients", "deleted_clients")
            p["expected_dependencies"] = {k:int(versions[k]) for k in dependencies if k in versions}
        result = storage_api_call("state_set_v2", p)
        versions[key] = int(result.get("version", versions[key]+1))
        url, token = get_storage_api_config()
        remote_state_get_cached.clear(url, token, key)
        remote_state_get_cached.clear(url, token, "user_action_log")
        storage_manifest_cached.clear()
        operational_bundle_cached.clear()
        st.session_state.pop("__ready_dataset", None)
        _RUN_BUNDLE = None  # Mai riutilizzare una lettura precedente alla scrittura nello stesso ciclo.
        return True
    except StorageError as exc:
        st.error(str(exc))
        return False





def remote_save_active_ssc(file_bytes, file_name):
    raise StorageError("Usare Anteprima e Conferma situazione ufficiale: l'upload diretto è disabilitato.")



def remote_load_active_ssc():
    m = remote_manifest()
    meta = m.get("active")
    if not meta:
        return None, "", None
    raw, loaded = remote_file_cached(*get_storage_api_config(), meta["file_hash"])
    return raw, loaded.get("file_name", "SALDI.xlsx"), meta.get("uploaded_at")



@st.cache_data(ttl=120, show_spinner=False, max_entries=8)
def remote_upload_history_cached(url, token, limit):
    result = storage_api_call("upload_list", {"limit": int(limit)}, quiet=True)
    rows = result.get("uploads", []) if result else []
    return rows if isinstance(rows, list) else []


def remote_upload_history(limit=25):
    m = remote_manifest()
    active = (m.get("active") or {}).get("file_hash")
    rows = [{**r, "active":r.get("file_hash")==active} for r in m.get("uploads", [])]
    return pd.DataFrame(sorted(rows, key=lambda x:str(x.get("uploaded_at","")), reverse=True)[:limit])



def remote_restore_ssc(file_hash):
    raise StorageError("Il ripristino richiede anteprima, data e conferma esplicita.")



# ======================================================
# BRANDING DIVISPACK / DI COSTANZO / GREENPACK
# Logo unico incorporato nel file: non servono immagini esterne.
# ======================================================
BRAND_LOGO_B64 = """/9j/4AAQSkZJRgABAQEBLAEsAAD/4QAiRXhpZgAATU0AKgAAAAgAAQESAAMAAAABAAEAAAAAAAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwMDAwYEBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCADnAyADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9/KKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACijNGaACio7i5jtbd5pJI44o1L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"""

def render_brand_header():
    user = st.session_state.get("current_user", {}) or {}
    user_name = user.get("nome", "Accesso riservato")
    user_role = ROLE_LABELS.get(user.get("ruolo", ""), user.get("ruolo", "")) if "ROLE_LABELS" in globals() else ""
    role_html = f"<span>{escape(user_role)}</span>" if user_role else "<span>DIVISPACK Analytics Platform V1</span>"
    st.markdown(
        f"""
        <style>
        .block-container {{
            padding-top: 1.1rem !important;
            padding-bottom: 4.2rem !important;
        }}
        .divis-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 22px;
            padding: 16px 20px;
            margin: 0 0 18px 0;
            border-radius: 18px;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 58%, #eef6ff 100%);
            border: 1px solid #dbe3ec;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
        }}
        .divis-logo-wrap {{
            display: flex;
            align-items: center;
            gap: 16px;
            min-width: 360px;
        }}
        .divis-logo-wrap img {{
            max-height: 92px;
            max-width: 650px;
            object-fit: contain;
        }}
        .divis-title-box {{
            text-align: right;
            min-width: 320px;
        }}
        .divis-title {{
            font-size: 30px;
            font-weight: 950;
            letter-spacing: .02em;
            color: #10233f;
            line-height: 1.05;
            margin: 0;
        }}
        .divis-subtitle {{
            font-size: 13px;
            font-weight: 700;
            color: #64748b;
            margin-top: 8px;
        }}
        .divis-user-pill {{
            display: inline-flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 12px;
            padding: 8px 12px;
            border-radius: 999px;
            background: #111827;
            color: white;
            font-size: 12px;
            font-weight: 800;
        }}
        .divis-user-pill span {{
            color: #d1d5db;
            font-weight: 700;
        }}
        .divis-footer {{
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 9999;
            background: #050505;
            color: #ffffff;
            padding: 7px 14px;
            text-align: center;
            font-size: 11px;
            letter-spacing: .02em;
            border-top: 1px solid rgba(255,255,255,.16);
        }}
        @media (max-width: 980px) {{
            .divis-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .divis-title-box {{
                text-align: left;
                min-width: 0;
            }}
            .divis-logo-wrap {{
                min-width: 0;
                width: 100%;
            }}
            .divis-logo-wrap img {{
                max-width: 100%;
                max-height: 86px;
            }}
        }}
        </style>

        <div class="divis-header">
            <div class="divis-logo-wrap">
                <img src="data:image/jpeg;base64,{BRAND_LOGO_B64}" alt="DIVISPACK - Di Costanzo - Greenpack">
            </div>
            <div class="divis-title-box">
                <div class="divis-title">DIVISPACK TOOL</div>
                <div class="divis-subtitle">Sistema automatico di pulizia, controllo clienti e dashboard SSC</div>
                <div class="divis-user-pill">👤 {escape(str(user_name))} &nbsp;|&nbsp; {role_html}</div>
            </div>
        </div>
        <div class="divis-footer">Developed by Pentti Salenius © 2026 | DIVISPACK Analytics Platform</div>
        """,
        unsafe_allow_html=True,
    )

render_brand_header()


# ======================================================
# LOGIN / UTENTI / RUOLI
# ======================================================

USERS_FILE = Path(__file__).with_name("divispack_users.json")
USER_ACTION_LOG_FILE = Path(__file__).with_name("divispack_user_action_log.json")

def load_initial_users_from_secrets():
    """Carica gli utenti iniziali da Streamlit Secrets / ambiente.

    Nessuna password viene conservata nel repository GitHub.
    In locale, se esiste già divispack_users.json, continua a essere usato.
    """
    configured = {}

    try:
        raw = st.secrets.get("initial_users", {})
        for username, info in raw.items():
            username = str(username).strip().lower()
            password = str(info.get("password", "")).strip()
            if not username or not password:
                continue
            configured[username] = {
                "nome": str(info.get("nome", username)).strip() or username,
                "ruolo": str(info.get("ruolo", "viewer")).strip() or "viewer",
                "password": password,
            }
    except Exception:
        pass

    # Fallback utile per deploy/container non Streamlit Cloud.
    env_user = os.getenv("DIVISPACK_ADMIN_USER", "").strip().lower()
    env_password = os.getenv("DIVISPACK_ADMIN_PASSWORD", "").strip()
    if env_user and env_password and env_user not in configured:
        configured[env_user] = {
            "nome": os.getenv("DIVISPACK_ADMIN_NAME", env_user).strip() or env_user,
            "ruolo": "super_admin",
            "password": env_password,
        }

    return configured


DEFAULT_USERS = load_initial_users_from_secrets()


ROLE_LABELS = {
    "super_admin": "Supervisione completa",
    "admin": "Amministrazione operativa",
    "editor": "Visualizzazione + modifiche complete",
    "viewer": "Solo visualizzazione completa",
}


def hash_password(password):
    salt = os.urandom(16).hex()
    rounds = 600000
    value = hashlib.pbkdf2_hmac("sha256", str(password).encode(), bytes.fromhex(salt), rounds).hex()
    return f"pbkdf2_sha256${rounds}${salt}${value}"



def ensure_users_file():
    if USERS_FILE.exists():
        return
    users = {}
    for username, info in DEFAULT_USERS.items():
        users[username] = {
            "nome": info["nome"],
            "ruolo": info["ruolo"],
            "password_hash": hash_password(info["password"]),
            "attivo": True,
        }
    if users:
        USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")



def load_users():
    configured = load_initial_users_from_secrets()
    try:
        users = remote_state_get("users", {}) or {}
        reachable = True
    except StorageError:
        # Consente solo l'accesso di bootstrap per sistemare la configurazione.
        # Non recupera utenti o saldi da copie locali obsolete.
        users, reachable = {}, False
    changed = False
    for username, info in configured.items():
        username = str(username).strip().lower()
        prev = users.get(username, {})
        desired = {"nome":info.get("nome",username),"ruolo":info.get("ruolo","viewer"),
                   "attivo":bool(info.get("attivo",True)),
                   "password_hash":prev.get("password_hash","")}
        if not verify_password(info.get("password", ""), desired["password_hash"]):
            desired["password_hash"] = hash_password(info.get("password", ""))
        if prev != desired:
            users[username] = desired; changed = True
    if changed and reachable:
        remote_state_set("users", users, "__bootstrap__", bootstrap=True)
    return users





def save_users(users):
    if not is_super_admin():
        st.error("Gestione utenti riservata al super_admin."); return False
    return remote_state_set("users", users)





def carica_log_azioni_utenti():
    if not can_view_user_audit():
        return pd.DataFrame()
    return pd.DataFrame(remote_state_get("user_action_log", []) or [])





def registra_azione(azione, cliente="", zona="", agente="", dettaglio="", vecchio_valore="", nuovo_valore=""):
    user = st.session_state.get("current_user", {}) or {}
    record = {"DATA_ORA":datetime.now().isoformat(timespec="seconds"),"UTENTE":user.get("nome",""),
      "USERNAME":user.get("username",""),"RUOLO":user.get("ruolo",""),"AZIONE":azione,
      "CLIENTE":cliente,"ZONA":zona,"AGENTE":agente,"DETTAGLIO":dettaglio,
      "VALORE_PRECEDENTE":vecchio_valore,"VALORE_NUOVO":nuovo_valore}
    try:
        storage_api_call("audit_append_v2", {"record":record,"actor":user.get("username",""),"request_id":str(uuid.uuid4())})
        remote_state_get_cached.clear(*get_storage_api_config(), "user_action_log")
        audit_page_cached.clear()
    except StorageError:
        # Le mutazioni hanno anche un audit nella stessa transazione remota.
        st.caption("Annotazione accessoria non registrata. Non è una conferma di salvataggio dati.")




def login_ok(username, password):
    username = str(username).strip().lower()
    users = load_users()
    u = users.get(username)
    if not u or not u.get("attivo", True) or not verify_password(password, u.get("password_hash", "")):
        return None
    return {"username":username, "nome":u.get("nome",username), "ruolo":u.get("ruolo","viewer")}



def is_logged_in():
    return bool(st.session_state.get("current_user"))


def current_user_role():
    return (st.session_state.get("current_user") or {}).get("ruolo", "viewer")



def can_edit():
    return (
        current_user_role() in ["super_admin", "admin", "editor"]
        and bool(st.session_state.get("__storage_ready", False))
        and not st.session_state.get("__history_readonly", False)
        and not st.session_state.get("__period_view_readonly", False)
    )





def is_super_admin():
    return current_user_role() == "super_admin"


def can_view_user_audit():
    """La cronologia azioni utenti è riservata esclusivamente al super_admin."""
    return is_super_admin()


def can_manage_users():
    """Gestione credenziali/ruoli riservata al super_admin."""
    return is_super_admin()


def can_manage_operational_data():
    """Modifiche operative consentite a super_admin, admin ed editor."""
    return can_edit()


def render_login():
    st.markdown("---")
    st.subheader("Accesso utenti DIVISPACK")
    st.caption(f"Build {APP_BUILD}")
    st.caption("Inserisci le credenziali per accedere al tool.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Accedi", width='stretch')
    if submit:
        user = login_ok(username, password)
        if user:
            st.session_state["current_user"] = user
            registra_azione("LOGIN", dettaglio="Accesso al tool")
            st.rerun()
        else:
            st.error("Credenziali non valide o utente disattivato.")
            try:
                configured = load_initial_users_from_secrets()
                if not configured:
                    st.caption(
                        "Nessun utente risulta configurato nei Secrets di questa app. "
                        "Verifica App → Settings → Secrets e riavvia l'app."
                    )
            except Exception:
                pass


def require_login():
    if not is_logged_in():
        render_login(); st.stop()
    # Rilettura cache breve anche durante una sessione, per ruoli revocati.
    user = st.session_state.get("current_user", {})
    users = load_users()
    refreshed = users.get(user.get("username", ""))
    if not refreshed or not refreshed.get("attivo", True):
        st.session_state.pop("current_user", None)
        st.warning("Sessione non più autorizzata."); st.stop()
    st.session_state["current_user"] = {**user, "nome":refreshed.get("nome",user.get("nome")),
                                       "ruolo":refreshed.get("ruolo","viewer")}



def render_user_sidebar():
    user = st.session_state.get("current_user", {}) or {}
    st.sidebar.markdown("---")
    st.sidebar.subheader("Utente")
    st.sidebar.write(f"**{user.get('nome', '')}**")
    ruolo = user.get("ruolo", "viewer")
    st.sidebar.caption(ROLE_LABELS.get(ruolo, ruolo))
    if st.sidebar.button("Logout", width='stretch'):
        registra_azione("LOGOUT", dettaglio="Uscita dal tool")
        st.session_state.clear()  # Il login successivo non eredita moduli e valori del precedente.
        st.rerun()


def render_gestione_utenti():
    st.header("Gestione utenti")
    if not can_manage_users():
        st.warning("Gestione utenti disponibile solo al super_admin.")
        return
    users = load_users()
    rows = []
    for username, info in users.items():
        rows.append({
            "USERNAME": username,
            "NOME": info.get("nome", ""),
            "RUOLO": info.get("ruolo", "viewer"),
            "ATTIVO": bool(info.get("attivo", True)),
            "NUOVA_PASSWORD": "",
        })
    df_users = pd.DataFrame(rows)
    edited = st.data_editor(
        df_users,
        width='stretch',
        hide_index=True,
        column_config={
            "RUOLO": st.column_config.SelectboxColumn(
                "Ruolo", options=["super_admin", "admin", "editor", "viewer"]
            ),
            "ATTIVO": st.column_config.CheckboxColumn("Attivo"),
            "NUOVA_PASSWORD": st.column_config.TextColumn("Nuova password"),
        },
        key="editor_gestione_utenti",
    )
    if st.button("Salva utenti", width='stretch'):
        new_users = users.copy()
        for _, r in edited.iterrows():
            username = str(r.get("USERNAME", "")).strip().lower()
            if not username:
                continue
            old = new_users.get(username, {})
            new_users[username] = {
                "nome": str(r.get("NOME", "")).strip(),
                "ruolo": str(r.get("RUOLO", "viewer")).strip(),
                "attivo": bool(r.get("ATTIVO", True)),
                "password_hash": old.get("password_hash") or hash_password("cambiami"),
            }
            nuova_pw = str(r.get("NUOVA_PASSWORD", "")).strip()
            if nuova_pw:
                new_users[username]["password_hash"] = hash_password(nuova_pw)
        if save_users(new_users):
            st.success("Utenti aggiornati nell’archivio condiviso.")
            st.rerun()


# ======================================================
# FUNZIONI BASE
# ======================================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_upper(value):
    return clean_text(value).upper()


def to_number(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text == "":
        return None

    text = (
        text.replace("€", "")
        .replace(" ", "")
        .replace("\xa0", "")
        .replace('"', "")
    )

    if "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def numeri_da_testo(txt):
    txt = clean_text(txt)

    if txt == "":
        return []

    pattern = r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:,\d+)?|-?\d+"

    matches = re.findall(pattern, txt)

    numeri = []

    for m in matches:
        n = to_number(m)
        if n is not None:
            numeri.append(n)

    return numeri


def is_numeric(value):
    return to_number(value) is not None


def format_euro(value):
    if pd.isna(value):
        return "0,00 €"

    try:
        value = float(value)
    except Exception:
        return "0,00 €"

    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"




def format_codice_cliente(value):
    """Mostra il codice cliente come intero, evitando 12345.0."""
    if value is None or pd.isna(value):
        return ""
    txt = str(value).strip()
    if txt == "" or txt.lower() == "nan":
        return ""
    try:
        n = float(txt.replace(",", "."))
        if n.is_integer():
            return str(int(n))
    except Exception:
        pass
    # fallback: se arriva già come stringa tipo 00123, non la roviniamo
    if re.fullmatch(r"\d+", txt):
        return txt
    return txt

def is_money_column_name(col):
    c=re.sub(r'\s+','_',str(col).upper())
    if c.startswith(('ID_','FLAG_','NUM_','N_','N._','RIGA_','CODICE_','BASELINE_','DATA_','PUGLIA_GRUPPO')):
        return False
    if any(x in c for x in ['PERIODI','ANNI','FORMULA','TESTO_RIGA','MEMO_ESCLUSO','IMPORTO_TESTO']):return False
    return any(x in c for x in ['IMPORTO','TOTALE','FATTURE','BUONI','PAGATO','DIFFERENZA','DELTA','RESIDUO','SALDO','PRECEDENTE','ATTUALE','VARIAZIONE'])


def row_text(row, data_columns):
    values = [clean_text(row[c]) for c in data_columns]
    return " ".join([v for v in values if v != ""]).upper()


def count_numeric_cells(row, data_columns):
    return sum(1 for c in data_columns if is_numeric(row[c]))


def is_sicilia_sheet(sheet_name):
    return canonical_sheet(sheet_name)=="SICILIA"



def is_puglia_sheet(sheet_name):
    return canonical_sheet(sheet_name)=="PUGLIA"



# ======================================================
# LETTURA FILE
# ======================================================


@st.cache_data(show_spinner=False, max_entries=4)
def prepara_saldi_base_cached(file_bytes, reference_date=""):
    fmt, engine=excel_format_from_bytes(file_bytes)
    try:
        sheets=pd.read_excel(BytesIO(file_bytes),sheet_name=None,header=None,engine=engine,dtype=object)
    except ImportError as exc:
        library='xlrd==2.0.2' if fmt=='xls' else 'openpyxl>=3.1,<4'
        raise ValueError(f"Manca il lettore {fmt}: aggiungere {library} a requirements.txt e attendere il redeploy. Il file non è stato attivato.") from exc
    except Exception as exc:
        raise ValueError("Excel non leggibile o protetto da password. Il file non è stato attivato.") from exc
    forms=xlsx_formula_metadata(file_bytes) if fmt=='xlsx' else {}
    if not sheets:raise ValueError("Nessun foglio nel file.")
    frames=[]; seen=set()
    for name,sh in sheets.items():
        n=canonical_sheet(name)
        if n in seen:raise ValueError("Nomi di fogli ambigui dopo la normalizzazione: "+n)
        seen.add(n)
        if len(sh)>30000 or len(sh.columns)>100:
            raise ValueError("Dimensioni foglio inattese: controllare l'export.")
        sh.attrs['ssc_formulas']=forms.get(n,{})
        sh.attrs['ssc_format']=fmt
        f=sh.copy();f['FOGLIO_ORIGINE']=name;f['RIGA_SHEET']=range(len(f));frames.append(f)
    raw=pd.concat(frames,ignore_index=True)
    _parsed_date = parse_reference_date(reference_date)
    _year_token=_SSC_PARSE_YEAR.set((_parsed_date or data_riferimento_da_fogli(sheets)).year)
    try:
        db,debug,cols=pulisci_ssc(raw)
    finally:
        _SSC_PARSE_YEAR.reset(_year_token)
    if db.empty:raise ValueError("Non ho riconosciuto posizioni cliente: il SALDI non viene attivato.")
    # Perimetro Valeria: riferimenti della formula come prova strutturale.
    for name,sh in sheets.items():
        if is_puglia_sheet(name):db=arricchisci_blocchi_puglia(db,sh,name)
    return raw,list(sheets),sheets,db,debug,cols





def dataframe_fingerprint(df, columns=None):
    if df is None or df.empty:
        return "EMPTY"
    work = df
    if columns:
        available = [c for c in columns if c in work.columns]
        if available:
            work = work[available]
    hashed = pd.util.hash_pandas_object(
        work.fillna(""),
        index=True,
    ).values.tobytes()
    return hashlib.sha256(hashed).hexdigest()


def quadratura_session_cached(file_hash, sheets, db_originale):
    """Ricalcola la quadratura solo se cambia file o stato base/correzioni."""
    fp = dataframe_fingerprint(
        db_originale,
        [
            "FOGLIO_ORIGINE", "RIGA_SHEET", "ID_POSIZIONE_SSC",
            "TIPO_DOCUMENTO", "IMPORTO_STANDARD",
            "IMPORTO_FATTURE_RIGA", "IMPORTO_BUONI_RIGA",
            "IMPORTO_NOTE_CREDITO", "PUGLIA_GRUPPO",
            "PUGLIA_IMPORTO_TESTO",
        ],
    )
    key = f"{file_hash}:{fp}"

    if (
        st.session_state.get("__quadratura_cache_key") == key
        and isinstance(st.session_state.get("__quadratura_cache_value"), pd.DataFrame)
    ):
        return st.session_state["__quadratura_cache_value"].copy()

    quadratura = calcola_quadratura_excel(
        None,
        db_originale,
        sheets=sheets,
    )
    st.session_state["__quadratura_cache_key"] = key
    st.session_state["__quadratura_cache_value"] = quadratura.copy()
    return quadratura

def leggi_tutte_le_sheet(file):
    sheets = pd.read_excel(file, sheet_name=None, header=None)
    frames = []

    for sheet_name, df in sheets.items():
        df = df.copy()
        df["FOGLIO_ORIGINE"] = sheet_name
        df["RIGA_SHEET"] = range(len(df))
        frames.append(df)

    df_raw = pd.concat(frames, ignore_index=True)
    return df_raw, list(sheets.keys())


def normalizza_colonne(df_raw):
    df = df_raw.copy()

    colonne_tecniche = ["FOGLIO_ORIGINE", "RIGA_SHEET"]
    colonne_excel = [c for c in df.columns if c not in colonne_tecniche]

    rename_map = {
        old: f"COL_{i + 1}"
        for i, old in enumerate(colonne_excel)
    }

    df = df.rename(columns=rename_map)
    data_columns = list(rename_map.values())

    df = df[data_columns + colonne_tecniche]
    df = df.dropna(subset=data_columns, how="all").copy()
    df = df.reset_index(drop=True)
    df["RIGA_GLOBALE"] = df.index

    return df, data_columns


# ======================================================
# PARSING GENERALE
# ======================================================

def estrai_codice_cliente(row, data_columns, col_codice=None):
    colonne = [col_codice] if col_codice else data_columns

    for c in colonne:
        if c is None:
            continue

        n = to_number(row[c])

        if n is not None and float(n).is_integer():
            codice = int(n)

            if 0 < codice < 999999:
                return codice

    return None


def is_total_row(txt):
    patterns = [
        "TOTALE CLIENTI",
        "TOTALI CLIENTI",
        "TOTALE ZONA",
        "TOTALI ZONA",
        "TOTALE GENERALE",
        "TOTALI GENERALE",
        "TOTALE AGENTE",
        "TOTALI AGENTE",
        "TOTALI AL 31 MARZO",
        "TOTALE AL 31 MARZO",
        "TOTALI",
        "TOTALI ",
    ]

    return any(p in txt for p in patterns)


def is_header_row(row, data_columns):
    txt = row_text(row, data_columns)
    txt_norm = txt.replace(",", ".")

    if "COD.CLI" in txt_norm or "COD CLI" in txt_norm or "CODCLI" in txt_norm:
        return True

    # Header speciale Sicilia: AGENTE | DIVISPACK | Rif. Fatture | SSC | TOTALE | DATA
    if "DIVISPACK" in txt and "SSC" in txt and "TOTALE" in txt:
        return True

    # Header senza codice esplicito ma con colonne documentali/importo
    if ("CLIENTE" in txt or "AZIENDA" in txt) and ("DOCUMENT" in txt or "DOC" in txt) and ("IMPORTO" in txt or "FATTURE" in txt or "TOTALE" in txt):
        return True

    return False

def mappa_header(row, data_columns):
    mapping = {
        "codice": None,
        "cliente": None,
        "documento": None,
        "riferimento": None,
        "importo": None,       # colonna importo/buoni/SSC nei layout standard
        "totale": None,
        "fatture": None,       # colonna fatture nei layout a doppio importo
        "agente_header": None,

        "sicilia_importo_fatture": None,
        "sicilia_rif_fatture": None,
        "sicilia_buoni": None,
        "sicilia_totale": None,
        "sicilia_modalita_pagamento": None,
    }

    def norm(v):
        v = clean_upper(v)
        v = v.replace(",", ".")
        v = re.sub(r"\s+", " ", v).strip()
        return v

    vals = {c: norm(row[c]) for c in data_columns}

    for i, c in enumerate(data_columns):
        val = vals[c]

        if val in ["COD.CLI.", "COD.CLI", "COD CLI", "CODCLI"] or val.startswith("COD.CLI"):
            mapping["codice"] = c

        elif val in ["CLIENTE", "CLIENTI", "AZIENDA", "RAGIONE SOCIALE"]:
            mapping["cliente"] = c

        elif val == "DIVISPACK":
            mapping["sicilia_importo_fatture"] = c
            mapping["fatture"] = c

        elif "RIF" in val and "FATT" in val:
            mapping["sicilia_rif_fatture"] = c
            mapping["riferimento"] = c

        elif val == "SSC":
            mapping["sicilia_buoni"] = c
            mapping["importo"] = c

        elif val == "FATTURE" or val == "FATTURA":
            mapping["fatture"] = c

        elif val in ["IMPORTO", "TOTALE", "TOT", "SALDO", "VALORE", "TOT DOC", "TOTALE DOC"]:
            # Nei layout standard TOTALE/IMPORTO è spesso la colonna dei buoni/acconti,
            # mentre FATTURE è in una colonna separata. In Sicilia il totale viene gestito a parte.
            if val == "TOTALE":
                mapping["totale"] = c
                mapping["sicilia_totale"] = c
            if mapping["importo"] is None:
                mapping["importo"] = c

        elif "DOC" in val or "DOCUMENT" in val:
            mapping["documento"] = c

        elif "RIFERIMENTO" in val or val == "RIF":
            mapping["riferimento"] = c

        elif re.search(r"\d{2}/\d{2}/\d{4}", val) or val == "DATA":
            mapping["sicilia_modalita_pagamento"] = c

    # Fallback posizione classica: codice, cliente, documento, riferimento/importo, fatture
    if mapping["codice"] is not None:
        idx_cod = data_columns.index(mapping["codice"])
        if mapping["cliente"] is None and idx_cod + 1 < len(data_columns):
            mapping["cliente"] = data_columns[idx_cod + 1]

    # Header disallineato tipo MONDRAG-CAPUA:
    # Cod.Cli | CLIENTE | [documento reale] | DOCUMENTI/RIF | IMPORTO
    if mapping["cliente"] is not None and mapping["importo"] is not None:
        idx_cli = data_columns.index(mapping["cliente"])
        idx_imp = data_columns.index(mapping["importo"])
        between = data_columns[idx_cli + 1:idx_imp]
        if between:
            # se la colonna mappata come documento coincide con quella subito prima dell'importo,
            # spesso il documento reale è la colonna precedente.
            if mapping["documento"] is None:
                mapping["documento"] = between[0]
            elif len(between) >= 2 and mapping["documento"] == between[-1]:
                mapping["riferimento"] = mapping["documento"]
                mapping["documento"] = between[0]

    # Header classico con agente scritto nella riga intestazione dopo il codice, raro ma possibile
    for i, c in enumerate(data_columns):
        val = vals[c]
        if val.startswith("COD.CLI") or val.startswith("COD CLI"):
            if i + 1 < len(data_columns):
                possibile = clean_text(row[data_columns[i + 1]])
                possibile_upper = possibile.upper()
                if possibile and possibile_upper not in ["CLIENTE", "CLIENTI", "AZIENDA"]:
                    mapping["agente_header"] = possibile_upper

    # Header Sicilia: la colonna cliente è quella immediatamente prima di DIVISPACK.
    if mapping["sicilia_importo_fatture"] is not None:
        idx_divispack = data_columns.index(mapping["sicilia_importo_fatture"])
        if idx_divispack - 1 >= 0:
            mapping["cliente"] = data_columns[idx_divispack - 1]
            agente = clean_text(row[data_columns[idx_divispack - 1]])
            if agente and clean_upper(agente) not in ["CLIENTE", "CLIENTI"]:
                mapping["agente_header"] = agente.upper()

    return mapping

def is_zona_row(row, txt, data_columns):
    txt = txt.upper().strip()

    if txt == "":
        return False

    if is_total_row(txt):
        return False

    if is_header_row(row, data_columns):
        return False

    if estrai_codice_cliente(row, data_columns) is not None:
        return False

    if count_numeric_cells(row, data_columns) > 0:
        return False

    if txt.startswith("ZONA"):
        return True

    zone_keywords = [
        "MERCATO ORTOFRUTTICOLO",
        "FUNGAIE",
        "PUGLIA",
        "CAPUA-MONDRAGONE",
        "MONDRAGONE",
        "MONDRAG",
        "CASERTA",
        "MADDALONI",
        "ARIENZO",
        "SARNO",
        "PAGANI",
        "ZAPPONETA",
        "MARGHERITA DI SAVOIA",
        "SOMMA VESUVIANA",
    ]

    return any(k in txt for k in zone_keywords)

def pulisci_zona(txt, fallback):
    raw = txt.upper().strip()
    fb = str(fallback).upper().strip()
    raw = re.sub(r"\s+", " ", raw)

    # Normalizzazioni forti per evitare che descrizioni lunghe diventino zone diverse
    if "SARNO" in raw and "PAGANI" in raw:
        return "SARNO-PAGANI"
    if "CASERTA" in raw:
        return "CASERTA"
    if "CAPUA" in raw or "MONDRAGONE" in raw or "MONDRAG" in fb:
        return "MONDRAG-CAPUA"
    if "SOMMA" in raw:
        return "SOMMA VESUVIANA"
    if "GIUGLIANO" in raw:
        return "GIUGLIANO"
    if "CARDITO" in raw:
        return "CARDITO"
    if "NAPOLI" in raw:
        return "NAPOLI"
    if "VOLLA" in raw:
        return "VOLLA"
    if "PUGLIA" in raw:
        return "PUGLIA"
    if "FUNGAIE" in raw:
        return "FUNGAIE"
    if "SICILIA" in raw or "SICILIA" in fb:
        return "SICILIA"

    txt = raw
    txt = re.sub(r"AL\s+31\s+MARZO\s+2026", "", txt, flags=re.IGNORECASE).strip()
    txt = txt.replace("31 MARZO 2026", "").strip()
    if txt.startswith("ZONA"):
        txt = txt.replace("ZONA", "", 1).strip()
    txt = txt.replace(":", "").strip()

    return txt if txt else fb

def is_agente_row(row, txt, data_columns):
    txt = txt.upper().strip()

    if txt == "":
        return False

    if is_zona_row(row, txt, data_columns):
        return False

    if is_header_row(row, data_columns):
        return False

    if is_total_row(txt):
        return False

    if estrai_codice_cliente(row, data_columns) is not None:
        return False

    if count_numeric_cells(row, data_columns) > 0:
        return False

    parole_escluse = [
        "BUONO", "BUONI", "FT", "FATTURA", "FATTURE",
        "CLIENTE", "DOCUMENTO", "IMPORTO", "SCADUTO",
        "SALDO", "PAGINA", "DIVISPACK",
    ]

    if any(p in txt for p in parole_escluse):
        return False

    if len(txt.split()) < 2:
        return False

    return True


def estrai_cliente(row, data_columns, col_cliente=None):
    colonne = [col_cliente] if col_cliente else data_columns

    for c in colonne:
        if c is None:
            continue

        v = clean_text(row[c])

        if v == "":
            continue

        if is_numeric(v):
            continue

        vu = v.upper()

        blacklist = [
            "BUONO", "BUONI", "FT", "FATTURA",
            "FATTURE", "TOTALE", "DIVISPACK", "RIF.",
            "RIF", "SSC"
        ]

        if any(b in vu for b in blacklist):
            continue

        return v

    return ""


def estrai_documento(row, data_columns, col_documento=None):
    candidates = []

    if col_documento:
        candidates.append(clean_text(row[col_documento]))

    txt = row_text(row, data_columns)
    candidates.append(txt)

    for source in candidates:
        source_upper = source.upper()

        patterns = [
            r"\d+\s*BUONO",
            r"\d+\s*BUONI",
            r"\d+\s*FT\.?",
            r"\d+\s*FATTURA",
            r"\d+\s*FATTURE",
        ]

        for p in patterns:
            m = re.search(p, source_upper)

            if m:
                return m.group(0)

        if any(x in source_upper for x in ["BUONO", "BUONI", "FT", "FATTURA", "FATTURE"]):
            return source

    return ""


def estrai_num_documenti(documento_raw, tipo_documento):
    testo = clean_upper(documento_raw)

    patterns = [
        r"(\d+)\s*BUONO",
        r"(\d+)\s*BUONI",
        r"(\d+)\s*FT\.?",
        r"(\d+)\s*FATTURA",
        r"(\d+)\s*FATTURE",
    ]

    for p in patterns:
        m = re.search(p, testo)

        if m:
            return int(m.group(1))

    if tipo_documento in ["BUONO", "FATTURA"]:
        return 1

    return 0


def estrai_periodi_riferimento(txt):
    txt = txt.upper()

    mesi_map = {
        "GENNAIO": "Gennaio", "GEN": "Gennaio",
        "FEBBRAIO": "Febbraio", "FEB": "Febbraio",
        "MARZO": "Marzo", "MAR": "Marzo",
        "APRILE": "Aprile", "APR": "Aprile",
        "MAGGIO": "Maggio", "MAG": "Maggio",
        "GIUGNO": "Giugno", "GIU": "Giugno",
        "LUGLIO": "Luglio", "LUG": "Luglio",
        "AGOSTO": "Agosto", "AGO": "Agosto",
        "SETTEMBRE": "Settembre", "SET": "Settembre",
        "OTTOBRE": "Ottobre", "OTT": "Ottobre",
        "NOVEMBRE": "Novembre", "NOV": "Novembre",
        "DICEMBRE": "Dicembre", "DIC": "Dicembre",
    }

    trovati = []

    for chiave, valore in mesi_map.items():
        if re.search(rf"\b{chiave}\b", txt):
            if valore not in trovati:
                trovati.append(valore)

    return ", ".join(trovati)


MESE_ALIASES = {
    "GENNAIO": "Gennaio", "GEN": "Gennaio",
    "FEBBRAIO": "Febbraio", "FEB": "Febbraio",
    "MARZO": "Marzo", "MAR": "Marzo",
    "APRILE": "Aprile", "APR": "Aprile",
    "MAGGIO": "Maggio", "MAG": "Maggio",
    "GIUGNO": "Giugno", "GIU": "Giugno",
    "LUGLIO": "Luglio", "LUG": "Luglio",
    "AGOSTO": "Agosto", "AGO": "Agosto",
    "SETTEMBRE": "Settembre", "SET": "Settembre",
    "OTTOBRE": "Ottobre", "OTT": "Ottobre",
    "NOVEMBRE": "Novembre", "NOV": "Novembre",
    "DICEMBRE": "Dicembre", "DIC": "Dicembre",
}


def normalizza_anno(anno):
    anno = clean_text(anno).replace("'", "")
    if anno == "":
        return ""
    try:
        n = int(anno)
    except Exception:
        return anno
    if n < 100:
        return str(2000 + n) if n <= 35 else str(1900 + n)
    return str(n)


def mese_numero(mese):
    ordine = {
        "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
        "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
        "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12,
    }
    return ordine.get(mese, 0)




def estrai_periodi_anni_importi(txt, anno_default=None):
    items=parse_period_evidence(txt,anno_default)
    def unique(xs):return list(dict.fromkeys(xs))
    details=[f"{x['mese']} {x['anno']}: {format_euro(x['amount'])}" for x in items if x['amount'] is not None]
    return (', '.join(unique(x['mese'] for x in items)),', '.join(unique(x['anno'] for x in items)),
      ' | '.join(unique(details)),', '.join(sorted(unique(f"{x['anno']}-{mese_numero(x['mese']):02d}" for x in items))),
      ', '.join(unique(x['anno'] for x in items if x['stimato'])))






def estrai_periodi_standard_da_riga(row,mapping,importo_riga,anno_default=None):
    return estrai_periodi_anni_importi(sorgente_documentale(row,mapping),anno_default)





def estrai_dettaglio_periodi_documenti(txt,num_fatture=0,num_buoni=0,anno_default=None,dettaglio_importi=''):
    items=parse_period_evidence(txt,anno_default)
    if not items:
        return clean_text(dettaglio_importi)
    if len(items)==1 and items[0]['count'] is None and items[0]['amount'] is None and int(num_fatture or 0)>0 and int(num_buoni or 0)==0:
        items[0]['count']=int(num_fatture)
    parts=[]
    for x in items:
        label=f"{x['mese']} {x['anno']}"
        if x['amount'] is not None:label+=f": {format_euro(x['amount'])}"
        elif x['count'] is not None:label+=f" ({x['count']} {'fattura' if x['count']==1 else 'fatture'})"
        if label not in parts:parts.append(label)
    return ' | '.join(parts)




def join_periodi_dettaglio(values):
    """Aggrega dettagli senza spezzare i decimali italiani sulle virgole."""
    out = []
    for v in values:
        if pd.isna(v):
            continue
        testo = clean_text(v)
        if not testo:
            continue
        for pezzo in re.split(r"\s*\|\s*", testo):
            pezzo = clean_text(pezzo)
            if pezzo and pezzo not in out:
                out.append(pezzo)
    return " | ".join(out)

def estrai_anni_riferimento(txt):
    _, anni, _, _, _ = estrai_periodi_anni_importi(txt)
    return anni


def estrai_dettaglio_periodi_importi(txt):
    periodi, anni, dettaglio, _, _ = estrai_periodi_anni_importi(txt)
    if dettaglio:
        return dettaglio
    return clean_text(txt)


def estrai_modalita_pagamento(txt):
    """Estrae la modalità di pagamento come TESTO, evitando falsi positivi sui mesi.

    Regole operative:
    - cerca solo pattern di pagamento veri: Bon.Ban, Bonifico, Ri.Ba, Riba, Rimessa,
      Contrassegno, B.B./BB come token autonomo, D.F.M./DFM, assegno, insoluto, ecc.;
    - NON interpreta pezzi di mese come pagamento: es. FEBBRAIO non deve diventare BBRAIO;
    - rimuove eventuali importi finali attaccati alla modalità;
    - se non trova una modalità riconoscibile, restituisce stringa vuota.
    """
    originale = clean_text(txt)
    if originale == "":
        return ""

    # Normalizzo solo per la ricerca, senza perdere il testo originale.
    upper = re.sub(r"\s+", " ", originale.upper()).strip()

    # Pattern rigorosi. Nota: BB viene accettato solo come token autonomo, non dentro FEBBRAIO.
    payment_patterns = [
        r"BON\.?\s*BAN\.?",
        r"BONIFICO(?:\s+BANCARIO)?",
        r"RI\.?\s*BA\.?",
        r"\bRIBA\b",
        r"\bB\.?\s*B\.?\b",
        r"RIMESSA(?:\s+DIRETTA)?",
        r"CONTRASSEGNO",
        r"D\.?\s*F\.?\s*M\.?",
        r"\bDFM\b",
        r"\bASSEGNO\b",
        r"\bASS\.?(?:\s*INS\.?)?\b",
        r"INSOLUTO",
        r"PRATICA",
        r"CONCORDATO",
    ]

    first_match = None
    for pat in payment_patterns:
        m = re.search(pat, upper, flags=re.IGNORECASE)
        if m:
            if first_match is None or m.start() < first_match.start():
                first_match = m

    if first_match is None:
        return ""

    start = first_match.start()
    pagamento = originale[start:].strip()

    # Se dopo la modalità compare un nuovo documento, taglio lì.
    doc_after = re.search(
        r"\b\d+\s*(?:BUONO|BUONI|FT\.?|FATTURA|FATTURE)\b",
        pagamento.upper(),
        flags=re.IGNORECASE,
    )
    if doc_after and doc_after.start() > 0:
        pagamento = pagamento[:doc_after.start()].strip()

    # Taglia se dopo la modalità inizia chiaramente una sequenza di mesi/riferimenti.
    mesi_pattern = "|".join(sorted(MESE_ALIASES.keys(), key=len, reverse=True))
    mese_after = re.search(rf"\b(?:{mesi_pattern})\b", pagamento.upper(), flags=re.IGNORECASE)
    # Non taglio se il mese compare prima del pattern pagamento: qui pagamento parte già dal pattern.
    if mese_after and mese_after.start() > 0:
        pagamento = pagamento[:mese_after.start()].strip()

    # Conserva eventuali giorni: 30 GG, 60+10 GG, 75/90 GG, ecc.
    gg = re.search(r"\b\d{1,3}(?:\s*[+/]\s*\d{1,3})?\s*GG\b", pagamento.upper())
    if gg:
        pagamento = pagamento[:gg.end()].strip()

    # Rimuove importi finali eventualmente concatenati alla modalità.
    amount_end_patterns = [
        r"[\s|;,-]*(?:€\s*)?-?\d{1,3}(?:\.\d{3})*,\d{1,2}\s*$",
        r"[\s|;,-]*(?:€\s*)?-?\d+(?:[\.,]\d{2})\s*$",
        r"[\s|;,-]*(?:€\s*)?-?\d{4,}\s*$",
    ]
    changed = True
    while changed:
        changed = False
        for pat in amount_end_patterns:
            nuovo = re.sub(pat, "", pagamento).strip()
            if nuovo != pagamento:
                pagamento = nuovo
                changed = True

    pagamento = re.sub(r"\s+", " ", pagamento).strip(" -|;,")

    # Ultima difesa: se resta solo un pezzo di mese o un testo senza pattern pagamento, svuota.
    pagamento_upper = pagamento.upper()
    if not any(re.search(pat, pagamento_upper, flags=re.IGNORECASE) for pat in payment_patterns):
        return ""

    return pagamento


def modalita_pagamento_sicilia_da_cella(value):
    """Per la Sicilia la modalità pagamento sta nella colonna finale DATA/30-04-2026.
    Non va ricavata da Rif. Fatture o SSC, perché lì ci sono mesi, importi,
    spese insoluto e altre note operative. Se la cella finale contiene una
    vera modalità di pagamento, restituiamo il testo completo della cella.
    """
    testo = clean_text(value)
    if testo == "":
        return ""

    upper = re.sub(r"\s+", " ", testo.upper()).strip()
    payment_patterns = [
        r"BON\.?\s*BAN\.?",
        r"BONIFICO(?:\s+BANCARIO)?",
        r"RI\.?\s*BA\.?",
        r"\bRIBA\b",
        r"\bB\.?\s*B\.?\b",
        r"RIMESSA(?:\s+DIRETTA)?",
        r"CONTRASSEGNO",
        r"D\.?\s*F\.?\s*M\.?",
        r"\bDFM\b",
        r"\bASSEGNO\b",
        r"\bASS\.?(?:\s*INS\.?)?\b",
        r"INSOLUTO",
        r"PRATICA",
        r"CONCORDATO",
        r"A\s+VISTA",
        r"MEZZO\s+AGENTE",
        r"FM\b",
    ]

    if any(re.search(pat, upper, flags=re.IGNORECASE) for pat in payment_patterns):
        return testo
    return ""

def join_unici(values):
    puliti = []

    for v in values:
        if pd.isna(v):
            continue

        testo = str(v).strip()

        if testo == "":
            continue

        for pezzo in testo.split(","):
            pezzo = pezzo.strip()

            if pezzo and pezzo not in puliti:
                puliti.append(pezzo)

    return ", ".join(puliti)


def classifica_tipo_documento(documento_raw, txt, importo_standard):
    base = f"{documento_raw} {txt}".upper()

    if "BUONO" in base or "BUONI" in base or "ACCONTO" in base or "ACCONTI" in base:
        return "BUONO"

    if "FT." in base or " FT " in base or "FATTURA" in base or "FATTURE" in base:
        return "FATTURA"

    if importo_standard is not None and importo_standard != 0:
        return "FATTURA"

    # Una riga cliente senza esposizione non è un errore di parsing.
    return "SALDO_ZERO"


def estrai_importo_standard(row, data_columns, mapping, codice_cliente):
    colonne_da_escludere = set()

    if mapping.get("codice"):
        colonne_da_escludere.add(mapping.get("codice"))

    priorita = [
        mapping.get("totale"),
        mapping.get("importo"),
        mapping.get("fatture"),
    ]

    for c in priorita:
        if c and c not in colonne_da_escludere:
            n = to_number(row[c])

            if n is not None and n != 0:
                if codice_cliente is not None and abs(n - codice_cliente) < 0.0001:
                    continue
                return n, c

    numeri = []

    for c in data_columns:
        if c in colonne_da_escludere:
            continue

        n = to_number(row[c])

        if n is not None and n != 0:
            if codice_cliente is not None and abs(n - codice_cliente) < 0.0001:
                continue
            numeri.append((c, n))

    if not numeri:
        return None, None

    return numeri[-1][1], numeri[-1][0]


def is_data_row(row, txt, data_columns, mapping):
    txt = txt.upper().strip()

    if txt == "":
        return False

    if is_zona_row(row, txt, data_columns):
        return False

    if is_header_row(row, data_columns):
        return False

    if is_total_row(txt):
        return False

    codice = estrai_codice_cliente(row, data_columns, mapping.get("codice"))

    # Se esiste una colonna codice mappata, non cerchiamo il codice in tutta la riga:
    # rischieremmo di leggere un importo piccolo come codice cliente.
    if codice is None and mapping.get("codice") is None:
        codice = estrai_codice_cliente(row, data_columns)

    if codice is not None:
        return True

    # Fallback per righe reali senza codice cliente ma con cliente + importo.
    # Esempio: alcune righe operative/vecchie sezioni hanno codice vuoto ma saldo valorizzato.
    cliente_col = mapping.get("cliente")
    cliente = clean_text(row[cliente_col]) if cliente_col else ""
    if cliente == "":
        return False

    if clean_upper(cliente) in ["CLIENTE", "CLIENTI", "AZIENDA", "TOTALI", "TOTALE"]:
        return False

    candidate_cols = [
        mapping.get("fatture"),
        mapping.get("importo"),
        mapping.get("totale"),
        mapping.get("riferimento"),
        mapping.get("documento"),
    ]
    for c in candidate_cols:
        if c and to_number(row[c]) not in [None, 0]:
            return True

    return False



def contiene_fattura(txt):
    txt = clean_upper(txt)
    return bool(re.search(r"\bFT\b|FT\.|FATTURA|FATTURE", txt))


def contiene_buono_o_acconto(txt):
    txt = clean_upper(txt)
    keywords = [
        "BUONO", "BUONI", "ACCONTO", "ACCONTI", "ACC.", "RESTA",
        "RESO", "RESI", "VS AVERE", "VOSTRO AVERE", "INSOLUTO", "ASS.INS",
    ]
    return any(k in txt for k in keywords)


def estrai_num_fatture_da_testo(txt):
    txt = clean_upper(txt)
    m = re.search(r"(\d+)\s*(?:FT\.?|FATTURA|FATTURE)", txt)
    if m:
        return int(m.group(1))
    return 1 if contiene_fattura(txt) else 0


def estrai_num_buoni_da_testo(txt):
    txt = clean_upper(txt)
    m = re.search(r"(\d+)\s*(?:BUONO|BUONI)", txt)
    if m:
        return int(m.group(1))
    return 1 if ("BUONO" in txt or "BUONI" in txt) else 0


def numeri_riga_con_colonne(row, data_columns, exclude_cols=None):
    exclude_cols = set(exclude_cols or [])
    out = []
    for c in data_columns:
        if c in exclude_cols:
            continue
        n = to_number(row[c])
        if n is not None and n != 0:
            out.append((c, n))
    return out


def estrai_importi_standard(row, data_columns, mapping, codice_cliente, documento, txt):
    """
    Parser contabile standard.
    - colonna FATTURE => fatture;
    - colonna IMPORTO/TOTALE intermedia => buoni/acconti/resi;
    - layout senza FATTURE => importo classificato dal testo;
    - note credito/resi scalano fatture o buoni in base alla colonna in cui si trovano.
    """
    col_codice = mapping.get("codice")
    col_cliente = mapping.get("cliente")
    col_doc = mapping.get("documento")
    col_rif = mapping.get("riferimento")
    col_importo = mapping.get("importo") or mapping.get("totale")
    col_fatture = mapping.get("fatture")

    testo = f"{documento} {txt}"

    importo_fatture = 0.0
    importo_buoni = 0.0
    colonna_importo = None

    if col_fatture:
        n_fatt = to_number(row[col_fatture])
        if n_fatt is not None and n_fatt != 0:
            if codice_cliente is None or abs(n_fatt - codice_cliente) > 0.0001:
                importo_fatture += n_fatt
                colonna_importo = col_fatture

        if col_importo and col_importo != col_fatture:
            n_imp = to_number(row[col_importo])
            if n_imp is not None and n_imp != 0:
                if codice_cliente is None or abs(n_imp - codice_cliente) > 0.0001:
                    importo_buoni += n_imp
                    colonna_importo = col_importo if colonna_importo is None else f"{colonna_importo}+{col_importo}"

        # Caso reale riscontrato su CASERTA e zone simili:
        # layout: DOCUMENTI = "1 Buono" / "5 Buoni", RIFERIMENTO = importo buono, FATTURE = 0.
        # Se esiste la colonna FATTURE, ma la riga parla di buoni, l'importo può trovarsi
        # nella colonna RIFERIMENTO anziché in una colonna dedicata ai buoni.
        if ("BUONO" in clean_upper(testo)) or ("BUONI" in clean_upper(testo)):
            for c in [col_rif, col_doc, col_importo]:
                if not c or c == col_fatture:
                    continue
                n_buono = to_number(row[c])
                if n_buono is not None and n_buono != 0:
                    if codice_cliente is not None and abs(n_buono - codice_cliente) < 0.0001:
                        continue
                    # Evita doppio conteggio se lo stesso importo è già stato preso da col_importo.
                    if abs(importo_buoni - n_buono) > 0.0001:
                        importo_buoni += n_buono
                        colonna_importo = c if colonna_importo is None else f"{colonna_importo}+{c}"
                    break

        exclude = {c for c in [col_codice, col_cliente, col_doc, col_rif, col_fatture, col_importo] if c}
        for c, n in numeri_riga_con_colonne(row, data_columns, exclude):
            if codice_cliente is not None and abs(n - codice_cliente) < 0.0001:
                continue
            importo_buoni += n
            colonna_importo = c if colonna_importo is None else f"{colonna_importo}+{c}"

    else:
        n_main = to_number(row[col_importo]) if col_importo else None

        if n_main is not None and n_main != 0:
            if codice_cliente is None or abs(n_main - codice_cliente) > 0.0001:
                if contiene_buono_o_acconto(testo) and not contiene_fattura(testo):
                    importo_buoni += n_main
                elif contiene_buono_o_acconto(testo) and n_main < 0:
                    importo_buoni += n_main
                else:
                    importo_fatture += n_main
                colonna_importo = col_importo

        if importo_fatture == 0 and importo_buoni == 0:
            search_cols = []
            for c in [col_rif, col_doc]:
                if c and c not in search_cols:
                    search_cols.append(c)
            for c in search_cols:
                n = to_number(row[c])
                if n is not None and n != 0:
                    importo_buoni += n
                    colonna_importo = c
                    break

    importo_standard = importo_fatture + importo_buoni

    if importo_fatture != 0 and importo_buoni != 0:
        tipo_documento = "MISTO"
    elif importo_fatture != 0:
        tipo_documento = "FATTURA"
    elif importo_buoni != 0:
        tipo_documento = "BUONO"
    else:
        tipo_documento = "SALDO_ZERO"

    num_fatture = estrai_num_fatture_da_testo(testo) if importo_fatture != 0 else 0
    num_buoni = estrai_num_buoni_da_testo(testo) if importo_buoni != 0 else 0

    flag_nota_credito = bool(
        importo_fatture < 0
        or importo_buoni < 0
        or re.search(r"N\.C|NOTA CREDITO|NOTA DI CREDITO|RESO|RESI|VS\.?\s*AVERE", clean_upper(testo))
    )
    importo_note_credito = 0.0
    if importo_fatture < 0:
        importo_note_credito += importo_fatture
    if importo_buoni < 0:
        importo_note_credito += importo_buoni

    return {
        "TIPO_DOCUMENTO": tipo_documento,
        "NUM_DOCUMENTI": num_fatture + num_buoni,
        "NUM_FATTURE": num_fatture,
        "NUM_BUONI": num_buoni,
        "IMPORTO_STANDARD": importo_standard,
        "IMPORTO_FATTURE_RIGA": importo_fatture,
        "IMPORTO_BUONI_RIGA": importo_buoni,
        "IMPORTO_NOTE_CREDITO": importo_note_credito,
        "FLAG_NOTA_CREDITO": flag_nota_credito,
        "COLONNA_IMPORTO": colonna_importo,
    }


# ======================================================
# PARSER SPECIALE SICILIA
# ======================================================



def estrai_puglia(row, data_columns, mapping, codice_cliente, documento, txt):
    """
    Parser strutturale PUGLIA.

    Regole:
    - Ft/Fatture -> fatture;
    - Buono/Buoni/Acconto senza Ft -> buoni/acconti;
    - una riga autonoma negativa "Vs. Avere x Resi" / NC è una rettifica
      NEGATIVA delle fatture e contemporaneamente viene tracciata come
      nota credito/reso;
    - Ft + N.C. con saldo positivo resta saldo fatture: l'importo esposto è
      già il residuo del file.

    Nessuna regola dipende dal nome di un cliente.
    """
    col_importo = mapping.get("importo") or mapping.get("totale")
    raw_importo_cell = row[col_importo] if col_importo else None
    importo_raw = to_number(raw_importo_cell) if col_importo else None

    if importo_raw is None:
        _, fallback_col = estrai_importo_standard(
            row, data_columns, mapping, codice_cliente
        )
        col_importo = fallback_col
        raw_importo_cell = row[col_importo] if col_importo else None
        importo_raw = to_number(raw_importo_cell) if col_importo else 0.0

    importo_raw = float(importo_raw or 0.0)
    puglia_importo_testo = bool(
        isinstance(raw_importo_cell, str)
        and to_number(raw_importo_cell) is not None
        and not clean_text(raw_importo_cell).startswith("=")
    )

    testo = f"{documento} {txt}"
    upper = clean_upper(testo)

    ha_fattura = contiene_fattura(upper)
    ha_buono = bool(re.search(r"\bBUONO\b|\bBUONI\b", upper))
    ha_acconto = bool(re.search(r"\bACCONTO\b|\bACCONTI\b", upper))
    ha_reso_nc = bool(
        re.search(
            r"N\.?\s*C\.?|NOTA\s+(?:DI\s+)?CREDITO|RESO|RESI|VS\.?\s*AVERE|VOSTRO\s+AVERE",
            upper,
        )
    )

    importo_fatture = 0.0
    importo_buoni = 0.0
    importo_note_credito = 0.0

    if importo_raw < 0 and ha_reso_nc and not ha_fattura:
        # Esempio strutturale: "Vs. Avere x Resi" con importo negativo.
        # È una rettifica fatture: deve ridurre IMPORTO_FATTURE e TOTALE.
        importo_fatture = importo_raw
        importo_note_credito = importo_raw
        importo_standard = importo_raw
        tipo_documento = "NOTA_CREDITO_RESO"
        num_fatture = 0
        num_buoni = 0

    elif (ha_buono or ha_acconto) and not ha_fattura:
        importo_buoni = importo_raw
        importo_standard = importo_buoni
        tipo_documento = "BUONO" if importo_buoni != 0 else "SALDO_ZERO"
        num_fatture = 0
        num_buoni = estrai_num_buoni_da_testo(upper) if importo_buoni != 0 else 0
        if num_buoni == 0 and importo_buoni != 0:
            num_buoni = 1

    else:
        importo_fatture = importo_raw
        importo_standard = importo_fatture
        tipo_documento = "FATTURA" if importo_fatture != 0 else "SALDO_ZERO"
        num_fatture = estrai_num_fatture_da_testo(upper) if importo_fatture != 0 else 0
        num_buoni = 0

        # Ft + N.C.: l'importo residuo rimane fattura, ma segnaliamo la presenza
        # della nota credito nel testo senza inventarne l'importo.
        if importo_fatture < 0:
            importo_note_credito = importo_fatture

    flag_nota_credito = bool(ha_reso_nc or importo_note_credito < 0)

    return {
        "TIPO_DOCUMENTO": tipo_documento,
        "NUM_DOCUMENTI": num_fatture + num_buoni,
        "NUM_FATTURE": num_fatture,
        "NUM_BUONI": num_buoni,
        "IMPORTO_STANDARD": importo_standard,
        "IMPORTO_FATTURE_RIGA": importo_fatture,
        "IMPORTO_BUONI_RIGA": importo_buoni,
        "IMPORTO_NOTE_CREDITO": importo_note_credito,
        "FLAG_NOTA_CREDITO": flag_nota_credito,
        "COLONNA_IMPORTO": col_importo,
        "PUGLIA_MEMO_ESCLUSO_TOTALE": False,
        "PUGLIA_IMPORTO_TESTO": puglia_importo_testo,
    }



def arricchisci_puglia_valeria(db, df_normalizzato, data_columns):
    # Non ricostruisce confini sommando importi fino al subtotale.
    # Il perimetro viene definito da arricchisci_blocchi_puglia dopo la lettura.
    out=db.copy()
    if not out.empty:
        out.loc[out['FOGLIO_ORIGINE'].map(is_puglia_sheet),'PUGLIA_GRUPPO']='DA_IDENTIFICARE'
    return out


def is_data_row_sicilia(row, txt, data_columns, mapping):
    txt = txt.upper().strip()

    if txt == "":
        return False

    if is_header_row(row, data_columns):
        return False

    if is_total_row(txt):
        return False

    cliente_col = mapping.get("cliente")

    if cliente_col is None:
        return False

    cliente = clean_text(row[cliente_col])

    if cliente == "":
        return False

    if clean_upper(cliente) in ["TOTALI", "TOTALE", "DIVISPACK", "SSC", "RIF. FATTURE"]:
        return False

    valori_importo = []

    for c in [
        mapping.get("sicilia_importo_fatture"),
        mapping.get("sicilia_buoni"),
        mapping.get("sicilia_totale"),
    ]:
        if c:
            valori_importo.extend(numeri_da_testo(row[c]))

    rif = clean_text(row[mapping.get("sicilia_rif_fatture")]) if mapping.get("sicilia_rif_fatture") else ""

    return len(valori_importo) > 0 or rif != ""

def estrai_sicilia(row, data_columns, mapping):
    col_fatture = mapping.get("sicilia_importo_fatture")
    col_rif = mapping.get("sicilia_rif_fatture")
    col_buoni = mapping.get("sicilia_buoni")
    col_totale = mapping.get("sicilia_totale")
    col_pagamento = mapping.get("sicilia_modalita_pagamento")

    importo_fatture = to_number(row[col_fatture]) if col_fatture else None
    rif_fatture = clean_text(row[col_rif]) if col_rif else ""
    periodi, anni_riferimento, dettaglio_periodi_importi, periodi_ordinabili, anni_stimati = estrai_periodi_anni_importi(rif_fatture)
    if periodi == "":
        periodi = estrai_periodi_riferimento(rif_fatture)

    buoni_raw = clean_text(row[col_buoni]) if col_buoni else ""
    valore_ssc_diretto = to_number(row[col_buoni]) if col_buoni else None

    importo_fatture = importo_fatture if importo_fatture is not None else 0.0

    # SICILIA - LOGICA SSC/BUONI CORRETTA:
    # - se la colonna SSC contiene un numero puro, quel numero è il valore buoni/SSC;
    # - se la colonna SSC contiene testo con importi negativi (es. "Vs Avere x Reso - € 1.295,46"),
    #   questi importi devono scalare i buoni/SSC, non restare fuori dal conteggio;
    # - non leggiamo numeri da descrizioni generiche se non sono importi con segno, per evitare falsi positivi.
    importo_buoni = 0.0
    if valore_ssc_diretto is not None:
        importo_buoni = valore_ssc_diretto
    else:
        buoni_raw_per_numeri = re.sub(r"-\s*€\s*", "-", buoni_raw)
        buoni_raw_per_numeri = re.sub(r"-\s+(?=\d)", "-", buoni_raw_per_numeri)
        numeri_ssc = numeri_da_testo(buoni_raw_per_numeri)
        if numeri_ssc:
            buoni_upper = buoni_raw.upper()
            contiene_logica_buoni = any(k in buoni_upper for k in [
                "BUONO", "BUONI", "SSC", "ACCONTO", "ACCONTI",
                "VS AVERE", "RESO", "N.C", "NOTA CREDITO", "NOTA DI CREDITO"
            ])
            contiene_negativi = any(n < 0 for n in numeri_ssc)

            if contiene_logica_buoni or contiene_negativi:
                importo_buoni = float(sum(numeri_ssc))

    testo_nc = f"{rif_fatture} {buoni_raw}".upper()
    flag_nota_credito = bool(
        importo_fatture < 0
        or importo_buoni < 0
        or "RESO" in testo_nc
        or "N.C" in testo_nc
        or "NOTA CREDITO" in testo_nc
        or "NOTA DI CREDITO" in testo_nc
        or "VS AVERE" in testo_nc
    )

    importo_note_credito = 0.0
    if importo_fatture < 0:
        importo_note_credito += importo_fatture
    if importo_buoni < 0:
        importo_note_credito += importo_buoni

    # Sicilia: modalità di pagamento SOLO dalla colonna finale (DATA/30-04-2026).
    # Non facciamo fallback su Rif. Fatture/SSC perché lì ci sono mesi, importi e note
    # che non sono modalità pagamento.
    modalita_pagamento = modalita_pagamento_sicilia_da_cella(row[col_pagamento]) if col_pagamento else ""

    # IMPORTANTE: per Sicilia il valore direzionale è DIVISPACK + SSC.
    # La colonna TOTALE del file può essere un residuo/valore operativo e non coincide sempre
    # con la somma contabile richiesta per dashboard fatture/buoni.
    importo_standard = importo_fatture + importo_buoni

    if importo_fatture != 0 and importo_buoni != 0:
        tipo_documento = "MISTO"
    elif importo_fatture != 0:
        tipo_documento = "FATTURA"
    elif importo_buoni != 0:
        tipo_documento = "BUONO"
    else:
        tipo_documento = "SALDO_ZERO"

    num_fatture = 1 if importo_fatture != 0 else 0
    num_buoni = 1 if importo_buoni != 0 else 0

    return {
        "TIPO_DOCUMENTO": tipo_documento,
        "NUM_DOCUMENTI": num_fatture + num_buoni,
        "NUM_FATTURE": num_fatture,
        "NUM_BUONI": num_buoni,
        "PERIODI_RIFERIMENTO": periodi,
        "ANNI_RIFERIMENTO": anni_riferimento,
        "PERIODI_ORDINABILI": periodi_ordinabili,
        "ANNI_STIMATI": anni_stimati,
        "DETTAGLIO_PERIODI_IMPORTI": dettaglio_periodi_importi,
        "MODALITA_PAGAMENTO": modalita_pagamento,
        "IMPORTO_STANDARD": importo_standard,
        "IMPORTO_FATTURE_RIGA": importo_fatture,
        "IMPORTO_BUONI_RIGA": importo_buoni,
        "IMPORTO_NOTE_CREDITO": importo_note_credito,
        "FLAG_NOTA_CREDITO": flag_nota_credito,
        "SICILIA_RIF_FATTURE": rif_fatture,
        "SICILIA_BUONI": buoni_raw,
        "SICILIA_MODALITA_PAGAMENTO": modalita_pagamento,
        "COLONNA_IMPORTO": "+".join([c for c in [col_fatture, col_buoni] if c])
    }

# ======================================================
# MOTORE PRINCIPALE
# ======================================================

def reset_mapping():
    return {
        "codice": None,
        "cliente": None,
        "documento": None,
        "importo": None,
        "totale": None,
        "fatture": None,
        "agente_header": None,

        "sicilia_importo_fatture": None,
        "sicilia_rif_fatture": None,
        "sicilia_buoni": None,
        "sicilia_totale": None,
        "sicilia_modalita_pagamento": None
    }


def pulisci_ssc(df_raw):
    df, data_columns = normalizza_colonne(df_raw)

    records = []
    debug_rows = []

    zona_attiva = None
    agente_attivo = "NON ASSEGNATO"
    cliente_padre_attivo = None
    foglio_corrente = None

    mapping_attivo = reset_mapping()

    for _, row in df.iterrows():
        txt = row_text(row, data_columns)
        tipo_riga = "IGNORATA"

        if foglio_corrente != row["FOGLIO_ORIGINE"]:
            foglio_corrente = row["FOGLIO_ORIGINE"]
            zona_attiva = str(row["FOGLIO_ORIGINE"]).strip()
            agente_attivo = "NON ASSEGNATO"
            cliente_padre_attivo = None
            mapping_attivo = reset_mapping()

        if is_zona_row(row, txt, data_columns):
            zona_attiva = pulisci_zona(txt, row["FOGLIO_ORIGINE"])
            tipo_riga = "ZONA"

        elif is_header_row(row, data_columns):
            nuovo_mapping = mappa_header(row, data_columns)

            for k, v in nuovo_mapping.items():
                if v is not None:
                    mapping_attivo[k] = v

            if nuovo_mapping.get("agente_header"):
                agente_attivo = nuovo_mapping["agente_header"]

            tipo_riga = "HEADER"

        elif is_total_row(txt):
            tipo_riga = "TOTALE"

        elif is_agente_row(row, txt, data_columns):
            agente_attivo = txt
            tipo_riga = "AGENTE"

        elif (
            is_sicilia_sheet(row["FOGLIO_ORIGINE"])
            and is_data_row_sicilia(row, txt, data_columns, mapping_attivo)
        ) or (
            not is_sicilia_sheet(row["FOGLIO_ORIGINE"])
            and is_data_row(row, txt, data_columns, mapping_attivo)
        ):
            codice_cliente = estrai_codice_cliente(
                row,
                data_columns,
                mapping_attivo.get("codice"),
            )

            # Se la colonna codice è nota ma vuota, non cerchiamo codici in tutta la riga:
            # alcuni saldi senza codice hanno importi che potrebbero essere scambiati per codice cliente.
            if codice_cliente is None and mapping_attivo.get("codice") is None:
                codice_cliente = estrai_codice_cliente(row, data_columns)

            cliente_originale = estrai_cliente(
                row,
                data_columns,
                mapping_attivo.get("cliente"),
            )

            if cliente_originale == "":
                cliente_originale = estrai_cliente(row, data_columns)

            flag_plus = str(cliente_originale).strip().startswith("+")

            cliente_clean = (
                str(cliente_originale)
                .replace("+", "")
                .strip()
            )

            if not flag_plus and cliente_clean != "":
                cliente_padre_attivo = cliente_clean
                cliente_padre = cliente_clean
            else:
                cliente_padre = cliente_padre_attivo

            documento = estrai_documento(
                row,
                data_columns,
                mapping_attivo.get("documento"),
            )

            documento_integrale = sorgente_documentale(row, mapping_attivo)

            if is_sicilia_sheet(row["FOGLIO_ORIGINE"]):
                dati_riga = estrai_sicilia(row, data_columns, mapping_attivo)

                tipo_documento = dati_riga["TIPO_DOCUMENTO"]
                numero_documenti = dati_riga["NUM_DOCUMENTI"]
                periodi_riferimento = dati_riga["PERIODI_RIFERIMENTO"]
                anni_riferimento = dati_riga.get("ANNI_RIFERIMENTO", "")
                periodi_ordinabili = dati_riga.get("PERIODI_ORDINABILI", "")
                anni_stimati = dati_riga.get("ANNI_STIMATI", "")
                dettaglio_periodi_importi = dati_riga["DETTAGLIO_PERIODI_IMPORTI"]
                modalita_pagamento = dati_riga["MODALITA_PAGAMENTO"]
                importo = dati_riga["IMPORTO_STANDARD"]
                colonna_importo = dati_riga["COLONNA_IMPORTO"]
                importo_fatture_riga = dati_riga["IMPORTO_FATTURE_RIGA"]
                importo_buoni_riga = dati_riga["IMPORTO_BUONI_RIGA"]
                importo_note_credito = dati_riga["IMPORTO_NOTE_CREDITO"]
                flag_nota_credito = dati_riga["FLAG_NOTA_CREDITO"]
                num_fatture = dati_riga["NUM_FATTURE"]
                num_buoni = dati_riga["NUM_BUONI"]
                sicilia_rif = dati_riga["SICILIA_RIF_FATTURE"]
                sicilia_buoni = dati_riga["SICILIA_BUONI"]
                sicilia_pag = dati_riga["SICILIA_MODALITA_PAGAMENTO"]
                periodi_dettaglio = estrai_dettaglio_periodi_documenti(
                    sicilia_rif,
                    num_fatture=num_fatture,
                    num_buoni=num_buoni,
                    dettaglio_importi=dettaglio_periodi_importi,
                )
                puglia_memo_escluso = False
                puglia_importo_testo = False

            elif is_puglia_sheet(row["FOGLIO_ORIGINE"]):
                dati_riga = estrai_puglia(
                    row,
                    data_columns,
                    mapping_attivo,
                    codice_cliente,
                    documento,
                    txt,
                )

                tipo_documento = dati_riga["TIPO_DOCUMENTO"]
                numero_documenti = dati_riga["NUM_DOCUMENTI"]
                importo = dati_riga["IMPORTO_STANDARD"]
                colonna_importo = dati_riga["COLONNA_IMPORTO"]
                importo_fatture_riga = dati_riga["IMPORTO_FATTURE_RIGA"]
                importo_buoni_riga = dati_riga["IMPORTO_BUONI_RIGA"]
                importo_note_credito = dati_riga["IMPORTO_NOTE_CREDITO"]
                flag_nota_credito = dati_riga["FLAG_NOTA_CREDITO"]
                num_fatture = dati_riga["NUM_FATTURE"]
                num_buoni = dati_riga["NUM_BUONI"]
                puglia_memo_escluso = dati_riga.get("PUGLIA_MEMO_ESCLUSO_TOTALE", False)
                puglia_importo_testo = dati_riga.get("PUGLIA_IMPORTO_TESTO", False)

                periodi_riferimento, anni_riferimento, dettaglio_periodi_importi, periodi_ordinabili, anni_stimati = estrai_periodi_standard_da_riga(
                    row,
                    mapping_attivo,
                    importo,
                )
                if periodi_riferimento == "":
                    periodi_riferimento = estrai_periodi_riferimento(documento_integrale or txt)

                periodi_dettaglio = estrai_dettaglio_periodi_documenti(
                    documento_integrale or txt,
                    num_fatture=num_fatture,
                    num_buoni=num_buoni,
                    dettaglio_importi=dettaglio_periodi_importi,
                )
                modalita_pagamento = estrai_modalita_pagamento(documento_integrale or txt)

                sicilia_rif = ""
                sicilia_buoni = ""
                sicilia_pag = ""

            else:
                dati_riga = estrai_importi_standard(
                    row,
                    data_columns,
                    mapping_attivo,
                    codice_cliente,
                    documento,
                    txt,
                )

                tipo_documento = dati_riga["TIPO_DOCUMENTO"]
                numero_documenti = dati_riga["NUM_DOCUMENTI"]

                importo = dati_riga["IMPORTO_STANDARD"]
                colonna_importo = dati_riga["COLONNA_IMPORTO"]
                importo_fatture_riga = dati_riga["IMPORTO_FATTURE_RIGA"]
                importo_buoni_riga = dati_riga["IMPORTO_BUONI_RIGA"]

                periodi_riferimento, anni_riferimento, dettaglio_periodi_importi, periodi_ordinabili, anni_stimati = estrai_periodi_standard_da_riga(
                    row,
                    mapping_attivo,
                    importo,
                )
                if periodi_riferimento == "":
                    periodi_riferimento = estrai_periodi_riferimento(clean_text(row[mapping_attivo.get("importo")]) if mapping_attivo.get("importo") else txt)
                modalita_pagamento = estrai_modalita_pagamento(txt)
                importo_note_credito = dati_riga["IMPORTO_NOTE_CREDITO"]
                flag_nota_credito = dati_riga["FLAG_NOTA_CREDITO"]
                num_fattures = dati_riga["NUM_FATTURE"]
                num_fatture = num_fattures
                num_buoni = dati_riga["NUM_BUONI"]

                periodi_dettaglio = estrai_dettaglio_periodi_documenti(
                    documento_integrale or txt,
                    num_fatture=num_fatture,
                    num_buoni=num_buoni,
                    dettaglio_importi=dettaglio_periodi_importi,
                )

                sicilia_rif = ""
                sicilia_buoni = ""
                sicilia_pag = ""
                puglia_memo_escluso = False
                puglia_importo_testo = False

            # Manteniamo anche le righe cliente con importo pari a 0:
            # servono per capire chi NON sta acquistando / chi va richiamato.
            importo = importo if importo is not None else 0.0
            importo_fatture_riga = importo_fatture_riga if importo_fatture_riga is not None else 0.0
            importo_buoni_riga = importo_buoni_riga if importo_buoni_riga is not None else 0.0
            importo_note_credito = importo_note_credito if importo_note_credito is not None else 0.0

            if cliente_clean != "":
                records.append({
                    "FOGLIO_ORIGINE": row["FOGLIO_ORIGINE"],
                    "ZONA": zona_attiva,
                    "AGENTE": agente_attivo,
                    "CODICE_CLIENTE": codice_cliente,
                    "CLIENTE_ORIGINALE": cliente_originale,
                    "CLIENTE": cliente_clean,
                    "CLIENTE_CLEAN": cliente_clean,
                    "FLAG_PLUS": flag_plus,
                    "CLIENTE_PADRE": cliente_padre,
                    "DOCUMENTO_RAW": documento,
                    "DOCUMENTO_ORIGINALE": documento_integrale,
                    "TIPO_DOCUMENTO": tipo_documento,
                    "NUM_DOCUMENTI": numero_documenti,
                    "NUM_FATTURE": num_fatture,
                    "NUM_BUONI": num_buoni,
                    "PERIODI_RIFERIMENTO": periodi_riferimento,
                    "ANNI_RIFERIMENTO": anni_riferimento,
                    "PERIODI_ORDINABILI": periodi_ordinabili,
                    "ANNI_STIMATI": anni_stimati,
                    "DETTAGLIO_PERIODI_IMPORTI": dettaglio_periodi_importi,
                    "PERIODI_DETTAGLIO": periodi_dettaglio,
                    "MODALITA_PAGAMENTO": modalita_pagamento,
                    "IMPORTO_STANDARD": importo,
                    "FLAG_IMPORTO_ZERO": abs(float(importo)) < 0.0001,
                    "IMPORTO_FATTURE_RIGA": importo_fatture_riga,
                    "IMPORTO_BUONI_RIGA": importo_buoni_riga,
                    "IMPORTO_NOTE_CREDITO": importo_note_credito,
                    "FLAG_NOTA_CREDITO": flag_nota_credito,
                    "COLONNA_IMPORTO": colonna_importo,
                    "SICILIA_RIF_FATTURE": sicilia_rif,
                    "SICILIA_BUONI": sicilia_buoni,
                    "SICILIA_MODALITA_PAGAMENTO": sicilia_pag,
                    "PUGLIA_MEMO_ESCLUSO_TOTALE": puglia_memo_escluso,
                    "PUGLIA_IMPORTO_TESTO": puglia_importo_testo,
                    "PUGLIA_GRUPPO": "",
                    "RIGA_SHEET": row["RIGA_SHEET"],
                    "RIGA_GLOBALE": row["RIGA_GLOBALE"],
                    "TESTO_RIGA": txt,
                })

            tipo_riga = "DATI"

        debug_row = {
            "TIPO_RIGA": tipo_riga,
            "FOGLIO_CORRENTE": foglio_corrente,
            "ZONA_ATTIVA": zona_attiva,
            "AGENTE_ATTIVO": agente_attivo,
            "CLIENTE_PADRE_ATTIVO": cliente_padre_attivo,
            "TESTO_RIGA": txt,
            "RIGA_SHEET": row["RIGA_SHEET"],
            "RIGA_GLOBALE": row["RIGA_GLOBALE"],
        }

        for c in data_columns:
            debug_row[c] = row[c]

        debug_rows.append(debug_row)

    db = pd.DataFrame(records)
    debug_df = pd.DataFrame(debug_rows)

    # Puglia ha un blocco strutturale "Totale Clienti VALERIA":
    # lo identifichiamo tramite il subtotale, senza dipendere da righe fisse.
    db = arricchisci_puglia_valeria(db, df, data_columns)

    return db, debug_df, data_columns




# ======================================================
# CORREZIONI DI QUADRATURA
# ======================================================
# Le correzioni non "forzano" lo stato OK: correggono la singola posizione.
# La quadratura diventa OK solo quando i totali tornano matematicamente.
CLASSIFICATION_RULES_FILE = Path(__file__).with_name("divispack_correzioni_quadratura.json")



def carica_correzioni_quadratura():
    return remote_state_get("quadrature_corrections", {}) or {}





def salva_correzioni_quadratura(data):
    if not can_edit():
        st.error("Modifica non autorizzata."); return False
    return remote_state_set("quadrature_corrections", data)




def applica_correzioni_quadratura(db):
    if db is None or db.empty:
        return db
    out=db.copy(); baseline=st.session_state.get("current_baseline_hash","")
    rules=carica_correzioni_quadratura()
    st.session_state["__legacy_corrections"] = sum(1 for x in rules.values() if not x.get("baseline_hash") and not x.get("legacy_migrated_to"))
    for rule in rules.values():
        if not baseline or rule.get("baseline_hash") != baseline:
            continue
        mask=out["ID_POSIZIONE_SSC"].astype(str).eq(str(rule.get("id_posizione","")))
        out.loc[mask,"IMPORTO_FATTURE_RIGA"]=float(rule["fatture"])
        out.loc[mask,"IMPORTO_BUONI_RIGA"]=float(rule["buoni"])
        out.loc[mask,"CORREZIONE_QUADRATURA"]=True
    return ricalcola_importi_da_editor(out)



def salva_correzione_posizione(row, fatture, buoni, nota=""):
    if not can_edit() or not clean_text(nota):
        st.error("Servono autorizzazione e motivazione della correzione."); return False
    baseline = st.session_state.get("current_baseline_hash", "")
    rid = clean_text(row.get("ID_POSIZIONE_SSC", ""))
    if not baseline or not rid:
        st.error("Situazione o posizione non identificata."); return False
    rules = carica_correzioni_quadratura()
    rules[baseline+":"+rid] = {"baseline_hash":baseline,"id_posizione":rid,
        "fatture":round(float(fatture),2),"buoni":round(float(buoni),2),"nota":clean_text(nota),
        "fatture_file":float(row.get("IMPORTO_FATTURE_RIGA",0)),"buoni_file":float(row.get("IMPORTO_BUONI_RIGA",0)),
        "utente":st.session_state["current_user"]["username"],"salvato_il":datetime.now().isoformat(),
        "cliente":clean_text(row.get("CLIENTE","")),"zona":clean_text(row.get("ZONA",""))}
    return salva_correzioni_quadratura(rules)



def elimina_correzione_posizione(rid):
    if not can_edit():
        return False
    rules=carica_correzioni_quadratura()
    rules.pop(st.session_state.get("current_baseline_hash","")+":"+str(rid),None)
    return salva_correzioni_quadratura(rules)


# ======================================================
# QUADRATURA EXCEL / CONTROLLO CONTABILE
# ======================================================

def _numeri_riga_totale_excel(row_values):
    out = []
    for v in row_values:
        n = to_number(v)
        if n is not None:
            out.append(float(n))
    return out


def _sicilia_totali_excel_specifici(df_sheet):
    """Legge i totali Sicilia usando le colonne DIVISPACK e SSC dell'ultimo
    blocco intestato, invece dei primi due numeri della riga totale.
    """
    data_columns = list(df_sheet.columns)
    mapping = reset_mapping()
    last_values = None

    for _, row in df_sheet.iterrows():
        txt = " ".join(
            clean_text(v) for v in row.tolist()
            if clean_text(v) != ""
        ).upper()

        if is_header_row(row, data_columns):
            detected = mappa_header(row, data_columns)
            if detected.get("sicilia_importo_fatture") is not None:
                mapping = detected
            continue

        if not is_total_row(txt):
            continue

        col_f = mapping.get("sicilia_importo_fatture")
        col_b = mapping.get("sicilia_buoni")

        fatture = to_number(row[col_f]) if col_f is not None else None
        buoni = to_number(row[col_b]) if col_b is not None else None

        # Alcune celle SSC possono essere testo con segno/importo.
        if buoni is None and col_b is not None:
            nums = numeri_da_testo(row[col_b])
            if nums:
                buoni = float(sum(nums))

        if fatture is not None or buoni is not None:
            last_values = (
                float(buoni or 0),
                float(fatture or 0),
            )

    return last_values



def _puglia_totali_excel_specifici(df_sheet):
    """Legge separatamente Totale Puglia principale e Totale Clienti VALERIA."""
    totale_principale = None
    totale_valeria = None

    for _, row in df_sheet.iterrows():
        txt = " ".join(
            clean_text(v) for v in row.tolist()
            if clean_text(v) != ""
        ).upper()

        nums = _numeri_riga_totale_excel(row.tolist())
        if not nums:
            continue

        if "TOTALE CLIENTI VALERIA" in txt:
            totale_valeria = float(nums[-1])
        elif "TOTALI AL" in txt and "VALERIA" not in txt:
            totale_principale = float(nums[-1])

    if totale_principale is None and totale_valeria is None:
        return None
    return totale_principale, totale_valeria

def _motivo_quadratura(delta_buoni, delta_fatture, delta_totale, nota):
    parts = []
    if delta_buoni is not None and abs(delta_buoni) >= 0.05:
        parts.append(f"Buoni/SSC: scostamento {format_euro(delta_buoni)}")
    if delta_fatture is not None and abs(delta_fatture) >= 0.05:
        parts.append(f"Fatture: scostamento {format_euro(delta_fatture)}")
    if not parts and delta_totale is not None and abs(delta_totale) >= 0.05:
        parts.append(f"Totale: scostamento {format_euro(delta_totale)}")
    if not parts:
        parts.append(nota)
    return " | ".join(parts)


def calcola_quadratura_excel(file_obj, db, sheets=None):
    """Confronta i valori ricostruiti dal parser con i totali scritti nell'Excel.

    Lo stato OK è esclusivamente matematico: nessun utente può forzarlo.
    Sicilia usa le colonne DIVISPACK e SSC del suo layout dedicato.
    """
    if sheets is None:
        try:
            sheets = pd.read_excel(file_obj, sheet_name=None, header=None)
        except Exception:
            return pd.DataFrame()

    righe = []
    db = db.copy() if db is not None else pd.DataFrame()

    for sheet_name, df_sheet in sheets.items():
        if df_sheet is None or df_sheet.empty:
            continue

        total_rows = []
        for idx, row in df_sheet.iterrows():
            txt = " ".join([
                clean_text(v) for v in row.tolist()
                if clean_text(v) != ""
            ]).upper()
            if "TOTAL" in txt or "TOTALE" in txt or "TOTALI" in txt:
                nums = _numeri_riga_totale_excel(row.tolist())
                if nums:
                    total_rows.append((idx, txt, nums))

        if total_rows:
            idx_tot, txt_tot, nums = total_rows[-1]
        else:
            idx_tot, txt_tot, nums = None, "", []

        df_sheet_parser = (
            db[db["FOGLIO_ORIGINE"].astype(str) == str(sheet_name)]
            if not db.empty and "FOGLIO_ORIGINE" in db.columns
            else pd.DataFrame()
        )
        parser_totale = float(df_sheet_parser["IMPORTO_STANDARD"].sum()) if not df_sheet_parser.empty else 0.0
        parser_fatture = float(df_sheet_parser["IMPORTO_FATTURE_RIGA"].sum()) if not df_sheet_parser.empty else 0.0
        parser_buoni = float(df_sheet_parser["IMPORTO_BUONI_RIGA"].sum()) if not df_sheet_parser.empty else 0.0

        excel_buoni = None
        excel_fatture = None
        excel_da_classificare = None
        nota = ""
        regola = "STANDARD"

        excel_puglia_valeria = None
        excel_puglia_principale_formula = None
        excel_puglia_principale_corretto = None
        excel_puglia_valeria_corretto = None
        puglia_rettifiche_testo_principale = 0.0
        puglia_rettifiche_testo_valeria = 0.0
        tool_puglia_valeria = None
        delta_puglia_valeria = None

        if is_sicilia_sheet(sheet_name):
            regola = "SICILIA_DIVISPACK_SSC"
            specifici = _sicilia_totali_excel_specifici(df_sheet)
            if specifici is not None:
                excel_buoni, excel_fatture = specifici
                nota = "Sicilia: totale letto dalle colonne dedicate DIVISPACK e SSC."
            else:
                nota = "Sicilia: non trovo un totale leggibile nelle colonne DIVISPACK/SSC."

        elif is_puglia_sheet(sheet_name):
            regola = "PUGLIA_PRINCIPALE_PLUS_VALERIA_RETTIFICHE_TESTO"
            specifici = _puglia_totali_excel_specifici(df_sheet)

            if specifici is not None:
                excel_puglia_principale_formula, excel_puglia_valeria = specifici

                if "PUGLIA_GRUPPO" in df_sheet_parser.columns:
                    valeria_mask = (
                        df_sheet_parser["PUGLIA_GRUPPO"]
                        .astype(str)
                        .str.upper()
                        .eq("VALERIA")
                    )
                else:
                    valeria_mask = pd.Series(False, index=df_sheet_parser.index)

                tool_puglia_valeria = float(
                    df_sheet_parser.loc[valeria_mask, "IMPORTO_STANDARD"].sum()
                )
                parser_principale = float(
                    df_sheet_parser.loc[~valeria_mask, "IMPORTO_STANDARD"].sum()
                )

                # Excel SUM ignora celle testuali come "- € 4.495,38".
                # Non ignoriamo l'importo: lo leggiamo, lo classifichiamo e lo
                # aggiungiamo come rettifica al totale formula del foglio.
                if "PUGLIA_IMPORTO_TESTO" in df_sheet_parser.columns:
                    text_mask = df_sheet_parser["PUGLIA_IMPORTO_TESTO"].fillna(False).astype(bool)
                    puglia_rettifiche_testo_principale = float(
                        df_sheet_parser.loc[text_mask & ~valeria_mask, "IMPORTO_STANDARD"].sum()
                    )
                    puglia_rettifiche_testo_valeria = float(
                        df_sheet_parser.loc[text_mask & valeria_mask, "IMPORTO_STANDARD"].sum()
                    )

                excel_puglia_principale_corretto = (
                    float(excel_puglia_principale_formula or 0.0)
                    + puglia_rettifiche_testo_principale
                )
                excel_puglia_valeria_corretto = (
                    float(excel_puglia_valeria or 0.0)
                    + puglia_rettifiche_testo_valeria
                )

                # Per il motore di quadratura il valore atteso è quello corretto,
                # non il SUM Excel che salta le celle testo.
                excel_da_classificare = excel_puglia_principale_corretto
                parser_totale = parser_principale

                nota = (
                    "Puglia: totale principale e VALERIA controllati separatamente. "
                    "Gli importi numerici memorizzati come testo nel file vengono "
                    "rettificati perché la formula SUM di Excel li ignora."
                )
            else:
                nota = "Puglia: totali principale/VALERIA non leggibili."

        elif len(nums) >= 2:
            excel_buoni = float(nums[0])
            excel_fatture = float(nums[1])
            nota = "Riga totale con colonne BUONI/SSC e FATTURE."
        elif len(nums) == 1:
            excel_da_classificare = float(nums[0])
            nota = "Riga totale con un solo importo: serve regola dedicata del foglio."
            regola = "TOTALE_UNICO"
        else:
            nota = "Nessuna riga Totali leggibile nel foglio."
            regola = "NESSUN_TOTALE"

        delta_buoni = None if excel_buoni is None else parser_buoni - excel_buoni
        delta_fatture = None if excel_fatture is None else parser_fatture - excel_fatture

        if excel_buoni is not None and excel_fatture is not None:
            delta_totale = parser_totale - (excel_buoni + excel_fatture)
            is_ok = abs(delta_buoni) < 0.05 and abs(delta_fatture) < 0.05

        elif is_puglia_sheet(sheet_name) and excel_da_classificare is not None:
            delta_totale = parser_totale - excel_da_classificare
            if excel_puglia_valeria_corretto is not None and tool_puglia_valeria is not None:
                delta_puglia_valeria = tool_puglia_valeria - excel_puglia_valeria_corretto
                is_ok = (
                    abs(delta_totale) < 0.05
                    and abs(delta_puglia_valeria) < 0.05
                )
            else:
                is_ok = False

        elif excel_da_classificare is not None:
            delta_totale = parser_totale - excel_da_classificare
            is_ok = abs(delta_totale) < 0.05

        else:
            delta_totale = None
            is_ok = False

        if is_ok:
            motivo = "Quadratura matematica corretta."
        elif is_puglia_sheet(sheet_name) and delta_puglia_valeria is not None:
            parti = []
            if delta_totale is not None and abs(delta_totale) >= 0.05:
                parti.append(f"Puglia principale: scostamento {format_euro(delta_totale)}")
            if abs(delta_puglia_valeria) >= 0.05:
                parti.append(f"VALERIA: scostamento {format_euro(delta_puglia_valeria)}")
            motivo = " | ".join(parti) if parti else nota
        else:
            motivo = _motivo_quadratura(
                delta_buoni, delta_fatture, delta_totale, nota
            )

        righe.append({
            "FOGLIO": sheet_name,
            "RIGA_TOTALE_EXCEL": idx_tot,
            "TESTO_TOTALE_EXCEL": txt_tot[:180],
            "REGOLA_QUADRATURA": regola,
            "EXCEL_BUONI_SSC": excel_buoni,
            "EXCEL_FATTURE": excel_fatture,
            "EXCEL_TOTALE_DA_CLASSIFICARE": excel_da_classificare,
            "TOOL_BUONI_SSC": parser_buoni,
            "TOOL_FATTURE": parser_fatture,
            "TOOL_TOTALE": parser_totale,
            "DELTA_BUONI_SSC": delta_buoni,
            "DELTA_FATTURE": delta_fatture,
            "DELTA_TOTALE": delta_totale,
            "EXCEL_PUGLIA_PRINCIPALE_FORMULA": excel_puglia_principale_formula,
            "PUGLIA_RETTIFICHE_TESTO_PRINCIPALE": puglia_rettifiche_testo_principale,
            "EXCEL_PUGLIA_PRINCIPALE_CORRETTO": excel_puglia_principale_corretto,
            "EXCEL_PUGLIA_VALERIA": excel_puglia_valeria,
            "PUGLIA_RETTIFICHE_TESTO_VALERIA": puglia_rettifiche_testo_valeria,
            "EXCEL_PUGLIA_VALERIA_CORRETTO": excel_puglia_valeria_corretto,
            "TOOL_PUGLIA_VALERIA": tool_puglia_valeria,
            "DELTA_PUGLIA_VALERIA": delta_puglia_valeria,
            "ESITO": "OK" if is_ok else "DA_VERIFICARE",
            "MOTIVO": motivo,
            "NOTA": nota,
        })

    return pd.DataFrame(righe)


# ======================================================
# QUADRATURA CHIARA — DIAGNOSTICA, NON RICERCA PER IMPORTO
# ======================================================
def quad_number(value):
    """Numero finito o None: un valore assente non viene inventato come zero."""
    try:
        number = to_number(value)
        return float(number) if number is not None and math.isfinite(float(number)) else None
    except (ValueError, TypeError, OverflowError):
        return None


def quad_sheet(sheets, name):
    matches = [v for k, v in (sheets or {}).items() if canonical_sheet(k) == canonical_sheet(name)]
    return matches[0] if len(matches) == 1 else None


def quad_source_cells(row, sheet):
    """Mostra i valori originali. Confronta solo celle con provenienza esplicita.

    COLONNA_IMPORTO è una traccia prodotta dal parser, non una prova che il
    parser abbia scelto tutte e sole le celle corrette. Non inferiamo colonne
    in base alla vicinanza degli importi.
    """
    records = []
    if sheet is None:
        return pd.DataFrame(), None, "Foglio originale non disponibile."
    rn = quad_number(row.get('RIGA_SHEET'))
    if rn is None or not rn.is_integer() or not 0 <= rn < len(sheet):
        return pd.DataFrame(), None, "Riga originale non identificabile in modo univoco."
    rn = int(rn)
    spec = clean_text(row.get('COLONNA_IMPORTO', '')).replace(' ', '')
    valid = bool(re.fullmatch(r'COL_\d+(?:\+COL_\d+)*', spec))
    cols = [int(v) - 1 for v in re.findall(r'COL_(\d+)', spec)] if valid else []
    valid = valid and len(cols) == len(set(cols)) and all(0 <= c < len(sheet.columns) for c in cols)
    formulas = sheet.attrs.get('ssc_formulas', {})
    amounts = []
    for c, raw in enumerate(sheet.iloc[rn].tolist()):
        selected = valid and c in cols
        addr = excel_col(c + 1) + str(rn + 1)
        if not selected and not clean_text(raw) and addr not in formulas:
            continue
        number = quad_number(raw)
        if selected:
            amounts.append(number)
        records.append({
            'Cella Excel': addr,
            'Contenuto originale': clean_text(raw),
            'Formula originale': formulas.get(addr, ''),
            'Usata per il totale parser': 'Sì' if selected else 'No / non tracciata',
            'Valore numerico letto': number if selected else None,
        })
    if not valid:
        return pd.DataFrame(records), None, "Provenienza delle celle importo incompleta: differenza di lettura N/D."
    if len(amounts) != len(cols) or any(n is None for n in amounts):
        return pd.DataFrame(records), None, "Almeno una cella tracciata non è numerica: differenza di lettura N/D."
    return pd.DataFrame(records), round(sum(amounts), 2), (
        "Confronto limitato alle celle importo tracciate. Non certifica da solo la classificazione fatture/buoni né eventuali celle omesse."
    )


@st.cache_data(max_entries=8, show_spinner=False)
def quad_position_checks(db_parser, db_corretto, sheet_name, sheet, source_metadata=""):
    """Dati letti, differenza misurabile e rettifiche: nessun ranking euristico."""
    if db_parser is None or db_parser.empty:
        return pd.DataFrame()
    base = db_parser[db_parser['FOGLIO_ORIGINE'].map(canonical_sheet).eq(canonical_sheet(sheet_name))].copy()
    if base.empty:
        return pd.DataFrame()
    if db_corretto is None:
        current = base
    elif db_corretto.empty or 'FOGLIO_ORIGINE' not in db_corretto:
        current = pd.DataFrame()
    else:
        current = db_corretto[db_corretto['FOGLIO_ORIGINE'].map(canonical_sheet).eq(canonical_sheet(sheet_name))].copy()
    current_map = {}
    for _, row in current.iterrows():
        sid = clean_text(row.get('ID_POSIZIONE_SSC', ''))
        if sid:
            current_map.setdefault(sid, []).append(row)
    records = []
    for _, row in base.iterrows():
        sid = clean_text(row.get('ID_POSIZIONE_SSC', ''))
        _, source_total, source_note = quad_source_cells(row, sheet)
        parsed_total = quad_number(row.get('IMPORTO_STANDARD'))
        delta = round(parsed_total - source_total, 2) if parsed_total is not None and source_total is not None else None
        candidates = current_map.get(sid, []) if sid else []
        same_row = [r for r in candidates if quad_number(r.get('RIGA_SHEET')) == quad_number(row.get('RIGA_SHEET'))]
        chosen = same_row[0] if len(same_row) == 1 else (candidates[0] if len(candidates) == 1 else None)
        ff, bf = quad_number(row.get('IMPORTO_FATTURE_RIGA')), quad_number(row.get('IMPORTO_BUONI_RIGA'))
        fc = quad_number(chosen.get('IMPORTO_FATTURE_RIGA')) if chosen is not None else None
        bc = quad_number(chosen.get('IMPORTO_BUONI_RIGA')) if chosen is not None else None
        tc = quad_number(chosen.get('IMPORTO_STANDARD')) if chosen is not None else None
        flag = str(chosen.get('CORREZIONE_QUADRATURA', '')).lower() in ('true', '1') if chosen is not None else False
        changed = any(a is not None and b is not None and abs(a-b) >= .005 for a,b in ((ff,fc),(bf,bc),(parsed_total,tc)))
        correction = 'Rettifica già applicata' if flag or changed else ('Nessuna rettifica rilevata' if chosen is not None else 'Confronto rettifiche non disponibile')
        if delta is None:
            status = 'Confronto lettura N/D'
            reason = source_note
        elif abs(delta) < .005:
            status = 'Importo letto coincidente'
            reason = 'Il totale parser coincide con le celle importo tracciate. Nessuna differenza di lettura misurata su queste celle.'
        else:
            status = 'Differenza di lettura misurata'
            reason = 'Totale parser meno celle importo tracciate: ' + format_euro(delta) + '. Verificare selezione celle e trasformazioni del parser.'
        if flag or changed:
            reason += ' La rettifica del tool è distinta dall’importo del file originale; non cancella l’evidenza sul sorgente.'
        rn = quad_number(row.get('RIGA_SHEET'))
        records.append({
            'ID_POSIZIONE_SSC': sid, 'Cliente': clean_text(row.get('CLIENTE')),
            'Codice cliente': clean_text(row.get('CODICE_CLIENTE')),
            'Riga Excel': int(rn)+1 if rn is not None else None,
            'Importo celle tracciate': source_total, 'Totale parser': parsed_total,
            'Differenza lettura': delta,
            'Fatture lette': ff, 'Buoni letti': bf,
            'Fatture dopo rettifiche': fc, 'Buoni dopo rettifiche': bc,
            'Totale dopo rettifiche': tc, 'Esito lettura': status,
            'Stato rettifica': correction, 'Spiegazione': reason,
        })
    return pd.DataFrame(records)


def quad_balance_components(qrow):
    """Riferimenti aggregati del controllo esistente, senza alterarli."""
    b, f = quad_number(qrow.get('EXCEL_BUONI_SSC')), quad_number(qrow.get('EXCEL_FATTURE'))
    rows = []
    for label, ref, tool in (
        ('Buoni / SSC', b, quad_number(qrow.get('TOOL_BUONI_SSC'))),
        ('Fatture', f, quad_number(qrow.get('TOOL_FATTURE'))),
    ):
        if ref is not None:
            rows.append({'Componente': label, 'Riferimento del controllo': ref,
                         'Totale parser': tool, 'Differenza': round(tool-ref,2) if tool is not None else None})
    ref = b+f if b is not None and f is not None else quad_number(qrow.get('EXCEL_TOTALE_DA_CLASSIFICARE'))
    tool = quad_number(qrow.get('TOOL_TOTALE'))
    puglia = clean_text(qrow.get('REGOLA_QUADRATURA')).startswith('PUGLIA')
    rows.append({'Componente': 'Totale Puglia principale' if puglia else 'Totale foglio',
                 'Riferimento del controllo': ref, 'Totale parser': tool,
                 'Differenza': round(tool-ref,2) if ref is not None and tool is not None else None})
    if puglia:
        vr = quad_number(qrow.get('EXCEL_PUGLIA_VALERIA_CORRETTO'))
        if vr is None: vr = quad_number(qrow.get('EXCEL_PUGLIA_VALERIA'))
        vt = quad_number(qrow.get('TOOL_PUGLIA_VALERIA'))
        if vr is not None or vt is not None:
            rows.append({'Componente': 'Blocco VALERIA', 'Riferimento del controllo': vr,
                         'Totale parser': vt, 'Differenza': round(vt-vr,2) if vt is not None and vr is not None else None})
    return pd.DataFrame(rows)


def quad_display(df):
    """N/D resta esplicito nelle colonne monetarie della diagnostica."""
    out = prepara_display(df)
    cols = [c for c in df.columns if is_money_column_name(c) or c in ('Riferimento del controllo',)]
    for c in cols:
        out[c] = df[c].map(lambda v: format_euro(quad_number(v)) if quad_number(v) is not None else 'N/D')
    return out


def render_quadratura_excel(quadratura_df, db_parser=None, sheets=None, db_corretto=None, read_only=False):
    st.header('Quadratura Excel')
    st.caption('Confronto dei totali del foglio: non è un elenco di clienti sbagliati. OK indica la quadratura prevista dalla regola del foglio, non una certificazione di tutte le righe.')
    if quadratura_df is None or quadratura_df.empty:
        st.warning('Quadratura non disponibile.'); return
    q = quadratura_df.copy()
    ok_count = int(q['ESITO'].eq('OK').sum())
    a,b = st.columns(2)
    a.metric('Fogli con quadratura OK', f'{ok_count}/{len(q)}')
    b.metric('Controlli da spiegare', len(q)-ok_count)
    st.info('Le differenze qui sono aggregate: totale ricostruito meno riferimento del foglio. Un importo cliente può essere corretto anche quando il totale del foglio non quadra.')
    maincols = [c for c in ['FOGLIO','ESITO','MOTIVO','DELTA_BUONI_SSC','DELTA_FATTURE','DELTA_TOTALE','DELTA_PUGLIA_VALERIA'] if c in q]
    st.dataframe(prepara_display(q[maincols]), width='stretch', hide_index=True)
    if not st.checkbox('Apri spiegazione e confronto con il file', key='quad_open_analysis'):
        return
    st.subheader('Perché questo controllo non quadra?')
    names = q.sort_values('ESITO', kind='stable')['FOGLIO'].astype(str).tolist()
    key = 'quadratura_foglio_analisi'
    if st.session_state.get(key) not in names: st.session_state[key] = names[0]
    selected_sheet = st.selectbox('Foglio / zona', names, key=key)
    qrow = q[q['FOGLIO'].astype(str).eq(selected_sheet)].iloc[0]
    sheet = quad_sheet(sheets, selected_sheet)
    scope = hashlib.sha256((clean_text(st.session_state.get('current_baseline_hash'))+'|'+selected_sheet).encode()).hexdigest()[:16]
    st.write('**Differenza = totale del parser − riferimento del controllo.** Positivo: il parser contiene di più. Negativo: contiene di meno.')
    st.dataframe(quad_display(quad_balance_components(qrow)), width='stretch', hide_index=True)
    st.write('**Risultato del controllo:** ' + clean_text(qrow.get('MOTIVO')))
    st.caption('Regola applicata: ' + clean_text(qrow.get('REGOLA_QUADRATURA')) + '. ' + clean_text(qrow.get('NOTA')))
    if clean_text(qrow.get('REGOLA_QUADRATURA')).startswith('PUGLIA'):
        st.caption('Il riferimento Puglia può includere rettifiche per celle numeriche memorizzate come testo. Non coincide necessariamente con il totale originale della formula; i valori distinti sono nei dettagli tecnici.')
    if st.checkbox('Mostra riferimenti e valori tecnici del controllo', key='qtech_'+scope):
        st.dataframe(prepara_display(pd.DataFrame([qrow])), width='stretch', hide_index=True)

    proofs = pd.DataFrame()
    if sheet is not None and db_parser is not None and not db_parser.empty and sheet.attrs.get('ssc_formulas'):
        # Solo il foglio selezionato, solo quando l’operatore apre l’analisi.
        proofs = righe_fuori_formula({selected_sheet:sheet}, db_parser)
        if not proofs.empty:
            st.warning('Evidenza nel file: alcune celle cliente sono fuori dagli intervalli di formule di totale. Verificare se le esclusioni sono volute; non azzerare gli importi per far tornare il totale.')
            st.dataframe(prepara_display(proofs), width='stretch', hide_index=True)
            st.caption('Sono prove del perimetro di formule SUM semplici, non una dimostrazione automatica della causa di ogni differenza. Il controllo può non coprire formule complesse.')
        else:
            st.caption('Nessuna esclusione rilevata nelle formule SUM semplici analizzabili. Questo non dimostra che il foglio sia privo di errori.')
    else:
        st.warning('Causa non accertata dalla sola differenza dei totali. Per il formato .xls questa versione legge i valori, ma non analizza le formule: controlla l’intervallo del totale nel file originale.')

    checks = quad_position_checks(db_parser, db_corretto, selected_sheet, sheet,
        source_metadata=json.dumps(sheet.attrs, sort_keys=True, default=str) if sheet is not None else "")
    if checks.empty:
        st.info('Nessuna posizione del parser per questo foglio.'); return
    st.markdown('#### Confronta una posizione — non un elenco di errori')
    st.caption('La vecchia distanza dallo scostamento è stata eliminata: confrontava importi di clienti con un totale di zona e non misurava un errore. Qui sono visibili soltanto confronti tra la stessa riga e le sue celle sorgente.')
    query = st.text_input('Cerca cliente / codice', key='qsearch_'+scope).strip()
    view = checks
    if query:
        view = view[view['Cliente'].str.contains(query, case=False, regex=False, na=False) | view['Codice cliente'].str.contains(query, case=False, regex=False, na=False)]
    focus = st.selectbox('Mostra', ['Tutte le posizioni','Rettifiche già applicate','Differenze di lettura misurate'], key='qfocus_'+scope)
    if focus == 'Rettifiche già applicate': view = view[view['Stato rettifica'].eq('Rettifica già applicata')]
    elif focus == 'Differenze di lettura misurate': view = view[view['Esito lettura'].eq('Differenza di lettura misurata')]
    view = view.sort_values(['Cliente','Riga Excel'], kind='stable').reset_index(drop=True)
    if view.empty:
        st.info('Nessuna posizione nella selezione.'); return
    if st.checkbox('Mostra tabella dei confronti (100 righe per pagina)', key='qtable_'+scope):
        pages = list(range(1, max(1,(len(view)+99)//100)+1)); pk='qpage_'+scope
        if st.session_state.get(pk) not in pages: st.session_state[pk]=1
        page=st.selectbox('Pagina confronti',pages,key=pk)
        cols=['Cliente','Codice cliente','Riga Excel','Importo celle tracciate','Totale parser','Differenza lettura','Totale dopo rettifiche','Esito lettura','Stato rettifica']
        st.dataframe(quad_display(view.iloc[(page-1)*100:page*100][cols]), width='stretch', hide_index=True)
    opts=list(range(len(view)))
    sk='qsel_'+scope+'_'+hashlib.sha256((query+'|'+focus).encode()).hexdigest()[:8]
    if st.session_state.get(sk) not in opts: st.session_state[sk]=opts[0]
    selected=st.selectbox('Cliente / riga da confrontare',opts,
        format_func=lambda i:f"{view.iloc[i]['Cliente']} · riga Excel {view.iloc[i]['Riga Excel']} · {view.iloc[i]['Stato rettifica']}",key=sk)
    check=view.iloc[selected]
    matches=db_parser[db_parser['ID_POSIZIONE_SSC'].astype(str).eq(check['ID_POSIZIONE_SSC']) & db_parser['FOGLIO_ORIGINE'].map(canonical_sheet).eq(canonical_sheet(selected_sheet))]
    matches=matches[pd.to_numeric(matches['RIGA_SHEET'],errors='coerce').eq(float(check['Riga Excel'])-1)]
    if len(matches)!=1:
        st.warning('Posizione non univoca: nessuna correzione consentita da questo confronto.');return
    original_row=matches.iloc[0]
    if check['Esito lettura']=='Importo letto coincidente':
        st.success(check['Spiegazione'])
    else:
        st.warning(check['Spiegazione'])
    st.write('**Stato rettifica:** '+check['Stato rettifica'])
    cells, _, source_note=quad_source_cells(original_row,sheet)
    if not cells.empty:
        st.dataframe(cells,width='stretch',hide_index=True)
    st.caption(source_note)
    comparison=pd.DataFrame([
        {'Componente':'Fatture','Letto dal parser':check['Fatture lette'],'Dopo rettifiche del tool':check['Fatture dopo rettifiche']},
        {'Componente':'Buoni / SSC','Letto dal parser':check['Buoni letti'],'Dopo rettifiche del tool':check['Buoni dopo rettifiche']},
        {'Componente':'Totale','Letto dal parser':check['Totale parser'],'Dopo rettifiche del tool':check['Totale dopo rettifiche']},
    ])
    # Etichette monetarie esplicite per non formattare come euro ID o numeri di riga.
    for c in ['Letto dal parser','Dopo rettifiche del tool']:
        comparison[c]=comparison[c].map(lambda v:format_euro(v) if quad_number(v) is not None else 'N/D')
    st.dataframe(comparison,width='stretch',hide_index=True)
    st.caption('Questo confronto esclude i pagamenti e i clienti aggiunti manualmente: una rettifica non altera il file archiviato. Una riga corretta può restare consultabile senza essere un errore aperto.')
    if read_only or not can_edit():
        st.caption('Sola lettura. Nessuna modifica consentita in questa vista.');return
    if not st.checkbox('Apri rettifica motivata di questa posizione',key='qedit_'+scope+'_'+str(selected)):
        return
    st.warning('Non modificare una posizione solo perché il totale del foglio non quadra. Questa rettifica modifica il saldo operativo della situazione corrente, non la formula Excel né l’evidenza originale.')
    rid=check['ID_POSIZIONE_SSC']
    rules=carica_correzioni_quadratura()
    baseline=clean_text(st.session_state.get('current_baseline_hash'))
    rule=rules.get(baseline+':'+rid,{})
    if rule: st.caption('Rettifica registrata: '+clean_text(rule.get('salvato_il'))+' — '+clean_text(rule.get('nota')))
    ff=quad_number(check['Fatture dopo rettifiche']);bf=quad_number(check['Buoni dopo rettifiche'])
    if ff is None or bf is None:
        st.warning('Valori correnti non disponibili: aggiornare i dati prima di correggere.');return
    tag=scope+'_'+rid+'_'+hashlib.sha256(json.dumps(rule,sort_keys=True,default=str).encode()).hexdigest()[:8]
    with st.form('qform_'+tag):
        x,y=st.columns(2)
        fatture=x.number_input('Fatture dopo rettifica',value=ff,step=.01,format='%.2f')
        buoni=y.number_input('Buoni / SSC dopo rettifica',value=bf,step=.01,format='%.2f')
        nota=st.text_input('Motivazione e riferimento verificato',value='')
        confirm=st.checkbox('Ho confrontato la riga originale: non sto forzando il totale della zona.')
        submit=st.form_submit_button('Salva rettifica della posizione',type='primary')
    if submit:
        if not confirm or not clean_text(nota):
            st.warning('Conferma il confronto e indica la motivazione.')
        elif salva_correzione_posizione(original_row,fatture,buoni,nota):
            st.session_state.pop('__ready_dataset',None)
            st.success('Rettifica salvata nell’archivio condiviso. Il controllo sul file originale rimane distinto.')
            st.rerun()
    if rule and st.button('Rimuovi questa rettifica (ripristina i valori letti)',key='qremove_'+tag):
        if elimina_correzione_posizione(rid):
            st.session_state.pop('__ready_dataset',None)
            st.rerun()


# ======================================================
# DISPLAY
# ======================================================

def prepara_display(df):
    df_display = df.copy()

    for col in df_display.columns:
        if "PERIOD" in str(col).upper() or "DETTAGLIO" in str(col).upper():
            continue
        if str(col).upper() == "CODICE_CLIENTE":
            df_display[col] = df_display[col].apply(format_codice_cliente)
            continue

        if is_money_column_name(col):
            # Proviamo a formattare come euro anche colonne tecniche non numeriche
            # se contengono valori convertibili; altrimenti lasciamo il testo invariato.
            def _fmt(v):
                n = to_number(v)
                return format_euro(n) if n is not None else clean_text(v)
            df_display[col] = df_display[col].apply(_fmt)

    return df_display



def riepilogo_per(df, colonne):
    if df.empty:
        return pd.DataFrame()
    numeric = {
        "IMPORTO_TOTALE":"IMPORTO_STANDARD", "IMPORTO_FATTURE":"IMPORTO_FATTURE_RIGA",
        "IMPORTO_BUONI":"IMPORTO_BUONI_RIGA", "IMPORTO_NOTE_CREDITO":"IMPORTO_NOTE_CREDITO",
        "N_FATTURE":"NUM_FATTURE", "N_BUONI":"NUM_BUONI",
    }
    text = ["PERIODI_RIFERIMENTO", "ANNI_RIFERIMENTO", "PERIODI_ORDINABILI",
            "ANNI_STIMATI", "DETTAGLIO_PERIODI_IMPORTI", "PERIODI_DETTAGLIO", "MODALITA_PAGAMENTO"]
    work = df[list(dict.fromkeys(list(colonne) + list(numeric.values()) + text))].copy()
    for col in numeric.values():
        work[col] = pd.to_numeric(work[col], errors="coerce")
    grouped = work.groupby(colonne, dropna=False)
    amounts = grouped[list(numeric.values())].sum(min_count=1)
    amounts = amounts.rename(columns={v:k for k,v in numeric.items()})
    details = grouped[text].agg({c:join_periodi_dettaglio if c in
        ("DETTAGLIO_PERIODI_IMPORTI", "PERIODI_DETTAGLIO") else join_unici for c in text})
    result = pd.concat([amounts, details, grouped.size().rename("RIGHE")], axis=1)
    return result.reset_index().sort_values("IMPORTO_TOTALE", ascending=False)










# ======================================================
# IDENTITÀ STABILE POSIZIONI SSC
# ======================================================

def _identity_value(value):
    return re.sub(r"\s+", " ", clean_upper(value)).strip()


def _base_id_posizione_ssc(row):
    """Identità logica della posizione, indipendente dall'indice globale del file.

    RIGA_SHEET NON viene usata normalmente: entra solo come disambiguatore
    quando nel medesimo file esistono due righe semanticamente indistinguibili.
    """
    foglio = _identity_value(row.get("FOGLIO_ORIGINE", ""))
    legacy = clean_text(row.get("RIGA_GLOBALE", ""))

    if foglio == "MANUALE" and legacy:
        payload = f"MANUALE|{legacy}"
    else:
        parts = [
            format_codice_cliente(row.get("CODICE_CLIENTE", "")),
            _identity_value(row.get("CLIENTE", "")),
            _identity_value(row.get("CLIENTE_PADRE", "")),
            _identity_value(row.get("ZONA", "")),
            _identity_value(row.get("AGENTE", "")),
            _identity_value(row.get("TIPO_DOCUMENTO", "")),
            _identity_value(row.get("DOCUMENTO_RAW", "")),
            foglio,
            _identity_value(row.get("COLONNA_IMPORTO", "")),
            _identity_value(row.get("SICILIA_RIF_FATTURE", "")),
        ]
        payload = "|".join(parts)

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def aggiungi_id_posizione_stabile(db):
    if db is None or db.empty:return db
    out=db.copy()
    # Dentro lo stesso hash del file la coordinata originale è immutabile.
    # Gli eventi di file diversi sono sempre separati per BASELINE_HASH.
    if 'ID_POSIZIONE_SSC' not in out:out['ID_POSIZIONE_SSC']=''
    missing=out['ID_POSIZIONE_SSC'].fillna('').astype(str).eq('')
    for idx,row in out[missing].iterrows():
        sheet=canonical_sheet(row.get('FOGLIO_ORIGINE',''))
        coord=clean_text(row.get('RIGA_SHEET',''))
        if sheet=='MANUALE':coord=clean_text(row.get('RIGA_GLOBALE',''))
        raw=f"SSC2|{sheet}|{coord}"
        out.at[idx,'ID_POSIZIONE_SSC']=hashlib.sha256(raw.encode()).hexdigest()[:24]
    if out['ID_POSIZIONE_SSC'].duplicated().any():
        raise ValueError('Posizioni con coordinate duplicate: impossibile applicare modifiche in sicurezza.')
    return out



# ======================================================
# CONFIGURAZIONE VISTE / COLONNE
# ======================================================

PREFS_FILE = Path(__file__).with_name("divispack_view_defaults.json")
HISTORY_FILE = Path(__file__).with_name("divispack_storico_pagamenti.json")
MANUAL_FILE = Path(__file__).with_name("divispack_clienti_manuali.json")
DELETED_CLIENTS_FILE = Path(__file__).with_name("divispack_clienti_eliminati.json")

# Colori fissi per zona: devono restare sempre uguali per facilitare la lettura
ZONE_COLORS = {
    # Palette volutamente molto diversa zona per zona: deve restare fissa nel tempo.
    "CARDITO": "#FFE066",          # giallo pieno
    "CASERTA": "#74C0FC",          # azzurro vivo
    "SICILIA": "#69DB7C",          # verde vivo
    "SARNO-PAGANI": "#F783AC",     # rosa deciso
    "MONDRAG-CAPUA": "#B197FC",    # viola/lilla
    "PUGLIA": "#FFA94D",           # arancio
    "GIUGLIANO": "#63E6BE",        # turchese/menta
    "NAPOLI": "#4DABF7",           # blu
    "VOLLA": "#FFD43B",            # giallo caldo
    "SOMMA VESUVIANA": "#D8A657",  # ocra
    "FUNGAIE": "#C084FC",          # viola acceso
    "MERCATO ORTOFRUTTICOLO D": "#A9E34B",
}

DEFAULT_ZONE_COLORS = [
    "#FFE066", "#74C0FC", "#69DB7C", "#F783AC", "#B197FC", "#FFA94D",
    "#63E6BE", "#4DABF7", "#FFD43B", "#D8A657", "#C084FC", "#A9E34B",
    "#FF8787", "#66D9E8", "#FCC2D7", "#8CE99A"
]


def normalizza_nome_zona(zona):
    return re.sub(r"\s+", " ", clean_upper(zona)).strip()


def colore_zona(zona):
    z = normalizza_nome_zona(zona)
    if z in ZONE_COLORS:
        return ZONE_COLORS[z]
    # match morbido per nomi più lunghi o lievemente variati
    for key, color in ZONE_COLORS.items():
        if key in z or z in key:
            return color
    # Fallback DETERMINISTICO: una zona nuova mantiene lo stesso colore
    # anche dopo riavvii di Python/Streamlit.
    if not z:
        return DEFAULT_ZONE_COLORS[0]
    digest = hashlib.sha256(z.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(DEFAULT_ZONE_COLORS)
    return DEFAULT_ZONE_COLORS[idx]


def testo_colore_su_sfondo(hex_color):
    hex_color = str(hex_color).lstrip("#")
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        luminanza = (0.299 * r + 0.587 * g + 0.114 * b)
        return "#111827" if luminanza > 150 else "#FFFFFF"
    except Exception:
        return "#111827"


def render_zone_badge(zona):
    bg = colore_zona(zona)
    fg = testo_colore_su_sfondo(bg)
    st.markdown(
        f'<div style="background:{bg}; color:{fg}; padding:6px 8px; border-radius:10px; '
        f'border:1px solid #111827; font-weight:900; text-align:center; font-size:12px; '
        f'margin-bottom:3px;">{escape(str(zona).title())}</div>',
        unsafe_allow_html=True,
    )

def get_query_param_safe(key, default=""):
    try:
        v = st.query_params.get(key, default)
        if isinstance(v, list):
            return v[0] if v else default
        return v if v not in [None, ""] else default
    except Exception:
        return default


def safe_key_from_value(value):
    txt = clean_upper(value)
    txt = re.sub(r"[^A-Z0-9]+", "_", txt).strip("_")
    return txt or "TUTTE"


def render_zone_filter_button(label, value, active=False, neutral=False):
    """Bottone Streamlit reale, non link HTML.
    Così il click NON cambia URL e NON fa perdere il file caricato.
    Il colore viene applicato via CSS al container con key stabile.
    """
    if neutral:
        bg = "#FFFFFF"
        fg = "#111827"
        border = "#9CA3AF"
    else:
        bg = colore_zona(value)
        fg = testo_colore_su_sfondo(bg)
        border = "#111827"

    shadow = "0 0 0 3px rgba(17,24,39,.28)" if active else "0 1px 4px rgba(17,24,39,.12)"
    key_base = f"zone_filter_{safe_key_from_value(value)}"

    st.markdown(
        f"""
        <style>
        .st-key-{key_base} button {{
            background-color: {bg} !important;
            color: {fg} !important;
            border: 2px solid {border} !important;
            border-radius: 12px !important;
            padding: 0.60rem 0.55rem !important;
            font-weight: 900 !important;
            font-size: 0.86rem !important;
            box-shadow: {shadow} !important;
            min-height: 44px !important;
            white-space: normal !important;
            line-height: 1.05 !important;
        }}
        .st-key-{key_base} button:hover {{
            filter: brightness(0.96);
            transform: translateY(-1px);
        }}
        .st-key-{key_base} button p {{
            color: {fg} !important;
            font-weight: 900 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key=key_base):
        return st.button(str(label), key=f"btn_{key_base}", width='stretch')

VIEW_STANDARD_COLUMNS = {
    "Vista Zone": [
        "ZONA", "IMPORTO_TOTALE", "IMPORTO_FATTURE", "IMPORTO_BUONI",
        "N_FATTURE", "N_BUONI", "PERIODI_RIFERIMENTO", "ANNI_RIFERIMENTO",
        "PERIODI_ORDINABILI", "RIGHE"
    ],
    "Vista Agenti": [
        "AGENTE", "IMPORTO_TOTALE", "IMPORTO_FATTURE", "IMPORTO_BUONI",
        "N_FATTURE", "N_BUONI", "PERIODI_RIFERIMENTO", "ANNI_RIFERIMENTO",
        "PERIODI_ORDINABILI", "RIGHE"
    ],
    "Vista Clienti": [
        "CLIENTE_PADRE",
        "CLIENTE",
        "AGENTE",
        "ZONA",
        "IMPORTO_FATTURE",
        "N_FATTURE",
        "IMPORTO_BUONI",
        "N_BUONI",
        "IMPORTO_TOTALE",
        "PERIODI_RIFERIMENTO_VISIBILI",
        "MODALITA_PAGAMENTO",
    ],
    "Dettaglio Sicilia": [
        "CLIENTE", "AGENTE", "ZONA", "IMPORTO_FATTURE_RIGA", "SICILIA_RIF_FATTURE",
        "PERIODI_RIFERIMENTO", "ANNI_RIFERIMENTO", "PERIODI_ORDINABILI", "ANNI_STIMATI",
        "DETTAGLIO_PERIODI_IMPORTI", "IMPORTO_BUONI_RIGA", "IMPORTO_STANDARD",
        "SICILIA_MODALITA_PAGAMENTO"
    ],
    "Note credito / Resi": [
        "FOGLIO_ORIGINE", "ZONA", "AGENTE", "CLIENTE", "CLIENTE_PADRE",
        "TIPO_DOCUMENTO", "IMPORTO_STANDARD", "IMPORTO_FATTURE_RIGA",
        "IMPORTO_BUONI_RIGA", "DOCUMENTO_RAW", "TESTO_RIGA"
    ],
    "Clienti raggruppati +": [
        "FOGLIO_ORIGINE", "ZONA", "AGENTE", "CLIENTE_PADRE", "CLIENTE",
        "IMPORTO_STANDARD", "IMPORTO_FATTURE_RIGA", "IMPORTO_BUONI_RIGA",
        "PERIODI_RIFERIMENTO", "ANNI_RIFERIMENTO", "DETTAGLIO_PERIODI_IMPORTI"
    ],
    "DB Pulito": [
        "FOGLIO_ORIGINE", "ZONA", "AGENTE", "CODICE_CLIENTE", "CLIENTE", "CLIENTE_PADRE",
        "TIPO_DOCUMENTO", "NUM_FATTURE", "NUM_BUONI", "PERIODI_RIFERIMENTO",
        "ANNI_RIFERIMENTO", "PERIODI_ORDINABILI", "ANNI_STIMATI", "DETTAGLIO_PERIODI_IMPORTI",
        "PERIODI_DETTAGLIO", "MODALITA_PAGAMENTO", "IMPORTO_STANDARD", "IMPORTO_FATTURE_RIGA", "IMPORTO_BUONI_RIGA",
        "IMPORTO_NOTE_CREDITO", "PUGLIA_GRUPPO", "PUGLIA_MEMO_ESCLUSO_TOTALE", "PUGLIA_IMPORTO_TESTO",
        "RIGA_SHEET", "TESTO_RIGA"
    ],
    "Da verificare": [
        "FOGLIO_ORIGINE", "ZONA", "AGENTE", "CLIENTE", "CLIENTE_PADRE",
        "DOCUMENTO_RAW", "TIPO_DOCUMENTO", "IMPORTO_STANDARD", "TESTO_RIGA", "RIGA_SHEET"
    ],
}


def load_view_defaults():
    return remote_state_get("view_defaults",{}) or {}



def save_view_defaults(data):
    if not is_super_admin():
        return False
    return remote_state_set("view_defaults", data)



def colonne_valide(df, colonne):
    return [c for c in colonne if c in df.columns]


def scegli_colonne_vista(vista_key, df, standard_cols=None):
    """Permette di scegliere le colonne visibili e salvarle come default per singola vista."""
    if df is None or df.empty:
        return df

    defaults = load_view_defaults()
    all_cols = list(df.columns)
    standard = colonne_valide(df, standard_cols or VIEW_STANDARD_COLUMNS.get(vista_key, all_cols))
    custom_default = colonne_valide(df, defaults.get(vista_key, []))
    initial_cols = custom_default if custom_default else standard

    if not initial_cols:
        initial_cols = all_cols

    key = f"cols_{vista_key}"
    reset_key = f"reset_cols_{vista_key}"

    if reset_key in st.session_state and st.session_state[reset_key]:
        st.session_state[key] = standard
        st.session_state[reset_key] = False

    if key not in st.session_state:
        st.session_state[key] = initial_cols

    with st.sidebar.expander("Colonne vista corrente", expanded=False):
        st.caption("Scegli le colonne da mostrare. Puoi salvare la scelta come predefinita per questa vista.")
        # Streamlit warning fix: se un widget ha già un valore in session_state,
        # non bisogna passare anche default, altrimenti compare l'avviso
        # "created with a default value but also had its value set via Session State".
        if key in st.session_state:
            selected = st.multiselect(
                "Colonne visibili",
                options=all_cols,
                key=key,
            )
        else:
            selected = st.multiselect(
                "Colonne visibili",
                options=all_cols,
                default=colonne_valide(df, initial_cols),
                key=key,
            )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Salva default", key=f"save_{vista_key}"):
                defaults[vista_key] = selected
                if save_view_defaults(defaults):
                    st.success("Default salvato")
        with c2:
            if st.button("Standard", key=f"std_{vista_key}"):
                defaults.pop(vista_key, None)
                save_view_defaults(defaults)
                st.session_state[reset_key] = True
                st.rerun()

    selected = colonne_valide(df, st.session_state.get(key, initial_cols))
    if not selected:
        selected = all_cols

    return df[selected]




# ======================================================
# STORICO PAGAMENTI / MODIFICHE MANUALI
# ======================================================


def carica_storico_pagamenti():
    return pd.DataFrame(remote_state_get("payment_history", []) or [])





def salva_storico_pagamenti(df_storico):
    if not can_edit():
        st.error("Modifica non autorizzata o archivio non disponibile."); return False
    return remote_state_set("payment_history", df_storico.fillna("").to_dict(orient="records"))




def aggiungi_eventi_storico(eventi):
    if not can_edit() or not eventi:
        return False
    history = normalizza_storico(carica_storico_pagamenti())
    ids = set(history["EVENT_ID"].astype(str)) if not history.empty else set()
    user = st.session_state.get("current_user", {})
    incoming = [{**e,"UTENTE":user.get("nome",""),"USERNAME":user.get("username",""),
                 "RUOLO":user.get("ruolo","")} for e in eventi if str(e["EVENT_ID"]) not in ids]
    if not incoming:
        return True
    return salva_storico_pagamenti(pd.concat([history, pd.DataFrame(incoming)], ignore_index=True))





def split_period_tokens(value):
    """Token semplice per confrontare periodi testuali senza rompere la logica originale."""
    txt = clean_text(value)
    if txt == "":
        return []
    parts = re.split(r"[,|;]+", txt)
    out = []
    for part in parts:
        part = re.sub(r"\s+", " ", clean_text(part))
        if part and part not in out:
            out.append(part)
    return out


def differenza_periodi_pagati(periodi_precedenti, periodi_nuovi, periodi_ord_precedenti="", periodi_ord_nuovi=""):
    """Restituisce i periodi rimossi dall'utente: quelli vanno nello storico come periodo pagato."""
    old_ord = split_period_tokens(periodi_ord_precedenti)
    new_ord = split_period_tokens(periodi_ord_nuovi)
    if old_ord:
        removed_ord = [p for p in old_ord if p not in new_ord]
        if removed_ord:
            return ", ".join(removed_ord)

    old_txt = split_period_tokens(periodi_precedenti)
    new_txt = split_period_tokens(periodi_nuovi)
    removed_txt = [p for p in old_txt if p not in new_txt]
    return ", ".join(removed_txt)



def storico_colonne_pubbliche(df):
    cols=["DATA_MOVIMENTO","CLIENTE","ZONA","AGENTE","TIPO_MOVIMENTO","ORIGINE","IMPORTO_MOVIMENTO","SALDO_PRECEDENTE","SALDO_NUOVO","BASELINE_FILE"]
    if df is None or df.empty:return pd.DataFrame(columns=cols)
    out=normalizza_storico(df)
    out["DATA_MOVIMENTO"]=out.get("DATA_OPERAZIONE",out.get("DATA_REGISTRAZIONE",""))
    for c in ["SALDO_PRECEDENTE","SALDO_NUOVO","VARIAZIONE_SALDO","IMPORTO_PAGATO"]:
        if c not in out:out[c]=None
        out[c]=pd.to_numeric(out[c],errors="coerce")
    out["IMPORTO_MOVIMENTO"]=out["VARIAZIONE_SALDO"]
    manual=out["ORIGINE"].str.startswith("MANUALE")
    out.loc[manual,"IMPORTO_MOVIMENTO"]=(out["SALDO_NUOVO"]-out["SALDO_PRECEDENTE"]).loc[manual]
    pay=out["TIPO_MOVIMENTO"].eq("PAGAMENTO")
    out.loc[pay,"IMPORTO_MOVIMENTO"]=out.loc[pay,"IMPORTO_PAGATO"]
    for c in cols:
        if c not in out:out[c]=""
    return out[cols]



def costruisci_eventi_modifica(originale,modificato):
    if originale is None or modificato is None or originale.empty:return []
    before=aggiungi_id_posizione_stabile(originale).set_index('ID_POSIZIONE_SSC',drop=False)
    after=aggiungi_id_posizione_stabile(modificato).set_index('ID_POSIZIONE_SSC',drop=False)
    baseline=st.session_state.get('current_baseline_hash','')
    fields=list(CLIENTI_EDITABLE_COLUMNS)
    result=[]
    for sid in before.index.intersection(after.index):
        a,b=before.loc[sid],after.loc[sid]
        changed=[]
        for c in fields:
            if c not in a or c not in b:continue
            if c in ['IMPORTO_FATTURE_RIGA','IMPORTO_BUONI_RIGA','NUM_FATTURE','NUM_BUONI']:
                if abs(float(to_number(a[c]) or 0)-float(to_number(b[c]) or 0))>=.005:changed.append(c)
            elif clean_text(a[c])!=clean_text(b[c]):changed.append(c)
        if not changed:continue
        oldf,oldb=float(a.get('IMPORTO_FATTURE_RIGA',0)),float(a.get('IMPORTO_BUONI_RIGA',0))
        newf,newb=float(b.get('IMPORTO_FATTURE_RIGA',0)),float(b.get('IMPORTO_BUONI_RIGA',0))
        totaldiff=round(oldf+oldb-newf-newb,2)
        event={'EVENT_ID':str(uuid.uuid4()),'ATTIVO':True,'ORIGINE':'MANUALE','APPLICA_AL_SALDO':True,
          'TIPO_MOVIMENTO':'RETTIFICA MANUALE','BASELINE_HASH':baseline,'BASELINE_FILE':st.session_state.get('current_baseline_file',''),
          'ID_POSIZIONE_SSC':sid,'DATA_REGISTRAZIONE':datetime.now().isoformat(timespec='microseconds'),
          'CAMPI_MODIFICATI':', '.join(changed),'VALORI_NUOVI':{c:(float(b[c]) if c in ['IMPORTO_FATTURE_RIGA','IMPORTO_BUONI_RIGA','NUM_FATTURE','NUM_BUONI'] else clean_text(b[c])) for c in changed},
          'IMPORTO_FATTURE_PRECEDENTE':oldf,'IMPORTO_BUONI_PRECEDENTE':oldb,'IMPORTO_FATTURE_NUOVO':newf,'IMPORTO_BUONI_NUOVO':newb,
          'DIFFERENZA_FATTURE':round(oldf-newf,2),'DIFFERENZA_BUONI':round(oldb-newb,2),'DIFFERENZA_TOTALE':totaldiff,
          'SALDO_PRECEDENTE':round(oldf+oldb,2),'SALDO_NUOVO':round(newf+newb,2),'IMPORTO_PAGATO':0,
          'DATA_PAGAMENTO':'','PERIODO_PAGATO':'','PERIODI_NUOVI':clean_text(b.get('PERIODI_RIFERIMENTO',''))}
        for c in ['RIGA_SHEET','RIGA_GLOBALE','FOGLIO_ORIGINE','CODICE_CLIENTE','CLIENTE','CLIENTE_PADRE','ZONA','AGENTE']:
            event[c]=clean_text(b.get(c,''))
        result.append(event)
    return result




def normalizza_storico(df_storico):
    """Normalizza storico manuale + variazioni automatiche delle baseline."""
    if df_storico is None or df_storico.empty:
        return pd.DataFrame()

    df = df_storico.copy()

    if "EVENT_ID" not in df.columns:
        df["EVENT_ID"] = [f"legacy_{i}" for i in range(len(df))]
    if "ATTIVO" not in df.columns:
        df["ATTIVO"] = True
    if "ID_POSIZIONE_SSC" not in df.columns:
        df["ID_POSIZIONE_SSC"] = ""
    if "ORIGINE" not in df.columns:
        df["ORIGINE"] = "MANUALE_LEGACY"
    if "TIPO_MOVIMENTO" not in df.columns:
        df["TIPO_MOVIMENTO"] = "PAGAMENTO/MODIFICA MANUALE"
    if "BASELINE_HASH" not in df.columns:
        df["BASELINE_HASH"] = ""
    if "BASELINE_FILE" not in df.columns:
        df["BASELINE_FILE"] = ""
    if "APPLICA_AL_SALDO" not in df.columns:
        # Lo storico preesistente nasceva come modifica manuale del saldo.
        df["APPLICA_AL_SALDO"] = True

    df["ATTIVO"] = df["ATTIVO"].apply(
        lambda x: False
        if str(x).strip().lower() in ["false", "0", "no", "annullato"]
        else True
    )
    df["APPLICA_AL_SALDO"] = df["APPLICA_AL_SALDO"].apply(
        lambda x: False
        if str(x).strip().lower() in ["false", "0", "no"]
        else True
    )
    df["BASELINE_HASH"] = df["BASELINE_HASH"].fillna("").astype(str)
    df["ORIGINE"] = df["ORIGINE"].fillna("").astype(str)

    return df




def migra_storico_legacy_alla_baseline_corrente(baseline_hash, baseline_file):
    # Non si attribuiscono automaticamente eventi non identificati a un file nuovo.
    return False



def snapshot_position_map(snapshot):
    out={}
    for r in (snapshot or {}).get('posizioni_cliente',[]) or []:
        key=r.get('entity_key')
        if not key:
            code=clean_text(r.get('codice_cliente',''))
            key='COD:'+code if code and ',' not in code else 'LEGACY:'+_identity_value(r.get('cliente') or r.get('cliente_padre'))
        out[key]=r
    return out



def crea_eventi_variazione_nuovo_saldi(current,previous):
    if not current or not previous or current.get('file_hash')==previous.get('file_hash'):return []
    cur,prev=snapshot_position_map(current),snapshot_position_map(previous)
    out=[]
    for key in sorted(set(cur)|set(prev)):
        a,b=prev.get(key),cur.get(key)
        # Assenza dal file non equivale a saldo zero.
        av,bv=(float(a.get('totale',0)) if a else None),(float(b.get('totale',0)) if b else None)
        if a is None:kind='CLIENTE NUOVO NEL FILE'
        elif b is None:kind='CLIENTE NON PIÙ PRESENTE — DA VERIFICARE'
        else:
            diff=round(bv-av,2)
            if abs(diff)<.01 and all(abs(float(b.get(c,0))-float(a.get(c,0)))<.01 for c in ['fatture','buoni']):continue
            kind='RIDUZIONE SALDO DA NUOVO SALDI' if diff<0 else ('AUMENTO SALDO DA NUOVO SALDI' if diff>0 else 'RICOMPOSIZIONE SALDO DA NUOVO SALDI')
        who=b or a
        out.append({'EVENT_ID':'SALDI_'+hashlib.sha256((previous['file_hash']+'|'+current['file_hash']+'|'+key).encode()).hexdigest(),
          'ATTIVO':True,'ORIGINE':'NUOVO_SALDI','TIPO_MOVIMENTO':kind,'APPLICA_AL_SALDO':False,
          'BASELINE_HASH':current['file_hash'],'BASELINE_FILE':current.get('file_name',''),
          'BASELINE_PRECEDENTE_HASH':previous['file_hash'],'BASELINE_PRECEDENTE_FILE':previous.get('file_name',''),
          'DATA_REGISTRAZIONE':datetime.now().isoformat(timespec='seconds'),'DATA_PAGAMENTO':'','IMPORTO_PAGATO':0,
          'CLIENTE':who.get('cliente',''),'CLIENTE_PADRE':who.get('cliente_padre',''),'CODICE_CLIENTE':who.get('codice_cliente',''),
          'ZONA':who.get('zona',''),'AGENTE':who.get('agente',''),
          'SALDO_PRECEDENTE':av,'SALDO_NUOVO':bv,'VARIAZIONE_SALDO':round(bv-av,2) if a and b else None,
          'PERIODI_PRECEDENTI':(a or {}).get('periodi',''),'PERIODI_NUOVI':(b or {}).get('periodi',''),
          'STATO_CONFRONTO':'COMPARABILE' if a and b else 'PRESENZA_DA_VERIFICARE'})
    return out



def registra_variazioni_nuovo_saldi(current, previous):
    """Registra le variazioni file-to-file una sola volta (EVENT_ID deterministico)."""
    eventi = crea_eventi_variazione_nuovo_saldi(current, previous)
    if not eventi:
        return 0

    storico = normalizza_storico(carica_storico_pagamenti())
    existing_ids = (
        set(storico["EVENT_ID"].astype(str))
        if not storico.empty and "EVENT_ID" in storico.columns
        else set()
    )

    nuovi = [e for e in eventi if str(e["EVENT_ID"]) not in existing_ids]
    if not nuovi:
        return 0

    nuovi_df = pd.DataFrame(nuovi)
    if storico.empty:
        nuovo_storico = nuovi_df
    else:
        nuovo_storico = pd.concat([storico, nuovi_df], ignore_index=True)

    if salva_storico_pagamenti(nuovo_storico):
        try:
            riduzioni = sum(
                1 for e in nuovi if e.get("TIPO_MOVIMENTO", "").startswith("RIDUZIONE")
            )
            aumenti = sum(
                1 for e in nuovi if e.get("TIPO_MOVIMENTO", "").startswith("AUMENTO")
            )
            registra_azione(
                "NUOVA BASELINE SALDI",
                dettaglio=(
                    f"{clean_text(previous.get('file_name',''))} → "
                    f"{clean_text(current.get('file_name',''))} | "
                    f"{len(nuovi)} clienti variati | "
                    f"{riduzioni} riduzioni | {aumenti} aumenti"
                ),
            )
        except Exception:
            pass
        return len(nuovi)

    return 0


def applica_storico_a_db(db,baseline_hash=None):
    if db is None or db.empty:return db
    out=aggiungi_id_posizione_stabile(db)
    history=normalizza_storico(carica_storico_pagamenti())
    if history.empty:return ricalcola_importi_da_editor(out)
    st.session_state['__legacy_history_count']=int((history['BASELINE_HASH'].fillna('').eq('') & history['APPLICA_AL_SALDO']).sum())
    current=baseline_hash or st.session_state.get('current_baseline_hash','')
    scope=history['BASELINE_HASH'].fillna('').eq(current)&bool(current)&history['ATTIVO']&history['APPLICA_AL_SALDO']
    history=history[scope].copy()
    if 'DATA_REGISTRAZIONE' in history:history=history.sort_values('DATA_REGISTRAZIONE',kind='stable')
    missing=0
    legacy_fields={'NUM_FATTURE':'NUM_FATTURE_NUOVO','NUM_BUONI':'NUM_BUONI_NUOVO',
      'PERIODI_RIFERIMENTO':'PERIODI_NUOVI','ANNI_RIFERIMENTO':'ANNI_NUOVI',
      'PERIODI_ORDINABILI':'PERIODI_ORD_NUOVI','DETTAGLIO_PERIODI_IMPORTI':'DETTAGLIO_NUOVO'}
    for _,ev in history.iterrows():
        selected=out['ID_POSIZIONE_SSC'].eq(clean_text(ev.get('ID_POSIZIONE_SSC','')))
        if selected.sum()!=1:
            coord=to_number(ev.get('RIGA_SHEET'))
            selected=out['FOGLIO_ORIGINE'].map(canonical_sheet).eq(canonical_sheet(ev.get('FOGLIO_ORIGINE','')))&pd.to_numeric(out['RIGA_SHEET'],errors='coerce').eq(coord)
        if selected.sum()!=1:
            missing+=1;continue
        idx=out.index[selected][0]
        values=ev.get('VALORI_NUOVI')
        changed=set()
        if isinstance(values,dict):
            # Importi come delta: annullare un evento elimina solo il suo effetto.
            for c,delta in [('IMPORTO_FATTURE_RIGA','DIFFERENZA_FATTURE'),('IMPORTO_BUONI_RIGA','DIFFERENZA_BUONI')]:
                out.at[idx,c]=float(out.at[idx,c])-float(to_number(ev.get(delta)) or 0)
            for c,v in values.items():
                if c in CLIENTI_EDITABLE_COLUMNS and c not in ['IMPORTO_FATTURE_RIGA','IMPORTO_BUONI_RIGA']:
                    out.at[idx,c]=v;changed.add(c)
        else:
            for c,delta in [('IMPORTO_FATTURE_RIGA','DIFFERENZA_FATTURE'),('IMPORTO_BUONI_RIGA','DIFFERENZA_BUONI')]:
                out.at[idx,c]=float(out.at[idx,c])-float(to_number(ev.get(delta)) or 0)
            fieldnames=set(x.strip() for x in clean_text(ev.get('CAMPI_MODIFICATI','')).split(','))
            for c,src in legacy_fields.items():
                if c in fieldnames and src in ev:
                    out.at[idx,c]=ev[src];changed.add(c)
        period_changed=bool(changed&{'PERIODI_RIFERIMENTO','ANNI_RIFERIMENTO','PERIODI_ORDINABILI','DETTAGLIO_PERIODI_IMPORTI'})
        if period_changed and 'PERIODI_DETTAGLIO' not in changed:
            # Non lasciare in tabella il testo ricco originario ormai superato.
            detail=clean_text(out.at[idx,'DETTAGLIO_PERIODI_IMPORTI']) if 'DETTAGLIO_PERIODI_IMPORTI' in changed else ''
            if not detail:
                detail=clean_text(out.at[idx,'PERIODI_RIFERIMENTO'])
                out.at[idx,'DETTAGLIO_PERIODI_IMPORTI']=''
            out.at[idx,'PERIODI_DETTAGLIO']=detail
        elif changed&{'NUM_FATTURE','NUM_BUONI'} and 'PERIODI_DETTAGLIO' not in changed:
            # Conteggio modificato: non conservare distribuzioni mensili obsolete.
            out.at[idx,'PERIODI_DETTAGLIO']=clean_text(out.at[idx,'PERIODI_RIFERIMENTO'])
    st.session_state['__unmatched_history']=missing
    return ricalcola_importi_da_editor(out)




def salva_storico_normalizzato(df_storico):
    return salva_storico_pagamenti(normalizza_storico(df_storico))

# ======================================================
# FILTRI RAPIDI / VISTA CLIENTI INTERATTIVA
# ======================================================

def _estrai_anni_da_valore(value):
    """Estrae anni a 4 cifre da campi come ANNI_RIFERIMENTO o PERIODI_ORDINABILI."""
    txt = clean_text(value)
    if txt == "":
        return []
    years = []
    for m in re.findall(r"\b(20\d{2}|19\d{2})\b", txt):
        y = int(m)
        if y not in years:
            years.append(y)
    return years


def filtra_per_anno(df, modalita):
    """Filtra righe per anno corrente / precedenti senza alterare gli importi delle righe."""
    if df.empty or modalita in [None, "TUTTI"]:
        return df

    anno_corrente = datetime.now().year

    def match(row):
        anni = []
        for col in ["ANNI_RIFERIMENTO", "PERIODI_ORDINABILI", "DETTAGLIO_PERIODI_IMPORTI"]:
            if col in row.index:
                anni.extend(_estrai_anni_da_valore(row[col]))
        anni = sorted(set(anni))
        if not anni:
            return False
        if modalita == "CORRENTE":
            return anno_corrente in anni
        if modalita == "PRECEDENTI":
            return any(y < anno_corrente for y in anni)
        return True

    return df[df.apply(match, axis=1)].copy()


def applica_filtri_rapidi_clienti(df):
    """Pulsanti rapidi per Vista Clienti: zone + agenti + anno corrente/precedenti.
    I bottoni zona sono bottoni Streamlit reali colorati via CSS.
    Non usano link/query-param, quindi il click non porta alla pagina iniziale.
    """
    if df.empty:
        return df

    st.subheader("Filtri rapidi Vista Clienti")

    if "vista_clienti_zone_rapida" not in st.session_state:
        st.session_state["vista_clienti_zone_rapida"] = "TUTTE"
    if "vista_clienti_agente_rapido" not in st.session_state:
        st.session_state["vista_clienti_agente_rapido"] = "TUTTI"
    if "vista_clienti_anno_rapido" not in st.session_state:
        st.session_state["vista_clienti_anno_rapido"] = "TUTTI"

    zone = sorted([z for z in df["ZONA"].dropna().unique() if clean_text(z) != ""])

    st.caption("Zona")
    zona_attiva = st.session_state.get("vista_clienti_zone_rapida", "TUTTE")
    cols = st.columns(min(max(len(zone) + 1, 1), 6))

    with cols[0]:
        if render_zone_filter_button("Tutte", "TUTTE", active=(zona_attiva == "TUTTE"), neutral=True):
            st.session_state["vista_clienti_zone_rapida"] = "TUTTE"
            zona_attiva = "TUTTE"

    for i, z in enumerate(zone):
        col = cols[(i + 1) % len(cols)]
        label = str(z).title()[:28]
        with col:
            if render_zone_filter_button(label, z, active=(zona_attiva == z), neutral=False):
                st.session_state["vista_clienti_zone_rapida"] = z
                zona_attiva = z

    zona_attiva = st.session_state.get("vista_clienti_zone_rapida", "TUTTE")
    if zona_attiva != "TUTTE":
        df = df[df["ZONA"] == zona_attiva].copy()

    agenti = sorted([a for a in df["AGENTE"].dropna().unique() if clean_text(a) != ""])
    st.caption("Agente")
    if len(agenti) > 0:
        max_buttons = 18
        agent_cols = st.columns(6)
        if agent_cols[0].button("Tutti", key="btn_agente_tutti_clienti", width='stretch'):
            st.session_state["vista_clienti_agente_rapido"] = "TUTTI"
            st.rerun()
        for i, a in enumerate(agenti[:max_buttons]):
            col = agent_cols[(i + 1) % 6]
            label = str(a).title()[:24]
            if col.button(label, key=f"btn_agente_clienti_{i}_{a}", width='stretch'):
                st.session_state["vista_clienti_agente_rapido"] = a
                st.rerun()
        if len(agenti) > max_buttons:
            agente_sel = st.selectbox(
                "Altri agenti",
                ["TUTTI"] + agenti,
                index=0,
                key="select_agente_clienti_esteso",
            )
            if agente_sel != "TUTTI":
                st.session_state["vista_clienti_agente_rapido"] = agente_sel
    else:
        st.caption("Nessun agente disponibile con i filtri attuali.")

    agente_attivo = st.session_state.get("vista_clienti_agente_rapido", "TUTTI")
    if agente_attivo != "TUTTI":
        df = df[df["AGENTE"] == agente_attivo].copy()

    st.caption("Anno")
    a1, a2, a3 = st.columns(3)
    anno_corrente = datetime.now().year
    if a1.button(f"Anno corrente ({anno_corrente})", key="btn_anno_corrente_clienti", width='stretch'):
        st.session_state["vista_clienti_anno_rapido"] = "CORRENTE"
        st.rerun()
    if a2.button("Anni precedenti", key="btn_anni_precedenti_clienti", width='stretch'):
        st.session_state["vista_clienti_anno_rapido"] = "PRECEDENTI"
        st.rerun()
    if a3.button("Tutti gli anni", key="btn_tutti_anni_clienti", width='stretch'):
        st.session_state["vista_clienti_anno_rapido"] = "TUTTI"
        st.rerun()

    modalita_anno = st.session_state.get("vista_clienti_anno_rapido", "TUTTI")
    df = filtra_per_anno(df, modalita_anno)

    active = []
    if zona_attiva != "TUTTE":
        active.append(f"Zona: {zona_attiva}")
    if agente_attivo != "TUTTI":
        active.append(f"Agente: {agente_attivo}")
    if modalita_anno == "CORRENTE":
        active.append(f"Anno: {anno_corrente}")
    elif modalita_anno == "PRECEDENTI":
        active.append("Anno: precedenti")
    if active:
        st.info("Filtri rapidi attivi — " + " | ".join(active))

    return df


def crea_tabella_clienti_con_totali_zona(df_clienti):
    """Crea una tabella ordinata per zona con righe totale zona, semplice da leggere."""
    if df_clienti.empty:
        return df_clienti

    righe = []
    sort_cols = [c for c in ["ZONA", "CLIENTE_PADRE", "CLIENTE"] if c in df_clienti.columns]
    df_sorted = df_clienti.sort_values(sort_cols).copy() if sort_cols else df_clienti.copy()

    for zona, gruppo in df_sorted.groupby("ZONA", dropna=False):
        totale = {
            "CLIENTE_PADRE": f"TOTALE ZONA {zona}",
            "CLIENTE": "",
            "AGENTE": "",
            "ZONA": zona,
            "IMPORTO_TOTALE": gruppo["IMPORTO_TOTALE"].sum(min_count=1) if "IMPORTO_TOTALE" in gruppo else 0,
            "IMPORTO_FATTURE": gruppo["IMPORTO_FATTURE"].sum(min_count=1) if "IMPORTO_FATTURE" in gruppo else 0,
            "IMPORTO_BUONI": gruppo["IMPORTO_BUONI"].sum(min_count=1) if "IMPORTO_BUONI" in gruppo else 0,
            "N_FATTURE": gruppo["N_FATTURE"].sum(min_count=1) if "N_FATTURE" in gruppo else 0,
            "N_BUONI": gruppo["N_BUONI"].sum(min_count=1) if "N_BUONI" in gruppo else 0,
            "RIGHE": gruppo["RIGHE"].sum(min_count=1) if "RIGHE" in gruppo else len(gruppo),
            "PERIODI_RIFERIMENTO": "",
            "ANNI_RIFERIMENTO": "",
            "PERIODI_ORDINABILI": "",
            "DETTAGLIO_PERIODI_IMPORTI": "",
            "PERIODI_DETTAGLIO": "",
            "PERIODI_RIFERIMENTO_VISIBILI": "",
            "MODALITA_PAGAMENTO": "",
            "TIPO_RIGA": "TOTALE_ZONA",
        }
        righe.append(totale)
        for _, r in gruppo.iterrows():
            d = r.to_dict()
            d["TIPO_RIGA"] = "CLIENTE"
            righe.append(d)

    return pd.DataFrame(righe)




def stile_righe_totale_zona(df_display, style_info):
    """Evidenzia SOLO le righe TOTALE ZONA con colori fissi per zona."""
    if df_display.empty or style_info is None or style_info.empty:
        return df_display

    def _style_row(row):
        idx = row.name
        try:
            info = style_info.iloc[idx]
            is_totale = str(info.get("TIPO_RIGA", "")).upper() == "TOTALE_ZONA"
            zona = str(info.get("ZONA", ""))
        except Exception:
            is_totale = False
            zona = ""

        if is_totale:
            bg = colore_zona(zona)
            fg = testo_colore_su_sfondo(bg)
            return [
                f"background-color: {bg}; color: {fg}; font-weight: 900; border-top: 2px solid #374151; border-bottom: 2px solid #374151;"
                for _ in row
            ]

        return ["" for _ in row]

    return df_display.style.apply(_style_row, axis=1)



# ======================================================
# VISTA CLIENTI LEGGIBILE / MODIFICHE CONSENTITE
# ======================================================

CLIENTI_EDITABLE_COLUMNS = [
    "IMPORTO_FATTURE_RIGA",
    "IMPORTO_BUONI_RIGA",
    "NUM_FATTURE",
    "NUM_BUONI",
    "PERIODI_RIFERIMENTO",
    "ANNI_RIFERIMENTO",
    "PERIODI_ORDINABILI",
    "DETTAGLIO_PERIODI_IMPORTI",
    "PERIODI_DETTAGLIO",
    "MODALITA_PAGAMENTO",
    "CLIENTE_PADRE",
    "CLIENTE",
    "AGENTE",
    "ZONA",
]

CLIENTI_CARD_COLUMNS = [
    "CLIENTE",
    "CODICE_CLIENTE",
    "AGENTE",
    "ZONA",
    "IMPORTO_STANDARD",
    "IMPORTO_FATTURE_RIGA",
    "IMPORTO_BUONI_RIGA",
    "NUM_FATTURE",
    "NUM_BUONI",
    "PERIODI_RIFERIMENTO",
    "ANNI_RIFERIMENTO",
    "PERIODI_ORDINABILI",
    "DETTAGLIO_PERIODI_IMPORTI",
    "PERIODI_DETTAGLIO",
    "MODALITA_PAGAMENTO",
]

CLIENTI_LABELS = {
    "CLIENTE": "Cliente",
    "AGENTE": "Agente",
    "ZONA": "Zona",
    "IMPORTO_STANDARD": "Totale",
    "IMPORTO_FATTURE_RIGA": "Fatture",
    "IMPORTO_BUONI_RIGA": "Buoni/SSC",
    "NUM_FATTURE": "N. fatture",
    "NUM_BUONI": "N. buoni",
    "PERIODI_RIFERIMENTO": "Periodi",
    "ANNI_RIFERIMENTO": "Anni",
    "PERIODI_ORDINABILI": "Periodo ord.",
    "DETTAGLIO_PERIODI_IMPORTI": "Dettaglio periodi/importi",
    "PERIODI_DETTAGLIO": "Periodi di riferimento",
    "MODALITA_PAGAMENTO": "Pagamento",
    "CODICE_CLIENTE": "Codice cliente",
    "RIGA_SHEET": "Riga origine",
}


def ricalcola_importi_da_editor(df):
    out=df.copy()
    for c in ['IMPORTO_FATTURE_RIGA','IMPORTO_BUONI_RIGA','NUM_FATTURE','NUM_BUONI']:
        if c not in out:out[c]=0
        out[c]=pd.to_numeric(out[c],errors='coerce').fillna(0)
    f,b=out['IMPORTO_FATTURE_RIGA'],out['IMPORTO_BUONI_RIGA']
    out['IMPORTO_STANDARD']=(f+b).round(2)
    # Un netto zero con +fatture e -credito NON è una posizione senza componenti.
    zero=f.abs().lt(.005)&b.abs().lt(.005)
    out['FLAG_IMPORTO_ZERO']=zero
    out['TIPO_DOCUMENTO']='MISTO'
    out.loc[f.abs().ge(.005)&b.abs().lt(.005),'TIPO_DOCUMENTO']='FATTURA'
    out.loc[b.abs().ge(.005)&f.abs().lt(.005),'TIPO_DOCUMENTO']='BUONO'
    out.loc[(f.lt(0)&b.eq(0))|(b.lt(0)&f.eq(0)),'TIPO_DOCUMENTO']='NOTA_CREDITO_RESO'
    out.loc[zero,'TIPO_DOCUMENTO']='SALDO_ZERO'
    out['NUM_DOCUMENTI']=out['NUM_FATTURE']+out['NUM_BUONI']
    out['IMPORTO_NOTE_CREDITO']=f.clip(upper=0)+b.clip(upper=0)
    if 'FLAG_NOTA_CREDITO' not in out:out['FLAG_NOTA_CREDITO']=False
    out['FLAG_NOTA_CREDITO']=out['FLAG_NOTA_CREDITO'].fillna(False).astype(bool)|out['IMPORTO_NOTE_CREDITO'].lt(0)
    for c in ['PERIODI_RIFERIMENTO','ANNI_RIFERIMENTO','PERIODI_ORDINABILI','ANNI_STIMATI','DETTAGLIO_PERIODI_IMPORTI','PERIODI_DETTAGLIO']:
        if c not in out:out[c]=''
        out.loc[zero,c]=''
    out.loc[zero,['NUM_FATTURE','NUM_BUONI','NUM_DOCUMENTI']]=0
    return out



def editor_clienti_valori(df,key_suffix='default'):
    if df is None or df.empty:return df
    if df.attrs.get("period_projection") or st.session_state.get("__history_readonly"):
        st.info("Vista di analisi o storica: torna alla situazione corrente e al saldo completo per registrare operazioni.")
        return df
    if not can_edit():
        st.info('Profilo in sola lettura o archivio non disponibile.');return df
    source=aggiungi_id_posizione_stabile(df)
    # Il widget viene ricreato al cambio situazione/storico; nessun vecchio
    # valore editato viene applicato a una revisione diversa dello storico.
    revisions = st.session_state.get('__state_versions', {})
    revision = '_'.join(str(int(revisions.get(k, 0))) for k in
        ('payment_history', 'quadrature_corrections', 'manual_clients', 'deleted_clients'))
    key=f"{key_suffix}_{st.session_state.get('current_baseline_hash','')[:12]}_{revision}"
    ids='|'.join(source['ID_POSIZIONE_SSC'].astype(str))
    key+='_'+hashlib.sha256(ids.encode()).hexdigest()[:10]
    cols=['ID_POSIZIONE_SSC','CLIENTE_PADRE','CLIENTE','CODICE_CLIENTE','AGENTE','ZONA']+list(CLIENTI_EDITABLE_COLUMNS)
    cols=list(dict.fromkeys(c for c in cols if c in source.columns))
    st.markdown('### Registra pagamento / modifica posizione')
    st.caption('Aggiorna residui, conteggi e periodi insieme. Un pagamento è tale solo se selezioni Pagamento effettivo; le altre variazioni sono rettifiche.')
    with st.form('form_operativa_'+key):
        kind=st.selectbox('Tipo operazione',['Rettifica / aggiornamento posizione','Pagamento effettivo'],key='kind_'+key)
        edited=st.data_editor(source[cols].copy(),hide_index=True,width='stretch',num_rows='fixed',
            disabled=[c for c in cols if c not in CLIENTI_EDITABLE_COLUMNS],key='grid_'+key,
            column_config={'ID_POSIZIONE_SSC':None,'NUM_FATTURE':st.column_config.NumberColumn('N. fatture',step=1,min_value=0),
                'NUM_BUONI':st.column_config.NumberColumn('N. buoni',step=1,min_value=0),
                'PERIODI_DETTAGLIO':st.column_config.TextColumn('Dettaglio mesi / importi o n. fatture'),
                'MODALITA_PAGAMENTO':st.column_config.TextColumn('Modalità pagamento')})
        movement_date=st.date_input('Data operazione',value=datetime.now().date(),key='date_'+key)
        note=st.text_input('Motivo / riferimento operazione',key='note_'+key)
        submitted=st.form_submit_button('Salva nell’archivio condiviso',type='primary')
    if not submitted:return source
    if not clean_text(note):st.error('Indica un motivo o un riferimento.');return source
    updated=source.copy().set_index('ID_POSIZIONE_SSC',drop=False)
    edit=edited.set_index('ID_POSIZIONE_SSC')
    for c in CLIENTI_EDITABLE_COLUMNS:
        if c in edit:updated[c]=edit[c].reindex(updated.index)
    for c in ['NUM_FATTURE','NUM_BUONI']:
        nums=pd.to_numeric(updated[c],errors='coerce')
        if nums.isna().any() or nums.lt(0).any() or ((nums%1)!=0).any():
            st.error('I conteggi devono essere interi non negativi.');return source
    for c in ['IMPORTO_FATTURE_RIGA','IMPORTO_BUONI_RIGA']:
        nums=pd.to_numeric(updated[c],errors='coerce')
        if nums.isna().any() or not nums.map(math.isfinite).all():
            st.error('Importi non validi.');return source
    updated=updated.reset_index(drop=True)
    events=costruisci_eventi_modifica(source,updated)
    if not events:st.info('Nessuna variazione.');return source
    for ev in events:
        ev['NOTE']=clean_text(note);ev['DATA_OPERAZIONE']=movement_date.isoformat()
        if kind=='Pagamento effettivo':
            if ev['DIFFERENZA_TOTALE']<=0:
                st.error('Un pagamento deve ridurre il residuo. Per altre modifiche usa Rettifica.');return source
            ev['TIPO_MOVIMENTO']='PAGAMENTO';ev['IMPORTO_PAGATO']=ev['DIFFERENZA_TOTALE'];ev['DATA_PAGAMENTO']=movement_date.isoformat()
    if aggiungi_eventi_storico(events):
        st.session_state['__saved_notice']='Operazione salvata nell’archivio condiviso.'
        st.rerun()
    return source





def render_tabella_clienti_normale(df):
    """Vista tabellare operativa con colonne essenziali di default."""
    if df is None or df.empty:
        st.info("Nessun cliente da mostrare con i filtri attuali.")
        return

    riepilogo = riepilogo_per(
        df,
        ["CLIENTE_PADRE", "CLIENTE", "CODICE_CLIENTE", "AGENTE", "ZONA"],
    )
    tabella = crea_tabella_clienti_con_totali_zona(riepilogo)

    # La colonna visibile "Periodi di riferimento" privilegia:
    # importo/mese -> numero fatture/mese -> semplice elenco mesi.
    if "PERIODI_DETTAGLIO" in tabella.columns:
        dettagli = tabella["PERIODI_DETTAGLIO"].fillna("").astype(str).str.strip()
        fallback = tabella.get(
            "PERIODI_RIFERIMENTO",
            pd.Series("", index=tabella.index),
        ).fillna("").astype(str)
        tabella["PERIODI_RIFERIMENTO_VISIBILI"] = dettagli.where(
            dettagli != "",
            fallback,
        )
    else:
        tabella["PERIODI_RIFERIMENTO_VISIBILI"] = tabella.get(
            "PERIODI_RIFERIMENTO",
            "",
        )

    default_cols = [
        "CLIENTE_PADRE",
        "CLIENTE",
        "AGENTE",
        "ZONA",
        "IMPORTO_FATTURE",
        "N_FATTURE",
        "IMPORTO_BUONI",
        "N_BUONI",
        "IMPORTO_TOTALE",
        "PERIODI_RIFERIMENTO_VISIBILI",
        "MODALITA_PAGAMENTO",
    ]
    default_cols = [c for c in default_cols if c in tabella.columns]

    extra_cols = [
        c for c in tabella.columns
        if c not in default_cols and c != "TIPO_RIGA"
    ]

    mostra_extra = st.checkbox(
        "Mostra colonne aggiuntive",
        value=False,
        key="clienti_tabella_mostra_extra",
        help="Le colonne operative principali restano sempre visibili; abilita qui quelle tecniche o di approfondimento.",
    )

    selected_extra = []
    if mostra_extra:
        selected_extra = st.multiselect(
            "Colonne aggiuntive",
            options=extra_cols,
            default=[],
            key="clienti_tabella_extra_cols",
        )

    cols = default_cols + [c for c in selected_extra if c not in default_cols]

    labels = {
        "CLIENTE_PADRE": "Cliente padre",
        "CLIENTE": "Cliente",
        "AGENTE": "Agente",
        "ZONA": "Zona",
        "IMPORTO_FATTURE": "Importo fatture",
        "N_FATTURE": "N. fatture",
        "IMPORTO_BUONI": "Importo buoni",
        "N_BUONI": "N. buoni",
        "IMPORTO_TOTALE": "Importo totale",
        "PERIODI_RIFERIMENTO_VISIBILI": "Periodi di riferimento",
        "MODALITA_PAGAMENTO": "Modalità di pagamento",
    }

    if "TIPO_RIGA" in tabella.columns:
        style_info = tabella[["TIPO_RIGA", "ZONA"]].reset_index(drop=True)
    else:
        style_info = pd.DataFrame()

    raw_display = tabella[cols].reset_index(drop=True).rename(columns=labels)
    display = prepara_display(raw_display)
    if df.attrs.get("period_projection"):
        display = display.astype(object)
        for col in raw_display.columns:
            if is_money_column_name(col) or col in ["N. fatture", "N. buoni"]:
                display.loc[raw_display[col].isna(), col] = "N/D"

    try:
        display = stile_righe_totale_zona(display, style_info)
    except Exception:
        pass

    st.dataframe(
        display,
        width="stretch",
        height=650,
        hide_index=True,
    )

    if st.checkbox("Dettaglio completo delle singole posizioni", value=False, key="ssc_full_rows"):
        st.caption("Qui trovi le righe operative del SALDI, senza aggregazione cliente.")
        business_first = [
            "FOGLIO_ORIGINE", "ZONA", "AGENTE", "PUGLIA_GRUPPO",
            "CODICE_CLIENTE", "CLIENTE", "CLIENTE_PADRE",
            "DOCUMENTO_RAW", "TIPO_DOCUMENTO", "NUM_DOCUMENTI",
            "NUM_FATTURE", "NUM_BUONI",
            "IMPORTO_STANDARD", "IMPORTO_FATTURE_RIGA", "IMPORTO_BUONI_RIGA",
            "IMPORTO_NOTE_CREDITO", "PUGLIA_MEMO_ESCLUSO_TOTALE", "PUGLIA_IMPORTO_TESTO",
            "PERIODI_RIFERIMENTO", "PERIODI_DETTAGLIO",
            "ANNI_RIFERIMENTO", "PERIODI_ORDINABILI", "ANNI_STIMATI",
            "DETTAGLIO_PERIODI_IMPORTI", "MODALITA_PAGAMENTO",
            "FLAG_PLUS", "FLAG_NOTA_CREDITO",
            "RIGA_SHEET", "RIGA_GLOBALE", "ID_POSIZIONE_SSC",
        ]
        cols_full = [c for c in business_first if c in df.columns]
        cols_extra = [c for c in df.columns if c not in cols_full]
        st.dataframe(
            prepara_display(df[cols_full + cols_extra]),
            width="stretch",
            height=650,
            hide_index=True,
        )





def seleziona_cliente_operativo(db, key_prefix="op"):
    """Selettore cascata zona -> cliente per registrare pagamenti/modifiche."""
    if db is None or db.empty:
        return pd.DataFrame(), None

    c1, c2 = st.columns([1, 2])
    zone = sorted([z for z in db["ZONA"].dropna().astype(str).unique() if clean_text(z)]) if "ZONA" in db.columns else []
    zona = c1.selectbox("Zona", ["TUTTE"] + zone, key=f"{key_prefix}_zona")

    work = db.copy()
    if zona != "TUTTE" and "ZONA" in work.columns:
        work = work[work["ZONA"].astype(str) == str(zona)].copy()

    key_cliente = "CLIENTE_PADRE" if "CLIENTE_PADRE" in work.columns else "CLIENTE"
    clienti = sorted([x for x in work[key_cliente].dropna().astype(str).unique() if clean_text(x)])
    if not clienti:
        c2.info("Nessun cliente disponibile.")
        return pd.DataFrame(), None

    # Etichetta con saldo corrente per rendere il selettore operativo.
    totals = work.groupby(key_cliente, dropna=False)["IMPORTO_STANDARD"].sum().to_dict()
    cliente = c2.selectbox(
        "Cliente",
        clienti,
        format_func=lambda x: f"{x} — {format_euro(totals.get(x, 0))}",
        key=f"{key_prefix}_cliente",
    )
    det = work[work[key_cliente].astype(str) == str(cliente)].copy()
    return det, cliente


def render_operativita_cliente(db, key_prefix="op"):
    if db is None or db.empty:
        st.info("Nessun cliente disponibile.")
        return

    det, cliente = seleziona_cliente_operativo(db, key_prefix=key_prefix)
    if det.empty or cliente is None:
        return

    a, b, c, d = st.columns(4)
    a.metric("Saldo cliente", format_euro(pd.to_numeric(det["IMPORTO_STANDARD"], errors="coerce").fillna(0).sum()))
    b.metric("Fatture", format_euro(pd.to_numeric(det["IMPORTO_FATTURE_RIGA"], errors="coerce").fillna(0).sum()))
    c.metric("Buoni / SSC", format_euro(pd.to_numeric(det["IMPORTO_BUONI_RIGA"], errors="coerce").fillna(0).sum()))
    d.metric("Posizioni", len(det))

    view_cols = [
        "CLIENTE", "CODICE_CLIENTE", "ZONA", "AGENTE", "TIPO_DOCUMENTO",
        "IMPORTO_STANDARD", "IMPORTO_FATTURE_RIGA", "IMPORTO_BUONI_RIGA",
        "NUM_FATTURE", "NUM_BUONI", "PERIODI_RIFERIMENTO", "PERIODI_DETTAGLIO",
        "DETTAGLIO_PERIODI_IMPORTI", "MODALITA_PAGAMENTO",
    ]
    view_cols = [c for c in view_cols if c in det.columns]
    st.dataframe(prepara_display(det[view_cols]), width="stretch", hide_index=True)

    if can_edit():
        editor_clienti_valori(det, key_suffix=key_prefix)
    else:
        st.info("Il tuo profilo è in sola lettura: per registrare pagamenti serve il ruolo admin, editor o super_admin.")

def render_vista_clienti_cards(df, colonne_visibili=None):
    """Render HTML senza scroll orizzontale interno: righe grandi, testo a capo, colori e totali zona."""
    if df.empty:
        st.info("Nessun cliente da mostrare con i filtri attuali.")
        return

    colonne = colonne_visibili or CLIENTI_CARD_COLUMNS
    colonne = [c for c in colonne if c in df.columns]
    if "CLIENTE" not in colonne:
        colonne = ["CLIENTE"] + colonne
    if "ZONA" not in colonne and "ZONA" in df.columns:
        colonne = ["ZONA"] + colonne

    zone = sorted([str(z) for z in df["ZONA"].dropna().unique()]) if "ZONA" in df.columns else [""]
    color_by_zone = {z: colore_zona(z) for z in zone}

    css = """
    <style>
    .clienti-wrap{font-family:Arial, sans-serif; width:100%;}
    .zona-box{margin:14px 0 8px 0; padding:10px 14px; border-radius:14px; border:2px solid #111827; color:#111827; font-weight:900; font-size:21px; line-height:1.2;}
    .zona-sub{font-size:14px; font-weight:800; margin-top:3px;}
    .cliente-card{margin:6px 0; padding:9px 11px; border-radius:12px; background:#ffffff; border:1px solid #d1d5db; border-left:7px solid #4b5563; box-shadow:0 1px 3px rgba(0,0,0,.07);}
    .cliente-title{font-size:17px; line-height:1.18; font-weight:900; color:#111827; margin-bottom:6px; overflow-wrap:anywhere;}
    .cliente-grid{display:grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap:6px; align-items:stretch;}
    .field{background:#f9fafb; border:1px solid #e5e7eb; border-radius:9px; padding:6px 7px; min-height:40px; overflow-wrap:anywhere;}
    .field .lab{display:block; font-size:10px; text-transform:uppercase; letter-spacing:.035em; color:#6b7280; font-weight:800; margin-bottom:2px;}
    .field .val{font-size:13.5px; line-height:1.22; color:#111827; font-weight:700;}
    .money .val{font-size:15.5px; font-weight:900;}
    .periodi .val{font-size:12.8px; font-weight:700;}
    </style>
    """

    html = [css, '<div class="clienti-wrap">']
    sort_cols = [c for c in ["ZONA", "CLIENTE", "RIGA_SHEET"] if c in df.columns]
    df_sorted = df.sort_values(sort_cols).copy() if sort_cols else df.copy()

    for zona, gruppo in df_sorted.groupby("ZONA", dropna=False):
        zona_label = str(zona)
        bg = color_by_zone.get(zona_label, "#FFF3B0")
        tot = gruppo["IMPORTO_STANDARD"].sum() if "IMPORTO_STANDARD" in gruppo else 0
        fat = gruppo["IMPORTO_FATTURE_RIGA"].sum() if "IMPORTO_FATTURE_RIGA" in gruppo else 0
        buo = gruppo["IMPORTO_BUONI_RIGA"].sum() if "IMPORTO_BUONI_RIGA" in gruppo else 0
        html.append(
            f'<div class="zona-box" style="background:{bg};">ZONA {escape(zona_label)}'
            f'<div class="zona-sub">Totale {escape(format_euro(tot))} &nbsp; | &nbsp; Fatture {escape(format_euro(fat))} &nbsp; | &nbsp; Buoni {escape(format_euro(buo))} &nbsp; | &nbsp; Clienti {gruppo["CLIENTE"].nunique() if "CLIENTE" in gruppo.columns else len(gruppo)}</div></div>'
        )

        for _, r in gruppo.iterrows():
            cliente = escape(clean_text(r.get("CLIENTE", "")))
            codice = escape(format_codice_cliente(r.get("CODICE_CLIENTE", "")))
            codice_label = f"cod. {codice}" if codice else "cod. n/d"
            html.append(f'<div class="cliente-card"><div class="cliente-title">{cliente} <span style="font-size:13px;color:#6b7280;">{codice_label}</span></div>')
            html.append('<div class="cliente-grid">')
            for c in colonne:
                if c == "CLIENTE":
                    continue
                val = r.get(c, "")
                if str(c).upper() == "CODICE_CLIENTE":
                    val = format_codice_cliente(val)
                elif is_money_column_name(c):
                    val = format_euro(to_number(val) if to_number(val) is not None else val)
                elif pd.isna(val):
                    val = ""
                label = CLIENTI_LABELS.get(c, c)
                extra_class = " money" if c.startswith("IMPORTO") else (" periodi" if "PERIOD" in c or "DETTAGLIO" in c else "")
                html.append(f'<div class="field{extra_class}"><span class="lab">{escape(str(label))}</span><span class="val">{escape(clean_text(val))}</span></div>')
            html.append('</div></div>')
    html.append('</div>')
    st.markdown("\n".join(html), unsafe_allow_html=True)




def render_schede_generiche(df, titolo_col=None, colonne_visibili=None, group_col=None):
    """Grafica a schede compatta applicabile a tutte le viste principali."""
    if df is None or df.empty:
        st.info("Nessun dato da mostrare con i filtri attuali.")
        return

    colonne = colonne_visibili or list(df.columns)
    colonne = [c for c in colonne if c in df.columns]
    if not colonne:
        colonne = list(df.columns)

    if titolo_col is None:
        for candidate in ["CLIENTE", "CLIENTE_PADRE", "ZONA", "AGENTE", "TIPO_DOCUMENTO", "FOGLIO_ORIGINE"]:
            if candidate in df.columns:
                titolo_col = candidate
                break
        if titolo_col is None:
            titolo_col = colonne[0]

    if group_col is None:
        group_col = "ZONA" if "ZONA" in df.columns else None

    groups = sorted([str(z) for z in df[group_col].dropna().unique()]) if group_col and group_col in df.columns else [""]
    color_by_group = {z: colore_zona(z) for z in groups}

    css = """
    <style>
    .schede-wrap{font-family:Arial, sans-serif; width:100%;}
    .schede-group{margin:10px 0 6px 0; padding:8px 12px; border-radius:12px; border:2px solid #111827; color:#111827; font-weight:900; font-size:19px; line-height:1.15;}
    .schede-sub{font-size:13px; font-weight:800; margin-top:2px;}
    .scheda-card{margin:5px 0; padding:8px 10px; border-radius:11px; background:#ffffff; border:1px solid #d1d5db; border-left:6px solid #4b5563; box-shadow:0 1px 3px rgba(0,0,0,.06);}
    .scheda-title{font-size:16px; line-height:1.15; font-weight:900; color:#111827; margin-bottom:5px; overflow-wrap:anywhere;}
    .scheda-grid{display:grid; grid-template-columns: repeat(auto-fit, minmax(112px, 1fr)); gap:5px; align-items:stretch;}
    .scheda-field{background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:5px 6px; min-height:34px; overflow-wrap:anywhere;}
    .scheda-field .lab{display:block; font-size:9.5px; text-transform:uppercase; letter-spacing:.03em; color:#6b7280; font-weight:800; margin-bottom:1px;}
    .scheda-field .val{font-size:12.8px; line-height:1.18; color:#111827; font-weight:700;}
    .scheda-money .val{font-size:14.5px; font-weight:900;}
    .scheda-periodi .val{font-size:12px; font-weight:700;}
    </style>
    """

    html = [css, '<div class="schede-wrap">']
    df_work = df.copy()
    sort_cols = [c for c in [group_col, titolo_col] if c and c in df_work.columns]
    if sort_cols:
        df_work = df_work.sort_values(sort_cols)

    iterable = df_work.groupby(group_col, dropna=False) if group_col and group_col in df_work.columns else [("", df_work)]
    for gruppo_label, gruppo in iterable:
        gruppo_label = str(gruppo_label)
        bg = color_by_group.get(gruppo_label, "#FFF3B0")
        tot = gruppo["IMPORTO_STANDARD"].sum() if "IMPORTO_STANDARD" in gruppo.columns else (gruppo["IMPORTO_TOTALE"].sum() if "IMPORTO_TOTALE" in gruppo.columns else None)
        fat = gruppo["IMPORTO_FATTURE_RIGA"].sum() if "IMPORTO_FATTURE_RIGA" in gruppo.columns else (gruppo["IMPORTO_FATTURE"].sum() if "IMPORTO_FATTURE" in gruppo.columns else None)
        buo = gruppo["IMPORTO_BUONI_RIGA"].sum() if "IMPORTO_BUONI_RIGA" in gruppo.columns else (gruppo["IMPORTO_BUONI"].sum() if "IMPORTO_BUONI" in gruppo.columns else None)
        sub = []
        if tot is not None: sub.append(f"Totale {format_euro(tot)}")
        if fat is not None: sub.append(f"Fatture {format_euro(fat)}")
        if buo is not None: sub.append(f"Buoni {format_euro(buo)}")
        sub.append(f"Righe {len(gruppo)}")
        group_title = gruppo_label if gruppo_label else "Dati"
        html.append(f'<div class="schede-group" style="background:{bg};">{escape(group_title)}<div class="schede-sub">{" &nbsp; | &nbsp; ".join(escape(x) for x in sub)}</div></div>')

        for _, r in gruppo.iterrows():
            titolo = escape(clean_text(r.get(titolo_col, "")))
            codice = escape(format_codice_cliente(r.get("CODICE_CLIENTE", "")))
            codice_label = f"cod. {codice}" if codice else ""
            html.append(f'<div class="scheda-card"><div class="scheda-title">{titolo} <span style="font-size:12px;color:#6b7280;">{codice_label}</span></div>')
            html.append('<div class="scheda-grid">')
            for c in colonne:
                if c == titolo_col:
                    continue
                val = r.get(c, "")
                if str(c).upper() == "CODICE_CLIENTE":
                    val = format_codice_cliente(val)
                elif is_money_column_name(c):
                    val = format_euro(to_number(val) if to_number(val) is not None else val)
                elif pd.isna(val):
                    val = ""
                label = CLIENTI_LABELS.get(c, c)
                extra_class = " scheda-money" if (c.startswith("IMPORTO") or c.startswith("DIFFERENZA")) else (" scheda-periodi" if "PERIOD" in c or "DETTAGLIO" in c else "")
                html.append(f'<div class="scheda-field{extra_class}"><span class="lab">{escape(str(label))}</span><span class="val">{escape(clean_text(val))}</span></div>')
            html.append('</div></div>')
    html.append('</div>')
    st.markdown("\n".join(html), unsafe_allow_html=True)


# ======================================================
# CLIENTI MANUALI
# ======================================================


def carica_clienti_manuali():
    return pd.DataFrame(remote_state_get("manual_clients", []) or [])





def salva_clienti_manuali(df_manuali):
    if not can_edit():
        st.error("Modifica non autorizzata."); return False
    work=df_manuali.copy()
    # Solo i nuovi record senza provenienza ricevono la baseline corrente.
    if "BASELINE_HASH" not in work.columns:
        work["BASELINE_HASH"]=""
    old = carica_clienti_manuali()
    old_ids = set(old.get("RIGA_GLOBALE",pd.Series(dtype=str)).astype(str))
    for idx,r in work.iterrows():
        if not clean_text(r.get("BASELINE_HASH","")) and str(r.get("RIGA_GLOBALE","")) not in old_ids:
            work.at[idx,"BASELINE_HASH"] = st.session_state.get("current_baseline_hash","")
    return remote_state_set("manual_clients", work.fillna("").to_dict(orient="records"))




def aggiungi_clienti_manuali_a_db(db):
    manuali = carica_clienti_manuali()
    if manuali.empty:
        return db
    current=st.session_state.get("current_baseline_hash","")
    mask=manuali.get("BASELINE_HASH",pd.Series("",index=manuali.index)).fillna("").eq(current)
    st.session_state["__legacy_manuals"] = int(manuali.get("BASELINE_HASH",pd.Series("",index=manuali.index)).fillna("").eq("").sum())
    manuali=manuali[mask & bool(current)].copy()
    if manuali.empty:
        return db
    return pd.concat([db,manuali],ignore_index=True)



def render_form_nuovo_cliente(db_base):
    st.markdown("### Inserisci nuovo cliente")
    with st.expander("➕ Nuovo cliente / nuova posizione", expanded=False):
        zone = sorted([z for z in db_base["ZONA"].dropna().unique() if clean_text(z) != ""]) if "ZONA" in db_base.columns else []
        agenti = sorted([a for a in db_base["AGENTE"].dropna().unique() if clean_text(a) != ""]) if "AGENTE" in db_base.columns else []
        mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        mese_map = {m: i + 1 for i, m in enumerate(mesi)}

        with st.form("form_nuovo_cliente_manuale", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                codice = st.text_input("Codice cliente")
                cliente = st.text_input("Ragione sociale")
                nessun_padre = st.checkbox("Nessun cliente padre", value=True)
                cliente_padre = st.text_input("Cliente padre", disabled=nessun_padre)
            with c2:
                zona = st.selectbox("Zona", zone + ["ALTRO"], index=0 if zone else 0)
                zona_altro = st.text_input("Nuova zona", disabled=(zona != "ALTRO"))
                agente = st.selectbox("Agente", agenti + ["NON ASSEGNATO", "ALTRO"], index=(agenti.index("NON ASSEGNATO") if "NON ASSEGNATO" in agenti else 0) if agenti else 0)
                agente_altro = st.text_input("Nuovo agente", disabled=(agente != "ALTRO"))
            with c3:
                tipo = st.selectbox("Tipologia documento", ["FATTURA", "BUONO"])
                importo = st.number_input("Totale buono o fattura", min_value=-999999999.0, max_value=999999999.0, value=0.0, step=1.0, format="%.2f")
                mese = st.selectbox("Mese di riferimento", mesi, index=max(0, datetime.now().month - 1))
                anno = st.number_input("Anno di riferimento", min_value=1900, max_value=2100, value=datetime.now().year, step=1)
                pagamento = st.text_input("Modalità di pagamento")

            submitted = st.form_submit_button("Inserisci cliente", width='stretch')
            if submitted:
                if clean_text(cliente) == "":
                    st.error("Inserisci almeno la ragione sociale.")
                    return
                zona_finale = zona_altro if zona == "ALTRO" and clean_text(zona_altro) else zona
                agente_finale = agente_altro if agente == "ALTRO" and clean_text(agente_altro) else agente
                padre_finale = cliente if nessun_padre else (cliente_padre if clean_text(cliente_padre) else cliente)
                anno = int(anno)
                periodo_ord = f"{anno}-{mese_map.get(mese, 1):02d}"
                dettaglio = f"{mese} {anno}: {format_euro(importo)}" if abs(float(importo)) > 0.0001 else ""
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rid = f"MANUAL_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                importo_fatt = float(importo) if tipo == "FATTURA" else 0.0
                importo_buo = float(importo) if tipo == "BUONO" else 0.0
                record = {
                    "FOGLIO_ORIGINE": "MANUALE",
                    "ZONA": zona_finale,
                    "AGENTE": agente_finale,
                    "CODICE_CLIENTE": codice,
                    "CLIENTE_ORIGINALE": cliente,
                    "CLIENTE": cliente,
                    "CLIENTE_CLEAN": cliente,
                    "FLAG_PLUS": False,
                    "CLIENTE_PADRE": padre_finale,
                    "DOCUMENTO_RAW": "Inserimento manuale",
                    "TIPO_DOCUMENTO": tipo,
                    "NUM_DOCUMENTI": 1 if abs(float(importo)) > 0.0001 else 0,
                    "NUM_FATTURE": 1 if tipo == "FATTURA" and abs(float(importo)) > 0.0001 else 0,
                    "NUM_BUONI": 1 if tipo == "BUONO" and abs(float(importo)) > 0.0001 else 0,
                    "PERIODI_RIFERIMENTO": mese if abs(float(importo)) > 0.0001 else "",
                    "ANNI_RIFERIMENTO": str(anno) if abs(float(importo)) > 0.0001 else "",
                    "PERIODI_ORDINABILI": periodo_ord if abs(float(importo)) > 0.0001 else "",
                    "ANNI_STIMATI": "",
                    "DETTAGLIO_PERIODI_IMPORTI": dettaglio,
                    "PERIODI_DETTAGLIO": dettaglio,
                    "MODALITA_PAGAMENTO": pagamento,
                    "IMPORTO_STANDARD": importo_fatt + importo_buo,
                    "FLAG_IMPORTO_ZERO": abs(float(importo)) < 0.0001,
                    "IMPORTO_FATTURE_RIGA": importo_fatt,
                    "IMPORTO_BUONI_RIGA": importo_buo,
                    "IMPORTO_NOTE_CREDITO": 0.0,
                    "FLAG_NOTA_CREDITO": False,
                    "COLONNA_IMPORTO": "MANUALE",
                    "SICILIA_RIF_FATTURE": "",
                    "SICILIA_BUONI": "",
                    "SICILIA_MODALITA_PAGAMENTO": "",
                    "RIGA_SHEET": "MANUALE",
                    "RIGA_GLOBALE": rid,
                    "TESTO_RIGA": f"INSERIMENTO MANUALE {cliente} {tipo} {format_euro(importo)} {mese} {anno}",
                    "DATA_INSERIMENTO_MANUALE": now,
                }
                manuali = carica_clienti_manuali()
                manuali = pd.concat([manuali, pd.DataFrame([record])], ignore_index=True)
                if salva_clienti_manuali(manuali):
                    registra_azione(
                        "INSERIMENTO CLIENTE MANUALE",
                        cliente=cliente,
                        zona=zona_finale,
                        agente=agente_finale,
                        dettaglio=f"{tipo} {mese} {anno}",
                        nuovo_valore=format_euro(importo),
                    )
                    # Porta subito l'utente sulla zona/agente appena inseriti e non far nascondere il nuovo record
                    # da eventuali filtri laterali rimasti attivi.
                    # I filtri della dashboard sono già istanziati in questo ciclo:
                    # salviamo la selezione desiderata e la applichiamo al prossimo rerun.
                    st.session_state["__dashboard_zone_after_manual_insert"] = zona_finale
                    st.session_state["__dashboard_agente_after_manual_insert"] = agente_finale if clean_text(agente_finale) else "TUTTI"
                    st.session_state["__dashboard_include_zero_after_manual_insert"] = bool(abs(float(importo)) < 0.0001)
                    st.success("Cliente/posizione inserito correttamente. La zona, i totali e la Vista Clienti sono stati aggiornati.")
                    st.rerun()



# ======================================================
# ELIMINAZIONE / RIPRISTINO CLIENTI-POSIZIONI
# ======================================================

def chiave_cliente_eliminazione(row):
    """Chiave stabile per nascondere una posizione cliente senza toccare il file originale."""
    try:
        stable_id = clean_text(row.get("ID_POSIZIONE_SSC", ""))
        if stable_id:
            return f"SSC|{stable_id}"
        foglio = clean_text(row.get("FOGLIO_ORIGINE", ""))
        riga = clean_text(row.get("RIGA_SHEET", ""))
        codice = format_codice_cliente(row.get("CODICE_CLIENTE", ""))
        cliente = clean_text(row.get("CLIENTE", ""))
        tipo = clean_text(row.get("TIPO_DOCUMENTO", ""))
        manual_id = clean_text(row.get("RIGA_GLOBALE", "")) if foglio.upper() == "MANUALE" else ""
        return f"{foglio}|{riga}|{codice}|{cliente}|{tipo}|{manual_id}"
    except Exception:
        return ""



def carica_clienti_eliminati():
    values=remote_state_get("deleted_clients",[]) or []
    baseline=st.session_state.get("current_baseline_hash","")
    return [str(x)[len(baseline)+1:] for x in values if str(x).startswith(baseline+":") and baseline]





def salva_clienti_eliminati(keys):
    if not can_edit():
        return False
    baseline=st.session_state.get("current_baseline_hash","")
    if not baseline:
        return False
    all_keys=remote_state_get("deleted_clients",[]) or []
    values=[k for k in all_keys if not str(k).startswith(baseline+":")]
    values += [baseline+":"+str(x) for x in dict.fromkeys(keys)]
    return remote_state_set("deleted_clients",values)




def applica_clienti_eliminati(db):
    if db is None or db.empty:
        return db
    keys = set(carica_clienti_eliminati())
    if not keys:
        return db
    out = db.copy()
    out["_CHIAVE_ELIMINAZIONE"] = out.apply(chiave_cliente_eliminazione, axis=1)
    out = out[~out["_CHIAVE_ELIMINAZIONE"].isin(keys)].copy()
    out = out.drop(columns=["_CHIAVE_ELIMINAZIONE"], errors="ignore")
    return out


def render_gestione_elimina_cliente(df_base):
    """Permette a Super Admin/Editor di eliminare una posizione cliente dal tool.
    L'eliminazione è logica: il file Excel originale resta intatto, ma la posizione
    viene nascosta dal DB pulito, dalle viste e dai totali. Può essere ripristinata.
    """
    if not can_edit():
        return
    if df_base is None or df_base.empty:
        return

    with st.expander("🗑️ Elimina / ripristina cliente o posizione", expanded=False):
        st.caption("Eliminazione logica: la posizione sparisce da Vista Clienti, totali zona e totali generali. Il file originale non viene modificato.")
        df = df_base.copy()
        df["_CHIAVE_ELIMINAZIONE"] = df.apply(chiave_cliente_eliminazione, axis=1)
        df["_LABEL_ELIMINAZIONE"] = df.apply(
            lambda r: f"{format_codice_cliente(r.get('CODICE_CLIENTE','')) or 's/c'} — {clean_text(r.get('CLIENTE',''))} — {clean_text(r.get('ZONA',''))} — {format_euro(to_number(r.get('IMPORTO_STANDARD')) or 0)} — riga {clean_text(r.get('RIGA_SHEET',''))}",
            axis=1,
        )
        options = df["_CHIAVE_ELIMINAZIONE"].tolist()
        labels = dict(zip(df["_CHIAVE_ELIMINAZIONE"], df["_LABEL_ELIMINAZIONE"]))

        if options:
            scelta = st.selectbox(
                "Cliente/posizione da eliminare",
                options=options,
                format_func=lambda x: labels.get(x, x),
                key="select_cliente_da_eliminare",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Elimina posizione selezionata", key="btn_elimina_cliente_posizione", width='stretch'):
                    eliminati = carica_clienti_eliminati()
                    if scelta not in eliminati:
                        eliminati.append(scelta)
                    if salva_clienti_eliminati(eliminati):
                        r = df[df["_CHIAVE_ELIMINAZIONE"] == scelta].iloc[0]
                        registra_azione(
                            "ELIMINAZIONE CLIENTE/POSIZIONE",
                            cliente=clean_text(r.get("CLIENTE", "")),
                            zona=clean_text(r.get("ZONA", "")),
                            agente=clean_text(r.get("AGENTE", "")),
                            dettaglio="Eliminazione logica da Vista Clienti e totali",
                            vecchio_valore=format_euro(to_number(r.get("IMPORTO_STANDARD")) or 0),
                            nuovo_valore="0,00 € / nascosto",
                        )
                        st.success("Cliente/posizione eliminato dal tool. Ricalcolo viste e totali...")
                        st.rerun()
            with c2:
                eliminati = carica_clienti_eliminati()
                st.metric("Posizioni eliminate", len(eliminati))

        eliminati = carica_clienti_eliminati()
        if eliminati:
            st.divider()
            rip = st.selectbox(
                "Ripristina posizione eliminata",
                options=[""] + eliminati,
                format_func=lambda x: "Seleziona..." if x == "" else x,
                key="select_cliente_da_ripristinare",
            )
            if rip and st.button("Ripristina posizione", key="btn_ripristina_cliente_posizione", width='stretch'):
                eliminati = [k for k in eliminati if k != rip]
                if salva_clienti_eliminati(eliminati):
                    registra_azione("RIPRISTINO CLIENTE/POSIZIONE", dettaglio=rip)
                    st.success("Posizione ripristinata. Ricalcolo viste e totali...")
                    st.rerun()


# ======================================================
# SNAPSHOT SALDI / DASHBOARD UNIFICATA
# ======================================================

SNAPSHOTS_FILE = Path(__file__).with_name("divispack_ssc_snapshots.json")



def _snapshot_summary(db):
    if db is None or db.empty:
        return {'schema_version':3,'totale':0,'fatture':0,'buoni':0,'note_credito':0,'clienti':0,'zone':[],'posizioni_cliente':[]}
    base=db.copy()
    def entity(r):
        code=format_codice_cliente(r.get('CODICE_CLIENTE',''))
        return 'COD:'+code if code and code.lower() not in ['nan','none'] else 'NOME:'+_identity_value(r.get('CLIENTE',''))
    base['__entity']=base.apply(entity,axis=1)
    rows=[]
    for key,part in base.groupby('__entity',sort=True):
        def vals(c):return ' | '.join(dict.fromkeys(clean_text(v) for v in part.get(c,pd.Series(dtype=str)) if clean_text(v)))
        rows.append({'entity_key':key,'cliente':vals('CLIENTE'),'cliente_padre':vals('CLIENTE_PADRE'),
            'codice_cliente':vals('CODICE_CLIENTE'),'zona':vals('ZONA'),'agente':vals('AGENTE'),
            'totale':round(float(part['IMPORTO_STANDARD'].sum()),2),'fatture':round(float(part['IMPORTO_FATTURE_RIGA'].sum()),2),
            'buoni':round(float(part['IMPORTO_BUONI_RIGA'].sum()),2),'n_fatture':float(part['NUM_FATTURE'].sum()),
            'n_buoni':float(part['NUM_BUONI'].sum()),'periodi':vals('PERIODI_DETTAGLIO') or vals('PERIODI_RIFERIMENTO')})
    return {'schema_version':3,'totale':round(float(base['IMPORTO_STANDARD'].sum()),2),
        'fatture':round(float(base['IMPORTO_FATTURE_RIGA'].sum()),2),'buoni':round(float(base['IMPORTO_BUONI_RIGA'].sum()),2),
        'note_credito':round(float(base['IMPORTO_NOTE_CREDITO'].sum()),2),'clienti':len(rows),
        'zone':sorted(base['ZONA'].dropna().astype(str).unique().tolist()),'posizioni_cliente':rows}





def carica_snapshots():
    return remote_state_get("ssc_snapshots",[]) or []






def salva_snapshot_se_nuovo(file_bytes, file_name, db_originale):
    # Solo usata se il confronto è richiesto: nessuna scrittura di snapshot in lettura.
    digest = hashlib.sha256(file_bytes).hexdigest()
    current = snapshot_for_file(file_bytes, file_name, st.session_state.get("view_reference_date", ""))
    snaps = carica_snapshots()
    before = [s for s in snaps if s.get("file_hash") != digest]
    return current, (before[-1] if before else None), False







def confronto_snapshot_clienti(current,previous):
    events=crea_eventi_variazione_nuovo_saldi(current,previous)
    if not events:return pd.DataFrame()
    return pd.DataFrame([{'CLIENTE':e['CLIENTE'],'ZONA':e['ZONA'],'AGENTE':e['AGENTE'],
      'PRECEDENTE':e['SALDO_PRECEDENTE'],'ATTUALE':e['SALDO_NUOVO'],'VARIAZIONE':e['VARIAZIONE_SALDO'],
      'ESITO':e['TIPO_MOVIMENTO'],'PERIODI_PRECEDENTI':e['PERIODI_PRECEDENTI'],'PERIODI_ATTUALI':e['PERIODI_NUOVI']} for e in events]).sort_values('VARIAZIONE',ascending=False,na_position='last')




def estrai_anni_disponibili(df):
    anni = set()
    if df is None or df.empty:
        return []
    for col in ["ANNI_RIFERIMENTO", "PERIODI_ORDINABILI", "DETTAGLIO_PERIODI_IMPORTI"]:
        if col not in df.columns:
            continue
        for value in df[col].fillna(""):
            anni.update(_estrai_anni_da_valore(value))
    return sorted(anni, reverse=True)


def filtra_anno_esatto(df, anno):
    if df is None or df.empty or anno in [None, "TUTTI"]:
        return df
    anno = int(anno)
    def _match(row):
        for col in ["ANNI_RIFERIMENTO", "PERIODI_ORDINABILI", "DETTAGLIO_PERIODI_IMPORTI"]:
            if col in row.index and anno in _estrai_anni_da_valore(row.get(col, "")):
                return True
        return False
    return df[df.apply(_match, axis=1)].copy()


def render_zone_selector_dashboard(df):
    zone = sorted([z for z in df.get("ZONA", pd.Series(dtype=str)).dropna().unique() if clean_text(z)])
    if "dashboard_zona" not in st.session_state:
        st.session_state["dashboard_zona"] = "TUTTE"
    active = st.session_state.get("dashboard_zona", "TUTTE")
    if active != "TUTTE" and active not in zone:
        st.session_state["dashboard_zona"] = "TUTTE"
        active = "TUTTE"

    st.markdown("### Zone")
    buttons = [("Tutte", "TUTTE", True)] + [(str(z).title(), z, False) for z in zone]
    per_row = 6
    for start in range(0, len(buttons), per_row):
        row_buttons = buttons[start:start + per_row]
        cols = st.columns(per_row)
        for i, (label, value, neutral) in enumerate(row_buttons):
            with cols[i]:
                if render_zone_filter_button(label, value, active=(active == value), neutral=neutral):
                    st.session_state["dashboard_zona"] = value
                    active = value
    return active


def applica_filtri_dashboard(db, registro=None, controllo_periodi=None):
    df = db.copy()
    st.session_state["__period_view_readonly"] = False
    st.session_state["__period_projection"] = False

    # Se arriva da un inserimento manuale, applichiamo le preferenze prima
    # di creare i widget del nuovo ciclo Streamlit.
    if st.session_state.pop("__reset_dashboard_filters", False):
        st.session_state["dashboard_zona"] = "TUTTE"
        st.session_state["dash_agente"] = "TUTTI"
        st.session_state["dash_cliente"] = "TUTTI"
        st.session_state["dash_tipo"] = []
        st.session_state["dash_componenti_v2"] = []
        st.session_state["dash_anno"] = "TUTTI"
        st.session_state["dash_mesi_v3"] = []
        st.session_state["dash_focus"] = "Tutto"
        st.session_state["dash_includi_zero"] = False

    pending_zone = st.session_state.pop("__dashboard_zone_after_manual_insert", None)
    pending_agent = st.session_state.pop("__dashboard_agente_after_manual_insert", None)
    pending_zero = st.session_state.pop("__dashboard_include_zero_after_manual_insert", None)
    if pending_zone:
        st.session_state["dashboard_zona"] = pending_zone
    if pending_agent:
        st.session_state["dash_agente"] = pending_agent
    if pending_zero is not None:
        st.session_state["dash_includi_zero"] = bool(pending_zero)

    zona = render_zone_selector_dashboard(df)
    if zona != "TUTTE":
        df = df[df["ZONA"] == zona].copy()

    c1, c2, c3, c4 = st.columns(4)

    agenti = ["TUTTI"] + sorted([a for a in df["AGENTE"].dropna().unique() if clean_text(a)])
    if st.session_state.get("dash_agente", "TUTTI") not in agenti:
        st.session_state["dash_agente"] = "TUTTI"
    agente = c1.selectbox("Agente", agenti, key="dash_agente")
    if agente != "TUTTI":
        df = df[df["AGENTE"] == agente].copy()

    clienti = ["TUTTI"] + sorted([a for a in df["CLIENTE_PADRE"].dropna().unique() if clean_text(a)])
    if st.session_state.get("dash_cliente", "TUTTI") not in clienti:
        st.session_state["dash_cliente"] = "TUTTI"
    cliente = c2.selectbox("Cliente", clienti, key="dash_cliente")
    if cliente != "TUTTI":
        df = df[df["CLIENTE_PADRE"] == cliente].copy()

    tipi = sorted([a for a in df["TIPO_DOCUMENTO"].dropna().unique() if clean_text(a)])
    selected_types = [x for x in st.session_state.get("dash_tipo", []) if x in tipi]
    if selected_types != st.session_state.get("dash_tipo", []):
        st.session_state["dash_tipo"] = selected_types
    tipo_sel = c3.multiselect("Posizioni con", ["Fatture", "Buoni / SSC", "Note credito / resi"], key="dash_componenti_v2")
    if tipo_sel:
        mask = pd.Series(False, index=df.index)
        if "Fatture" in tipo_sel:
            mask |= df["IMPORTO_FATTURE_RIGA"].abs().ge(0.005)
        if "Buoni / SSC" in tipo_sel:
            mask |= df["IMPORTO_BUONI_RIGA"].abs().ge(0.005)
        if "Note credito / resi" in tipo_sel:
            mask |= df["FLAG_NOTA_CREDITO"].fillna(False)
        df = df[mask].copy()
        st.caption("Filtro su clienti/posizioni: sono incluse anche quelle miste. Il totale conserva tutte le loro componenti.")

    reg = registro if registro is not None else costruisci_registro_periodi(db, st.session_state.get("view_reference_date", ""))[0]
    scoped = reg[reg["ID_POSIZIONE_SSC"].isin(df["ID_POSIZIONE_SSC"])].copy()
    anni = ["TUTTI"] + [str(y) for y in sorted(scoped["ANNO"].dropna().unique(), reverse=True)]
    if st.session_state.get("dash_anno", "TUTTI") not in anni:
        st.session_state["dash_anno"] = "TUTTI"
    anno = c4.selectbox("Anno dei documenti", anni, key="dash_anno")
    mesi = st.multiselect("Mesi dei documenti", list(MESE_NOMI_V3), format_func=lambda m:MESE_NOMI_V3[m], key="dash_mesi_v3")
    period_selected = anno != "TUTTI" or bool(mesi)
    mode = "Saldo completo dei clienti"
    if period_selected:
        mode = st.radio("Quali importi vuoi leggere?", ["Quote documentate del periodo", "Saldo completo dei clienti"], horizontal=True, key="ssc_period_mode")
    c5, c6 = st.columns([2.3, 1])
    focus = c5.selectbox(
        "Focus",
        ["Tutto", "Note credito / Resi", "Clienti raggruppati +", "Da verificare", "Saldo zero", "Solo Sicilia"],
        key="dash_focus",
    )
    includi_zero = c6.checkbox(
        "Includi saldo 0",
        value=st.session_state.get("dash_includi_zero", False),
        key="dash_includi_zero",
    )

    if not includi_zero and focus != "Saldo zero" and "FLAG_IMPORTO_ZERO" in df.columns:
        df = df[df["FLAG_IMPORTO_ZERO"] == False].copy()

    if focus == "Note credito / Resi":
        df = df[df["FLAG_NOTA_CREDITO"] == True].copy()
    elif focus == "Clienti raggruppati +":
        df = df[df["FLAG_PLUS"] == True].copy()
    elif focus == "Da verificare":
        df = df[df["TIPO_DOCUMENTO"] == "DA_VERIFICARE"].copy()
    elif focus == "Saldo zero":
        df = df[df["TIPO_DOCUMENTO"] == "SALDO_ZERO"].copy()
    elif focus == "Solo Sicilia":
        df = df[df["ZONA"].astype(str).str.upper().str.contains("SICILIA", na=False)].copy()

    if period_selected:
        if mode == "Quote documentate del periodo":
            source_filtered = df.copy()
            df, evidenze = seleziona_quote_periodo(df, reg, anno, mesi)
            st.session_state["__period_view_readonly"] = True
            st.session_state["__period_projection"] = True
            unknown = int(pd.to_numeric(df.get("IMPORTO_STANDARD",pd.Series(dtype=float)),errors="coerce").isna().sum())
            st.info("Quote del periodo selezionato. Se una posizione si riferisce interamente a un solo mese, o tutti i suoi mesi rientrano nel filtro, viene incluso il suo importo intero una sola volta. N/D resta solo quando non si puo' attribuire il saldo al periodo: nessuna divisione per numero fatture.")
            if unknown:st.warning(f"{unknown} posizioni del periodo hanno riferimenti o conteggi, ma non importi attribuibili. Non entrano nel totale monetario del periodo.")
            if not evidenze.empty and evidenze["ANNO_DA_DATA_SALDI"].any():
                st.caption("Per i mesi senza anno nel file viene usato l’anno della situazione SALDI; gli anni espliciti restano invariati.")
            if controllo_periodi is not None and not controllo_periodi.empty:
                unresolved = controllo_periodi[controllo_periodi["ID_POSIZIONE_SSC"].isin(source_filtered["ID_POSIZIONE_SSC"]) & controllo_periodi["IMPORTO_NON_RIPARTITO"].abs().ge(.005)]
                whole_scope_count = len(df.attrs.get("whole_scope_ids", []))
                st.caption(f"Dettaglio mensile: {len(unresolved)} posizioni del perimetro hanno somme non ripartite per singolo mese. Di queste, {whole_scope_count} sono incluse per intero nel filtro perche' tutti i loro riferimenti sono selezionati; gli importi dei singoli mesi restano non ripartiti.")
                if not unresolved.empty and st.checkbox("Mostra importi non ripartiti / dettagli da aggiornare",key="ssc_period_unallocated"):
                    st.dataframe(prepara_display(unresolved.drop(columns=["ID_POSIZIONE_SSC"])),width="stretch",hide_index=True)
        else:
            evidence = reg[reg["ID_POSIZIONE_SSC"].isin(df["ID_POSIZIONE_SSC"])]
            if anno != "TUTTI":evidence = evidence[evidence["ANNO"].eq(int(anno))]
            if mesi:evidence = evidence[evidence["MESE"].isin(mesi)]
            df = df[df["ID_POSIZIONE_SSC"].isin(evidence["ID_POSIZIONE_SSC"])].copy()
            st.warning("Questa modalità cerca clienti con quei riferimenti e mantiene il loro saldo INTERO. Non è il totale del mese/anno.")
    if st.checkbox("Mostra dettaglio per mese",key="ssc_show_month_register"):
        evidence = reg[reg["ID_POSIZIONE_SSC"].isin(df["ID_POSIZIONE_SSC"])].copy()
        if anno != "TUTTI":evidence=evidence[evidence["ANNO"].eq(int(anno))]
        if mesi:evidence=evidence[evidence["MESE"].isin(mesi)]
        st.dataframe(prepara_display(evidence.drop(columns=["ID_POSIZIONE_SSC"])),width="stretch",hide_index=True)

    if st.button("Reset filtri", key="btn_reset_dashboard_filters"):
        st.session_state["__reset_dashboard_filters"] = True
        st.rerun()

    return df



def _periodo_piu_vecchio_mesi(value):
    tokens = re.findall(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", clean_text(value))
    if not tokens:
        return None
    dates = [(int(y), int(m)) for y, m in tokens]
    y, m = min(dates)
    now = datetime.now()
    return max(0, (now.year - y) * 12 + (now.month - m))


def priorita_operativa_clienti(df):
    if df is None or df.empty:
        return pd.DataFrame()
    tab = riepilogo_per(df, ["CLIENTE_PADRE", "ZONA", "AGENTE"])
    if tab.empty:
        return tab
    tab["MESI_ANZIANITA"] = tab["PERIODI_ORDINABILI"].apply(_periodo_piu_vecchio_mesi)
    # Nessun rating inventato: prima anzianità, poi importo.
    tab["MESI_ANZIANITA_SORT"] = pd.to_numeric(tab["MESI_ANZIANITA"], errors="coerce").fillna(-1)
    tab = tab.sort_values(["MESI_ANZIANITA_SORT", "IMPORTO_TOTALE"], ascending=[False, False])
    return tab.drop(columns=["MESI_ANZIANITA_SORT"], errors="ignore")



def render_snapshot_delta(current_snapshot, previous_snapshot):
    if not previous_snapshot:
        st.caption("Snapshot iniziale salvato. Il confronto comparirà al prossimo SALDI differente.")
        return

    st.markdown("### Confronto tra le due situazioni SALDI")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Saldo file",
        format_euro(current_snapshot.get("totale", 0)),
        format_euro(current_snapshot.get("totale", 0) - previous_snapshot.get("totale", 0)),
    )
    c2.metric(
        "Fatture file",
        format_euro(current_snapshot.get("fatture", 0)),
        format_euro(current_snapshot.get("fatture", 0) - previous_snapshot.get("fatture", 0)),
    )
    c3.metric(
        "Buoni / SSC file",
        format_euro(current_snapshot.get("buoni", 0)),
        format_euro(current_snapshot.get("buoni", 0) - previous_snapshot.get("buoni", 0)),
    )
    c4.metric(
        "Clienti file",
        int(current_snapshot.get("clienti", 0)),
        int(current_snapshot.get("clienti", 0) - previous_snapshot.get("clienti", 0)),
    )
    st.caption(
        f"Confronto: {previous_snapshot.get('file_name','precedente')} → "
        f"{current_snapshot.get('file_name','attuale')}."
    )

    mostra_variazioni = st.checkbox(
        "Mostra variazioni clienti",
        value=False,
        key="mostra_variazioni_snapshot",
    )
    if not mostra_variazioni:
        return

    diff = confronto_snapshot_clienti(current_snapshot, previous_snapshot)
    if not diff.empty:
        inc = diff.head(10)
        dec = diff.sort_values("VARIAZIONE").head(10)
        a, b = st.columns(2)
        with a:
            st.markdown("**Maggiori aumenti**")
            st.dataframe(prepara_display(inc), width="stretch", hide_index=True)
        with b:
            st.markdown("**Maggiori diminuzioni**")
            st.dataframe(prepara_display(dec), width="stretch", hide_index=True)




@st.cache_data(max_entries=3, show_spinner=False)
def costruisci_excel_export(db_pulito, db_originale, debug_df, storico_visibile, eliminati):
    """Stessi fogli, generati una volta per dati identici. Nessun accesso di rete."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        db_pulito.to_excel(writer, index=False, sheet_name="DB_PULITO_AGGIORNATO")
        db_originale.to_excel(writer, index=False, sheet_name="DB_ORIGINALE_DA_FILE")
        riepilogo_per(db_pulito, ["ZONA"]).to_excel(writer, index=False, sheet_name="RIEPILOGO_ZONE")
        riepilogo_per(db_pulito, ["AGENTE"]).to_excel(writer, index=False, sheet_name="RIEPILOGO_AGENTI")
        riepilogo_per(
            db_pulito,
            ["CLIENTE_PADRE", "CLIENTE", "AGENTE", "ZONA"],
        ).to_excel(writer, index=False, sheet_name="RIEPILOGO_CLIENTI")
        db_pulito[db_pulito["FLAG_PLUS"] == True].to_excel(
            writer, index=False, sheet_name="CLIENTI_PLUS"
        )
        db_pulito[
            db_pulito["FOGLIO_ORIGINE"].astype(str).str.upper() == "SICILIA"
        ].to_excel(writer, index=False, sheet_name="DETTAGLIO_SICILIA")
        db_pulito[db_pulito["FLAG_NOTA_CREDITO"] == True].to_excel(
            writer, index=False, sheet_name="NOTE_CREDITO_RESI"
        )
        db_pulito[db_pulito["TIPO_DOCUMENTO"] == "DA_VERIFICARE"].to_excel(
            writer, index=False, sheet_name="DA_VERIFICARE"
        )

        if not storico_visibile.empty:
            storico_visibile.to_excel(writer, index=False, sheet_name="STORICO_PAGAMENTI")
        eliminati_export = pd.DataFrame({"CHIAVE_ELIMINAZIONE": list(eliminati)})
        if not eliminati_export.empty:
            eliminati_export.to_excel(writer, index=False, sheet_name="CLIENTI_ELIMINATI")

        debug_df.to_excel(writer, index=False, sheet_name="DEBUG")

    return output.getvalue()

def render_export_area(df_view, db_pulito, db_originale, debug_df):
    """Costruisce export solo su richiesta esplicita."""
    prepara_export = st.checkbox(
        "Esporta dati",
        value=False,
        key="prepara_export_dati",
    )
    if not prepara_export:
        return

    csv = df_view.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        label="Scarica CSV filtrato",
        data=csv,
        file_name="DB_PULITO_SSC_FILTRATO.csv",
        mime="text/csv",
        key="download_csv_filtrato_unificato",
    )

    prepara_excel = st.checkbox(
        "Prepara anche Excel completo",
        value=False,
        key="prepara_excel_completo",
        help="Richiede più elaborazione; attivalo solo quando serve.",
    )
    if not prepara_excel:
        return

    with st.spinner("Preparazione Excel completo..."):
        storico_export = normalizza_storico(carica_storico_pagamenti())
        storico_visibile = storico_export if can_view_user_audit() else storico_colonne_pubbliche(storico_export)
        excel_bytes = costruisci_excel_export(
            db_pulito, db_originale, debug_df, storico_visibile,
            tuple(carica_clienti_eliminati()),
        )
    st.download_button(
        label="Scarica Excel completo",
        data=excel_bytes,
        file_name="DB_PULITO_SSC.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_excel_completo_unificato",
    )



# ======================================================
# CACHE FILE CARICATO
# ======================================================
# Serve per non perdere il file quando i filtri rapidi ricaricano la pagina.
# Non è un database: è solo l'ultimo Excel caricato, salvato localmente nella cartella dell'app.
LAST_UPLOAD_FILE = Path(__file__).with_name("divispack_last_upload.xlsx")
LAST_UPLOAD_META = Path(__file__).with_name("divispack_last_upload_meta.json")



def salva_file_caricato_in_cache(uploaded_file):
    raise StorageError("Upload diretto disabilitato: usare anteprima e conferma.")





def recupera_file_caricato_da_cache():
    data, name, _ = remote_load_active_ssc()
    return data, name



# ======================================================
# APP - STRUTTURA UNIFICATA
# ======================================================


class StorageError(RuntimeError):
    pass


@st.cache_data(ttl=15, max_entries=4, show_spinner=False)
def storage_manifest_cached(url, token):
    return storage_api_call("upload_manifest_v2")


def remote_manifest(force=False):
    if force:
        storage_manifest_cached.clear()
        operational_bundle_cached.clear()
    if not force and isinstance(_RUN_BUNDLE, dict):
        return _RUN_BUNDLE
    return storage_manifest_cached(*get_storage_api_config())



@st.cache_data(max_entries=8, show_spinner=False)
def remote_file_cached(url, token, file_hash):
    # Un hash SHA256 identifica byte immutabili: nessun download ogni 5 minuti.
    result = storage_api_call("upload_get_v2", {"file_hash": file_hash}, timeout=120)
    if not result.get("found"):
        raise StorageError("Versione SALDI non trovata nell’archivio.")
    raw = base64.b64decode(result["file_base64"], validate=True)
    if hashlib.sha256(raw).hexdigest() != file_hash:
        raise StorageError("Integrità del file archiviato non verificata.")
    return raw, result



@st.cache_data(max_entries=128, show_spinner=False)
def verify_password(password, encoded):
    try:
        if str(encoded).startswith("pbkdf2_sha256$"):
            _, rounds, salt, expected = str(encoded).split("$")
            value = hashlib.pbkdf2_hmac("sha256", str(password).encode(), bytes.fromhex(salt), int(rounds)).hex()
            return hmac.compare_digest(value, expected)
        return bool(encoded) and hmac.compare_digest(hashlib.sha256(str(password).encode()).hexdigest(), str(encoded))
    except (ValueError, TypeError):
        return False


def can_activate_saldi():
    return is_super_admin() and bool(st.session_state.get("__storage_ready", False))


def canonical_sheet(name):
    return re.sub(r"\s+", " ", str(name or "")).strip().upper()


def excel_format_from_bytes(raw):
    if not isinstance(raw,(bytes,bytearray)) or not raw:
        raise ValueError("Il file è vuoto.")
    if len(raw)>10*1024*1024:
        raise ValueError("File superiore a 10 MB: non attivato. Controllare l'export.")
    if raw[:8]==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return "xls", "xlrd"
    if raw[:4]==b'PK\x03\x04':
        with zipfile.ZipFile(BytesIO(raw)) as z:
            if "xl/workbook.xml" not in z.namelist():
                raise ValueError("Il file non è un foglio Excel .xlsx leggibile.")
            if sum(x.file_size for x in z.infolist()) > 100*1024*1024:
                raise ValueError("File Excel espanso troppo grande: caricamento interrotto.")
        return "xlsx", "openpyxl"
    raise ValueError("Formato non riconosciuto. Esportare un vero Excel .xls o .xlsx: rinominare l'estensione non converte il file.")


def xlsx_formula_metadata(raw):
    """Legge le formule XML senza ricalcolare né modificare il workbook."""
    out={}; ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    relns={'r':'http://schemas.openxmlformats.org/package/2006/relationships'}
    with zipfile.ZipFile(BytesIO(raw)) as z:
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        rel=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        paths={r.get('Id'):r.get('Target') for r in rel}
        for sh in wb.find('s:sheets',ns):
            target=paths[sh.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
            root=ET.fromstring(z.read(path)); formulas={}
            for c in root.findall('.//s:c',ns):
                f=c.find('s:f',ns)
                if f is not None and f.text:
                    formulas[c.get('r')]=f.text
            out[canonical_sheet(sh.get('name'))]=formulas
    return out


def sum_range_cells(formula):
    """Solo SUM/SOMMA di riferimenti locali. Nessuna valutazione arbitraria."""
    text=str(formula or '').strip().lstrip('=').upper().replace('$','')
    m=re.fullmatch(r'(?:SUM|SOMMA)\(([^()]*)\)',text)
    if not m:
        return None
    result=set()
    for part in re.split('[;,]',m.group(1)):
        part=part.strip()
        r=re.fullmatch(r'([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?',part)
        if not r: return None
        c1=c2=r.group(1); a=int(r.group(2)); b=a
        if r.group(3):c2=r.group(3);b=int(r.group(4))
        def colnum(s):
            n=0
            for ch in s:n=n*26+ord(ch)-64
            return n
        ca,cb=colnum(c1),colnum(c2)
        if a>b or ca>cb or (b-a+1)*(cb-ca+1)>100000:return None
        for rn in range(a,b+1):
            for cn in range(ca,cb+1):result.add((rn,cn))
    return result


def arricchisci_blocchi_puglia(db, sheet, name):
    out=db.copy(); mask=out['FOGLIO_ORIGINE'].map(canonical_sheet).eq(canonical_sheet(name))
    forms=sheet.attrs.get('ssc_formulas',{})
    identified=set()
    for idx,row in sheet.iterrows():
        txt=' '.join(clean_upper(v) for v in row)
        label='VALERIA' if 'TOTALE CLIENTI VALERIA' in txt else ('PUGLIA PRINCIPALE' if 'TOTALI AL' in txt else None)
        if not label:continue
        for col in sheet.columns:
            cell=excel_col(int(col)+1)+str(int(idx)+1)
            refs=sum_range_cells(forms.get(cell))
            if refs is None:continue
            rows={r-1 for r,c in refs}
            sel=mask & pd.to_numeric(out['RIGA_SHEET'],errors='coerce').isin(rows)
            out.loc[sel,'PUGLIA_GRUPPO']=label
            identified |= set(out.index[sel])
            if label=='VALERIA':
                missing=out['AGENTE'].fillna('').astype(str).str.upper().isin(['','NON ASSEGNATO','NAN'])
                out.loc[sel & missing,'AGENTE']='VALERIA'
    # .xls: niente formule leggibili via xlrd. Si conservano i saldi senza
    # attribuire un agente o un blocco basandosi sulla coincidenza del totale.
    return out


def excel_col(n):
    s=''
    while n:
        n,r=divmod(n-1,26);s=chr(65+r)+s
    return s


def sorgente_documentale(row,mapping):
    parts=[]
    for key in ('documento','riferimento'):
        c=mapping.get(key)
        if c is not None:
            v=clean_text(row[c])
            if v and v not in parts:parts.append(v)
    return ' | '.join(parts)


def parse_period_evidence(txt, anno_default=None):
    text = re.sub(r"\s+", " ", clean_text(txt))
    if not text:
        return []
    default = str(anno_default or _SSC_PARSE_YEAR.get() or datetime.now().year)
    months = "|".join(sorted(MESE_ALIASES, key=len, reverse=True))
    matches = list(re.finditer(rf"\b(?P<mese>{months})\b\.?", text, re.I))
    items = []
    for m in matches:
        tail = text[m.end():]
        ym = re.match(r"\s*(?:(20\d{2}|19\d{2})(?![\d.,])|['’](\d{2})(?!\d)|(\d{2})['’](?!\d))", tail)
        year, end = "", m.end()
        if ym:
            year = normalizza_anno(next(x for x in ym.groups() if x))
            end += ym.end()
        items.append({"mese": MESE_ALIASES.get(m.group("mese").upper(), m.group("mese").title()),
                      "anno": year, "stimato": not bool(year), "start": m.start(), "end": end,
                      "amount": None, "count": None})
    explicit = {x["anno"] for x in items if x["anno"]}
    shared = next(iter(explicit)) if len(explicit) == 1 else ""
    # Importi monetari: decimali italiani, separatori migliaia o simbolo euro.
    # "4 Apr.25'" resta un conteggio, non quattro euro.
    money = r"(?:[-−]\s*)?€\s*(?:[-−]\s*)?\d[\d.]*(?:,\d{1,2})?|(?:[-−]\s*)?(?:€\s*)?(?:[-−]\s*)?(?:\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+,\d{1,2}|\d+\.\d{2}(?!\d)|\d+(?=\s*€))\s*€?"
    for i, item in enumerate(items):
        if not item["anno"]:
            item["anno"] = shared or default
            item["stimato"] = not bool(shared)
        before = text[items[i-1]["end"] if i else 0:item["start"]]
        am = re.search(r"(?<![\w.,])(" + money + r")\s*$", before)
        if not am:
            after = text[item["end"]:items[i+1]["start"] if i+1<len(items) else len(text)]
            am = re.match(r"\s*[:=]\s*(" + money + r")", after)
        if am:
            item["amount"] = monetary_value(am.group(1))
        else:
            cm = re.search(r"(?<![\d.,])(?P<n>\d{1,3})\s*(?:(?:FT\.?|FATTURE?)\s*)?$", before, re.I)
            if not cm:
                after = text[item["end"]:items[i+1]["start"] if i+1<len(items) else len(text)]
                cm = re.match(r"\s*\(\s*(?P<n>\d+)\s*(?:FATTURA|FATTURE|FT\.?)\s*\)", after, re.I)
            if cm:
                item["count"] = int(cm.group("n"))
    return items



@st.cache_data(max_entries=12, show_spinner=False)
def snapshot_for_file(raw, name, reference_date=""):
    _, _, _, db, _, _ = prepara_saldi_base_cached(raw, reference_date)
    return {"file_hash": hashlib.sha256(raw).hexdigest(), "file_name": name,
            "reference_date": reference_date, "parser_build": APP_BUILD, **_snapshot_summary(db)}



def reset_remote_views():
    global _RUN_BUNDLE
    _RUN_BUNDLE = None
    remote_state_get_cached.clear()
    storage_manifest_cached.clear()
    storage_health_cached.clear()
    operational_bundle_cached.clear()
    audit_page_cached.clear()
    st.session_state.pop("__ready_dataset", None)
    st.session_state.pop("__quadratura_cache_key", None)
    st.session_state.pop("__quadratura_cache_value", None)



def data_riferimento_da_fogli(sheets):
    dates=[];months='|'.join(sorted(MESE_ALIASES,key=len,reverse=True))
    for name,sh in sheets.items():
        for _,row in sh.iterrows():
            txt=' '.join(clean_text(v) for v in row)
            if not re.search(r'\b(?:SALDI|TOTALI|TOTALE)\b',txt,re.I):continue
            m=re.search(rf'\b(\d{{1,2}})\s+({months})\s+(20\d{{2}})\b',txt,re.I)
            if m:
                try:dates.append(datetime(int(m.group(3)),mese_numero(MESE_ALIASES.get(m.group(2).upper(),m.group(2))),int(m.group(1))).date())
                except ValueError:pass
    return max(dates) if dates else datetime.now().date()


def render_upload_controllato(manifest):
    if not can_activate_saldi():return
    show=st.checkbox('Aggiorna situazione SALDI / archivio',value=not bool(manifest.get('active')),key='ssc_update_panel')
    if not show:return
    st.caption('Il file corrente cambia solo dopo lettura, anteprima e conferma. Selezionare un file non lo pubblica.')
    upload=st.file_uploader('Nuovo SALDI (.xls o .xlsx)',type=['xls','xlsx'],key='ssc_staging_uploader')
    raw=None;name=''
    mode=st.radio('Origine file',['Nuovo caricamento','Versione archiviata'],horizontal=True,key='ssc_upload_mode')
    if mode=='Nuovo caricamento' and upload is not None:
        raw,name=upload.getvalue(),upload.name
    elif mode=='Versione archiviata':
        arch=manifest.get('uploads',[])
        if arch:
            choices={x['file_hash']:x for x in arch}
            h=st.selectbox('File archiviato',list(choices),format_func=lambda k:choices[k].get('file_name','')+' — '+str(choices[k].get('uploaded_at','')),key='ssc_archived_choice')
            if st.checkbox('Apri anteprima della versione scelta',key='ssc_restore_preview'):
                try:raw,meta=remote_file_cached(*get_storage_api_config(),h);name=meta['file_name']
                except StorageError as e:st.error(str(e))
    if raw is None:return
    try:
        _,_,sheets,db,_,_=prepara_saldi_base_cached(raw)
        digest=hashlib.sha256(raw).hexdigest()
        snap=snapshot_for_file(raw,name)
    except Exception as exc:
        st.error(str(exc));st.info('La situazione corrente non è stata sostituita.');return
    current=manifest.get('active') or {}
    if digest==current.get('file_hash') and current.get('reference_date'):
        st.info('Questo è già il file corrente. Nessuna duplicazione o riapplicazione dello storico.');return
    prev=None
    if current.get('file_hash') and current['file_hash']!=digest:
        try:
            oldbytes,_=remote_file_cached(*get_storage_api_config(),current['file_hash'])
            prev=snapshot_for_file(oldbytes,current['file_name'],current.get('reference_date',''))
        except Exception:
            st.warning('Impossibile confrontare il file precedente: non verranno inventate variazioni di saldo.')
    a,b,c=st.columns(3)
    a.metric('Saldo letto dal nuovo file',format_euro(snap['totale']))
    b.metric('Clienti nel nuovo file',snap['clienti']);c.metric('Zone',len(snap['zone']))
    missing=sorted(set((prev or {}).get('zone',[]))-set(snap['zone']))
    if missing:st.warning('Zone non presenti rispetto al precedente: '+', '.join(missing))
    events=crea_eventi_variazione_nuovo_saldi(snap,prev)
    if events:
        st.dataframe(prepara_display(pd.DataFrame(events)[['CLIENTE','TIPO_MOVIMENTO','SALDO_PRECEDENTE','SALDO_NUOVO','VARIAZIONE_SALDO']]),width='stretch',hide_index=True)
    key=digest[:16]
    # Congela le versioni dell'anteprima: un cambiamento concorrente la invalida.
    pending=st.session_state.get('__pending_upload')
    if not pending or pending['hash']!=digest:
        st.session_state['__pending_upload']={'hash':digest,'request_id':str(uuid.uuid4()),'versions':dict(manifest.get('versions',{}))}
    pending=st.session_state['__pending_upload']
    with st.form('ssc_activate_'+key):
        date=st.date_input('Data ufficiale della situazione (non data di caricamento)',value=data_riferimento_da_fogli(sheets),key='ssc_date_'+key)
        confirmed=st.checkbox('Ho controllato perimetro e differenze. Questo file diventa la situazione ufficiale; le vecchie modifiche non verranno sottratte di nuovo.',key='ssc_confirm_'+key)
        submit=st.form_submit_button('Conferma situazione ufficiale',type='primary')
    if not submit:return
    if not confirmed:st.warning('Confermare il controllo prima di attivare.');return
    snap = snapshot_for_file(raw, name, date.isoformat())
    events = crea_eventi_variazione_nuovo_saldi(snap, prev)
    versions=pending['versions']
    p={'file_hash':digest,'file_name':name,'file_base64':base64.b64encode(raw).decode(),
        'reference_date':date.isoformat(),'snapshot':snap,'previous_snapshot':prev,'events':events,
        'expected':{k:int(versions.get(k,0)) for k in ['active_upload','payment_history','ssc_snapshots']},
        'request_id':pending['request_id'],'actor':st.session_state['current_user']['username']}
    try:
        storage_api_call('upload_activate_v2',p,timeout=120)
    except StorageError as exc:
        st.error(str(exc));st.session_state.pop('__pending_upload',None);reset_remote_views();return
    reset_remote_views()
    st.session_state.pop('__pending_upload',None)
    st.session_state['__saved_notice']='Nuova situazione ufficiale salvata nell’archivio condiviso.'
    st.session_state['__close_update_panel'] = True
    st.rerun()


def righe_fuori_formula(sheets, db):
    evidence=[]
    for name,sh in sheets.items():
        forms=sh.attrs.get('ssc_formulas',{})
        if not forms:continue
        part=db[db['FOGLIO_ORIGINE'].map(canonical_sheet).eq(canonical_sheet(name))]
        if part.empty:continue
        for addr,formula in forms.items():
            rn=int(re.search(r'\d+',addr).group())
            if rn>len(sh):continue
            text=' '.join(clean_upper(v) for v in sh.iloc[rn-1])
            if not re.search(r'\bTOTAL[EI]\b',text):continue
            refs=sum_range_cells(formula)
            if refs is None or not refs:continue
            # Solo confronto di colonna monetaria singola; non espande formule complesse.
            columns={c for r,c in refs}
            if len(columns)!=1:continue
            col=next(iter(columns)); covered={r for r,c in refs}
            # Esclude righe clienti riferite ad altro totale dello stesso foglio.
            othercovered=set()
            for aa,ff in forms.items():
                if aa==addr:continue
                rr=int(re.search(r'\d+',aa).group())
                if rr>len(sh):continue
                if 'TOTAL' not in ' '.join(clean_upper(v) for v in sh.iloc[rr-1]):continue
                rf=sum_range_cells(ff)
                if rf:othercovered|={r for r,c in rf if c==col}
            for _,r in part.iterrows():
                sr=int(r['RIGA_SHEET'])+1
                if sr in covered or sr in othercovered or sr>len(sh) or col>len(sh.columns):continue
                value=to_number(sh.iloc[sr-1,col-1])
                if value is not None and abs(value)>=.005:
                    evidence.append({'FOGLIO':name,'CELLA_TOTALE':addr,'FORMULA':formula,
                      'CELLA_ESCLUSA':excel_col(col)+str(sr),'CLIENTE':r['CLIENTE'],'IMPORTO_ESCLUSO':value,
                      'MOTIVO':'Riga cliente fuori dall’intervallo della formula. Verificare se l’esclusione è voluta.'})
    return pd.DataFrame(evidence)


def render_revisione_legacy(db):
    if not is_super_admin():
        st.info('Sezione riservata al super_admin.');return
    st.subheader('Attribuzione delle operazioni precedenti')
    st.caption('Nessun record viene cancellato. Un evento senza situazione non viene attribuito automaticamente al file appena caricato.')
    history=normalizza_storico(carica_storico_pagamenti())
    manifest=remote_manifest()
    uploads=manifest.get('uploads',[])
    choices={x['file_hash']:x.get('file_name','')+' — '+str(x.get('reference_date') or x.get('uploaded_at','')) for x in uploads}
    current=st.session_state.get('current_baseline_hash','')
    if current and current not in choices:choices[current]=st.session_state.get('current_baseline_file','Situazione corrente')
    if not history.empty:
        pending=history[history['BASELINE_HASH'].fillna('').eq('')&history['APPLICA_AL_SALDO']].copy()
    else:pending=pd.DataFrame()
    st.markdown('**Movimenti manuali senza situazione**')
    if pending.empty:st.info('Nessun movimento da attribuire.')
    elif choices:
        columns=[c for c in ['EVENT_ID','CLIENTE','DATA_REGISTRAZIONE','IMPORTO_FATTURE_PRECEDENTE','IMPORTO_FATTURE_NUOVO','DIFFERENZA_TOTALE'] if c in pending]
        st.dataframe(prepara_display(pending[columns]),width='stretch',hide_index=True)
        selected=st.multiselect('Movimenti da attribuire',pending.EVENT_ID.astype(str).tolist(),key='legacy_event_ids')
        target=st.selectbox('Situazione sulla quale furono registrati',list(choices),format_func=lambda k:choices[k],key='legacy_event_target')
        confirm=st.checkbox('Confermo che questi movimenti appartengono alla situazione scelta, non sono già incorporati nei suoi saldi.',key='legacy_event_confirm')
        if st.button('Associa i movimenti selezionati',key='legacy_events_save'):
            if not confirm or not selected:st.error('Selezionare i movimenti e confermare l’attribuzione.')
            else:
                mask=history.EVENT_ID.astype(str).isin(selected)
                history.loc[mask,'BASELINE_HASH']=target
                history.loc[mask,'BASELINE_FILE']=choices[target]
                if salva_storico_pagamenti(history):st.rerun()
    st.markdown('**Clienti inseriti manualmente senza situazione**')
    manual=carica_clienti_manuali()
    if not manual.empty:
        if 'BASELINE_HASH' not in manual:manual['BASELINE_HASH']=''
        pend=manual[manual.BASELINE_HASH.fillna('').eq('')]
    else:pend=pd.DataFrame()
    if pend.empty:st.info('Nessun cliente manuale da attribuire.')
    elif choices:
        st.dataframe(prepara_display(pend[[c for c in ['RIGA_GLOBALE','CLIENTE','ZONA','IMPORTO_STANDARD'] if c in pend]]),width='stretch',hide_index=True)
        selected=st.multiselect('Posizioni manuali',pend.RIGA_GLOBALE.astype(str).tolist(),key='legacy_manual_ids')
        target=st.selectbox('Situazione di inserimento',list(choices),format_func=lambda k:choices[k],key='legacy_manual_target')
        if st.button('Associa le posizioni manuali',key='legacy_manual_save') and selected:
            manual.loc[manual.RIGA_GLOBALE.astype(str).isin(selected),'BASELINE_HASH']=target
            if salva_clienti_manuali(manual):st.rerun()
    st.markdown('**Rettifiche importi senza situazione**')
    corrections=carica_correzioni_quadratura()
    old={k:v for k,v in corrections.items() if not v.get('baseline_hash') and not v.get('legacy_migrated_to')}
    if not old:st.info('Nessuna rettifica da attribuire.')
    elif current and not db.empty:
        key=st.selectbox('Rettifica precedente',list(old),format_func=lambda k:clean_text(old[k].get('cliente',''))+' | '+clean_text(old[k].get('zona',''))+' | '+k[:12],key='legacy_corr_choice')
        rule=old[key]
        st.write('Fatture: '+format_euro(rule.get('fatture',0))+' · Buoni: '+format_euro(rule.get('buoni',0)))
        labels={str(r.ID_POSIZIONE_SSC):str(r.CLIENTE)+' | '+str(r.ZONA)+' | riga '+str(r.RIGA_SHEET) for _,r in db.iterrows()}
        sid=st.selectbox('Posizione della situazione corrente da rettificare',list(labels),format_func=lambda k:labels[k],key='legacy_corr_target')
        ok=st.checkbox('Ho verificato questa correzione contro la situazione corrente.',key='legacy_corr_confirm')
        if st.button('Attribuisci la rettifica alla posizione corrente',key='legacy_corr_save'):
            if not ok:st.error('Confermare la verifica della rettifica.')
            else:
                newkey=current+':'+sid
                corrections[newkey]={**rule,'baseline_hash':current,'id_posizione':sid,'nota':'Attribuzione manuale rettifica legacy: '+clean_text(rule.get('nota',''))}
                corrections[key]={**rule,'legacy_migrated_to':newkey}
                if salva_correzioni_quadratura(corrections):st.rerun()




# ======================================================
# CONTROLLI2 — SITUAZIONI, QUOTE MENSILI E DATI OPERATIVI
# ======================================================

def parse_reference_date(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def format_reference_date(value):
    d = parse_reference_date(value)
    return d.strftime("%d/%m/%Y") if d else "data da confermare"


def monetary_value(value):
    text = re.sub(r"[€\s]", "", str(value)).replace("−", "-")
    try:
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", text):
            text = text.replace(".", "")
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def sum_known(values):
    return pd.to_numeric(values, errors="coerce").sum(min_count=1)


@st.cache_data(ttl=60, max_entries=24, show_spinner=False)
def operational_bundle_cached(url, token, actor):
    result = storage_api_call("operational_bundle_v3", {"actor": actor}, timeout=90)
    if int(result.get("protocol", 0)) < 3:
        raise StorageError("Aggiornare Code.gs a CONTROLLI2 e pubblicare Nuova versione del deployment esistente.")
    result["read_at"] = datetime.now().isoformat(timespec="seconds")
    return result


def situazione_options(manifest):
    active = manifest.get("active") or {}
    options = {"__CURRENT__": {**active, "is_current": True}}
    for meta in sorted(manifest.get("uploads", []), key=lambda x: str(x.get("reference_date") or x.get("uploaded_at", "")), reverse=True):
        h = meta.get("file_hash")
        if h and h != active.get("file_hash"):
            options[h] = {**meta, "is_current": False}
    return options


def scegli_situazione(manifest):
    opts = situazione_options(manifest)
    if st.session_state.get("ssc_view_situation", "__CURRENT__") not in opts:
        st.session_state["ssc_view_situation"] = "__CURRENT__"
    def label(k):
        m = opts[k]
        prefix = "CORRENTE" if k == "__CURRENT__" else "ARCHIVIO — sola lettura"
        suffix = (" · caricato " + str(m.get('uploaded_at',''))[:10]) if not m.get('reference_date') else ''
        return f"{prefix} · SALDI al {format_reference_date(m.get('reference_date'))} · {m.get('file_name','nessun file')}{suffix}"
    choice = st.selectbox("Quale situazione SALDI vuoi consultare?", list(opts), format_func=label, key="ssc_view_situation")
    meta = opts[choice]
    readonly = choice != "__CURRENT__"
    st.session_state["__history_readonly"] = readonly
    st.session_state["__period_view_readonly"] = False
    st.session_state["view_reference_date"] = meta.get("reference_date", "")
    if readonly:
        st.warning("Stai consultando la fotografia Excel archiviata. Non cambia il SALDI corrente per gli altri utenti e non puoi registrare pagamenti su questa vista.")
    return meta, readonly


def render_data_situazione(meta, manifest, sheets):
    if not is_super_admin(): return
    if not st.checkbox("Conferma / correggi la data di questa situazione", key="ssc_reference_metadata"):
        return
    h = meta.get("file_hash", "")
    rev = manifest.get("versions", {})
    key = h[:12] + "_" + str(rev.get("uploads_v2",0)) + "_" + str(rev.get("active_upload",0))
    with st.form("ssc_ref_form_" + key):
        d = st.date_input("Data a cui si riferisce il SALDI", value=parse_reference_date(meta.get("reference_date")) or data_riferimento_da_fogli(sheets), key="date_meta_" + key)
        confirmed = st.checkbox("Confermo la data di riferimento. Non sto ripristinando il file né registrando un pagamento.", key="date_meta_confirm_" + key)
        go = st.form_submit_button("Salva data della situazione")
    if not go: return
    if not confirmed:
        st.warning("Conferma la data prima di salvarla."); return
    payload = {"file_hash": h,"reference_date": d.isoformat(), "actor":st.session_state["current_user"]["username"],
               "request_id":str(uuid.uuid4()), "expected":{"active_upload":int(rev.get("active_upload",0)),"uploads_v2":int(rev.get("uploads_v2",0))}}
    try:
        storage_api_call("reference_date_set_v3",payload)
    except StorageError as exc:
        st.error(str(exc));return
    reset_remote_views()
    st.session_state["__saved_notice"]="Data della situazione salvata. Nessun file riattivato."
    st.rerun()


def dettaglio_periodi_di_riga(row, year):
    # Il testo operativo aggiornato prevale sul documento originario.
    rich = clean_text(row.get("PERIODI_DETTAGLIO", ""))
    text = rich or clean_text(row.get("DETTAGLIO_PERIODI_IMPORTI", "")) or clean_text(row.get("PERIODI_RIFERIMENTO", ""))
    items = parse_period_evidence(text, year)
    estimated = set(re.findall(r"(?:19|20)\d{2}", clean_text(row.get("ANNI_STIMATI", ""))))
    for x in items:
        if x["anno"] in estimated:
            x["stimato"] = True
    return items



def importo_intero_riferimenti(row, items):
    """Importo della posizione riferita all'insieme COMPLETO dei suoi periodi.

    Non ripartisce il saldo per numero di fatture. L'importo puo' essere usato
    su un solo mese, oppure una sola volta se il filtro include tutti i periodi
    della posizione. Non si usa con componenti miste, riferimenti parziali,
    conteggi discordanti o dettagli monetari (che hanno la propria quadratura).
    """
    if not items or any(x.get('amount') is not None for x in items):
        return None
    values = {}
    for key in ('IMPORTO_FATTURE_RIGA', 'IMPORTO_BUONI_RIGA'):
        value = to_number(row.get(key))
        if value is None or not math.isfinite(float(value)):
            return None
        values[key] = float(value)
    nonzero = [(comp, key, count) for comp, key, count in (
        ('FATTURE', 'IMPORTO_FATTURE_RIGA', 'NUM_FATTURE'),
        ('BUONI', 'IMPORTO_BUONI_RIGA', 'NUM_BUONI'),
    ) if abs(values[key]) >= .005]
    if len(nonzero) != 1:
        return None
    component, amount_key, count_key = nonzero[0]
    # Usa solo riferimenti operativi correnti, mai dettagli vecchi dopo un edit.
    text = (clean_text(row.get('PERIODI_DETTAGLIO', ''))
            or clean_text(row.get('DETTAGLIO_PERIODI_IMPORTI', ''))
            or clean_text(row.get('PERIODI_RIFERIMENTO', '')))
    if re.search(r'\b(?:DI\s+CUI|PARZIAL\w*|ALTRI?\s+(?:MESI|PERIODI|DOCUMENTI)|'
                 r'RESTO|RIMANEN\w*|SENZA\s+(?:DATA|PERIODO)|NON\s+RIPARTIT\w*)\b', text, re.I):
        return None
    periods = {f"{x['anno']}-{mese_numero(x['mese']):02d}" for x in items}
    declared = set(re.findall(r'\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])\b',
                              clean_text(row.get('PERIODI_ORDINABILI', ''))))
    if declared and declared != periods:
        return None
    expected = to_number(row.get(count_key))
    if expected is not None and (not math.isfinite(float(expected)) or expected < 0):
        return None
    counts = [float(x['count']) for x in items if x.get('count') is not None]
    if any(not math.isfinite(x) or x < 0 for x in counts):
        return None
    if counts and expected is not None and abs(sum(counts) - float(expected)) > .0001:
        return None
    return {'component': component, 'amount': values[amount_key],
            'count': float(expected) if expected is not None else None}


def totale_monetario_dashboard(values):
    """Nessuna riga = zero; righe presenti tutte N/D = N/D; altrimenti quote note."""
    if len(values) == 0:
        return 0.0
    return float(pd.to_numeric(values, errors='coerce').sum(min_count=1))


def format_totale_dashboard(value):
    return 'N/D' if pd.isna(value) else format_euro(value)


def costruisci_registro_periodi(db, reference_date=""):
    """Quote documentate, mai una divisione proporzionale del saldo.

    Ogni posizione conserva il proprio saldo. Qui si affiancano le evidenze
    mensili per analisi; un dettaglio interamente numerico che non quadra è
    segnalato e non entra negli importi attribuiti.
    """
    date = parse_reference_date(reference_date)
    year = date.year if date else (_SSC_PARSE_YEAR.get() or datetime.now().year)
    records, checks = [], []
    for _, row in db.iterrows():
        sid = clean_text(row.get("ID_POSIZIONE_SSC", ""))
        f = float(to_number(row.get("IMPORTO_FATTURE_RIGA")) or 0)
        b = float(to_number(row.get("IMPORTO_BUONI_RIGA")) or 0)
        nf = to_number(row.get("NUM_FATTURE"))
        nb = to_number(row.get("NUM_BUONI"))
        items = dettaglio_periodi_di_riga(row, year)
        whole = importo_intero_riferimenti(row, items)
        single_whole = whole if len(items) == 1 else None
        amounts = [x["amount"] for x in items if x["amount"] is not None]
        s = round(sum(amounts), 2)
        has_f, has_b = abs(f) >= .005, abs(b) >= .005
        component = None
        if has_f and not has_b:
            component = "FATTURE"
        elif has_b and not has_f:
            component = "BUONI"
        elif has_f and has_b and amounts:
            match_f, match_b = abs(s-f) < .01, abs(s-b) < .01
            if match_f != match_b:
                component = "FATTURE" if match_f else "BUONI"
        elif nf and not nb:
            component = "FATTURE"
        elif nb and not nf:
            component = "BUONI"
        target = f if component == "FATTURE" else b if component == "BUONI" else None
        complete = bool(items and len(amounts) == len(items))
        coherent = bool(amounts and component and target is not None and abs(s-target) < .01)
        partial = bool(amounts and not complete and component and target is not None
                       and abs(s) <= abs(target)+.01 and (s == 0 or target*s >= 0))
        valid_money = coherent or partial
        if single_whole:
            reason = "Importo della posizione riferito al suo unico mese (non ripartito)"
        elif amounts and not valid_money:
            reason = "Dettaglio mensile non quadrato o componente fatture/buoni ambigua"
        elif partial:
            reason = "Ripartizione parziale: residuo non attribuito automaticamente"
        elif not amounts and items:
            reason = "Solo mesi / numero fatture: importi mensili non disponibili"
        elif not items:
            reason = "Nessun riferimento mensile disponibile"
        else:
            reason = "Importi mensili coerenti con la componente"
        counts = [x["count"] for x in items if x["count"] is not None]
        expected_n = nf if component == "FATTURE" else nb if component == "BUONI" else None
        count_valid = bool(component and counts and (not expected_n or sum(counts) <= expected_n))
        for x in items:
            records.append({"ID_POSIZIONE_SSC": sid, "CLIENTE": row.get("CLIENTE", ""),
                "ZONA": row.get("ZONA", ""), "AGENTE": row.get("AGENTE", ""),
                "ANNO": int(x["anno"]), "MESE": mese_numero(x["mese"]),
                "PERIODO": f"{x['anno']}-{mese_numero(x['mese']):02d}", "COMPONENTE": component or "NON DEFINITA",
                "IMPORTO": (single_whole["amount"] if single_whole else
                            float(x["amount"]) if x["amount"] is not None and valid_money else None),
                "N_DOCUMENTI": (single_whole["count"] if single_whole else
                                x["count"] if count_valid else None),
                "ANNO_DA_DATA_SALDI": bool(x["stimato"]), "ESITO": reason,
                # Non inventiamo un importo scritto accanto al mese: provenienza distinta.
                "IMPORTO_NEL_TESTO": x["amount"],
                "IMPORTO_INTERO_RIFERIMENTI": whole["amount"] if whole else None,
                "N_DOCUMENTI_INTERI_RIFERIMENTI": whole["count"] if whole else None,
                "ORIGINE_IMPORTO": ("POSIZIONE_UNICO_PERIODO" if single_whole else
                                    "DETTAGLIO_MENSILE" if x["amount"] is not None and valid_money else "NON_ATTRIBUITO")})
        attributed = single_whole["amount"] if single_whole else s if valid_money else 0.0
        checks.append({"ID_POSIZIONE_SSC": sid, "CLIENTE": row.get("CLIENTE", ""),
            "ZONA": row.get("ZONA", ""), "SALDO_COMPLETO": round(f+b, 2),
            "IMPORTO_ATTRIBUITO_AI_MESI": attributed,
            "IMPORTO_NON_RIPARTITO": round(f+b-attributed, 2),
            "ESITO": reason, "DETTAGLIO": clean_text(row.get("PERIODI_DETTAGLIO", ""))})
    cols = ["ID_POSIZIONE_SSC","CLIENTE","ZONA","AGENTE","ANNO","MESE","PERIODO","COMPONENTE","IMPORTO","N_DOCUMENTI","ANNO_DA_DATA_SALDI","ESITO","IMPORTO_NEL_TESTO",
            "IMPORTO_INTERO_RIFERIMENTI","N_DOCUMENTI_INTERI_RIFERIMENTI","ORIGINE_IMPORTO"]
    return pd.DataFrame(records, columns=cols), pd.DataFrame(checks)


def seleziona_quote_periodo(db, registro, anno="TUTTI", mesi=()):
    """Proiezione analitica in sola lettura: NULL != zero."""
    all_ev = registro[registro["ID_POSIZIONE_SSC"].isin(db["ID_POSIZIONE_SSC"])].copy()
    all_by_id = {sid: group for sid, group in all_ev.groupby("ID_POSIZIONE_SSC", sort=False)}
    ev = all_ev.copy()
    covered_whole_ids = []
    if anno != "TUTTI":
        ev = ev[ev["ANNO"] == int(anno)]
    if mesi:
        ev = ev[ev["MESE"].isin([int(m) for m in mesi])]
    rows = []
    by_id = {sid: group for sid, group in ev.groupby("ID_POSIZIONE_SSC", sort=False)}
    for _, row in db.iterrows():
        group = by_id.get(row["ID_POSIZIONE_SSC"])
        if group is None:
            continue
        result = row.to_dict()
        result["SALDO_COMPLETO_CLIENTE"] = row.get("IMPORTO_STANDARD", 0)
        all_group = all_by_id[row["ID_POSIZIONE_SSC"]]
        # Si puo' usare l'importo intero una sola volta SOLO se nessun periodo
        # della posizione resta fuori dal filtro corrente.
        full_scope = (len(group) == len(all_group)
                      and set(group["PERIODO"]) == set(all_group["PERIODO"]))
        whole_used = False
        parts = []
        for comp, imp_col, n_col in [("FATTURE","IMPORTO_FATTURE_RIGA","NUM_FATTURE"),("BUONI","IMPORTO_BUONI_RIGA","NUM_BUONI")]:
            part = group[group["COMPONENTE"] == comp]
            source_amount = float(to_number(row.get(imp_col)) or 0)
            if part.empty:
                # Una componente senza riferimento non vale zero quando non è nota.
                result[imp_col] = 0.0 if abs(source_amount)<.005 else float("nan")
                result[n_col] = 0.0 if abs(source_amount)<.005 else float("nan")
            else:
                result[imp_col] = sum_known(part["IMPORTO"])
                result[n_col] = sum_known(part["N_DOCUMENTI"])
                whole_values = pd.to_numeric(
                    part.get("IMPORTO_INTERO_RIFERIMENTI", pd.Series(float("nan"), index=part.index)),
                    errors="coerce")
                if (full_scope and pd.isna(result[imp_col]) and whole_values.notna().all()
                        and whole_values.nunique() == 1):
                    result[imp_col] = float(whole_values.iloc[0])
                    result[n_col] = pd.to_numeric(part["N_DOCUMENTI_INTERI_RIFERIMENTI"], errors="coerce").iloc[0]
                    whole_used = True
        known_components = [result["IMPORTO_FATTURE_RIGA"], result["IMPORTO_BUONI_RIGA"]]
        actually_known = whole_used or pd.to_numeric(group["IMPORTO"], errors="coerce").notna().any()
        result["IMPORTO_STANDARD"] = sum(x for x in known_components if pd.notna(x)) if actually_known else float("nan")
        result["IMPORTO_NOTE_CREDITO"] = sum(x for x in known_components if pd.notna(x) and x<0) if actually_known else float("nan")
        result["NUM_DOCUMENTI"] = sum_known(pd.Series([result["NUM_FATTURE"],result["NUM_BUONI"]]))
        for _, x in group.sort_values(["ANNO","MESE"]).iterrows():
            label = f"{MESE_NOMI_V3[int(x['MESE'])]} {int(x['ANNO'])}"
            if pd.notna(x["IMPORTO"]):
                label += ": " + format_euro(x["IMPORTO"])
            elif pd.notna(x["N_DOCUMENTI"]):
                n = int(x["N_DOCUMENTI"])
                kind = ('buono' if n == 1 else 'buoni') if x['COMPONENTE'] == 'BUONI' else ('fattura' if n == 1 else 'fatture')
                label += f" ({n} {kind}; importo N/D)"
            else:
                label += " (importo N/D)"
            if whole_used:
                label = label.replace("; importo N/D", "; importo mensile non ripartito")
                label = label.replace("(importo N/D)", "(importo mensile non ripartito)")
            if label not in parts: parts.append(label)
        if whole_used:
            covered_whole_ids.append(row["ID_POSIZIONE_SSC"])
            parts.append("Totale dei riferimenti selezionati: " + format_euro(result["IMPORTO_STANDARD"]))
        result["PERIODI_DETTAGLIO"] = " | ".join(parts)
        result["PERIODI_RIFERIMENTO"] = ", ".join(dict.fromkeys(MESE_NOMI_V3[int(x)] for x in group["MESE"]))
        result["ANNI_RIFERIMENTO"] = ", ".join(str(x) for x in sorted(group["ANNO"].unique()))
        result["PERIODI_ORDINABILI"] = ", ".join(sorted(group["PERIODO"].unique()))
        result["DETTAGLIO_PERIODI_IMPORTI"] = " | ".join(p for p in parts if "N/D" not in p)
        result["FLAG_IMPORTO_ZERO"] = False
        rows.append(result)
    out = pd.DataFrame(rows, columns=list(db.columns)+(["SALDO_COMPLETO_CLIENTE"] if "SALDO_COMPLETO_CLIENTE" not in db else []))
    out.attrs["period_projection"] = True
    out.attrs["whole_scope_ids"] = covered_whole_ids
    return out, ev


MESE_NOMI_V3 = {1:"Gennaio",2:"Febbraio",3:"Marzo",4:"Aprile",5:"Maggio",6:"Giugno",7:"Luglio",8:"Agosto",9:"Settembre",10:"Ottobre",11:"Novembre",12:"Dicembre"}


def prepara_dataset_operativo(file_bytes, meta, manifest, historical=False):
    global _DATASET_USED_THIS_RUN
    _DATASET_USED_THIS_RUN = True
    h = meta["file_hash"]
    ref = meta.get("reference_date", "")
    statekeys = ["payment_history","manual_clients","deleted_clients","quadrature_corrections"]
    revisions = tuple(int(manifest.get("versions",{}).get(k,0)) for k in statekeys)
    key = (h, ref, historical, revisions if not historical else (), APP_BUILD)
    cached = st.session_state.get("__ready_dataset")
    if cached and cached["key"] == key:
        st.session_state["__dataset_cache_hit"] = True
        for k,v in cached["diagnostic"].items(): st.session_state[k]=v
        return cached["data"]
    st.session_state["__dataset_cache_hit"] = False
    start = time.perf_counter()
    df_raw, fogli, sheets, parsed, debug, cols = prepara_saldi_base_cached(file_bytes, ref)
    raw = aggiungi_id_posizione_stabile(parsed.copy())
    quad = quadratura_session_cached(h + ":" + ref, sheets, raw)
    if historical:
        original = raw.copy()
        db = ricalcola_importi_da_editor(raw.copy())
    else:
        original = applica_correzioni_quadratura(raw)
        original = aggiungi_clienti_manuali_a_db(original)
        original = aggiungi_id_posizione_stabile(original)
        db = applica_storico_a_db(original, baseline_hash=h)
        db = applica_clienti_eliminati(db)
    inferred_ref = ref or data_riferimento_da_fogli(sheets).isoformat()
    registro, check = costruisci_registro_periodi(db, inferred_ref)
    # Periodi derivati fuori dalla cache del parser: dipendono da tutte le modifiche.
    result = (df_raw, fogli, sheets, raw, original, db, debug, cols, quad, registro, check)
    keys=["__legacy_corrections","__legacy_manuals","__unmatched_history","__legacy_history_count"]
    diagnostic = {k:(0 if historical else st.session_state.get(k,0)) for k in keys}
    st.session_state["__ready_dataset"] = {"key":key,"data":result,"diagnostic":diagnostic}
    st.session_state["__dataset_compute_seconds"] = round(time.perf_counter()-start,3)
    return result



# ======================================================
# NAVIGAZIONE1 — PAGINE LEGGERE, DATI TECNICI SU RICHIESTA
# ======================================================

@st.cache_data(ttl=60, max_entries=32, show_spinner=False)
def audit_page_cached(url, token, actor, offset, query, version):
    return storage_api_call("audit_page_v3", {
        "actor": actor, "offset": int(offset), "limit": 100,
        "query": str(query), "expected_version": version,
    })


def render_cronologia_paginata():
    if not can_view_user_audit():
        st.warning("Cronologia azioni riservata al super_admin.")
        return
    actor = (st.session_state.get("current_user") or {}).get("username", "")
    namespace = "audit_nav_" + hashlib.sha256(actor.encode()).hexdigest()[:12]
    page_key, query_key, version_key = (namespace + x for x in ("_page", "_query", "_version"))
    st.caption("100 azioni per pagina, dalle più recenti. Nessuna riga viene eliminata dall’archivio.")
    with st.form(namespace + "_filter"):
        query = st.text_input("Cerca nella cronologia (utente, cliente o azione)",
                             value=st.session_state.get(query_key, ""), max_chars=200)
        search = st.form_submit_button("Applica ricerca")
    refresh = st.button("↻ Aggiorna cronologia", key=namespace + "_refresh")
    if search or refresh:
        if search: st.session_state[query_key] = query.strip()
        st.session_state[page_key] = 0
        st.session_state.pop(version_key, None)
        audit_page_cached.clear()
    offset = int(st.session_state.get(page_key, 0)) * 100
    try:
        result = audit_page_cached(*get_storage_api_config(), actor, offset,
                                   st.session_state.get(query_key, ""), None if offset == 0 else st.session_state.get(version_key))
    except StorageError as exc:
        st.error(str(exc))
        return
    st.session_state[version_key] = result["version"]
    rows, total = result.get("rows", []), int(result.get("total", 0))
    st.caption("Letto dall’archivio: " + str(result.get("read_at", "")))
    if not rows:
        st.info("Nessuna azione nella selezione. Aggiorna la cronologia se il contenuto è cambiato.")
    else:
        df = pd.DataFrame(rows)
        preferred = ["DATA_ORA", "UTENTE", "USERNAME", "AZIONE", "CLIENTE", "ZONA", "AGENTE", "DETTAGLIO", "VALORE_PRECEDENTE", "VALORE_NUOVO"]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        st.dataframe(prepara_display(df[cols]), width="stretch", height=520, hide_index=True)
        st.caption(f"Azioni {offset+1:,}–{offset+len(rows):,} di {total:,} nella selezione.")
    left, middle, right = st.columns([1, 2, 1])
    if left.button("← Precedenti", disabled=offset == 0, key=namespace + "_prev"):
        st.session_state[page_key] = max(0, offset // 100 - 1)
        st.rerun()
    middle.write(f"Pagina {offset//100+1} / {max(1, (total+99)//100)}")
    if right.button("Successive →", disabled=not result.get("has_more", False), key=namespace + "_next"):
        st.session_state[page_key] = offset // 100 + 1
        st.rerun()


def render_area_navigation(historical):
    st.sidebar.title("Navigazione")
    choices = ["Dashboard Saldi", "Controllo dati"] if historical else ["Dashboard Saldi", "Pagamenti", "Controllo dati"]
    if not historical and current_user_role() in ("super_admin", "admin", "editor"):
        choices.append("Amministrazione")
    if st.session_state.get("nav_area_unificata") not in choices:
        st.session_state["nav_area_unificata"] = choices[0]
    return st.sidebar.radio("Area", choices, key="nav_area_unificata")


def render_admin_navigation():
    st.header("Amministrazione")
    choices = ["Panoramica"]
    if current_user_role() in ("super_admin", "admin", "editor"):
        choices.append("Clienti / posizioni")
    if can_view_user_audit(): choices.append("Storico azioni")
    if can_manage_users(): choices.extend(["Gestione utenti", "Attribuzione dati precedenti"])
    key = "admin_view_navigazione1"
    if st.session_state.get(key) not in choices: st.session_state[key] = "Panoramica"
    return st.radio("Sezione", choices, horizontal=True, key=key)


def render_admin_light(section):
    """True: sezione completata senza scaricare o elaborare il SALDI."""
    if section == "Panoramica":
        st.info("Scegli l’attività in alto. Entrare in Amministrazione non carica la cronologia né ricalcola i SALDI.")
        st.markdown("**Clienti / posizioni** — inserimento e gestione delle posizioni operative.")
        if can_view_user_audit(): st.markdown("**Storico azioni** — consultazione delle operazioni, 100 per pagina.")
        if can_manage_users():
            st.markdown("**Gestione utenti** — account e permessi. **Attribuzione dati precedenti** — verifica dei record senza situazione associata.")
        return True
    if section == "Storico azioni":
        render_cronologia_paginata()
        return True
    if section == "Gestione utenti":
        render_gestione_utenti()
        return True
    return False


def render_tabella_tecnica_paginata(df, key, preferred=None):
    """Filtri su tutto il dataset, rendering limitato alla pagina scelta."""
    if df is None or df.empty:
        st.info("Nessuna riga disponibile.")
        return
    work = df.copy()
    n_all = len(work)
    c1, c2 = st.columns([1, 2])
    if "ZONA" in work.columns:
        zones = ["TUTTE"] + sorted(str(x) for x in work["ZONA"].dropna().unique() if str(x).strip())
        zk = key + "_zona"
        if st.session_state.get(zk) not in zones: st.session_state[zk] = "TUTTE"
        zone = c1.selectbox("Zona", zones, key=zk)
        if zone != "TUTTE":
            work = work[work["ZONA"].astype(str) == zone]
            render_zone_badge(zone)
    query = c2.text_input("Cerca cliente / codice", key=key + "_search").strip()
    if query:
        mask = pd.Series(False, index=work.index)
        for col in ["CLIENTE", "CLIENTE_PADRE", "CODICE_CLIENTE"]:
            if col in work:
                mask |= work[col].fillna("").astype(str).str.contains(query, case=False, regex=False)
        work = work[mask]
    if work.empty:
        st.info("Nessuna riga corrisponde ai filtri.")
        return
    order = [x for x in ["ZONA", "CLIENTE", "RIGA_SHEET"] if x in work]
    if order: work = work.sort_values(order, kind="stable")
    default_cols = preferred or ["CLIENTE_PADRE", "CLIENTE", "CODICE_CLIENTE", "AGENTE", "ZONA",
        "TIPO_DOCUMENTO", "IMPORTO_FATTURE_RIGA", "NUM_FATTURE", "IMPORTO_BUONI_RIGA", "NUM_BUONI",
        "IMPORTO_STANDARD", "PERIODI_DETTAGLIO", "PERIODI_RIFERIMENTO", "MODALITA_PAGAMENTO"]
    cols = [c for c in default_cols if c in work.columns] or list(work.columns)
    if st.checkbox("Tutte le colonne tecniche", key=key + "_all_cols"):
        cols = list(work.columns)
    pages = max(1, (len(work)+99)//100)
    pk = key + "_page"
    stamp = (query, str(st.session_state.get(key+"_zona", "TUTTE")), len(work), pages)
    if st.session_state.get(key + "_filter_stamp") != stamp:
        st.session_state[pk] = 1
        st.session_state[key + "_filter_stamp"] = stamp
    if st.session_state.get(pk, 1) not in range(1, pages+1): st.session_state[pk] = 1
    page = st.selectbox("Pagina", list(range(1, pages+1)), key=pk)
    start = (page-1)*100
    visible = work.iloc[start:start+100].copy().reset_index(drop=True)
    st.caption(f"{len(work):,} righe selezionate su {n_all:,}. Visualizzate {start+1:,}–{start+len(visible):,}. Totali e filtri usano l’intera selezione.")
    st.dataframe(prepara_display(visible[cols]), width="stretch", height=520, hide_index=True)
    if st.checkbox("Apri la scheda completa di una riga", key=key + "_detail"):
        ix = st.selectbox("Riga della pagina", list(range(len(visible))),
            format_func=lambda i: f"{start+i+1} · {visible.iloc[i].get('CLIENTE', visible.iloc[i].get('CLIENTE_PADRE', 'Riga'))}",
            key=key+"_row_"+str(page))
        render_schede_generiche(visible.iloc[[ix]], titolo_col="CLIENTE" if "CLIENTE" in visible else None,
                               group_col="ZONA" if "ZONA" in visible else None)



def mostra_diagnostica_tempi(manifest=None):
    if not is_super_admin(): return
    if st.sidebar.checkbox("Diagnostica tempi", key="ssc_perf_diagnostics"):
        st.sidebar.write(f"Ciclo server: {time.perf_counter()-_RUN_START:.2f} s")
        st.sidebar.write(f"Chiamate HTTP: {len(_RUN_HTTP)}")
        label = ("sì" if st.session_state.get("__dataset_cache_hit") else "no") if _DATASET_USED_THIS_RUN else "non richiesto da questa sezione"
        st.sidebar.write("Dataset da cache: " + label)
        st.sidebar.caption("Tempi server; non includono trasferimento/rendering nel browser. Apertura iniziale, letture remote e salvataggi possono richiedere attesa.")
        if manifest: st.sidebar.caption("Dati condivisi letti: " + str(manifest.get("read_at", "")))
        if _RUN_PHASES: st.sidebar.dataframe(pd.DataFrame(_RUN_PHASES), hide_index=True)
        if _RUN_HTTP: st.sidebar.dataframe(pd.DataFrame(_RUN_HTTP), hide_index=True)


_phase_start = time.perf_counter()
require_login()
_RUN_PHASES.append({"fase":"Verifica sessione", "secondi":round(time.perf_counter()-_phase_start,3)})
render_user_sidebar()
st.sidebar.caption(f"Build {APP_BUILD}")
if st.session_state.pop("__saved_notice", ""):
    st.success("Operazione salvata nell’archivio condiviso.")
if st.sidebar.button("↻ Aggiorna situazione condivisa", key="ssc_global_refresh"):
    reset_remote_views()
    st.rerun()

st.session_state["__period_view_readonly"] = False
st.session_state["__history_readonly"] = st.session_state.get("ssc_view_situation", "__CURRENT__") != "__CURRENT__"
area = render_area_navigation(st.session_state["__history_readonly"])
admin_view = None
if area == "Amministrazione":
    _phase_start = time.perf_counter()
    admin_view = render_admin_navigation()
    completed = render_admin_light(admin_view)
    _RUN_PHASES.append({"fase":"Amministrazione", "secondi":round(time.perf_counter()-_phase_start,3)})
    if completed:
        mostra_diagnostica_tempi()
        st.stop()
_phase_start = time.perf_counter()
try:
    with st.spinner("Sincronizzazione archivio..."):
        _RUN_BUNDLE = operational_bundle_cached(*get_storage_api_config(), st.session_state["current_user"]["username"])
    manifest = _RUN_BUNDLE
    _RUN_PHASES.append({"fase":"Archivio operativo", "secondi":round(time.perf_counter()-_phase_start,3)})
    st.session_state["__storage_ready"] = True
    st.session_state["__state_versions"] = dict(manifest.get("versions", {}))
except StorageError as exc:
    st.session_state["__storage_ready"] = False
    st.error(str(exc))
    st.warning("Archivio condiviso non disponibile: nessun salvataggio sostitutivo locale.")
    st.stop()
if st.session_state.pop("__close_update_panel", False):
    st.session_state["ssc_update_panel"] = False
render_upload_controllato(manifest)
active_meta = manifest.get("active") or {}
selected_meta, historical_view = scegli_situazione(manifest)
if historical_view and area not in ("Dashboard Saldi", "Controllo dati"):
    st.rerun()
file_bytes = None
file_name = selected_meta.get("file_name", "")
if selected_meta.get("file_hash"):
    try:
        file_bytes, _ = remote_file_cached(*get_storage_api_config(), selected_meta["file_hash"])
    except StorageError as exc:
        st.error(str(exc))

if file_bytes is not None:
    file_hash_corrente = selected_meta["file_hash"]
    # L'identità della situazione OPERATIVA è sempre quella condivisa, mai l'archivio consultato.
    st.session_state["current_baseline_hash"] = active_meta.get("file_hash", "")
    st.session_state["current_baseline_file"] = active_meta.get("file_name", "")
    ref_date = selected_meta.get("reference_date", "")
    st.subheader("SALDI AL " + format_reference_date(ref_date))
    st.caption(("Fotografia Excel archiviata — sola lettura." if historical_view else "Saldo del file aggiornato con le operazioni registrate su questa situazione.") + " Il periodo dei documenti si sceglie nei filtri sotto.")
    st.caption("Ultima sincronizzazione condivisa: " + manifest.get("read_at", "") + ". Le modifiche degli altri utenti vengono rilette alla prima interazione dopo 60 secondi o con Aggiorna dati.")
    _phase_start = time.perf_counter()
    try:
        (df_raw, fogli, sheets_originali, raw_originale, db_pulito_originale, db_pulito,
         debug_df, data_columns, quadratura_excel, registro_periodi, controllo_periodi) = prepara_dataset_operativo(file_bytes, selected_meta, manifest, historical_view)
    except (ValueError, StorageError) as exc:
        st.error(str(exc));st.info("Situazione non modificata. Controllare il file o l’archivio.");st.stop()
    _RUN_PHASES.append({"fase":"Dataset operativo", "secondi":round(time.perf_counter()-_phase_start,3)})
    if not ref_date:
        inferred_date = data_riferimento_da_fogli(sheets_originali)
        st.warning(f"Data non ancora confermata per questo archivio. Il file suggerisce {inferred_date:%d/%m/%Y}; non è la data del caricamento. Il super_admin può confermarla nell’anteprima della situazione.")
    render_data_situazione(selected_meta, manifest, sheets_originali)
    if db_pulito.empty:
        st.warning("Nessuna posizione visibile nella situazione.");st.stop()
    pending_count = sum(st.session_state.get(k,0) for k in ["__legacy_corrections","__legacy_manuals","__unmatched_history","__legacy_history_count"])
    if pending_count and not historical_view:
        st.warning(f"{pending_count} dati precedenti richiedono attribuzione: non sono applicati automaticamente.")

    q_prob = (
        quadratura_excel[quadratura_excel["ESITO"] != "OK"].copy()
        if quadratura_excel is not None and not quadratura_excel.empty
        else pd.DataFrame()
    )

    st.sidebar.divider()
    st.sidebar.caption("⚡ Cache prestazioni attiva")
    st.sidebar.markdown("**Stato dati**")
    if q_prob.empty:
        st.sidebar.success("Quadratura OK")
    else:
        st.sidebar.warning(f"{len(q_prob)} fogli da verificare")
    st.sidebar.caption(f"Righe operative: {len(db_pulito):,}".replace(",", "."))

    _render_start = time.perf_counter()
    # ==================================================
    # DASHBOARD SALDI
    # ==================================================
    if area == "Dashboard Saldi":
        st.header("Dashboard Saldi SSC")
        st.caption(
            "Una sola dashboard: zona, agente, cliente, documento e periodo sono dimensioni dello stesso credito."
        )

        df_view = applica_filtri_dashboard(db_pulito, registro_periodi, controllo_periodi)

        totale = totale_monetario_dashboard(df_view["IMPORTO_STANDARD"])
        totale_fatture = totale_monetario_dashboard(df_view["IMPORTO_FATTURE_RIGA"])
        totale_buoni = totale_monetario_dashboard(df_view["IMPORTO_BUONI_RIGA"])
        totale_note_credito = totale_monetario_dashboard(df_view["IMPORTO_NOTE_CREDITO"])

        st.divider()
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Importo attribuibile al periodo" if st.session_state.get("__period_projection") else "Esposizione totale", format_totale_dashboard(totale))
        k2.metric("Fatture — quote note" if st.session_state.get("__period_projection") else "Fatture", format_totale_dashboard(totale_fatture))
        k3.metric("Buoni — quote note" if st.session_state.get("__period_projection") else "Buoni / SSC", format_totale_dashboard(totale_buoni))
        k4.metric("Note credito / Resi", format_totale_dashboard(totale_note_credito))
        k5.metric("Clienti", df_view["CLIENTE"].nunique() if not df_view.empty else 0)

        if q_prob.empty:
            st.success("Controllo dati: quadratura del parser con il file Excel senza scostamenti rilevanti sui fogli strutturati.")
        else:
            st.warning(
                f"Controllo dati: {len(q_prob)} fogli richiedono verifica/regola dedicata. "
                "La dashboard resta consultabile, ma il dettaglio è in 'Controllo dati'."
            )

        if st.checkbox("Confronta con un altro SALDI archiviato", key="ssc_compare_requested"):
            choices = {m['file_hash']:m for m in manifest.get('uploads',[]) if m.get('file_hash') != file_hash_corrente}
            if not choices:
                st.info("Non esiste un’altra situazione archiviata da confrontare. Il tool non può ricostruire un file mai caricato.")
            else:
                compare_hash = st.selectbox("Situazione di confronto", list(choices),format_func=lambda h:format_reference_date(choices[h].get('reference_date'))+' — '+choices[h].get('file_name',''),key="ssc_compare_hash")
                other = choices[compare_hash]
                old_bytes,_ = remote_file_cached(*get_storage_api_config(),compare_hash)
                current_snapshot = snapshot_for_file(file_bytes,file_name,ref_date)
                previous_snapshot = snapshot_for_file(old_bytes,other['file_name'],other.get('reference_date',''))
                st.caption("Confronto tra fotografie dei file originali: non è una lista di pagamenti e non usa i filtri della dashboard.")
                render_snapshot_delta(current_snapshot,previous_snapshot)

        st.divider()
        vista_dinamica = st.radio(
            "Visualizza per",
            ["Clienti", "Agenti", "Zone", "Documenti"],
            horizontal=True,
            key="dashboard_vista_dinamica",
        )

        if vista_dinamica == "Clienti":
            if can_edit():
                mostra_gestione_clienti = st.checkbox(
                    "Gestione anagrafica clienti / posizioni",
                    value=False,
                    key="mostra_gestione_anagrafica_clienti",
                )
                if mostra_gestione_clienti:
                    render_form_nuovo_cliente(db_pulito_originale)
                    render_gestione_elimina_cliente(db_pulito)

            vista_clienti = st.radio(
                "Vista clienti",
                ["Tabella clienti", "Schede clienti", "Registra pagamento / modifica"],
                horizontal=True,
                key="dashboard_clienti_subview",
            )

            if vista_clienti == "Tabella clienti":
                st.caption("Vista tabellare classica con tutte le informazioni operative del cliente.")
                render_tabella_clienti_normale(df_view)

            elif vista_clienti == "Schede clienti":
                tab_clienti = riepilogo_per(
                    df_view,
                    ["CLIENTE_PADRE", "CLIENTE", "CODICE_CLIENTE", "AGENTE", "ZONA"],
                )
                render_schede_generiche(
                    tab_clienti,
                    titolo_col="CLIENTE",
                    group_col="ZONA" if "ZONA" in tab_clienti.columns else None,
                )

                if not df_view.empty:
                    st.markdown("### Dettaglio cliente")
                    clienti_detail = sorted([
                        x for x in df_view["CLIENTE_PADRE"].dropna().unique()
                        if clean_text(x)
                    ])
                    if clienti_detail:
                        selected_client = st.selectbox(
                            "Cliente padre / posizione",
                            clienti_detail,
                            key="dashboard_cliente_dettaglio",
                        )
                        det = df_view[df_view["CLIENTE_PADRE"] == selected_client].copy()
                        d1, d2, d3, d4 = st.columns(4)
                        d1.metric("Totale cliente", format_euro(det["IMPORTO_STANDARD"].sum()))
                        d2.metric("Fatture", format_euro(det["IMPORTO_FATTURE_RIGA"].sum()))
                        d3.metric("Buoni / SSC", format_euro(det["IMPORTO_BUONI_RIGA"].sum()))
                        d4.metric("Posizioni", len(det))

                        if det["FLAG_PLUS"].any() or det["CLIENTE"].nunique() > 1:
                            st.caption("Composizione del cliente raggruppato")
                            composizione = riepilogo_per(det, ["CLIENTE", "ZONA", "AGENTE"])
                            st.dataframe(prepara_display(composizione), width="stretch", hide_index=True)

                        dettaglio_cols = [
                            "CLIENTE", "CODICE_CLIENTE", "ZONA", "AGENTE", "TIPO_DOCUMENTO",
                            "IMPORTO_STANDARD", "IMPORTO_FATTURE_RIGA", "IMPORTO_BUONI_RIGA",
                            "IMPORTO_NOTE_CREDITO", "NUM_FATTURE", "NUM_BUONI",
                            "PERIODI_RIFERIMENTO", "PERIODI_DETTAGLIO",
                            "ANNI_RIFERIMENTO", "DETTAGLIO_PERIODI_IMPORTI",
                            "MODALITA_PAGAMENTO",
                        ]
                        dettaglio_cols = [c for c in dettaglio_cols if c in det.columns]
                        st.dataframe(prepara_display(det[dettaglio_cols]), width="stretch", hide_index=True)

            else:
                st.caption("Seleziona il cliente e registra il pagamento modificando i residui interessati.")
                if df_view.attrs.get("period_projection") or historical_view:
                    st.info("Per registrare un pagamento torna a CORRENTE e scegli Saldo completo dei clienti. Le quote del periodo sono una vista analitica, non saldi da sovrascrivere.")
                else:
                    render_operativita_cliente(df_view, key_prefix="dashboard_operazioni")

        elif vista_dinamica == "Agenti":
            tab_agenti = riepilogo_per(df_view, ["AGENTE"])
            render_schede_generiche(tab_agenti, titolo_col="AGENTE", group_col=None)

        elif vista_dinamica == "Zone":
            tab_zone = riepilogo_per(df_view, ["ZONA"])
            render_schede_generiche(tab_zone, titolo_col="ZONA", group_col=None)

        else:
            cols_doc = [
                "ZONA", "AGENTE", "CLIENTE_PADRE", "CLIENTE", "CODICE_CLIENTE",
                "TIPO_DOCUMENTO", "NUM_DOCUMENTI", "IMPORTO_STANDARD",
                "IMPORTO_FATTURE_RIGA", "IMPORTO_BUONI_RIGA", "IMPORTO_NOTE_CREDITO",
                "PERIODI_RIFERIMENTO", "ANNI_RIFERIMENTO", "MODALITA_PAGAMENTO",
                "FOGLIO_ORIGINE", "RIGA_SHEET",
            ]
            cols_doc = [c for c in cols_doc if c in df_view.columns]
            st.dataframe(prepara_display(df_view[cols_doc]), width="stretch", height=650, hide_index=True)

        mostra_priorita = st.checkbox(
            "Priorità incasso — posizioni più anziane e rilevanti",
            value=False,
            key="mostra_priorita_incasso",
        )
        if mostra_priorita:
            priority = priorita_operativa_clienti(df_view)
            if not priority.empty:
                st.caption(
                    "Non è un rating di rischio: ordina prima per anzianità del periodo aperto e poi per importo."
                )
                pcols = [
                    "CLIENTE_PADRE", "ZONA", "AGENTE", "IMPORTO_TOTALE",
                    "IMPORTO_FATTURE", "IMPORTO_BUONI", "MESI_ANZIANITA",
                    "PERIODI_RIFERIMENTO", "MODALITA_PAGAMENTO",
                ]
                pcols = [c for c in pcols if c in priority.columns]
                st.dataframe(
                    prepara_display(priority[pcols].head(20)),
                    width="stretch",
                    hide_index=True,
                )

        render_export_area(df_view, db_pulito, db_pulito_originale, debug_df)

    # ==================================================
    # PAGAMENTI
    # ==================================================
    elif area == "Pagamenti":
        st.header("Pagamenti / Movimenti SSC")

        st.subheader("Registra pagamento / modifica cliente")
        st.caption(
            "Questa è la funzione operativa: scegli zona e cliente, modifica i residui nelle celle e registra la variazione nello storico."
        )
        render_operativita_cliente(db_pulito, key_prefix="pagamenti_operativi")

        st.divider()
        st.subheader("Storico pagamenti / modifiche")
        storico = normalizza_storico(carica_storico_pagamenti())
        if storico.empty:
            st.info("Nessun pagamento/modifica registrato nello storico.")
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            zone_hist = c1.multiselect(
                "Zona",
                sorted(storico["ZONA"].dropna().unique()) if "ZONA" in storico.columns else [],
                key="hist_zone_filter_unificato",
            )
            agenti_hist = c2.multiselect(
                "Agente",
                sorted(storico["AGENTE"].dropna().unique()) if "AGENTE" in storico.columns else [],
                key="hist_agente_filter_unificato",
            )
            cliente_search = c3.text_input(
                "Cerca cliente",
                key="hist_cliente_search_unificato",
            )
            origini_hist = c4.multiselect(
                "Origine",
                sorted(storico["ORIGINE"].dropna().astype(str).unique())
                if "ORIGINE" in storico.columns else [],
                key="hist_origine_filter_unificato",
            )
            mostra_annullati = c5.checkbox(
                "Mostra annullati",
                value=False,
                key="hist_mostra_annullati_unificato",
            )

            storico_view = storico.copy()
            if not mostra_annullati and "ATTIVO" in storico_view.columns:
                storico_view = storico_view[storico_view["ATTIVO"] == True].copy()
            if zone_hist and "ZONA" in storico_view.columns:
                storico_view = storico_view[storico_view["ZONA"].isin(zone_hist)]
            if agenti_hist and "AGENTE" in storico_view.columns:
                storico_view = storico_view[storico_view["AGENTE"].isin(agenti_hist)]
            if cliente_search and "CLIENTE" in storico_view.columns:
                storico_view = storico_view[
                    storico_view["CLIENTE"].astype(str).str.contains(
                        cliente_search,
                        case=False,
                        regex=False,
                        na=False,
                    )
                ]
            if origini_hist and "ORIGINE" in storico_view.columns:
                storico_view = storico_view[
                    storico_view["ORIGINE"].isin(origini_hist)
                ]
            if "DATA_REGISTRAZIONE" in storico_view.columns:
                storico_view = storico_view.sort_values("DATA_REGISTRAZIONE", ascending=False)

            storico_pubblico = storico_colonne_pubbliche(storico_view)
            st.dataframe(
                prepara_display(storico_pubblico),
                width="stretch",
                height=520,
                hide_index=True,
            )
            st.caption(
                "Nota: una variazione da NUOVO_SALDI descrive il cambiamento tra "
                "due fotografie. Non viene chiamata pagamento e non modifica il saldo."
            )

            if can_edit():
                if st.checkbox("Gestione movimenti manuali", value=False, key="ssc_history_edit_requested"):
                    storico_gestione = storico_view[
                        storico_view["APPLICA_AL_SALDO"] == True
                    ].copy()
                    if storico_gestione.empty:
                        st.info(
                            "Nessun movimento manuale da gestire in questa selezione. "
                            "Le variazioni automatiche da nuovo SALDI sono audit e non si eliminano qui."
                        )
                    storico_gestione["ELIMINA"] = False
                    gestione_cols = [
                        "ELIMINA", "ATTIVO", "EVENT_ID", "CLIENTE", "ZONA", "AGENTE",
                        "DATA_PAGAMENTO", "IMPORTO_PAGATO", "PERIODO_PAGATO",
                        "ID_POSIZIONE_SSC", "RIGA_GLOBALE", "CAMPI_MODIFICATI",
                    ]
                    for c in gestione_cols:
                        if c not in storico_gestione.columns:
                            storico_gestione[c] = "" if c not in ["ELIMINA", "ATTIVO"] else (False if c == "ELIMINA" else True)
                    edited_hist = st.data_editor(
                        storico_gestione[gestione_cols],
                        width="stretch",
                        hide_index=True,
                        height=360,
                        disabled=[c for c in gestione_cols if c not in ["ELIMINA", "ATTIVO"]],
                        column_config={
                            "ELIMINA": st.column_config.CheckboxColumn("Elimina"),
                            "ATTIVO": st.column_config.CheckboxColumn("Attivo"),
                            "IMPORTO_PAGATO": st.column_config.NumberColumn("Importo pagato", format="%.2f"),
                        },
                        key=("editor_storico_pagamenti_unificato_" + st.session_state.get("current_baseline_hash", "")[:12]
                             + "_" + str(st.session_state.get("__state_versions", {}).get("payment_history", 0))),
                    )
                    a, b = st.columns(2)
                    if a.button("Salva modifiche storico", key="btn_salva_modifiche_storico_unificato", width="stretch"):
                        ids_delete = set(edited_hist.loc[edited_hist["ELIMINA"] == True, "EVENT_ID"].astype(str))
                        id_attivo = dict(zip(edited_hist["EVENT_ID"].astype(str), edited_hist["ATTIVO"]))
                        storico_full = normalizza_storico(carica_storico_pagamenti())
                        storico_full.loc[storico_full["EVENT_ID"].astype(str).isin(ids_delete), "ATTIVO"] = False
                        for _id in ids_delete: id_attivo[_id] = False
                        storico_full["ATTIVO"] = storico_full.apply(
                            lambda r: bool(id_attivo.get(str(r.get("EVENT_ID")), r.get("ATTIVO", True))), axis=1
                        )
                        if salva_storico_normalizzato(storico_full):
                            registra_azione("MODIFICA STORICO PAGAMENTI", dettaglio="Eliminazione/disattivazione movimenti storico")
                            st.success("Storico aggiornato. Ricalcolo residui e periodi...")
                            st.rerun()
                    st.caption("Lo storico non viene cancellato in massa. Per annullare un movimento togli ATTIVO: resta una traccia verificabile.")

            csv_hist = storico_pubblico.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button(
                "Scarica storico movimenti CSV",
                data=csv_hist,
                file_name="STORICO_MOVIMENTI_DIVISPACK.csv",
                mime="text/csv",
            )

    # ==================================================
    # CONTROLLO DATI
    # ==================================================
    elif area == "Controllo dati":
        st.header("Controllo dati")
        controllo = st.radio(
            "Vista tecnica",
            ["Quadratura Excel", "Da verificare", "Saldo zero", "Dettaglio Sicilia", "DB Pulito"],
            horizontal=True,
            key="controllo_dati_vista",
        )

        if controllo == "Quadratura Excel":
            render_quadratura_excel(
                quadratura_excel, raw_originale,
                sheets=sheets_originali,
                db_corretto=db_pulito_originale,
                read_only=historical_view,
            )
        elif controllo == "Da verificare":
            da_verificare = db_pulito[db_pulito["TIPO_DOCUMENTO"] == "DA_VERIFICARE"]
            st.caption(f"{len(da_verificare)} righe che il parser non classifica con sufficiente certezza.")
            render_tabella_tecnica_paginata(da_verificare, "ctrl_review")
        elif controllo == "Saldo zero":
            saldo_zero = db_pulito[db_pulito["TIPO_DOCUMENTO"] == "SALDO_ZERO"].copy()
            st.caption(
                f"{len(saldo_zero)} posizioni senza esposizione. Non sono errori di parsing e non entrano nel conteggio 'Da verificare'."
            )
            render_tabella_tecnica_paginata(saldo_zero, "ctrl_zero")
        elif controllo == "Dettaglio Sicilia":
            sicilia = db_pulito[db_pulito["FOGLIO_ORIGINE"].astype(str).str.upper() == "SICILIA"].copy()
            st.caption(
                "Dettaglio tecnico del parser Sicilia. La logica Sicilia resta separata nel motore, "
                "ma non occupa più una vista operativa principale."
            )
            colonne_sicilia = [
                "CLIENTE", "CODICE_CLIENTE", "AGENTE", "ZONA", "IMPORTO_STANDARD",
                "IMPORTO_FATTURE_RIGA", "SICILIA_RIF_FATTURE", "PERIODI_RIFERIMENTO",
                "ANNI_RIFERIMENTO", "PERIODI_ORDINABILI", "ANNI_STIMATI",
                "DETTAGLIO_PERIODI_IMPORTI", "IMPORTO_BUONI_RIGA", "IMPORTO_NOTE_CREDITO",
                "SICILIA_MODALITA_PAGAMENTO", "FLAG_NOTA_CREDITO", "TESTO_RIGA",
            ]
            colonne_sicilia = [c for c in colonne_sicilia if c in sicilia.columns]
            render_tabella_tecnica_paginata(sicilia, "ctrl_sicilia", preferred=colonne_sicilia)
        else:
            st.caption("Dataset normalizzato usato dal tool. Vista tecnica, non operativa.")
            render_tabella_tecnica_paginata(db_pulito, "ctrl_db")
            if st.checkbox("Debug parser", key="ctrl_open_debug"):
                render_tabella_tecnica_paginata(debug_df, "ctrl_debug", preferred=list(debug_df.columns))

    # Le sezioni amministrative senza dati SALDI sono state gestite prima.
    elif area == "Amministrazione":
        if admin_view == "Clienti / posizioni":
            if not can_manage_operational_data():
                st.warning("Operazione non consentita nella vista corrente.")
            else:
                operation = st.radio("Attività", ["Inserisci cliente / posizione", "Gestisci eliminazioni / ripristini"],
                                     horizontal=True, key="admin_operazione_clienti")
                if operation == "Inserisci cliente / posizione":
                    render_form_nuovo_cliente(db_pulito_originale)
                else:
                    render_gestione_elimina_cliente(db_pulito)
        elif admin_view == "Attribuzione dati precedenti" and can_manage_users():
            render_revisione_legacy(raw_originale)
    _RUN_PHASES.append({"fase":"Rendering " + area, "secondi":round(time.perf_counter()-_render_start,3)})

else:
    st.info("Carica un file Excel per iniziare.")

if is_logged_in() and isinstance(_RUN_BUNDLE, dict):
    mostra_diagnostica_tempi(_RUN_BUNDLE)
