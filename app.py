from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from db import get_db
from domain import (
    PERIODICITA_MESI,
    build_installment_plan,
    calculate_package_end,
    calculate_package_lessons,
    format_date_it,
    money,
)
from services import (
    annulla_documento_cliente,
    annulla_incasso,
    aggiorna_abbonamento_cliente,
    aggiorna_rate_abbonamento,
    carica_asset_azienda,
    carica_file_documento,
    carica_pdf_ricevuta,
    collega_pdf_ricevuta,
    crea_cliente_completo,
    crea_incasso_completo,
    crea_pacchetto,
    crea_url_asset_azienda,
    crea_url_documento,
    crea_url_ricevuta,
    elimina_asset_azienda,
    elimina_file_documento,
    elenco_aziende,
    elenco_clienti_operativo,
    elenco_incassi_operativo,
    elenco_pacchetti,
    elenco_rate_operativo,
    get_azienda,
    get_cliente_dettaglio,
    get_ricevuta_dettaglio,
    modifica_anagrafica_cliente,
    salva_asset_azienda,
    salva_azienda,
    salva_documento_cliente,
    scarica_asset_azienda,
    annulla_pagamento_spesa,
    carica_documento_spesa,
    crea_categoria_spesa,
    crea_fornitore,
    crea_spesa_completa,
    crea_url_documento_spesa,
    elimina_documento_spesa,
    elenco_categorie_spesa,
    elenco_fornitori,
    elenco_pagamenti_spesa,
    elenco_scadenze_spesa,
    elenco_spese,
    modifica_fornitore,
    registra_pagamento_spesa,
)
from receipts import build_receipt_pdf


APP_VERSION = "0.16.1"
DEVELOPER_CREDIT = "Developed by Pentti Salenius © 2026"

st.set_page_config(
    page_title="Gestionale",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --bg:#0D0F11;
        --sidebar:#08090A;
        --surface:#171A1E;
        --surface2:#20242A;
        --text:#F6F2E8;
        --muted:#AAA59A;
        --gold:#BFA15A;
        --gold2:#D4B96F;
        --border:#34383D;
    }
    .stApp { background:var(--bg); color:var(--text); }
    [data-testid="stSidebar"] { background:var(--sidebar); border-right:1px solid var(--border); }
    [data-testid="stSidebar"] * { color:var(--text) !important; }
    h1,h2,h3,h4,h5,h6,p,span,label { color:var(--text); }
    div.stButton > button,
    div.stFormSubmitButton > button {
        background:var(--surface) !important;
        color:var(--text) !important;
        border:1px solid var(--gold) !important;
        border-radius:8px !important;
        min-height:2.7rem;
        font-weight:650 !important;
    }
    div.stButton > button *,
    div.stFormSubmitButton > button * { color:var(--text) !important; }
    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover {
        background:var(--gold) !important;
        border-color:var(--gold2) !important;
        color:#111 !important;
    }
    div.stButton > button:hover *,
    div.stFormSubmitButton > button:hover * { color:#111 !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color:var(--border) !important;
        background:linear-gradient(180deg,#171A1E 0%,#14171A 100%);
        border-radius:14px;
    }

    /* Campi chiari: testo e cursore sempre scuri e leggibili. */
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] input,
    [data-baseweb="base-input"] input,
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input {
        color:#111827 !important;
        -webkit-text-fill-color:#111827 !important;
        caret-color:#111827 !important;
    }

    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div {
        color:#111827 !important;
    }

    .company-logo-wrap {
        min-height:72px;
        display:flex;
        align-items:center;
        justify-content:flex-end;
        overflow:hidden;
    }

    .company-logo-wrap img {
        max-width:150px;
        max-height:68px;
        width:auto;
        height:auto;
        object-fit:contain;
    }

    [data-testid="stSidebar"] .company-logo-wrap {
        min-height:64px;
        justify-content:flex-start;
        margin-bottom:.35rem;
    }

    [data-testid="stSidebar"] .company-logo-wrap img {
        max-width:165px;
        max-height:60px;
    }

    .footer {
        text-align:center;
        color:var(--muted);
        font-size:.82rem;
        margin-top:2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# STATO E DATI
# ============================================================

def init_state() -> None:
    defaults = {
        "menu": "Reception",
        "pending_menu": None,
        "pending_action": None,
        "selected_customer_id": None,
        "active_company_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


@st.cache_resource
def init_db():
    return get_db()


db = init_db()


@st.cache_data(ttl=30)
def load_companies() -> list[dict[str, Any]]:
    return elenco_aziende(db)


@st.cache_data(ttl=30)
def load_company_cached(company_id: str) -> dict[str, Any]:
    return get_azienda(db, company_id)


def load_company() -> dict[str, Any]:
    companies = load_companies()
    if not companies:
        raise RuntimeError("Nessuna azienda attiva configurata.")

    valid_ids = {company["id"] for company in companies}
    active_id = st.session_state.get("active_company_id")

    if active_id not in valid_ids:
        active_id = companies[0]["id"]
        st.session_state.active_company_id = active_id

    return load_company_cached(active_id)


@st.cache_data(ttl=240)
def load_company_logo_url(
    company_id: str,
    logo_path: str,
) -> str | None:
    if not logo_path:
        return None

    try:
        return crea_url_asset_azienda(
            db,
            logo_path,
            expires_in=300,
        )
    except Exception:
        return None


@st.cache_data(ttl=15)
def load_packages() -> list[dict[str, Any]]:
    return elenco_pacchetti(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_clients() -> list[dict[str, Any]]:
    return elenco_clienti_operativo(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_receipts() -> list[dict[str, Any]]:
    return elenco_incassi_operativo(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_installments() -> list[dict[str, Any]]:
    return elenco_rate_operativo(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_suppliers() -> list[dict[str, Any]]:
    return elenco_fornitori(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_expense_categories() -> list[dict[str, Any]]:
    return elenco_categorie_spesa(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_expenses() -> list[dict[str, Any]]:
    return elenco_spese(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_expense_deadlines() -> list[dict[str, Any]]:
    return elenco_scadenze_spesa(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_expense_payments() -> list[dict[str, Any]]:
    return elenco_pagamenti_spesa(db, load_company()["id"])


def clear_data_cache() -> None:
    load_companies.clear()
    load_company_cached.clear()
    load_company_logo_url.clear()
    load_packages.clear()
    load_clients.clear()
    load_receipts.clear()
    load_installments.clear()
    load_suppliers.clear()
    load_expense_categories.clear()
    load_expenses.clear()
    load_expense_deadlines.clear()
    load_expense_payments.clear()



def ensure_receipt_pdf(
    receipt_id: str,
    force: bool = False,
) -> str:
    detail = get_ricevuta_dettaglio(db, receipt_id)
    receipt = detail["ricevuta"]
    company = detail["azienda"]

    if receipt.get("pdf_path") and not force:
        return receipt["pdf_path"]

    logo_bytes = None
    if company.get("logo_path"):
        try:
            logo_bytes = scarica_asset_azienda(
                db,
                company["logo_path"],
            )
        except Exception:
            logo_bytes = None

    pdf_bytes = build_receipt_pdf(
        detail=detail,
        logo_bytes=logo_bytes,
    )

    pdf_path = carica_pdf_ricevuta(
        db=db,
        azienda_id=company["id"],
        anno=int(receipt["anno"]),
        ricevuta_id=receipt_id,
        numero_documento=detail["numero_documento"],
        contenuto=pdf_bytes,
    )

    collega_pdf_ricevuta(
        db,
        {
            "azienda_id": company["id"],
            "ricevuta_id": receipt_id,
            "pdf_path": pdf_path,
        },
    )
    clear_data_cache()
    return pdf_path


def switch_active_company(company_id: str) -> None:
    if company_id == st.session_state.get("active_company_id"):
        return

    st.session_state.active_company_id = company_id
    st.session_state.selected_customer_id = None
    clear_data_cache()
    st.rerun()


# ============================================================
# NAVIGAZIONE
# ============================================================

def goto(page: str, action: str | None = None) -> None:
    st.session_state.pending_menu = page
    st.session_state.pending_action = action
    st.rerun()


def apply_pending_action(state_key: str, allowed: list[str], default: str) -> None:
    pending = st.session_state.get("pending_action")
    if pending in allowed:
        st.session_state[state_key] = pending
        st.session_state.pending_action = None
    elif state_key not in st.session_state:
        st.session_state[state_key] = default


def render_company_logo(
    company: dict[str, Any],
    *,
    sidebar_mode: bool = False,
) -> bool:
    logo_path = company.get("logo_path")
    if not logo_path:
        return False

    logo_url = load_company_logo_url(
        company["id"],
        logo_path,
    )
    if not logo_url:
        return False

    wrapper_class = "company-logo-wrap"
    st.markdown(
        (
            f'<div class="{wrapper_class}">'
            f'<img src="{logo_url}" '
            f'alt="{company.get("nome_visualizzato") or "Logo azienda"}">'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )
    return True


def header(title: str, subtitle: str) -> None:
    company = load_company()
    left, right = st.columns([5.2, 1.1])

    with left:
        st.title(title)
        st.caption(subtitle)

    with right:
        if not render_company_logo(company):
            st.markdown(
                f"**{company['nome_visualizzato']}**"
            )




def status_icon(value: str | None) -> str:
    normalized = (value or "").lower()
    if any(token in normalized for token in ["pagata", "valido", "regolare", "emessa", "attivo"]):
        return "🟢"
    if any(token in normalized for token in ["scaduta", "annullata", "irregolare", "scaduto"]):
        return "🔴"
    if any(token in normalized for token in ["parziale", "attenzione", "in scadenza", "da verificare"]):
        return "🟠"
    return "⚪"


def render_packages_cards(rows: list[dict[str, Any]]) -> None:
    for package in rows:
        with st.container(border=True):
            left, middle, right = st.columns([2.4, 1.4, 1.2])
            with left:
                st.subheader(package["nome"])
                st.caption(
                    f"{package.get('periodicita') or '—'} · "
                    f"{package.get('modalita_lezioni') or '—'}"
                )
            with middle:
                st.metric("Prezzo standard", money(float(package.get("prezzo_standard") or 0)))
            with right:
                lessons = (
                    package.get("lezioni_totali")
                    if package.get("modalita_lezioni") == "Pacchetto lezioni"
                    else package.get("lezioni_per_periodo")
                )
                label = (
                    "Lezioni totali"
                    if package.get("modalita_lezioni") == "Pacchetto lezioni"
                    else "Lezioni per periodo"
                )
                st.metric(label, int(lessons or 0))
            st.caption(f"Stato: {'Attivo' if package.get('attivo') else 'Inattivo'}")


def render_installment_cards(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([1.8, 1, 1.2, 1.2, 1])
            with c1:
                st.write(f"**{row.get('cliente') or 'Cliente'}**")
                st.caption(f"{row.get('pacchetto') or '—'} · Rata {row.get('numero_rata') or '—'}")
            with c2:
                st.caption("SCADENZA")
                st.write(f"**{format_date_it(row.get('data_scadenza'))}**")
            with c3:
                st.caption("PREVISTO")
                st.write(f"**{money(float(row.get('importo_previsto') or 0))}**")
            with c4:
                st.caption("PAGATO / RESIDUO")
                st.write(
                    f"{money(float(row.get('importo_pagato') or 0))} / "
                    f"**{money(float(row.get('residuo_rata') or 0))}**"
                )
            with c5:
                state = row.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")


def render_receipt_cards(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2.1, 1, 1.2, 1.2, 1.2])
            with c1:
                st.write(f"**{row.get('cliente') or 'Cliente'}**")
                type_label = {
                    "abbonamento": "Abbonamento",
                    "vendita_prodotto": "Prodotto / integratori",
                    "servizio": "Servizio extra",
                    "altro_ricavo": "Altro ricavo",
                }.get(row.get("tipo_incasso"), "Incasso")
                st.caption(
                    f"{type_label} · {row.get('causale') or 'Senza descrizione'}"
                )
            with c2:
                st.caption("DATA")
                st.write(f"**{format_date_it(row.get('data_incasso'))}**")
            with c3:
                st.caption("IMPORTO")
                st.write(f"**{money(float(row.get('importo') or 0))}**")
            with c4:
                st.caption("METODO")
                st.write(f"**{row.get('metodo_pagamento') or '—'}**")
            with c5:
                state = row.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")
                if row.get("ricevuta_numero"):
                    st.caption(f"Ricevuta {row['ricevuta_numero']}")


def render_document_cards(
    rows: list[dict[str, Any]],
    allow_open: bool = False,
) -> None:
    for document in rows:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.2, 1.2, 1.2, 1])
            with c1:
                st.write(f"**{document.get('tipo') or 'Documento'}**")
                st.caption(document.get("nome_documento") or "File non associato")
            with c2:
                st.caption("DATA DOCUMENTO")
                st.write(f"**{format_date_it(document.get('data_documento'))}**")
            with c3:
                st.caption("SCADENZA")
                st.write(f"**{format_date_it(document.get('data_scadenza'))}**")
            with c4:
                state = document.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")

            if allow_open and document.get("file_path"):
                try:
                    signed_url = crea_url_documento(
                        db,
                        document["file_path"],
                        expires_in=300,
                    )
                    st.link_button("Apri file", signed_url, use_container_width=True)
                except Exception as exc:
                    st.caption(f"File non apribile: {exc}")

            if document.get("note"):
                st.caption(f"Note: {document['note']}")




def render_supplier_cards(rows: list[dict[str, Any]]) -> None:
    for supplier in rows:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.2, 1.4, 1.5, 1])
            with c1:
                st.subheader(
                    supplier.get("nome_commerciale")
                    or supplier.get("ragione_sociale")
                    or "Fornitore"
                )
                st.caption(supplier.get("ragione_sociale") or "—")
            with c2:
                st.caption("PARTITA IVA")
                st.write(f"**{supplier.get('partita_iva') or '—'}**")
            with c3:
                st.caption("CONTATTI")
                st.write(f"**{supplier.get('telefono') or '—'}**")
                st.caption(supplier.get("email") or supplier.get("pec") or "—")
            with c4:
                state = supplier.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")


def render_expense_cards(rows: list[dict[str, Any]]) -> None:
    for expense in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2.1, 1.4, 1.1, 1.2, 1.2])
            with c1:
                st.write(f"**{expense.get('descrizione') or 'Spesa'}**")
                st.caption(
                    f"{expense.get('fornitore') or 'Senza fornitore'} · "
                    f"{expense.get('categoria') or 'Senza categoria'}"
                )
            with c2:
                st.caption("DOCUMENTO / DATA")
                st.write(f"**{expense.get('numero_documento') or '—'}**")
                st.caption(format_date_it(expense.get("data_documento") or expense.get("data_spesa")))
            with c3:
                st.caption("TOTALE")
                st.write(f"**{money(float(expense.get('totale') or 0))}**")
            with c4:
                st.caption("PAGATO / RESIDUO")
                st.write(
                    f"{money(float(expense.get('pagato') or 0))} / "
                    f"**{money(float(expense.get('residuo') or 0))}**"
                )
            with c5:
                state = expense.get("stato_pagamento") or expense.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")

            if expense.get("allegato_path"):
                try:
                    url = crea_url_documento_spesa(
                        db,
                        expense["allegato_path"],
                        expires_in=300,
                    )
                    st.link_button(
                        "Apri documento",
                        url,
                        use_container_width=True,
                    )
                except Exception as exc:
                    st.caption(f"Documento non apribile: {exc}")


def render_expense_deadline_cards(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2.2, 1.1, 1.2, 1.2, 1.1])
            with c1:
                st.write(f"**{row.get('fornitore') or 'Fornitore'}**")
                st.caption(
                    f"{row.get('descrizione') or 'Spesa'} · "
                    f"Scadenza {row.get('numero_scadenza') or '—'}"
                )
            with c2:
                st.caption("SCADENZA")
                st.write(f"**{format_date_it(row.get('data_scadenza'))}**")
            with c3:
                st.caption("PREVISTO")
                st.write(f"**{money(float(row.get('importo_previsto') or 0))}**")
            with c4:
                st.caption("PAGATO / RESIDUO")
                st.write(
                    f"{money(float(row.get('importo_pagato') or 0))} / "
                    f"**{money(float(row.get('residuo_scadenza') or 0))}**"
                )
            with c5:
                state = row.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")


def render_expense_payment_cards(rows: list[dict[str, Any]]) -> None:
    for payment in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2.2, 1.1, 1.2, 1.3, 1])
            with c1:
                st.write(f"**{payment.get('fornitore') or 'Fornitore'}**")
                st.caption(payment.get("causale") or payment.get("descrizione_spesa") or "Pagamento spesa")
            with c2:
                st.caption("DATA")
                st.write(f"**{format_date_it(payment.get('data_pagamento'))}**")
            with c3:
                st.caption("IMPORTO")
                st.write(f"**{money(float(payment.get('importo') or 0))}**")
            with c4:
                st.caption("METODO")
                st.write(f"**{payment.get('metodo_pagamento') or '—'}**")
            with c5:
                state = payment.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")


def render_audit_cards(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1.2, 1.5, 2.5])
            with c1:
                raw_date = row.get("data")
                display_date = (
                    raw_date.replace("T", " ")[:19]
                    if raw_date and isinstance(raw_date, str)
                    else str(raw_date or "—")
                )
                st.caption("DATA E ORA")
                st.write(f"**{display_date}**")
            with c2:
                st.caption("OPERAZIONE")
                action = (row.get("azione") or "—").replace("_", " ").capitalize()
                st.write(f"**{action}**")
                st.caption((row.get("tabella") or "—").replace("_", " "))
            with c3:
                st.caption("MOTIVO / DETTAGLIO")
                st.write(row.get("motivo") or "Operazione registrata automaticamente")


def sidebar() -> str:
    with st.sidebar:
        companies = load_companies()
        company_labels = {
            (
                f"{company['nome_visualizzato']} · "
                f"{company.get('ragione_sociale') or 'Azienda'}"
            ): company["id"]
            for company in companies
        }

        current_id = load_company()["id"]
        current_label = next(
            label
            for label, company_id in company_labels.items()
            if company_id == current_id
        )

        selected_company_label = st.selectbox(
            "Azienda attiva",
            list(company_labels),
            index=list(company_labels).index(current_label),
        )
        selected_company_id = company_labels[selected_company_label]

        if selected_company_id != current_id:
            switch_active_company(selected_company_id)

        company = load_company()
        render_company_logo(
            company,
            sidebar_mode=True,
        )
        st.header(company["nome_visualizzato"])
        st.caption(
            company.get("ragione_sociale")
            or "Gestionale aziendale"
        )

        if st.session_state.pending_menu:
            st.session_state.menu = st.session_state.pending_menu
            st.session_state.pending_menu = None

        selected = st.radio(
            "Menu",
            [
                "Reception",
                "Pacchetti",
                "Abbonamenti",
                "Clienti",
                "Contabilità",
                "Admin",
                "Azienda",
            ],
            key="menu",
            label_visibility="collapsed",
        )

        st.divider()
        st.write("Pentti Salenius")
        st.caption("Super Admin · Multi-azienda")
        st.caption(f"Versione {APP_VERSION}")

    return selected


# ============================================================
# RECEPTION
# ============================================================

def page_reception() -> None:
    header("Reception", "Agenda, clienti, incassi, presenze, badge e alert.")

    actions = [
        ("Nuovo cliente", "Clienti", "Nuovo cliente"),
        ("Modifica cliente", "Clienti", "Modifica cliente"),
        ("Registra incasso", "Contabilità", "Nuovo incasso"),
        ("Accesso tornello", None, None),
        ("Agenda / Calendario", None, None),
        ("Stampa ricevuta", "Contabilità", "Ricevute"),
        ("Messaggio cliente", None, None),
        ("Associa badge", None, None),
        ("Sincronizza badge", None, None),
        ("Ricalcolo settimanale", None, None),
        ("Aggiungi prenotazione", None, None),
        ("Conferma presenza", None, None),
        ("Carica documento", "Clienti", "Modifica cliente"),
        ("Accesso manuale", None, None),
        ("Storico cliente", "Clienti", "Modifica cliente"),
        ("Situazione cliente", "Clienti", "Elenco clienti"),
    ]

    for start in range(0, len(actions), 4):
        cols = st.columns(4)
        for col, (label, page, action) in zip(cols, actions[start:start + 4]):
            with col:
                if st.button(label, key=f"rec_{label}", use_container_width=True):
                    if page:
                        goto(page, action)
                    else:
                        st.info(f"'{label}' verrà attivato nel blocco funzionale dedicato.")


# ============================================================
# PACCHETTI
# ============================================================

def page_packages() -> None:
    header("Pacchetti", "Listino generale dei servizi.")

    action = st.selectbox("Operazione", ["Elenco pacchetti", "Nuovo pacchetto"])

    if action == "Elenco pacchetti":
        rows = load_packages()
        if not rows:
            st.info("Nessun pacchetto registrato.")
            return

        render_packages_cards(rows)
        return

    with st.form("new_package_form"):
        nome = st.text_input("Nome pacchetto *")
        c1, c2 = st.columns(2)
        periodicita = c1.selectbox("Periodicità *", list(PERIODICITA_MESI))
        prezzo = c2.number_input("Prezzo standard", min_value=0.0, step=10.0)

        modalita = st.selectbox(
            "Modalità lezioni *",
            ["Settimanale", "Mensile", "Pacchetto lezioni"],
        )

        if modalita == "Settimanale":
            lezioni_per_periodo = st.number_input("Lezioni a settimana", min_value=1, step=1, value=3)
            lezioni_totali = 0
        elif modalita == "Mensile":
            lezioni_per_periodo = st.number_input("Lezioni al mese", min_value=1, step=1, value=12)
            lezioni_totali = 0
        else:
            lezioni_per_periodo = 0
            lezioni_totali = st.number_input("Numero totale di lezioni", min_value=1, step=1, value=20)

        submitted = st.form_submit_button("Salva pacchetto", use_container_width=True)

    if submitted:
        try:
            if not nome.strip():
                raise ValueError("Il nome del pacchetto è obbligatorio.")

            crea_pacchetto(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "nome": nome.strip(),
                    "periodicita": periodicita,
                    "prezzo_standard": float(prezzo),
                    "durata_numero": PERIODICITA_MESI[periodicita],
                    "durata_unita": "mesi",
                    "modalita_lezioni": modalita,
                    "lezioni_per_periodo": int(lezioni_per_periodo),
                    "lezioni_totali": int(lezioni_totali),
                    "lezioni_standard": calculate_package_lessons(
                        periodicita,
                        modalita,
                        int(lezioni_per_periodo),
                        int(lezioni_totali),
                    ),
                    "attivo": True,
                },
            )
            clear_data_cache()
            st.success("Pacchetto salvato nel database.")
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


# ============================================================
# CLIENTI - REGISTRAZIONE
# ============================================================

def new_customer_flow() -> None:
    packages = load_packages()
    if not packages:
        st.warning("Prima devi registrare almeno un pacchetto.")
        return

    st.subheader("1. Anagrafica")
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome *")
    cognome = c2.text_input("Cognome *")

    c3, c4, c5 = st.columns(3)
    telefono = c3.text_input("Telefono")
    whatsapp = c4.text_input("WhatsApp")
    email = c5.text_input("Email")

    c6, c7 = st.columns(2)
    codice_fiscale = c6.text_input("Codice fiscale")
    partita_iva = c7.text_input("Partita IVA")

    indirizzo = st.text_input("Indirizzo")
    note = st.text_area("Note")

    st.divider()
    st.subheader("2. Pacchetto e abbonamento")

    package_map = {p["nome"]: p for p in packages}
    package_name = st.selectbox("Pacchetto *", list(package_map))
    package = package_map[package_name]

    c8, c9 = st.columns(2)
    data_inizio = c8.date_input("Data inizio", value=date.today(), format="DD/MM/YYYY")
    data_fine = c9.date_input(
        "Data fine prevista",
        value=calculate_package_end(data_inizio, package["periodicita"]),
        format="DD/MM/YYYY",
    )

    c10, c11 = st.columns(2)
    prezzo_concordato = c10.number_input(
        "Prezzo concordato",
        min_value=0.0,
        step=10.0,
        value=float(package["prezzo_standard"]),
    )
    lezioni_iniziali = c11.number_input(
        "Lezioni iniziali",
        min_value=0,
        step=1,
        value=int(package["lezioni_standard"]),
    )

    tipologia_pagamento = st.selectbox(
        "Tipologia pagamento",
        ["Soluzione unica", "Mensile", "Trimestrale", "Semestrale", "Personalizzato"],
    )

    if tipologia_pagamento == "Soluzione unica":
        numero_rate = 1
        step_mesi = 0
    else:
        numero_rate = st.number_input("Numero rate", min_value=1, step=1, value=1)
        step_mesi = {
            "Mensile": 1,
            "Trimestrale": 3,
            "Semestrale": 6,
            "Personalizzato": 1,
        }[tipologia_pagamento]

    prima_scadenza = st.date_input("Data prima scadenza", value=data_inizio, format="DD/MM/YYYY")

    piano_rate = st.data_editor(
        pd.DataFrame(
            build_installment_plan(
                float(prezzo_concordato),
                int(numero_rate),
                prima_scadenza,
                step_mesi,
            )
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "numero_rata": st.column_config.NumberColumn("N. rata", min_value=1, step=1),
            "data_scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
            "importo_previsto": st.column_config.NumberColumn("Importo previsto", format="€ %.2f", min_value=0.0),
        },
    )

    st.divider()
    st.subheader("3. Acconto iniziale")

    c12, c13 = st.columns(2)
    acconto = c12.number_input(
        "Acconto iniziale",
        min_value=0.0,
        max_value=float(prezzo_concordato),
        step=10.0,
        value=0.0,
    )
    metodo_acconto = c13.selectbox(
        "Metodo di pagamento dell'acconto",
        ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
    )

    residuo_live = max(float(prezzo_concordato) - float(acconto), 0.0)
    m1, m2, m3 = st.columns(3)
    m1.metric("Prezzo pacchetto", money(float(prezzo_concordato)))
    m2.metric("Acconto iniziale", money(float(acconto)))
    m3.metric("Residuo aggiornato", money(residuo_live))

    st.divider()
    st.subheader("4. Documenti")

    documents = []
    for tipo, default_expiry in [
        ("Certificato medico", True),
        ("Privacy", False),
        ("Contratto", False),
    ]:
        with st.expander(tipo, expanded=(tipo == "Certificato medico")):
            presente = st.checkbox(f"{tipo} presente", key=f"{tipo}_presente_new")
            data_documento = st.date_input(
                "Data documento",
                value=date.today(),
                format="DD/MM/YYYY",
                key=f"{tipo}_data_new",
                disabled=not presente,
            )
            ha_scadenza = st.checkbox(
                "Documento con scadenza",
                value=default_expiry,
                key=f"{tipo}_scadenza_flag_new",
                disabled=not presente,
            )
            default_scadenza = (
                data_documento + relativedelta(years=1) - relativedelta(days=1)
                if default_expiry
                else data_documento
            )
            data_scadenza = st.date_input(
                "Data scadenza",
                value=default_scadenza,
                format="DD/MM/YYYY",
                key=f"{tipo}_scadenza_new",
                disabled=(not presente or not ha_scadenza),
            )
            documents.append(
                {
                    "tipo": tipo,
                    "presente": presente,
                    "data_documento": data_documento.isoformat() if presente else None,
                    "data_scadenza": data_scadenza.isoformat() if presente and ha_scadenza else None,
                }
            )

    if st.button("Salva cliente completo", use_container_width=True):
        totale_rate = float(piano_rate["importo_previsto"].sum()) if not piano_rate.empty else 0.0

        if not nome.strip() or not cognome.strip():
            st.error("Nome e cognome sono obbligatori.")
            return
        if abs(totale_rate - float(prezzo_concordato)) > 0.01:
            st.error("La somma delle rate deve coincidere con il prezzo concordato.")
            return
        if data_fine < data_inizio:
            st.error("La data fine non può precedere la data inizio.")
            return

        payload = {
            "azienda_id": load_company()["id"],
            "cliente": {
                "nome": nome.strip(),
                "cognome": cognome.strip(),
                "telefono": telefono.strip() or None,
                "whatsapp": whatsapp.strip() or None,
                "email": email.strip() or None,
                "codice_fiscale": codice_fiscale.strip() or None,
                "partita_iva": partita_iva.strip() or None,
                "indirizzo": indirizzo.strip() or None,
                "note": note.strip() or None,
            },
            "abbonamento": {
                "pacchetto_id": package["id"],
                "data_inizio": data_inizio.isoformat(),
                "data_fine_prevista": data_fine.isoformat(),
                "prezzo_concordato": float(prezzo_concordato),
                "lezioni_iniziali": int(lezioni_iniziali),
                "tipologia_pagamento": tipologia_pagamento,
            },
            "rate": [
                {
                    "numero_rata": int(row["numero_rata"]),
                    "data_scadenza": row["data_scadenza"].isoformat(),
                    "importo_previsto": float(row["importo_previsto"]),
                }
                for _, row in piano_rate.iterrows()
            ],
            "incasso_iniziale": (
                {
                    "importo": float(acconto),
                    "metodo_pagamento": metodo_acconto,
                    "causale": "Acconto iniziale",
                }
                if acconto > 0
                else None
            ),
            "documenti": [d for d in documents if d["presente"]],
        }

        try:
            result = crea_cliente_completo(db, payload)
            clear_data_cache()
            st.session_state.selected_customer_id = result["cliente_id"]
            st.success(f"Cliente salvato. Residuo iniziale: {money(residuo_live)}")
            st.balloons()
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


# ============================================================
# CLIENTI - ELENCO E SELETTORE
# ============================================================

def client_list() -> None:
    rows = load_clients()
    if not rows:
        st.info("Nessun cliente registrato.")
        return

    search = st.text_input("Cerca", placeholder="Nome, cognome, telefono o WhatsApp")
    filtered = []

    for row in rows:
        searchable = " ".join(
            str(row.get(key) or "")
            for key in ["nome", "cognome", "telefono", "whatsapp"]
        ).lower()
        if search and search.lower() not in searchable:
            continue
        filtered.append(row)

    st.info(
        f"{len(filtered)} clienti visualizzati · "
        f"Residuo complessivo {money(sum(float(r.get('residuo') or 0) for r in filtered))}"
    )

    for customer in filtered:
        with st.container(border=True):
            top_left, top_right = st.columns([4, 1])
            with top_left:
                st.subheader(f"{customer['cognome']} {customer['nome']}")
                st.caption(
                    " · ".join(
                        x for x in [customer.get("telefono"), customer.get("whatsapp")] if x
                    ) or "Contatti non inseriti"
                )
            with top_right:
                st.markdown(f"### {customer.get('stato_complessivo') or '—'}")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.caption("ABBONAMENTO")
            c1.write(f"**{customer.get('pacchetto_nome') or '—'}**")
            c1.caption(customer.get("tipologia_pagamento") or "—")

            c2.caption("SCADENZA")
            c2.write(f"**{format_date_it(customer.get('data_fine_prevista'))}**")

            c3.caption("SITUAZIONE ECONOMICA")
            c3.write(f"Iniziale **{money(float(customer.get('prezzo_concordato') or 0))}**")
            c3.caption(f"Pagato {money(float(customer.get('pagato') or 0))}")
            c3.write(f"Residuo **{money(float(customer.get('residuo') or 0))}**")

            c4.caption("PROSSIMA RATA")
            c4.write(f"**{format_date_it(customer.get('prossima_rata_data'))}**")
            c4.caption(money(float(customer.get("prossima_rata_importo") or 0)))

            c5.caption("CERTIFICATO")
            c5.write(f"**{customer.get('certificato_stato') or 'Mancante'}**")

            actions = st.columns(4)
            with actions[0]:
                if st.button(
                    "Apri scheda",
                    key=f"open_{customer['cliente_id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    st.session_state.pending_action = "Scheda cliente"
                    st.rerun()

            with actions[1]:
                if st.button(
                    "Modifica",
                    key=f"edit_{customer['cliente_id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    st.session_state.pending_action = "Modifica cliente"
                    st.rerun()

            with actions[2]:
                if st.button(
                    "Registra incasso",
                    key=f"cash_{customer['cliente_id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    goto("Contabilità", "Nuovo incasso")

            with actions[3]:
                if st.button(
                    "Documenti",
                    key=f"docs_{customer['cliente_id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    st.session_state.pending_action = "Modifica cliente"
                    st.rerun()


def customer_selector(label: str) -> str | None:
    rows = load_clients()
    if not rows:
        st.info("Nessun cliente registrato.")
        return None

    labels = {f"{r['cognome']} {r['nome']}": r["cliente_id"] for r in rows}
    selected_id = st.session_state.get("selected_customer_id")
    selected_label = next((k for k, v in labels.items() if v == selected_id), list(labels)[0])

    choice = st.selectbox(
        label,
        list(labels),
        index=list(labels).index(selected_label),
    )
    st.session_state.selected_customer_id = labels[choice]
    return labels[choice]


# ============================================================
# MODIFICA CLIENTE COMPLETA
# ============================================================

def manage_customer_page() -> None:
    customer_id = customer_selector("Cliente da gestire")
    if not customer_id:
        return

    detail = get_cliente_dettaglio(db, customer_id)
    customer = detail["cliente"]
    subscription = detail.get("abbonamento")
    installments = detail.get("rate") or []
    receipts = detail.get("incassi") or []
    documents = detail.get("documenti") or []
    audit = detail.get("audit") or []

    tabs = st.tabs([
        "Anagrafica",
        "Abbonamento",
        "Rate",
        "Documenti",
        "Incassi",
        "Storico",
    ])

    with tabs[0]:
        with st.form("modify_anagrafica_form"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome *", value=customer.get("nome") or "")
            cognome = c2.text_input("Cognome *", value=customer.get("cognome") or "")

            c3, c4, c5 = st.columns(3)
            telefono = c3.text_input("Telefono", value=customer.get("telefono") or "")
            whatsapp = c4.text_input("WhatsApp", value=customer.get("whatsapp") or "")
            email = c5.text_input("Email", value=customer.get("email") or "")

            c6, c7 = st.columns(2)
            codice_fiscale = c6.text_input("Codice fiscale", value=customer.get("codice_fiscale") or "")
            partita_iva = c7.text_input("Partita IVA", value=customer.get("partita_iva") or "")

            indirizzo = st.text_input("Indirizzo", value=customer.get("indirizzo") or "")
            stato = st.selectbox(
                "Stato cliente",
                ["attivo", "inattivo"],
                index=["attivo", "inattivo"].index(customer.get("stato") or "attivo"),
            )
            note = st.text_area("Note", value=customer.get("note") or "")

            submitted = st.form_submit_button("Salva anagrafica", use_container_width=True)

        if submitted:
            try:
                modifica_anagrafica_cliente(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "cliente_id": customer_id,
                        "nome": nome.strip(),
                        "cognome": cognome.strip(),
                        "telefono": telefono.strip() or None,
                        "whatsapp": whatsapp.strip() or None,
                        "email": email.strip() or None,
                        "codice_fiscale": codice_fiscale.strip() or None,
                        "partita_iva": partita_iva.strip() or None,
                        "indirizzo": indirizzo.strip() or None,
                        "stato": stato,
                        "note": note.strip() or None,
                    },
                )
                clear_data_cache()
                st.success("Anagrafica aggiornata.")
            except Exception as exc:
                st.error(f"Errore durante la modifica: {exc}")

    with tabs[1]:
        if not subscription:
            st.info("Nessun abbonamento attivo.")
        else:
            package_map = {p["nome"]: p for p in load_packages()}
            current_package_name = subscription["pacchetto_nome"]
            package_names = list(package_map)
            package_index = package_names.index(current_package_name) if current_package_name in package_names else 0

            with st.form("modify_subscription_form"):
                package_name = st.selectbox("Pacchetto", package_names, index=package_index)
                package = package_map[package_name]

                c1, c2 = st.columns(2)
                data_inizio = c1.date_input(
                    "Data inizio",
                    value=date.fromisoformat(subscription["data_inizio"]),
                    format="DD/MM/YYYY",
                )
                data_fine = c2.date_input(
                    "Data fine prevista",
                    value=date.fromisoformat(subscription["data_fine_prevista"]),
                    format="DD/MM/YYYY",
                )

                c3, c4 = st.columns(2)
                prezzo = c3.number_input(
                    "Prezzo concordato",
                    min_value=0.0,
                    step=10.0,
                    value=float(subscription["prezzo_concordato"]),
                )
                lezioni = c4.number_input(
                    "Lezioni iniziali",
                    min_value=0,
                    step=1,
                    value=int(subscription["lezioni_iniziali"]),
                )

                tipologia = st.selectbox(
                    "Tipologia pagamento",
                    ["Soluzione unica", "Mensile", "Trimestrale", "Semestrale", "Personalizzato"],
                    index=["Soluzione unica", "Mensile", "Trimestrale", "Semestrale", "Personalizzato"].index(
                        subscription["tipologia_pagamento"]
                    ),
                )

                stato_abbonamento = st.selectbox(
                    "Stato abbonamento",
                    ["da_attivare", "attivo", "sospeso", "terminato", "chiuso_anticipatamente"],
                    index=["da_attivare", "attivo", "sospeso", "terminato", "chiuso_anticipatamente"].index(
                        subscription["stato"]
                    ) if subscription["stato"] in ["da_attivare", "attivo", "sospeso", "terminato", "chiuso_anticipatamente"] else 1,
                )

                gestione_rate = st.selectbox(
                    "Gestione rate dopo la modifica",
                    ["Lascia invariato", "Rigenera solo le rate aperte", "Modifica manualmente nella scheda Rate"],
                )
                note_abbonamento = st.text_area(
                    "Note abbonamento",
                    value=subscription.get("note") or "",
                )

                submitted_subscription = st.form_submit_button(
                    "Salva abbonamento",
                    use_container_width=True,
                )

            if submitted_subscription:
                try:
                    aggiorna_abbonamento_cliente(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "cliente_id": customer_id,
                            "abbonamento_id": subscription["id"],
                            "pacchetto_id": package["id"],
                            "data_inizio": data_inizio.isoformat(),
                            "data_fine_prevista": data_fine.isoformat(),
                            "prezzo_concordato": float(prezzo),
                            "lezioni_iniziali": int(lezioni),
                            "tipologia_pagamento": tipologia,
                            "stato": stato_abbonamento,
                            "gestione_rate": gestione_rate,
                            "note": note_abbonamento.strip() or None,
                        },
                    )
                    clear_data_cache()
                    st.success("Abbonamento aggiornato.")
                except Exception as exc:
                    st.error(f"Errore durante la modifica: {exc}")

    with tabs[2]:
        if not subscription:
            st.info("Nessun abbonamento attivo.")
        elif not installments:
            st.info("Nessuna rata.")
        else:
            rate_df = pd.DataFrame([
                {
                    "rata_id": r["rata_id"],
                    "numero_rata": r["numero_rata"],
                    "data_scadenza": date.fromisoformat(r["data_scadenza"]),
                    "importo_previsto": float(r["importo_previsto"]),
                    "importo_pagato": float(r["importo_pagato"]),
                    "residuo_rata": float(r["residuo_rata"]),
                    "stato": r["stato"],
                    "annullata": r.get("annullata", False),
                }
                for r in installments
            ])

            edited_rates = st.data_editor(
                rate_df,
                use_container_width=True,
                hide_index=True,
                disabled=["rata_id", "numero_rata", "importo_pagato", "residuo_rata", "stato"],
                column_config={
                    "rata_id": None,
                    "numero_rata": st.column_config.NumberColumn("N. rata"),
                    "data_scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                    "importo_previsto": st.column_config.NumberColumn("Importo previsto", format="€ %.2f"),
                    "importo_pagato": st.column_config.NumberColumn("Pagato", format="€ %.2f"),
                    "residuo_rata": st.column_config.NumberColumn("Residuo", format="€ %.2f"),
                    "stato": st.column_config.TextColumn("Stato"),
                    "annullata": st.column_config.CheckboxColumn("Annullata"),
                },
            )

            motivo_rate = st.text_area("Motivo della modifica rate *")

            if st.button("Salva piano rate", use_container_width=True):
                if not motivo_rate.strip():
                    st.error("Il motivo della modifica è obbligatorio.")
                else:
                    try:
                        aggiorna_rate_abbonamento(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "cliente_id": customer_id,
                                "abbonamento_id": subscription["id"],
                                "motivo": motivo_rate.strip(),
                                "rate": [
                                    {
                                        "rata_id": row["rata_id"],
                                        "data_scadenza": row["data_scadenza"].isoformat(),
                                        "importo_previsto": float(row["importo_previsto"]),
                                        "annullata": bool(row["annullata"]),
                                    }
                                    for _, row in edited_rates.iterrows()
                                ],
                            },
                        )
                        clear_data_cache()
                        st.success("Piano rate aggiornato e allocazioni ricalcolate.")
                    except Exception as exc:
                        st.error(f"Errore durante la modifica: {exc}")

    with tabs[3]:
        st.subheader("Documenti presenti")

        active_docs = [d for d in documents if d.get("stato") != "annullato"]
        if active_docs:
            render_document_cards(active_docs, allow_open=True)
        else:
            st.info("Nessun documento.")

        st.subheader("Aggiungi o sostituisci documento")
        tipi_documento = [
            "Certificato medico",
            "Privacy",
            "Contratto",
            "Documento di identità",
            "Codice fiscale",
            "Altro",
        ]

        tipo = st.selectbox("Tipo documento", tipi_documento)
        file_documento = st.file_uploader(
            "Carica file *",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=False,
            help="Formati ammessi: PDF, PNG, JPG/JPEG. Dimensione massima del bucket: 10 MB.",
        )

        data_documento = st.date_input(
            "Data documento",
            value=date.today(),
            format="DD/MM/YYYY",
        )
        ha_scadenza = st.checkbox(
            "Documento con scadenza",
            value=(tipo == "Certificato medico"),
        )
        data_scadenza = st.date_input(
            "Data scadenza",
            value=data_documento + relativedelta(years=1) - relativedelta(days=1),
            format="DD/MM/YYYY",
            disabled=not ha_scadenza,
        )
        stato_documento = st.selectbox(
            "Stato documento",
            ["valido", "da_verificare", "in_scadenza", "scaduto"],
        )
        note_documento = st.text_area("Note documento")

        if st.button("Carica e salva documento", use_container_width=True):
            if file_documento is None:
                st.error("Devi selezionare un file.")
            else:
                uploaded_path = None
                try:
                    uploaded_path = carica_file_documento(
                        db=db,
                        azienda_id=load_company()["id"],
                        cliente_id=customer_id,
                        tipo_documento=tipo,
                        nome_file=file_documento.name,
                        mime_type=file_documento.type or "application/octet-stream",
                        contenuto=file_documento.getvalue(),
                    )

                    salva_documento_cliente(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "cliente_id": customer_id,
                            "abbonamento_id": (
                                subscription["id"]
                                if subscription and tipo == "Contratto"
                                else None
                            ),
                            "tipo": tipo,
                            "nome_documento": file_documento.name,
                            "file_path": uploaded_path,
                            "data_documento": data_documento.isoformat(),
                            "data_scadenza": (
                                data_scadenza.isoformat()
                                if ha_scadenza
                                else None
                            ),
                            "stato": stato_documento,
                            "note": note_documento.strip() or None,
                        },
                    )
                    clear_data_cache()
                    st.success("File caricato e documento salvato.")
                    st.rerun()

                except Exception as exc:
                    if uploaded_path:
                        try:
                            elimina_file_documento(db, uploaded_path)
                        except Exception:
                            pass
                    st.error(f"Errore durante il caricamento: {exc}")

        if active_docs:
            st.subheader("Annulla documento")
            doc_labels = {
                f"{d['tipo']} · {d.get('nome_documento') or 'senza nome'} · "
                f"{format_date_it(d.get('data_documento'))}": d
                for d in active_docs
            }
            selected_doc = doc_labels[st.selectbox("Documento", list(doc_labels))]
            motivo_doc = st.text_area("Motivo annullamento documento")

            if st.button("Annulla documento", use_container_width=True):
                if not motivo_doc.strip():
                    st.error("Il motivo è obbligatorio.")
                else:
                    try:
                        annulla_documento_cliente(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "documento_id": selected_doc["documento_id"],
                                "motivo": motivo_doc.strip(),
                            },
                        )
                        clear_data_cache()
                        st.success("Documento annullato. Il file resta archiviato per lo storico.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore durante l'annullamento: {exc}")

    with tabs[4]:
        if receipts:
            render_receipt_cards(receipts)
        else:
            st.info("Nessun incasso.")
        st.caption("Gli incassi non si modificano: si annullano e si registrano nuovamente.")

    with tabs[5]:
        if audit:
            render_audit_cards(audit)
        else:
            st.info("Nessuna operazione storicizzata.")


def customer_sheet_page() -> None:
    customer_id = customer_selector("Cliente")
    if not customer_id:
        return

    detail = get_cliente_dettaglio(db, customer_id)
    customer = detail["cliente"]
    subscription = detail.get("abbonamento")
    installments = detail.get("rate") or []
    receipts = detail.get("incassi") or []
    documents = detail.get("documenti") or []

    st.subheader(f"{customer['cognome']} {customer['nome']}")
    c1, c2, c3 = st.columns(3)
    c1.write(f"Telefono: **{customer.get('telefono') or '—'}**")
    c2.write(f"WhatsApp: **{customer.get('whatsapp') or '—'}**")
    c3.write(f"Email: **{customer.get('email') or '—'}**")

    st.divider()
    st.subheader("Abbonamento")
    if subscription:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Pacchetto", subscription.get("pacchetto_nome") or "—")
        m2.metric("Prezzo", money(float(subscription.get("prezzo_concordato") or 0)))
        m3.metric("Pagato", money(float(subscription.get("pagato") or 0)))
        m4.metric("Residuo", money(float(subscription.get("residuo") or 0)))
        st.write(
            f"Periodo: **{format_date_it(subscription.get('data_inizio'))} – "
            f"{format_date_it(subscription.get('data_fine_prevista'))}**"
        )
    else:
        st.info("Nessun abbonamento attivo.")

    st.divider()
    st.subheader("Rate")
    if installments:
        render_installment_cards(installments)
    else:
        st.info("Nessuna rata.")

    st.subheader("Incassi")
    if receipts:
        render_receipt_cards(receipts)
    else:
        st.info("Nessun incasso.")

    st.subheader("Documenti")
    active_documents = [d for d in documents if d.get("stato") != "annullato"]
    if active_documents:
        render_document_cards(active_documents, allow_open=True)
    else:
        st.info("Nessun documento.")


def page_customers() -> None:
    header("Clienti", "Anagrafiche, abbonamenti, documenti e storico.")

    actions = ["Elenco clienti", "Nuovo cliente", "Modifica cliente", "Scheda cliente"]
    apply_pending_action("client_action", actions, "Elenco clienti")

    action = st.selectbox("Operazione", actions, key="client_action")

    if action == "Elenco clienti":
        client_list()
    elif action == "Nuovo cliente":
        new_customer_flow()
    elif action == "Modifica cliente":
        manage_customer_page()
    else:
        customer_sheet_page()


# ============================================================
# CONTABILITÀ
# ============================================================

def new_receipt_page() -> None:
    rows = load_clients()
    if not rows:
        st.info("Nessun cliente registrato.")
        return

    type_map = {
        "Abbonamento": "abbonamento",
        "Vendita prodotto / integratori": "vendita_prodotto",
        "Servizio extra": "servizio",
        "Altro ricavo": "altro_ricavo",
    }

    tipo_label = st.selectbox(
        "Tipo di incasso",
        list(type_map),
        help=(
            "Solo gli incassi riferiti all'abbonamento riducono il residuo "
            "e vengono allocati alle rate."
        ),
    )
    tipo_incasso = type_map[tipo_label]
    is_subscription = tipo_incasso == "abbonamento"

    if is_subscription:
        selectable = [
            row for row in rows
            if row.get("abbonamento_id")
            and float(row.get("residuo") or 0) > 0
        ]
        if not selectable:
            st.info("Nessun cliente con residuo abbonamento aperto.")
            return
    else:
        selectable = rows

    labels = {
        f"{row['cognome']} {row['nome']}": row
        for row in selectable
    }
    selected_id = st.session_state.get("selected_customer_id")
    selected_label = next(
        (
            label for label, row in labels.items()
            if row["cliente_id"] == selected_id
        ),
        list(labels)[0],
    )
    customer = labels[
        st.selectbox(
            "Cliente",
            list(labels),
            index=list(labels).index(selected_label),
        )
    ]

    if is_subscription:
        summary = st.columns(4)
        summary[0].metric(
            "Prezzo iniziale",
            money(float(customer.get("prezzo_concordato") or 0)),
        )
        summary[1].metric(
            "Già pagato",
            money(float(customer.get("pagato") or 0)),
        )
        summary[2].metric(
            "Residuo",
            money(float(customer.get("residuo") or 0)),
        )
        summary[3].metric(
            "Prossima rata",
            f"{format_date_it(customer.get('prossima_rata_data'))} · "
            f"{money(float(customer.get('prossima_rata_importo') or 0))}",
        )
        max_amount = float(customer.get("residuo") or 0)
        default_description = "Pagamento abbonamento"
    else:
        st.info(
            "Questo incasso sarà registrato come ricavo autonomo e non "
            "modificherà residuo, rate o stato dell'abbonamento."
        )
        max_amount = None
        default_description = {
            "vendita_prodotto": "Vendita integratori / prodotto",
            "servizio": "Servizio extra",
            "altro_ricavo": "",
        }[tipo_incasso]

    with st.form("new_receipt_form"):
        c1, c2 = st.columns(2)

        amount_kwargs = {
            "label": "Importo",
            "min_value": 0.0,
            "step": 10.0,
        }
        if max_amount is not None:
            amount_kwargs["max_value"] = max_amount

        importo = c1.number_input(**amount_kwargs)
        data_incasso = c2.date_input(
            "Data incasso",
            value=date.today(),
            format="DD/MM/YYYY",
        )

        c3, c4 = st.columns(2)
        metodo = c3.selectbox(
            "Metodo",
            ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
        )
        with c4:
            if is_subscription:
                st.write("Allocazione automatica alle rate più vecchie")
            else:
                st.write("Ricavo autonomo, senza allocazione alle rate")

        descrizione = st.text_input(
            "Descrizione incasso *",
            value=default_description,
            placeholder=(
                "Es. integratori, lezione Pilates, visita nutrizionista, altro"
            ),
        )
        note = st.text_area("Note")
        genera_ricevuta = st.checkbox("Genera ricevuta", value=True)

        submitted = st.form_submit_button(
            "Registra incasso",
            use_container_width=True,
        )

    if submitted:
        if importo <= 0:
            st.error("L'importo deve essere maggiore di zero.")
            return
        if not descrizione.strip():
            st.error("La descrizione dell'incasso è obbligatoria.")
            return

        try:
            result = crea_incasso_completo(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "cliente_id": customer["cliente_id"],
                    "abbonamento_id": (
                        customer.get("abbonamento_id")
                        if is_subscription
                        else None
                    ),
                    "tipo_incasso": tipo_incasso,
                    "data_incasso": data_incasso.isoformat(),
                    "importo": float(importo),
                    "metodo_pagamento": metodo,
                    "causale": descrizione.strip(),
                    "note": note.strip() or None,
                    "genera_ricevuta": genera_ricevuta,
                },
            )
            clear_data_cache()

            pdf_message = ""
            if result.get("ricevuta_id"):
                try:
                    ensure_receipt_pdf(result["ricevuta_id"])
                    pdf_message = " Ricevuta PDF generata e archiviata."
                except Exception as pdf_exc:
                    pdf_message = (
                        " Incasso salvato, ma il PDF non è stato generato: "
                        f"{pdf_exc}. Potrai rigenerarlo dalla sezione Ricevute."
                    )

            if is_subscription:
                st.success(
                    "Incasso abbonamento registrato. "
                    f"Nuovo residuo: "
                    f"{money(float(result['nuovo_residuo']))}."
                    f"{pdf_message}"
                )
            else:
                st.success(
                    "Ricavo registrato senza modificare "
                    "abbonamento, rate o residuo."
                    f"{pdf_message}"
                )

        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


def receipts_list_page() -> None:
    rows = load_receipts()
    if not rows:
        st.info("Nessun incasso registrato.")
        return

    render_receipt_cards(rows)

    valid = [r for r in rows if r["stato"] == "valido"]
    if not valid:
        return

    labels = {
        f"{format_date_it(r['data_incasso'])} · {r['cliente']} · {money(float(r['importo']))}": r
        for r in valid
    }

    st.subheader("Annulla incasso")
    selected = labels[st.selectbox("Incasso", list(labels))]
    motivo = st.text_area("Motivo annullamento")

    if st.button("Annulla incasso", use_container_width=True):
        if not motivo.strip():
            st.error("Il motivo è obbligatorio.")
            return

        try:
            result = annulla_incasso(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "incasso_id": selected["incasso_id"],
                    "motivo": motivo.strip(),
                },
            )
            clear_data_cache()

            if result.get("ricevuta_id"):
                try:
                    ensure_receipt_pdf(
                        result["ricevuta_id"],
                        force=True,
                    )
                except Exception:
                    pass

            nuovo_residuo = result.get("nuovo_residuo")
            if nuovo_residuo is None:
                st.success("Incasso annullato.")
            else:
                st.success(
                    "Incasso annullato. Nuovo residuo: "
                    f"{money(float(nuovo_residuo))}"
                )
        except Exception as exc:
            st.error(f"Errore durante l'annullamento: {exc}")


def installments_page() -> None:
    rows = load_installments()
    if rows:
        render_installment_cards(rows)
    else:
        st.info("Nessuna rata registrata.")


def receipts_print_page() -> None:
    rows = [row for row in load_receipts() if row.get("ricevuta_numero")]
    if not rows:
        st.info("Nessuna ricevuta disponibile.")
        return

    labels = {
        (
            f"{row['ricevuta_numero']} · {row['cliente']} · "
            f"{money(float(row['importo']))}"
        ): row
        for row in rows
    }
    selected = labels[st.selectbox("Ricevuta", list(labels))]

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.2, 2, 1.2, 1.2])
        c1.metric("Numero", selected["ricevuta_numero"])
        c2.metric("Cliente", selected["cliente"])
        c3.metric("Importo", money(float(selected["importo"])))
        c4.metric(
            "Stato",
            selected.get("ricevuta_stato") or "emessa",
        )

        st.caption(
            f"Data {format_date_it(selected['data_incasso'])} · "
            f"{selected['metodo_pagamento']} · "
            f"{selected.get('causale') or 'Ricevuta'}"
        )

        if selected.get("pdf_path"):
            try:
                url = crea_url_ricevuta(
                    db,
                    selected["pdf_path"],
                    expires_in=300,
                )
                st.link_button(
                    "Apri / scarica PDF",
                    url,
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"PDF non apribile: {exc}")

        button_label = (
            "Rigenera PDF"
            if selected.get("pdf_path")
            else "Genera PDF"
        )
        if st.button(button_label, use_container_width=True):
            try:
                path = ensure_receipt_pdf(
                    selected["ricevuta_id"],
                    force=True,
                )
                url = crea_url_ricevuta(db, path, expires_in=300)
                st.success("Ricevuta PDF generata e archiviata.")
                st.link_button(
                    "Apri PDF",
                    url,
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"Errore durante la generazione: {exc}")




def suppliers_page() -> None:
    st.subheader("Fornitori")
    tabs = st.tabs(["Elenco", "Nuovo fornitore", "Modifica"])

    with tabs[0]:
        rows = load_suppliers()
        search = st.text_input(
            "Cerca fornitore",
            placeholder="Ragione sociale, nome commerciale, P. IVA",
            key="supplier_search",
        )
        if search:
            lowered = search.lower()
            rows = [
                row for row in rows
                if lowered in " ".join(
                    str(row.get(field) or "")
                    for field in [
                        "ragione_sociale",
                        "nome_commerciale",
                        "partita_iva",
                        "codice_fiscale",
                    ]
                ).lower()
            ]

        if rows:
            render_supplier_cards(rows)
        else:
            st.info("Nessun fornitore trovato.")

    with tabs[1]:
        with st.form("new_supplier_form"):
            c1, c2 = st.columns(2)
            legal_name = c1.text_input("Ragione sociale *")
            trade_name = c2.text_input("Nome commerciale")

            c3, c4 = st.columns(2)
            vat = c3.text_input("Partita IVA")
            tax_code = c4.text_input("Codice fiscale")

            address = st.text_input("Indirizzo")
            c5, c6, c7 = st.columns(3)
            city = c5.text_input("Città")
            cap = c6.text_input("CAP")
            province = c7.text_input("Provincia")

            c8, c9, c10 = st.columns(3)
            phone = c8.text_input("Telefono")
            email = c9.text_input("Email")
            pec = c10.text_input("PEC")

            c11, c12 = st.columns(2)
            sdi = c11.text_input("Codice SDI")
            iban = c12.text_input("IBAN")

            contact = st.text_input("Referente")
            notes = st.text_area("Note")

            submitted = st.form_submit_button(
                "Salva fornitore",
                use_container_width=True,
            )

        if submitted:
            if not legal_name.strip():
                st.error("La ragione sociale è obbligatoria.")
            else:
                try:
                    crea_fornitore(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "ragione_sociale": legal_name.strip(),
                            "nome_commerciale": trade_name.strip() or None,
                            "partita_iva": vat.strip() or None,
                            "codice_fiscale": tax_code.strip() or None,
                            "indirizzo": address.strip() or None,
                            "citta": city.strip() or None,
                            "cap": cap.strip() or None,
                            "provincia": province.strip() or None,
                            "telefono": phone.strip() or None,
                            "email": email.strip() or None,
                            "pec": pec.strip() or None,
                            "codice_sdi": sdi.strip() or None,
                            "iban": iban.strip() or None,
                            "referente": contact.strip() or None,
                            "note": notes.strip() or None,
                            "stato": "attivo",
                        },
                    )
                    clear_data_cache()
                    st.success("Fornitore salvato.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Errore durante il salvataggio: {exc}")

    with tabs[2]:
        suppliers = load_suppliers()
        if not suppliers:
            st.info("Nessun fornitore da modificare.")
        else:
            labels = {
                (
                    supplier.get("nome_commerciale")
                    or supplier["ragione_sociale"]
                ): supplier
                for supplier in suppliers
            }
            selected = labels[st.selectbox(
                "Fornitore da modificare",
                list(labels),
            )]

            with st.form("edit_supplier_form"):
                c1, c2 = st.columns(2)
                legal_name = c1.text_input(
                    "Ragione sociale *",
                    value=selected.get("ragione_sociale") or "",
                )
                trade_name = c2.text_input(
                    "Nome commerciale",
                    value=selected.get("nome_commerciale") or "",
                )

                c3, c4, c5 = st.columns(3)
                phone = c3.text_input(
                    "Telefono",
                    value=selected.get("telefono") or "",
                )
                email = c4.text_input(
                    "Email",
                    value=selected.get("email") or "",
                )
                iban = c5.text_input(
                    "IBAN",
                    value=selected.get("iban") or "",
                )

                state = st.selectbox(
                    "Stato",
                    ["attivo", "inattivo"],
                    index=0 if selected.get("stato") == "attivo" else 1,
                )
                notes = st.text_area(
                    "Note",
                    value=selected.get("note") or "",
                )

                submitted_edit = st.form_submit_button(
                    "Salva modifiche",
                    use_container_width=True,
                )

            if submitted_edit:
                try:
                    modifica_fornitore(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "fornitore_id": selected["id"],
                            "ragione_sociale": legal_name.strip(),
                            "nome_commerciale": trade_name.strip() or None,
                            "telefono": phone.strip() or None,
                            "email": email.strip() or None,
                            "iban": iban.strip() or None,
                            "stato": state,
                            "note": notes.strip() or None,
                        },
                    )
                    clear_data_cache()
                    st.success("Fornitore aggiornato.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Errore durante la modifica: {exc}")


def new_expense_page() -> None:
    suppliers = [
        row for row in load_suppliers()
        if row.get("stato") == "attivo"
    ]
    categories = [
        row for row in load_expense_categories()
        if row.get("attiva")
    ]

    if not suppliers:
        st.warning("Prima devi registrare almeno un fornitore attivo.")
        return

    st.subheader("Nuova spesa")

    supplier_map = {
        (
            supplier.get("nome_commerciale")
            or supplier["ragione_sociale"]
        ): supplier
        for supplier in suppliers
    }
    supplier_name = st.selectbox("Fornitore *", list(supplier_map))
    supplier = supplier_map[supplier_name]

    category_options = ["— Nuova categoria —"] + [
        category["nome"] for category in categories
    ]
    category_name = st.selectbox("Categoria *", category_options)

    new_category_name = None
    if category_name == "— Nuova categoria —":
        new_category_name = st.text_input(
            "Nome nuova categoria *",
            placeholder="Es. Affitto, utenze, consulenze, integratori",
        )

    c1, c2 = st.columns(2)
    description = c1.text_input("Descrizione *")
    expense_date = c2.date_input(
        "Data registrazione",
        value=date.today(),
        format="DD/MM/YYYY",
    )

    c3, c4, c5 = st.columns(3)
    taxable = c3.number_input(
        "Imponibile",
        min_value=0.0,
        step=10.0,
    )
    vat = c4.number_input(
        "IVA",
        min_value=0.0,
        step=1.0,
    )
    total = c5.number_input(
        "Totale documento *",
        min_value=0.0,
        step=10.0,
        value=float(taxable + vat),
    )

    c6, c7, c8 = st.columns(3)
    document_type = c6.selectbox(
        "Tipo documento",
        ["Fattura", "Ricevuta", "Nota di credito", "Altro"],
    )
    document_number = c7.text_input("Numero documento")
    document_date = c8.date_input(
        "Data documento",
        value=expense_date,
        format="DD/MM/YYYY",
    )

    competence = st.date_input(
        "Mese di competenza",
        value=expense_date.replace(day=1),
        format="DD/MM/YYYY",
    )

    st.subheader("Piano delle scadenze")
    installment_count = st.number_input(
        "Numero scadenze",
        min_value=1,
        step=1,
        value=1,
    )
    first_due = st.date_input(
        "Prima scadenza",
        value=document_date,
        format="DD/MM/YYYY",
    )
    due_step = st.number_input(
        "Intervallo in mesi",
        min_value=0,
        step=1,
        value=1,
    )

    due_plan = st.data_editor(
        pd.DataFrame(
            build_installment_plan(
                float(total),
                int(installment_count),
                first_due,
                int(due_step),
            )
        ).rename(columns={"numero_rata": "numero_scadenza"}),
        use_container_width=True,
        hide_index=True,
        column_config={
            "numero_scadenza": st.column_config.NumberColumn(
                "N. scadenza",
                min_value=1,
                step=1,
            ),
            "data_scadenza": st.column_config.DateColumn(
                "Data scadenza",
                format="DD/MM/YYYY",
            ),
            "importo_previsto": st.column_config.NumberColumn(
                "Importo previsto",
                format="€ %.2f",
                min_value=0.0,
            ),
        },
    )

    st.subheader("Pagamento iniziale")
    c9, c10 = st.columns(2)
    initial_payment = c9.number_input(
        "Importo pagato subito",
        min_value=0.0,
        max_value=float(total),
        step=10.0,
    )
    payment_method = c10.selectbox(
        "Metodo pagamento iniziale",
        ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
    )

    attachment = st.file_uploader(
        "Allega fattura o ricevuta",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=False,
    )
    notes = st.text_area("Note")

    m1, m2, m3 = st.columns(3)
    m1.metric("Totale", money(float(total)))
    m2.metric("Pagato subito", money(float(initial_payment)))
    m3.metric(
        "Debito residuo",
        money(max(float(total) - float(initial_payment), 0)),
    )

    if st.button("Salva spesa", use_container_width=True):
        if not description.strip():
            st.error("La descrizione è obbligatoria.")
            return
        if total <= 0:
            st.error("Il totale deve essere maggiore di zero.")
            return
        if abs(float(due_plan["importo_previsto"].sum()) - float(total)) > 0.01:
            st.error("La somma delle scadenze deve coincidere con il totale.")
            return
        if category_name == "— Nuova categoria —" and not (
            new_category_name and new_category_name.strip()
        ):
            st.error("Inserisci il nome della nuova categoria.")
            return

        uploaded_path = None
        try:
            if category_name == "— Nuova categoria —":
                category_result = crea_categoria_spesa(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "nome": new_category_name.strip(),
                        "descrizione": None,
                    },
                )
                category_id = category_result["categoria_id"]
            else:
                category_id = next(
                    category["id"]
                    for category in categories
                    if category["nome"] == category_name
                )

            if attachment is not None:
                uploaded_path = carica_documento_spesa(
                    db=db,
                    azienda_id=load_company()["id"],
                    fornitore_id=supplier["id"],
                    nome_file=attachment.name,
                    mime_type=(
                        attachment.type
                        or "application/octet-stream"
                    ),
                    contenuto=attachment.getvalue(),
                )

            crea_spesa_completa(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "fornitore_id": supplier["id"],
                    "categoria_spesa_id": category_id,
                    "data_spesa": expense_date.isoformat(),
                    "descrizione": description.strip(),
                    "imponibile": float(taxable),
                    "iva": float(vat),
                    "totale": float(total),
                    "numero_documento": document_number.strip() or None,
                    "tipo_documento": document_type,
                    "data_documento": document_date.isoformat(),
                    "competenza_mese": competence.replace(day=1).isoformat(),
                    "allegato_path": uploaded_path,
                    "note": notes.strip() or None,
                    "scadenze": [
                        {
                            "numero_scadenza": int(row["numero_scadenza"]),
                            "data_scadenza": row["data_scadenza"].isoformat(),
                            "importo_previsto": float(row["importo_previsto"]),
                        }
                        for _, row in due_plan.iterrows()
                    ],
                    "pagamento_iniziale": (
                        {
                            "data_pagamento": expense_date.isoformat(),
                            "importo": float(initial_payment),
                            "metodo_pagamento": payment_method,
                            "causale": "Pagamento iniziale spesa",
                        }
                        if initial_payment > 0
                        else None
                    ),
                },
            )
            clear_data_cache()
            st.success("Spesa, scadenze e pagamento iniziale salvati.")
            st.rerun()

        except Exception as exc:
            if uploaded_path:
                try:
                    elimina_documento_spesa(db, uploaded_path)
                except Exception:
                    pass
            st.error(f"Errore durante il salvataggio: {exc}")


def expenses_page() -> None:
    st.subheader("Spese")
    rows = load_expenses()

    if not rows:
        st.info("Nessuna spesa registrata.")
        return

    c1, c2 = st.columns(2)
    search = c1.text_input(
        "Cerca",
        placeholder="Descrizione, fornitore o documento",
        key="expense_search",
    )
    state_filter = c2.selectbox(
        "Stato pagamento",
        ["Tutti", "Da pagare", "Parzialmente pagata", "Pagata", "Scaduta"],
    )

    filtered = rows
    if search:
        lowered = search.lower()
        filtered = [
            row for row in filtered
            if lowered in " ".join(
                str(row.get(field) or "")
                for field in [
                    "descrizione",
                    "fornitore",
                    "numero_documento",
                    "categoria",
                ]
            ).lower()
        ]
    if state_filter != "Tutti":
        filtered = [
            row for row in filtered
            if row.get("stato_pagamento") == state_filter
        ]

    total = sum(float(row.get("totale") or 0) for row in filtered)
    paid = sum(float(row.get("pagato") or 0) for row in filtered)
    residual = sum(float(row.get("residuo") or 0) for row in filtered)

    m1, m2, m3 = st.columns(3)
    m1.metric("Totale spese", money(total))
    m2.metric("Pagato", money(paid))
    m3.metric("Debiti residui", money(residual))

    render_expense_cards(filtered)

    st.divider()
    st.subheader("Registra pagamento spesa")
    open_expenses = [
        row for row in rows
        if float(row.get("residuo") or 0) > 0
        and row.get("stato") != "annullata"
    ]
    if open_expenses:
        labels = {
            (
                f"{row.get('fornitore') or 'Fornitore'} · "
                f"{row['descrizione']} · residuo "
                f"{money(float(row.get('residuo') or 0))}"
            ): row
            for row in open_expenses
        }
        selected = labels[st.selectbox("Spesa", list(labels))]

        with st.form("expense_payment_form"):
            c3, c4 = st.columns(2)
            payment_amount = c3.number_input(
                "Importo pagamento",
                min_value=0.0,
                max_value=float(selected["residuo"]),
                step=10.0,
            )
            payment_date = c4.date_input(
                "Data pagamento",
                value=date.today(),
                format="DD/MM/YYYY",
            )
            method = st.selectbox(
                "Metodo",
                ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
            )
            reason = st.text_input(
                "Causale",
                value=f"Pagamento {selected['descrizione']}",
            )
            payment_notes = st.text_area("Note pagamento")
            submitted_payment = st.form_submit_button(
                "Registra pagamento",
                use_container_width=True,
            )

        if submitted_payment:
            if payment_amount <= 0:
                st.error("L'importo deve essere maggiore di zero.")
            else:
                try:
                    result = registra_pagamento_spesa(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "spesa_id": selected["spesa_id"],
                            "fornitore_id": selected.get("fornitore_id"),
                            "data_pagamento": payment_date.isoformat(),
                            "importo": float(payment_amount),
                            "metodo_pagamento": method,
                            "causale": reason.strip() or None,
                            "note": payment_notes.strip() or None,
                        },
                    )
                    clear_data_cache()
                    st.success(
                        "Pagamento registrato. Nuovo residuo: "
                        f"{money(float(result['nuovo_residuo']))}"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Errore durante il pagamento: {exc}")


def expense_deadlines_page() -> None:
    st.subheader("Scadenziario fornitori")
    rows = load_expense_deadlines()
    if not rows:
        st.info("Nessuna scadenza registrata.")
        return

    filter_value = st.selectbox(
        "Visualizza",
        ["Tutte", "Aperte", "Scadute", "Pagate"],
    )

    filtered = rows
    if filter_value == "Aperte":
        filtered = [
            row for row in rows
            if row.get("stato") in ["Da pagare", "Parzialmente pagata"]
        ]
    elif filter_value == "Scadute":
        filtered = [
            row for row in rows
            if "Scaduta" in (row.get("stato") or "")
        ]
    elif filter_value == "Pagate":
        filtered = [
            row for row in rows
            if row.get("stato") == "Pagata"
        ]

    render_expense_deadline_cards(filtered)

    st.divider()
    st.subheader("Storico pagamenti fornitori")
    payments = load_expense_payments()
    if payments:
        render_expense_payment_cards(payments)

        valid = [
            payment for payment in payments
            if payment.get("stato") == "valido"
        ]
        if valid:
            labels = {
                (
                    f"{format_date_it(payment['data_pagamento'])} · "
                    f"{payment.get('fornitore') or 'Fornitore'} · "
                    f"{money(float(payment['importo']))}"
                ): payment
                for payment in valid
            }
            selected = labels[st.selectbox(
                "Pagamento da annullare",
                list(labels),
            )]
            reason = st.text_area("Motivo annullamento pagamento")

            if st.button(
                "Annulla pagamento fornitore",
                use_container_width=True,
            ):
                if not reason.strip():
                    st.error("Il motivo è obbligatorio.")
                else:
                    try:
                        result = annulla_pagamento_spesa(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "pagamento_id": selected["pagamento_id"],
                                "motivo": reason.strip(),
                            },
                        )
                        clear_data_cache()
                        st.success(
                            "Pagamento annullato. Nuovo residuo: "
                            f"{money(float(result['nuovo_residuo']))}"
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore durante l'annullamento: {exc}")
    else:
        st.info("Nessun pagamento fornitore registrato.")


def page_accounting() -> None:
    header(
        "Contabilità",
        "Incassi, ricevute, fornitori, spese e scadenziario.",
    )

    actions = [
        "Nuovo incasso",
        "Elenco incassi",
        "Rate clienti",
        "Ricevute",
        "Fornitori",
        "Nuova spesa",
        "Spese",
        "Scadenziario fornitori",
    ]
    apply_pending_action(
        "accounting_action",
        actions,
        "Nuovo incasso",
    )

    action = st.selectbox(
        "Operazione",
        actions,
        key="accounting_action",
    )

    if action == "Nuovo incasso":
        new_receipt_page()
    elif action == "Elenco incassi":
        receipts_list_page()
    elif action == "Rate clienti":
        installments_page()
    elif action == "Ricevute":
        receipts_print_page()
    elif action == "Fornitori":
        suppliers_page()
    elif action == "Nuova spesa":
        new_expense_page()
    elif action == "Spese":
        expenses_page()
    else:
        expense_deadlines_page()


# ============================================================
# ALTRE PAGINE
# ============================================================


def company_page() -> None:
    header(
        "Azienda",
        "Configurazione dell'azienda attiva e dei documenti.",
    )

    company = load_company()
    tabs = st.tabs([
        "Dati generali",
        "Documenti",
        "Immagini",
        "Nuova azienda",
    ])

    with tabs[0]:
        with st.form("company_general_form"):
            c1, c2 = st.columns(2)
            nome_visualizzato = c1.text_input(
                "Nome commerciale *",
                value=company.get("nome_visualizzato") or "",
            )
            ragione_sociale = c2.text_input(
                "Ragione sociale *",
                value=company.get("ragione_sociale") or "",
            )

            c3, c4, c5 = st.columns(3)
            partita_iva = c3.text_input(
                "Partita IVA",
                value=company.get("partita_iva") or "",
            )
            codice_fiscale = c4.text_input(
                "Codice fiscale",
                value=company.get("codice_fiscale") or "",
            )
            forma_giuridica = c5.text_input(
                "Forma giuridica",
                value=company.get("forma_giuridica") or "",
            )

            indirizzo = st.text_input(
                "Indirizzo / sede legale",
                value=(
                    company.get("indirizzo")
                    or company.get("sede_legale")
                    or ""
                ),
            )

            c6, c7, c8 = st.columns(3)
            cap = c6.text_input("CAP", value=company.get("cap") or "")
            citta = c7.text_input(
                "Città",
                value=company.get("citta") or "",
            )
            provincia = c8.text_input(
                "Provincia",
                value=company.get("provincia") or "",
            )

            c9, c10, c11 = st.columns(3)
            telefono = c9.text_input(
                "Telefono",
                value=company.get("telefono") or "",
            )
            email = c10.text_input(
                "Email",
                value=company.get("email") or "",
            )
            pec = c11.text_input(
                "PEC",
                value=company.get("pec") or "",
            )

            c12, c13 = st.columns(2)
            codice_sdi = c12.text_input(
                "Codice SDI",
                value=company.get("codice_sdi") or "",
            )
            sito_web = c13.text_input(
                "Sito web",
                value=company.get("sito_web") or "",
            )

            submitted = st.form_submit_button(
                "Salva dati azienda",
                use_container_width=True,
            )

        if submitted:
            try:
                salva_azienda(
                    db,
                    {
                        "azienda_id": company["id"],
                        "nome_visualizzato": nome_visualizzato.strip(),
                        "ragione_sociale": ragione_sociale.strip(),
                        "partita_iva": partita_iva.strip() or None,
                        "codice_fiscale": codice_fiscale.strip() or None,
                        "forma_giuridica": forma_giuridica.strip() or None,
                        "indirizzo": indirizzo.strip() or None,
                        "cap": cap.strip() or None,
                        "citta": citta.strip() or None,
                        "provincia": provincia.strip() or None,
                        "telefono": telefono.strip() or None,
                        "email": email.strip() or None,
                        "pec": pec.strip() or None,
                        "codice_sdi": codice_sdi.strip() or None,
                        "sito_web": sito_web.strip() or None,
                        "attiva": True,
                    },
                )
                clear_data_cache()
                st.success("Dati azienda aggiornati.")
                st.rerun()
            except Exception as exc:
                st.error(f"Errore durante il salvataggio: {exc}")

    with tabs[1]:
        with st.form("company_documents_form"):
            intestazione = st.text_area(
                "Intestazione documenti",
                value=company.get("intestazione_documenti") or "",
                help="Testo opzionale mostrato nell'intestazione dei documenti.",
            )
            dicitura = st.text_input(
                "Dicitura ricevuta",
                value=(
                    company.get("dicitura_ricevuta")
                    or "Ricevuta non fiscale"
                ),
            )
            footer = st.text_area(
                "Piè di pagina documenti",
                value=company.get("footer_documenti") or "",
            )

            c1, c2 = st.columns(2)
            prefisso = c1.text_input(
                "Prefisso ricevute",
                value=company.get("prefisso_ricevute") or "",
                help="Es. KREO. La numerazione resta separata per azienda e anno.",
            )
            iban = c2.text_input(
                "IBAN",
                value=company.get("iban") or "",
            )
            banca = st.text_input(
                "Banca",
                value=company.get("banca") or "",
            )

            submitted_docs = st.form_submit_button(
                "Salva configurazione documenti",
                use_container_width=True,
            )

        if submitted_docs:
            try:
                salva_azienda(
                    db,
                    {
                        "azienda_id": company["id"],
                        "nome_visualizzato": company["nome_visualizzato"],
                        "ragione_sociale": company["ragione_sociale"],
                        "intestazione_documenti": intestazione.strip() or None,
                        "dicitura_ricevuta": dicitura.strip() or None,
                        "footer_documenti": footer.strip() or None,
                        "prefisso_ricevute": prefisso.strip() or None,
                        "iban": iban.strip() or None,
                        "banca": banca.strip() or None,
                        "attiva": company.get("attiva", True),
                    },
                )
                clear_data_cache()
                st.success("Configurazione documenti aggiornata.")
                st.rerun()
            except Exception as exc:
                st.error(f"Errore durante il salvataggio: {exc}")

    with tabs[2]:
        st.subheader("Logo, firma e timbro")

        for asset_type, label, current_path in [
            ("logo", "Logo aziendale", company.get("logo_path")),
            ("firma", "Firma", company.get("firma_path")),
            ("timbro", "Timbro", company.get("timbro_path")),
        ]:
            with st.container(border=True):
                st.write(f"**{label}**")

                if current_path:
                    try:
                        asset_url = crea_url_asset_azienda(
                            db,
                            current_path,
                            expires_in=300,
                        )
                        st.link_button(
                            "Apri file attuale",
                            asset_url,
                            use_container_width=True,
                        )
                    except Exception as exc:
                        st.caption(f"File non apribile: {exc}")
                else:
                    st.caption("Nessun file caricato.")

                uploaded = st.file_uploader(
                    f"Carica {label.lower()}",
                    type=["png", "jpg", "jpeg"],
                    key=f"company_asset_{asset_type}",
                )

                if st.button(
                    f"Salva {label.lower()}",
                    key=f"save_asset_{asset_type}",
                    use_container_width=True,
                ):
                    if uploaded is None:
                        st.error("Devi selezionare un file.")
                    else:
                        new_path = None
                        try:
                            new_path = carica_asset_azienda(
                                db=db,
                                azienda_id=company["id"],
                                asset_type=asset_type,
                                nome_file=uploaded.name,
                                mime_type=(
                                    uploaded.type
                                    or "application/octet-stream"
                                ),
                                contenuto=uploaded.getvalue(),
                            )
                            salva_asset_azienda(
                                db,
                                {
                                    "azienda_id": company["id"],
                                    "tipo_asset": asset_type,
                                    "file_path": new_path,
                                },
                            )

                            if current_path:
                                try:
                                    elimina_asset_azienda(
                                        db,
                                        current_path,
                                    )
                                except Exception:
                                    pass

                            clear_data_cache()
                            st.success(f"{label} aggiornato.")
                            st.rerun()

                        except Exception as exc:
                            if new_path:
                                try:
                                    elimina_asset_azienda(db, new_path)
                                except Exception:
                                    pass
                            st.error(f"Errore durante il caricamento: {exc}")

    with tabs[3]:
        st.info(
            "Le nuove aziende sono immediatamente separate tramite azienda_id. "
            "Come Super Admin potrai selezionarle dal menu laterale."
        )

        with st.form("new_company_form"):
            new_name = st.text_input("Nome commerciale *")
            new_legal_name = st.text_input("Ragione sociale *")
            new_vat = st.text_input("Partita IVA")
            new_prefix = st.text_input("Prefisso ricevute")

            submitted_new = st.form_submit_button(
                "Crea nuova azienda",
                use_container_width=True,
            )

        if submitted_new:
            if not new_name.strip() or not new_legal_name.strip():
                st.error("Nome commerciale e ragione sociale sono obbligatori.")
            else:
                try:
                    result = salva_azienda(
                        db,
                        {
                            "azienda_id": None,
                            "nome_visualizzato": new_name.strip(),
                            "ragione_sociale": new_legal_name.strip(),
                            "partita_iva": new_vat.strip() or None,
                            "prefisso_ricevute": new_prefix.strip() or None,
                            "dicitura_ricevuta": "Ricevuta non fiscale",
                            "attiva": True,
                        },
                    )
                    clear_data_cache()
                    st.session_state.active_company_id = result["azienda_id"]
                    st.session_state.selected_customer_id = None
                    st.success("Nuova azienda creata e selezionata.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Errore durante la creazione: {exc}")


def placeholder_page(title: str) -> None:
    header(title, "Sezione prevista nella struttura.")
    st.info("Questa sezione entrerà nel blocco funzionale dedicato.")


PAGES = {
    "Reception": page_reception,
    "Pacchetti": page_packages,
    "Abbonamenti": lambda: placeholder_page("Abbonamenti"),
    "Clienti": page_customers,
    "Contabilità": page_accounting,
    "Admin": lambda: placeholder_page("Admin"),
    "Azienda": company_page,
}


def main() -> None:
    selected = sidebar()
    PAGES[selected]()
    st.markdown(f'<div class="footer">{DEVELOPER_CREDIT}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
