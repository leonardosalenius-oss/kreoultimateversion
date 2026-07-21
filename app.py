from __future__ import annotations

from datetime import date, datetime, time, timedelta
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
    cambia_stato_abbonamento,
    crea_abbonamento_cliente,
    elenco_abbonamenti_operativo,
    elimina_cliente_definitivamente,
    get_abbonamento_dettaglio,
    rinnova_abbonamento_cliente,
    annulla_prenotazione,
    cambia_stato_prenotazione,
    crea_operatore_agenda,
    crea_prenotazione,
    elenco_operatori_agenda,
    elenco_prenotazioni,
    modifica_prenotazione,
    elenco_movimenti_lezioni,
    registra_movimento_lezioni,
    associa_badge_cliente,
    cambia_stato_badge,
    crea_dispositivo_accesso,
    elenco_accessi,
    elenco_badge,
    elenco_dispositivi_accesso,
    gestisci_accesso_manuale,
    rigenera_token_dispositivo,
)
from receipts import build_receipt_pdf


APP_VERSION = "0.20.0"
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
        "selected_subscription_id": None,
        "selected_booking_id": None,
        "pending_reception_action": None,
        "pending_subscription_action": None,
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


@st.cache_data(ttl=10)
def load_subscriptions() -> list[dict[str, Any]]:
    return elenco_abbonamenti_operativo(
        db,
        load_company()["id"],
    )


@st.cache_data(ttl=10)
def load_agenda_operators() -> list[dict[str, Any]]:
    return elenco_operatori_agenda(
        db,
        load_company()["id"],
    )


@st.cache_data(ttl=10)
def load_bookings(
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    return elenco_prenotazioni(
        db,
        load_company()["id"],
        start_date,
        end_date,
    )


@st.cache_data(ttl=10)
def load_lesson_movements(
    subscription_id: str | None = None,
) -> list[dict[str, Any]]:
    return elenco_movimenti_lezioni(
        db,
        load_company()["id"],
        subscription_id,
    )


@st.cache_data(ttl=10)
def load_badges() -> list[dict[str, Any]]:
    return elenco_badge(
        db,
        load_company()["id"],
    )


@st.cache_data(ttl=10)
def load_access_devices() -> list[dict[str, Any]]:
    return elenco_dispositivi_accesso(
        db,
        load_company()["id"],
    )


@st.cache_data(ttl=10)
def load_access_log(
    days_back: int = 30,
) -> list[dict[str, Any]]:
    start_date = date.today() - timedelta(days=days_back)
    return elenco_accessi(
        db,
        load_company()["id"],
        start_date.isoformat(),
        date.today().isoformat(),
    )


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
    load_subscriptions.clear()
    load_agenda_operators.clear()
    load_bookings.clear()
    load_lesson_movements.clear()
    load_badges.clear()
    load_access_devices.clear()
    load_access_log.clear()



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






def render_subscription_cards(
    rows: list[dict[str, Any]],
    *,
    show_actions: bool = True,
) -> None:
    for subscription in rows:
        with st.container(border=True):
            top_left, top_right = st.columns([4, 1.2])

            with top_left:
                st.subheader(subscription.get("cliente") or "Cliente")
                st.caption(
                    f"{subscription.get('pacchetto') or 'Pacchetto'} · "
                    f"{subscription.get('tipologia_pagamento') or '—'}"
                )

            with top_right:
                state = subscription.get("stato_visuale") or subscription.get("stato") or "—"
                st.write(f"**{status_icon(state)} {state}**")

            c1, c2, c3, c4, c5 = st.columns([1.25, 1.25, 1.15, 1.15, 1.2])
            with c1:
                st.caption("PERIODO")
                st.write(
                    f"**{format_date_it(subscription.get('data_inizio'))}**"
                )
                st.caption(
                    f"fino al {format_date_it(subscription.get('data_fine_prevista'))}"
                )
            with c2:
                st.caption("VALORE")
                st.write(
                    f"**{money(float(subscription.get('prezzo_concordato') or 0))}**"
                )
            with c3:
                st.caption("PAGATO")
                st.write(
                    f"**{money(float(subscription.get('pagato') or 0))}**"
                )
            with c4:
                st.caption("RESIDUO")
                st.write(
                    f"**{money(float(subscription.get('residuo') or 0))}**"
                )
            with c5:
                st.caption("PROSSIMA RATA")
                st.write(
                    f"**{format_date_it(subscription.get('prossima_rata_data'))}**"
                )
                st.caption(
                    money(float(subscription.get("prossima_rata_importo") or 0))
                )

            if subscription.get("motivo_stato"):
                st.caption(
                    f"Motivo stato: {subscription['motivo_stato']}"
                )

            if show_actions:
                a1, a2, a3 = st.columns(3)
                with a1:
                    if st.button(
                        "Gestisci",
                        key=f"manage_sub_{subscription['abbonamento_id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_subscription_id = (
                            subscription["abbonamento_id"]
                        )
                        st.session_state.pending_subscription_action = "Gestisci"
                        st.rerun()

                with a2:
                    if st.button(
                        "Rinnova",
                        key=f"renew_sub_{subscription['abbonamento_id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_subscription_id = (
                            subscription["abbonamento_id"]
                        )
                        st.session_state.pending_subscription_action = "Rinnova"
                        st.rerun()

                with a3:
                    if st.button(
                        "Apri cliente",
                        key=f"open_client_sub_{subscription['abbonamento_id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_customer_id = (
                            subscription["cliente_id"]
                        )
                        goto("Clienti", "Scheda cliente")


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



def format_time_it(value: Any) -> str:
    if value is None:
        return "—"

    text = str(value)
    if len(text) >= 5:
        return text[:5]
    return text


def booking_status_label(status: str | None) -> str:
    labels = {
        "prenotata": "Prenotata",
        "confermata": "Confermata",
        "presente": "Presente",
        "assente": "Assente",
        "annullata": "Annullata",
    }
    return labels.get(status or "", status or "—")


def booking_status_icon(status: str | None) -> str:
    icons = {
        "prenotata": "🟡",
        "confermata": "🔵",
        "presente": "🟢",
        "assente": "🟠",
        "annullata": "⚫",
    }
    return icons.get(status or "", "⚪")


def week_bounds(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def active_subscription_options() -> dict[str, dict[str, Any]]:
    subscriptions = [
        row for row in load_subscriptions()
        if row.get("stato") not in (
            "terminato",
            "chiuso_anticipatamente",
            "annullato",
        )
        and row.get("stato_visuale") not in ("Scaduto",)
    ]

    return {
        (
            f"{row['cliente']} · {row['pacchetto']} · "
            f"fino al {format_date_it(row['data_fine_prevista'])}"
        ): row
        for row in subscriptions
    }


def booking_card(
    booking: dict[str, Any],
    *,
    key_prefix: str,
    compact: bool = False,
) -> None:
    with st.container(border=True):
        left, right = st.columns([3.4, 1.1])

        with left:
            st.write(
                f"**{format_time_it(booking.get('ora_inizio'))}–"
                f"{format_time_it(booking.get('ora_fine'))} · "
                f"{booking.get('cliente') or 'Cliente'}**"
            )
            st.caption(
                f"{booking.get('pacchetto') or 'Nessun abbonamento'} · "
                f"{booking.get('operatore') or 'Operatore non assegnato'}"
            )
            if booking.get("saldo_lezioni") is not None:
                st.caption(
                    f"Lezioni disponibili: "
                    f"{int(booking.get('saldo_lezioni') or 0)}"
                )

        with right:
            status = booking.get("stato")
            st.write(
                f"**{booking_status_icon(status)} "
                f"{booking_status_label(status)}**"
            )

        if not compact:
            if booking.get("tipologia"):
                st.caption(f"Tipologia: {booking['tipologia']}")
            if booking.get("note"):
                st.caption(booking["note"])

            if booking.get("stato") != "annullata":
                cols = st.columns(4)

                with cols[0]:
                    if st.button(
                        "Conferma",
                        key=f"{key_prefix}_confirm_{booking['prenotazione_id']}",
                        use_container_width=True,
                        disabled=booking.get("stato") in (
                            "confermata",
                            "presente",
                        ),
                    ):
                        try:
                            cambia_stato_prenotazione(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "prenotazione_id": booking["prenotazione_id"],
                                    "stato": "confermata",
                                    "motivo": "Conferma da Reception",
                                },
                            )
                            clear_data_cache()
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Errore: {exc}")

                with cols[1]:
                    if st.button(
                        "Presente",
                        key=f"{key_prefix}_present_{booking['prenotazione_id']}",
                        use_container_width=True,
                        disabled=booking.get("stato") == "presente",
                    ):
                        try:
                            cambia_stato_prenotazione(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "prenotazione_id": booking["prenotazione_id"],
                                    "stato": "presente",
                                    "motivo": "Presenza confermata da Reception",
                                },
                            )
                            clear_data_cache()
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Errore: {exc}")

                with cols[2]:
                    if st.button(
                        "Assente",
                        key=f"{key_prefix}_absent_{booking['prenotazione_id']}",
                        use_container_width=True,
                        disabled=booking.get("stato") == "assente",
                    ):
                        try:
                            cambia_stato_prenotazione(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "prenotazione_id": booking["prenotazione_id"],
                                    "stato": "assente",
                                    "motivo": "Assenza registrata da Reception",
                                },
                            )
                            clear_data_cache()
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Errore: {exc}")

                with cols[3]:
                    if st.button(
                        "Gestisci",
                        key=f"{key_prefix}_manage_{booking['prenotazione_id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_booking_id = (
                            booking["prenotazione_id"]
                        )
                        st.session_state.pending_reception_action = (
                            "Modifica prenotazione"
                        )
                        st.rerun()


def build_reception_alerts() -> dict[str, list[dict[str, Any]]]:
    clients = load_clients()
    installments = load_installments()
    subscriptions = load_subscriptions()

    overdue_rates = [
        row for row in installments
        if float(row.get("residuo_rata") or 0) > 0
        and "scadut" in str(row.get("stato") or "").lower()
    ]

    expiring_rates = [
        row for row in installments
        if float(row.get("residuo_rata") or 0) > 0
        and "scadut" not in str(row.get("stato") or "").lower()
        and row.get("data_scadenza")
        and date.fromisoformat(str(row["data_scadenza"])) <= (
            date.today() + timedelta(days=7)
        )
    ]

    expired_certificates = [
        row for row in clients
        if "scadut" in str(row.get("certificato_stato") or "").lower()
        or "mancant" in str(row.get("certificato_stato") or "").lower()
    ]

    expiring_certificates = [
        row for row in clients
        if "scaden" in str(row.get("certificato_stato") or "").lower()
        and "scadut" not in str(row.get("certificato_stato") or "").lower()
    ]

    expired_subscriptions = [
        row for row in subscriptions
        if row.get("stato_visuale") == "Scaduto"
    ]

    expiring_subscriptions = [
        row for row in subscriptions
        if row.get("stato_visuale") == "In scadenza"
    ]

    return {
        "rate_scadute": overdue_rates,
        "rate_in_scadenza": expiring_rates,
        "certificati_scaduti": expired_certificates,
        "certificati_in_scadenza": expiring_certificates,
        "abbonamenti_scaduti": expired_subscriptions,
        "abbonamenti_in_scadenza": expiring_subscriptions,
    }


def render_reception_alerts() -> None:
    alerts = build_reception_alerts()

    groups = [
        (
            "Rate scadute",
            alerts["rate_scadute"],
            "🔴",
            "Contabilità",
            "Rate clienti",
        ),
        (
            "Certificati scaduti o mancanti",
            alerts["certificati_scaduti"],
            "🔴",
            "Clienti",
            "Elenco clienti",
        ),
        (
            "Abbonamenti scaduti",
            alerts["abbonamenti_scaduti"],
            "🔴",
            "Abbonamenti",
            "Elenco",
        ),
        (
            "Rate nei prossimi 7 giorni",
            alerts["rate_in_scadenza"],
            "🟡",
            "Contabilità",
            "Rate clienti",
        ),
        (
            "Certificati in scadenza",
            alerts["certificati_in_scadenza"],
            "🟡",
            "Clienti",
            "Elenco clienti",
        ),
        (
            "Abbonamenti in scadenza",
            alerts["abbonamenti_in_scadenza"],
            "🟡",
            "Abbonamenti",
            "Elenco",
        ),
    ]

    total_alerts = sum(len(rows) for _, rows, _, _, _ in groups)

    st.subheader("Alert operativi")
    if total_alerts == 0:
        st.success("Nessun alert operativo.")
        return

    cols = st.columns(3)
    for index, (title, rows, icon, page, action) in enumerate(groups):
        with cols[index % 3]:
            with st.container(border=True):
                st.markdown(f"### {icon} {len(rows)}")
                st.write(f"**{title}**")

                for row in rows[:3]:
                    name = (
                        row.get("cliente")
                        or " ".join(
                            part for part in [
                                row.get("cognome"),
                                row.get("nome"),
                            ]
                            if part
                        )
                        or "Cliente"
                    )
                    detail = ""
                    if row.get("data_scadenza"):
                        detail = format_date_it(row["data_scadenza"])
                    elif row.get("data_fine_prevista"):
                        detail = format_date_it(row["data_fine_prevista"])
                    elif row.get("certificato_stato"):
                        detail = str(row["certificato_stato"])

                    st.caption(
                        f"{name}"
                        + (f" · {detail}" if detail else "")
                    )

                if len(rows) > 3:
                    st.caption(f"+ altri {len(rows) - 3}")

                if st.button(
                    "Apri dettaglio",
                    key=f"alert_open_{index}_{title}",
                    use_container_width=True,
                ):
                    goto(page, action)



def access_result_icon(esito: str | None) -> str:
    mapping = {
        "consentito": "🟢",
        "consentito_manuale": "🟢",
        "negato": "🔴",
        "errore": "⚠️",
    }
    return mapping.get(esito or "", "⚪")


def render_access_log(rows: list[dict[str, Any]]) -> None:
    for access in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns(
                [1.25, 2.1, 1.2, 1.5, 2.3]
            )
            with c1:
                st.caption("DATA / ORA")
                st.write(
                    f"**{format_date_it(access.get('data_accesso'))}**"
                )
                st.caption(
                    format_time_it(access.get("ora_accesso"))
                )
            with c2:
                st.caption("CLIENTE")
                st.write(
                    f"**{access.get('cliente') or 'Non riconosciuto'}**"
                )
                if access.get("codice_badge"):
                    st.caption(
                        f"Badge {access['codice_badge']}"
                    )
            with c3:
                st.caption("ESITO")
                st.write(
                    f"**{access_result_icon(access.get('esito'))} "
                    f"{access.get('esito') or '—'}**"
                )
            with c4:
                st.caption("DISPOSITIVO")
                st.write(
                    f"**{access.get('dispositivo') or 'Manuale'}**"
                )
            with c5:
                st.caption("MOTIVO")
                st.write(
                    access.get("messaggio")
                    or access.get("motivazione")
                    or "—"
                )
                if access.get("movimento_lezione_id"):
                    st.caption("Lezione scalata")


def daily_agenda(selected_day: date) -> None:
    rows = load_bookings(
        selected_day.isoformat(),
        selected_day.isoformat(),
    )

    active_rows = [
        row for row in rows
        if row.get("stato") != "annullata"
    ]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prenotazioni", len(active_rows))
    m2.metric(
        "Confermate",
        sum(1 for row in active_rows if row.get("stato") == "confermata"),
    )
    m3.metric(
        "Presenti",
        sum(1 for row in active_rows if row.get("stato") == "presente"),
    )
    m4.metric(
        "Assenti",
        sum(1 for row in active_rows if row.get("stato") == "assente"),
    )

    if not rows:
        st.info("Nessuna prenotazione per questa giornata.")
        return

    for booking in rows:
        booking_card(
            booking,
            key_prefix=f"daily_{selected_day.isoformat()}",
        )


def weekly_agenda(selected_day: date) -> None:
    week_start, week_end = week_bounds(selected_day)
    rows = load_bookings(
        week_start.isoformat(),
        week_end.isoformat(),
    )

    by_day: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_day.setdefault(str(row["data_prenotazione"]), []).append(row)

    day_names = [
        "Lunedì",
        "Martedì",
        "Mercoledì",
        "Giovedì",
        "Venerdì",
        "Sabato",
        "Domenica",
    ]

    first_cols = st.columns(4)
    second_cols = st.columns(3)
    all_cols = first_cols + second_cols

    for offset, col in enumerate(all_cols):
        current_day = week_start + timedelta(days=offset)
        with col:
            st.markdown(
                f"### {day_names[offset]}"
            )
            st.caption(current_day.strftime("%d/%m/%Y"))

            day_rows = by_day.get(current_day.isoformat(), [])
            if not day_rows:
                st.caption("Nessuna prenotazione")
            else:
                for booking in day_rows:
                    booking_card(
                        booking,
                        key_prefix=f"weekly_{current_day.isoformat()}",
                        compact=True,
                    )


# ============================================================
# RECEPTION
# ============================================================


def page_reception() -> None:
    header(
        "Reception",
        "Agenda giornaliera e settimanale, prenotazioni e operatori.",
    )

    actions = [
        "Dashboard oggi",
        "Agenda giornaliera",
        "Agenda settimanale",
        "Nuova prenotazione",
        "Modifica prenotazione",
        "Lezioni e presenze",
        "Tornello e accessi",
        "Badge clienti",
        "Dispositivi accesso",
        "Operatori agenda",
        "Azioni rapide",
    ]

    pending = st.session_state.get("pending_reception_action")
    if pending in actions:
        st.session_state.reception_action = pending
        st.session_state.pending_reception_action = None
    elif "reception_action" not in st.session_state:
        st.session_state.reception_action = "Dashboard oggi"

    action = st.selectbox(
        "Operazione",
        actions,
        key="reception_action",
    )

    if action == "Dashboard oggi":
        today = date.today()
        rows = load_bookings(
            today.isoformat(),
            today.isoformat(),
        )
        active_rows = [
            row for row in rows
            if row.get("stato") != "annullata"
        ]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Prenotazioni oggi", len(active_rows))
        m2.metric(
            "Da confermare",
            sum(
                1 for row in active_rows
                if row.get("stato") == "prenotata"
            ),
        )
        m3.metric(
            "Presenti",
            sum(
                1 for row in active_rows
                if row.get("stato") == "presente"
            ),
        )
        m4.metric(
            "Assenti",
            sum(
                1 for row in active_rows
                if row.get("stato") == "assente"
            ),
        )

        render_reception_alerts()
        st.divider()

        left, right = st.columns([2.2, 1])

        with left:
            st.subheader("Agenda di oggi")
            if rows:
                for booking in rows:
                    booking_card(
                        booking,
                        key_prefix="dashboard",
                    )
            else:
                st.info("Nessuna prenotazione per oggi.")

        with right:
            st.subheader("Azioni rapide")

            dashboard_actions = [
                ("Nuovo cliente", "goto", ("Clienti", "Nuovo cliente")),
                ("Modifica cliente", "goto", ("Clienti", "Modifica cliente")),
                ("Registra incasso", "goto", ("Contabilità", "Nuovo incasso")),
                ("Accesso tornello", "reception", "Tornello e accessi"),
                ("Agenda / Calendario", "reception", "Agenda settimanale"),
                ("Stampa ricevuta", "goto", ("Contabilità", "Ricevute")),
                ("Messaggio cliente", "future", None),
                ("Associa badge", "reception", "Badge clienti"),
                ("Sincronizza badge", "reception", "Dispositivi accesso"),
                ("Ricalcolo settimanale", "future", None),
                ("Aggiungi prenotazione", "reception", "Nuova prenotazione"),
                ("Conferma presenza", "reception", "Agenda giornaliera"),
                ("Carica documento", "goto", ("Clienti", "Modifica cliente")),
                ("Accesso manuale", "reception", "Tornello e accessi"),
                ("Storico cliente", "goto", ("Clienti", "Modifica cliente")),
                ("Situazione cliente", "goto", ("Clienti", "Elenco clienti")),
            ]

            for label, action_type, target in dashboard_actions:
                if st.button(
                    label,
                    key=f"dashboard_action_{label}",
                    use_container_width=True,
                ):
                    if action_type == "goto":
                        page_name, target_action = target
                        goto(page_name, target_action)
                    elif action_type == "reception":
                        st.session_state.pending_reception_action = target
                        st.rerun()
                    else:
                        st.info(
                            f"'{label}' sarà attivato nel relativo "
                            "blocco funzionale, senza rimuovere il pulsante "
                            "dalla Reception."
                        )

    elif action == "Agenda giornaliera":
        selected_day = st.date_input(
            "Giorno",
            value=date.today(),
            format="DD/MM/YYYY",
            key="daily_agenda_date",
        )
        daily_agenda(selected_day)

    elif action == "Agenda settimanale":
        selected_day = st.date_input(
            "Settimana contenente il giorno",
            value=date.today(),
            format="DD/MM/YYYY",
            key="weekly_agenda_date",
        )
        week_start, week_end = week_bounds(selected_day)
        st.caption(
            f"Settimana {week_start.strftime('%d/%m/%Y')} – "
            f"{week_end.strftime('%d/%m/%Y')}"
        )
        weekly_agenda(selected_day)

    elif action == "Nuova prenotazione":
        subscriptions = active_subscription_options()
        operators = [
            row for row in load_agenda_operators()
            if row.get("attivo")
        ]

        if not subscriptions:
            st.warning(
                "Non risultano abbonamenti attivi o da attivare."
            )
            return

        if not operators:
            st.warning(
                "Prima registra almeno un operatore agenda."
            )
            return

        subscription_label = st.selectbox(
            "Cliente e abbonamento *",
            list(subscriptions),
        )
        subscription = subscriptions[subscription_label]

        operator_map = {
            row["nome_visualizzato"]: row
            for row in operators
        }
        operator_label = st.selectbox(
            "Operatore *",
            list(operator_map),
        )
        operator = operator_map[operator_label]

        c1, c2, c3 = st.columns(3)
        booking_date = c1.date_input(
            "Data",
            value=date.today(),
            format="DD/MM/YYYY",
        )
        start_time = c2.time_input(
            "Ora inizio",
            value=time(9, 0),
            step=900,
        )
        duration = c3.number_input(
            "Durata in minuti",
            min_value=15,
            max_value=240,
            step=15,
            value=60,
        )

        end_datetime = (
            datetime.combine(booking_date, start_time)
            + timedelta(minutes=int(duration))
        )
        end_time = end_datetime.time()

        c4, c5 = st.columns(2)
        booking_type = c4.selectbox(
            "Tipologia",
            [
                "Lezione ordinaria",
                "Recupero",
                "Lezione extra",
                "Valutazione",
                "Altro",
            ],
        )
        initial_status = c5.selectbox(
            "Stato iniziale",
            ["prenotata", "confermata"],
            format_func=booking_status_label,
        )

        notes = st.text_area("Note")

        if st.button(
            "Salva prenotazione",
            use_container_width=True,
        ):
            try:
                crea_prenotazione(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "cliente_id": subscription["cliente_id"],
                        "abbonamento_id": (
                            subscription["abbonamento_id"]
                        ),
                        "operatore_id": operator["id"],
                        "data_prenotazione": booking_date.isoformat(),
                        "ora_inizio": start_time.strftime("%H:%M:%S"),
                        "ora_fine": end_time.strftime("%H:%M:%S"),
                        "tipologia": booking_type,
                        "stato": initial_status,
                        "note": notes.strip() or None,
                    },
                )
                clear_data_cache()
                st.success("Prenotazione salvata.")
                st.session_state.pending_reception_action = (
                    "Agenda giornaliera"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Errore durante il salvataggio: {exc}")

    elif action == "Modifica prenotazione":
        today = date.today()
        range_start = today - timedelta(days=30)
        range_end = today + timedelta(days=90)
        rows = load_bookings(
            range_start.isoformat(),
            range_end.isoformat(),
        )

        if not rows:
            st.info("Nessuna prenotazione disponibile.")
            return

        labels = {
            (
                f"{format_date_it(row['data_prenotazione'])} · "
                f"{format_time_it(row['ora_inizio'])} · "
                f"{row['cliente']} · "
                f"{booking_status_label(row['stato'])}"
            ): row
            for row in rows
        }

        selected_id = st.session_state.get("selected_booking_id")
        default_label = next(
            (
                label
                for label, row in labels.items()
                if row["prenotazione_id"] == selected_id
            ),
            list(labels)[0],
        )

        selected_label = st.selectbox(
            "Prenotazione",
            list(labels),
            index=list(labels).index(default_label),
        )
        booking = labels[selected_label]
        st.session_state.selected_booking_id = (
            booking["prenotazione_id"]
        )

        operators = load_agenda_operators()
        operator_map = {
            row["nome_visualizzato"]: row
            for row in operators
        }
        operator_names = list(operator_map)
        current_operator_index = next(
            (
                index
                for index, name in enumerate(operator_names)
                if operator_map[name]["id"] == booking.get("operatore_id")
            ),
            0,
        )

        with st.form("edit_booking_form"):
            c1, c2, c3 = st.columns(3)
            booking_date = c1.date_input(
                "Data",
                value=date.fromisoformat(
                    str(booking["data_prenotazione"])
                ),
                format="DD/MM/YYYY",
            )
            start_time = c2.time_input(
                "Ora inizio",
                value=time.fromisoformat(
                    str(booking["ora_inizio"])[:8]
                ),
                step=900,
            )
            end_time = c3.time_input(
                "Ora fine",
                value=time.fromisoformat(
                    str(booking["ora_fine"])[:8]
                ),
                step=900,
            )

            operator_name = st.selectbox(
                "Operatore",
                operator_names,
                index=current_operator_index,
            )
            booking_type = st.selectbox(
                "Tipologia",
                [
                    "Lezione ordinaria",
                    "Recupero",
                    "Lezione extra",
                    "Valutazione",
                    "Altro",
                ],
                index=(
                    [
                        "Lezione ordinaria",
                        "Recupero",
                        "Lezione extra",
                        "Valutazione",
                        "Altro",
                    ].index(booking.get("tipologia"))
                    if booking.get("tipologia") in [
                        "Lezione ordinaria",
                        "Recupero",
                        "Lezione extra",
                        "Valutazione",
                        "Altro",
                    ]
                    else 0
                ),
            )
            notes = st.text_area(
                "Note",
                value=booking.get("note") or "",
            )
            submitted = st.form_submit_button(
                "Salva modifiche",
                use_container_width=True,
            )

        if submitted:
            try:
                modifica_prenotazione(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "prenotazione_id": booking["prenotazione_id"],
                        "operatore_id": operator_map[operator_name]["id"],
                        "data_prenotazione": booking_date.isoformat(),
                        "ora_inizio": start_time.strftime("%H:%M:%S"),
                        "ora_fine": end_time.strftime("%H:%M:%S"),
                        "tipologia": booking_type,
                        "note": notes.strip() or None,
                    },
                )
                clear_data_cache()
                st.success("Prenotazione aggiornata.")
                st.rerun()
            except Exception as exc:
                st.error(f"Errore durante la modifica: {exc}")

        if booking.get("stato") != "annullata":
            st.divider()
            st.subheader("Annulla prenotazione")
            cancellation_reason = st.text_area(
                "Motivo annullamento *",
                key="booking_cancel_reason",
            )

            if st.button(
                "Annulla prenotazione",
                use_container_width=True,
            ):
                if not cancellation_reason.strip():
                    st.error("Il motivo è obbligatorio.")
                else:
                    try:
                        annulla_prenotazione(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "prenotazione_id": (
                                    booking["prenotazione_id"]
                                ),
                                "motivo": cancellation_reason.strip(),
                            },
                        )
                        clear_data_cache()
                        st.success("Prenotazione annullata.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore: {exc}")


    elif action == "Lezioni e presenze":
        st.subheader("Saldi e movimenti lezioni")

        subscriptions = active_subscription_options()
        if not subscriptions:
            st.info("Nessun abbonamento operativo disponibile.")
            return

        selected_label = st.selectbox(
            "Cliente e abbonamento",
            list(subscriptions),
            key="lesson_movement_subscription",
        )
        subscription = subscriptions[selected_label]

        detail = get_abbonamento_dettaglio(
            db,
            subscription["abbonamento_id"],
        )
        current = detail["abbonamento"]
        movements = detail.get("movimenti_lezioni") or []

        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Lezioni iniziali",
            int(current.get("lezioni_iniziali") or 0),
        )
        m2.metric(
            "Movimenti netti",
            int(current.get("movimenti_lezioni_netto") or 0),
        )
        m3.metric(
            "Lezioni disponibili",
            int(current.get("saldo_lezioni") or 0),
        )

        st.caption(
            "Le presenze ordinarie e i recuperi scalano automaticamente "
            "una lezione. Le valutazioni non modificano il saldo."
        )

        tabs = st.tabs([
            "Storico movimenti",
            "Correzione manuale",
        ])

        with tabs[0]:
            if movements:
                for movement in movements:
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns(
                            [1.2, 1.5, 1.2, 2.4]
                        )
                        with c1:
                            st.caption("DATA")
                            st.write(
                                f"**{format_date_it(movement.get('data_movimento'))}**"
                            )
                        with c2:
                            st.caption("TIPO")
                            st.write(
                                f"**{movement.get('tipo') or '—'}**"
                            )
                        with c3:
                            quantity = int(
                                movement.get("quantita") or 0
                            )
                            st.caption("MOVIMENTO")
                            st.write(
                                f"**{quantity:+d}**"
                            )
                        with c4:
                            st.caption("CAUSALE")
                            st.write(
                                movement.get("causale")
                                or movement.get("tipologia_prenotazione")
                                or "—"
                            )
                            if movement.get("ora_inizio"):
                                st.caption(
                                    f"Prenotazione "
                                    f"{format_time_it(movement['ora_inizio'])}"
                                )
            else:
                st.info("Nessun movimento lezione registrato.")

        with tabs[1]:
            st.warning(
                "La correzione manuale non modifica i record precedenti: "
                "crea un nuovo movimento tracciato."
            )

            movement_type = st.selectbox(
                "Tipo movimento",
                [
                    "Carico amministrativo",
                    "Scarico amministrativo",
                    "Omaggio",
                    "Recupero credito",
                    "Correzione",
                ],
                key="manual_lesson_type",
            )

            c1, c2 = st.columns(2)
            quantity_abs = c1.number_input(
                "Numero lezioni",
                min_value=1,
                step=1,
                value=1,
                key="manual_lesson_quantity",
            )
            movement_date = c2.date_input(
                "Data movimento",
                value=date.today(),
                format="DD/MM/YYYY",
                key="manual_lesson_date",
            )

            negative_types = {
                "Scarico amministrativo",
            }
            signed_quantity = (
                -int(quantity_abs)
                if movement_type in negative_types
                else int(quantity_abs)
            )

            reason = st.text_area(
                "Motivazione obbligatoria",
                key="manual_lesson_reason",
            )

            if st.button(
                "Registra movimento lezioni",
                use_container_width=True,
            ):
                if not reason.strip():
                    st.error("La motivazione è obbligatoria.")
                elif (
                    signed_quantity < 0
                    and abs(signed_quantity)
                    > int(current.get("saldo_lezioni") or 0)
                ):
                    st.error(
                        "Lo scarico supera le lezioni disponibili."
                    )
                else:
                    try:
                        registra_movimento_lezioni(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "cliente_id": subscription["cliente_id"],
                                "abbonamento_id": (
                                    subscription["abbonamento_id"]
                                ),
                                "data_movimento": (
                                    movement_date.isoformat()
                                ),
                                "tipo": movement_type,
                                "quantita": signed_quantity,
                                "causale": reason.strip(),
                            },
                        )
                        clear_data_cache()
                        st.success("Movimento lezioni registrato.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore: {exc}")


    elif action == "Tornello e accessi":
        st.subheader("Accesso manuale")

        clients = [
            row for row in load_clients()
            if (
                row.get("stato_cliente")
                or row.get("stato")
                or "attivo"
            ) == "attivo"
        ]

        if not clients:
            st.info("Nessun cliente attivo.")
        else:
            client_map = {
                f"{row['cognome']} {row['nome']}": row
                for row in clients
            }
            selected_name = st.selectbox(
                "Cliente",
                list(client_map),
                key="manual_access_client",
            )
            selected_client = client_map[selected_name]

            c1, c2 = st.columns(2)
            access_mode = c1.selectbox(
                "Modalità",
                [
                    "Verifica completa",
                    "Accesso extra con scalare",
                    "Accesso senza scalare",
                ],
                key="manual_access_mode",
            )
            manual_reason = c2.text_input(
                "Motivazione",
                key="manual_access_reason",
            )

            if st.button(
                "Registra accesso manuale",
                use_container_width=True,
            ):
                if access_mode != "Verifica completa" and not manual_reason.strip():
                    st.error(
                        "La motivazione è obbligatoria per gli accessi extra."
                    )
                else:
                    try:
                        result = gestisci_accesso_manuale(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "cliente_id": (
                                    selected_client["cliente_id"]
                                ),
                                "modalita": access_mode,
                                "motivazione": (
                                    manual_reason.strip() or None
                                ),
                            },
                        )
                        clear_data_cache()
                        if result.get("consentito"):
                            st.success(
                                result.get("messaggio")
                                or "Accesso consentito."
                            )
                        else:
                            st.error(
                                result.get("messaggio")
                                or "Accesso negato."
                            )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore: {exc}")

        st.divider()
        st.subheader("Storico accessi")
        days_back = st.selectbox(
            "Periodo",
            [7, 30, 90],
            format_func=lambda value: f"Ultimi {value} giorni",
        )
        rows = load_access_log(days_back)
        if rows:
            render_access_log(rows)
        else:
            st.info("Nessun accesso registrato.")

    elif action == "Badge clienti":
        st.subheader("Associa badge")

        clients = [
            row for row in load_clients()
            if (
                row.get("stato_cliente")
                or row.get("stato")
                or "attivo"
            ) == "attivo"
        ]

        if clients:
            client_map = {
                f"{row['cognome']} {row['nome']}": row
                for row in clients
            }
            client_name = st.selectbox(
                "Cliente",
                list(client_map),
                key="badge_client",
            )
            client = client_map[client_name]
            badge_code = st.text_input(
                "Codice badge",
                placeholder="Passa il badge sul lettore o digita il codice",
                key="badge_code",
            )
            badge_note = st.text_input(
                "Note",
                key="badge_note",
            )

            if st.button(
                "Associa badge al cliente",
                use_container_width=True,
            ):
                if not badge_code.strip():
                    st.error("Il codice badge è obbligatorio.")
                else:
                    try:
                        associa_badge_cliente(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "cliente_id": client["cliente_id"],
                                "codice_badge": badge_code.strip(),
                                "note": badge_note.strip() or None,
                            },
                        )
                        clear_data_cache()
                        st.success("Badge associato.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore: {exc}")

        st.divider()
        st.subheader("Badge registrati")
        badges = load_badges()
        if badges:
            for badge in badges:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(
                        [1.7, 2.2, 1.1, 1.5]
                    )
                    c1.write(
                        f"**{badge.get('codice_badge') or '—'}**"
                    )
                    c2.write(
                        f"**{badge.get('cliente') or 'Cliente'}**"
                    )
                    c3.write(
                        "**Attivo**"
                        if badge.get("attivo")
                        else "**Inattivo**"
                    )
                    with c4:
                        button_label = (
                            "Disattiva"
                            if badge.get("attivo")
                            else "Riattiva"
                        )
                        if st.button(
                            button_label,
                            key=f"badge_toggle_{badge['badge_id']}",
                            use_container_width=True,
                        ):
                            try:
                                cambia_stato_badge(
                                    db,
                                    {
                                        "azienda_id": (
                                            load_company()["id"]
                                        ),
                                        "badge_id": badge["badge_id"],
                                        "attivo": not badge.get("attivo"),
                                        "motivo": (
                                            f"{button_label} da Reception"
                                        ),
                                    },
                                )
                                clear_data_cache()
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Errore: {exc}")
        else:
            st.info("Nessun badge registrato.")

    elif action == "Dispositivi accesso":
        st.subheader("Dispositivi registrati")

        devices = load_access_devices()
        if devices:
            for device in devices:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(
                        [2.1, 1.5, 1.1, 1.5]
                    )
                    c1.write(
                        f"**{device.get('nome') or 'Dispositivo'}**"
                    )
                    c1.caption(
                        device.get("postazione") or "—"
                    )
                    c2.write(
                        f"**{device.get('tipo_collegamento') or '—'}**"
                    )
                    c3.write(
                        "**Attivo**"
                        if device.get("attivo")
                        else "**Inattivo**"
                    )
                    with c4:
                        if st.button(
                            "Rigenera token",
                            key=f"regen_device_{device['dispositivo_id']}",
                            use_container_width=True,
                        ):
                            try:
                                result = rigenera_token_dispositivo(
                                    db,
                                    {
                                        "azienda_id": (
                                            load_company()["id"]
                                        ),
                                        "dispositivo_id": (
                                            device["dispositivo_id"]
                                        ),
                                    },
                                )
                                st.success(
                                    "Nuovo token generato. "
                                    "Copialo ora nel file config del Bridge."
                                )
                                st.code(result["token"])
                            except Exception as exc:
                                st.error(f"Errore: {exc}")
        else:
            st.info("Nessun dispositivo registrato.")

        st.divider()
        st.subheader("Nuovo dispositivo")

        with st.form("new_access_device"):
            c1, c2 = st.columns(2)
            device_name = c1.text_input(
                "Nome dispositivo *",
                value="Tornello Reception",
            )
            station = c2.text_input(
                "Postazione",
                value="Reception",
            )
            connection_type = st.selectbox(
                "Tipo collegamento",
                [
                    "keyboard_wedge",
                    "seriale",
                    "relay_command",
                    "solo_presenze",
                ],
            )
            submitted = st.form_submit_button(
                "Crea dispositivo",
                use_container_width=True,
            )

        if submitted:
            if not device_name.strip():
                st.error("Il nome è obbligatorio.")
            else:
                try:
                    result = crea_dispositivo_accesso(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "nome": device_name.strip(),
                            "postazione": station.strip() or None,
                            "tipo_collegamento": connection_type,
                        },
                    )
                    clear_data_cache()
                    st.success(
                        "Dispositivo creato. Copia il token nel Bridge."
                    )
                    st.code(result["token"])
                    st.rerun()
                except Exception as exc:
                    st.error(f"Errore: {exc}")

    elif action == "Operatori agenda":
        operators = load_agenda_operators()

        if operators:
            for operator in operators:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.4, 1.5, 1])
                    c1.write(
                        f"**{operator['nome_visualizzato']}**"
                    )
                    c2.caption(
                        operator.get("ruolo") or "Operatore"
                    )
                    c3.write(
                        "**Attivo**"
                        if operator.get("attivo")
                        else "**Inattivo**"
                    )
        else:
            st.info("Nessun operatore registrato.")

        st.divider()
        st.subheader("Nuovo operatore")

        with st.form("new_agenda_operator"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nome e cognome *")
            role = c2.text_input(
                "Ruolo",
                value="Trainer",
            )
            phone = st.text_input("Telefono")
            submitted = st.form_submit_button(
                "Salva operatore",
                use_container_width=True,
            )

        if submitted:
            if not name.strip():
                st.error("Il nome è obbligatorio.")
            else:
                try:
                    crea_operatore_agenda(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "nome_visualizzato": name.strip(),
                            "ruolo": role.strip() or None,
                            "telefono": phone.strip() or None,
                            "attivo": True,
                        },
                    )
                    clear_data_cache()
                    st.success("Operatore registrato.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Errore durante il salvataggio: {exc}")

    else:
        quick_actions = [
            ("Nuovo cliente", "goto", ("Clienti", "Nuovo cliente")),
            ("Modifica cliente", "goto", ("Clienti", "Modifica cliente")),
            ("Registra incasso", "goto", ("Contabilità", "Nuovo incasso")),
            ("Accesso tornello", "reception", "Tornello e accessi"),
            ("Agenda / Calendario", "reception", "Agenda settimanale"),
            ("Stampa ricevuta", "goto", ("Contabilità", "Ricevute")),
            ("Messaggio cliente", "future", None),
            ("Associa badge", "reception", "Badge clienti"),
            ("Sincronizza badge", "reception", "Dispositivi accesso"),
            ("Ricalcolo settimanale", "future", None),
            ("Aggiungi prenotazione", "reception", "Nuova prenotazione"),
            ("Conferma presenza", "reception", "Agenda giornaliera"),
            ("Carica documento", "goto", ("Clienti", "Modifica cliente")),
            ("Accesso manuale", "reception", "Tornello e accessi"),
            ("Storico cliente", "goto", ("Clienti", "Modifica cliente")),
            ("Situazione cliente", "goto", ("Clienti", "Elenco clienti")),
        ]

        for start_index in range(0, len(quick_actions), 4):
            cols = st.columns(4)
            for col, (
                label,
                action_type,
                target,
            ) in zip(
                cols,
                quick_actions[start_index:start_index + 4],
            ):
                with col:
                    if st.button(
                        label,
                        key=f"quick_{label}",
                        use_container_width=True,
                    ):
                        if action_type == "goto":
                            page_name, target_action = target
                            goto(page_name, target_action)
                        elif action_type == "reception":
                            st.session_state.pending_reception_action = target
                            st.rerun()
                        else:
                            st.info(
                                f"'{label}' sarà attivato nel relativo "
                                "blocco funzionale."
                            )


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

    c_search, c_status = st.columns([3, 1])
    search = c_search.text_input(
        "Cerca",
        placeholder="Nome, cognome, telefono o WhatsApp",
    )
    status_filter = c_status.selectbox(
        "Stato cliente",
        ["Tutti", "Attivi", "Inattivi"],
    )
    filtered = []

    for row in rows:
        row_status = row.get("stato_cliente") or row.get("stato") or "attivo"
        if status_filter == "Attivi" and row_status != "attivo":
            continue
        if status_filter == "Inattivi" and row_status != "inattivo":
            continue
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
                customer_state = (
                    customer.get("stato_cliente")
                    or customer.get("stato")
                    or "attivo"
                )
                st.markdown(
                    f"### {customer.get('stato_complessivo') or '—'}"
                )
                st.caption(
                    "Cliente attivo"
                    if customer_state == "attivo"
                    else "Cliente inattivo"
                )

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
        "Gestione cliente",
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




    with tabs[6]:
        st.subheader("Stato del cliente")

        current_status = customer.get("stato") or "attivo"
        target_status = (
            "inattivo"
            if current_status == "attivo"
            else "attivo"
        )
        action_label = (
            "Disattiva cliente"
            if target_status == "inattivo"
            else "Riattiva cliente"
        )

        st.info(
            "La disattivazione conserva anagrafica, documenti e storico, "
            "ma il cliente non sarà più considerato operativo."
        )
        status_reason = st.text_area(
            "Motivo cambio stato",
            key="customer_status_reason",
        )

        if st.button(
            action_label,
            use_container_width=True,
            key="toggle_customer_status",
        ):
            if not status_reason.strip():
                st.error("Inserisci il motivo del cambio stato.")
            else:
                try:
                    modifica_anagrafica_cliente(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "cliente_id": customer_id,
                            "nome": customer.get("nome"),
                            "cognome": customer.get("cognome"),
                            "telefono": customer.get("telefono"),
                            "whatsapp": customer.get("whatsapp"),
                            "email": customer.get("email"),
                            "codice_fiscale": customer.get("codice_fiscale"),
                            "partita_iva": customer.get("partita_iva"),
                            "indirizzo": customer.get("indirizzo"),
                            "stato": target_status,
                            "note": customer.get("note"),
                        },
                    )
                    clear_data_cache()
                    st.success(
                        "Cliente disattivato."
                        if target_status == "inattivo"
                        else "Cliente riattivato."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Errore durante il cambio stato: {exc}")

        st.divider()
        st.subheader("Eliminazione definitiva")
        st.warning(
            "Questa operazione elimina il cliente e tutti i dati collegati: "
            "abbonamenti, rate, incassi, ricevute, documenti e storico. "
            "Usala esclusivamente per clienti di prova o inserimenti errati."
        )

        confirmation_text = (
            f"ELIMINA {customer.get('cognome', '')} "
            f"{customer.get('nome', '')}"
        ).strip()

        typed_confirmation = st.text_input(
            f"Scrivi esattamente: {confirmation_text}",
            key="hard_delete_customer_confirmation",
        )
        accept_permanent_delete = st.checkbox(
            "Confermo che l'eliminazione è definitiva e non recuperabile.",
            key="hard_delete_customer_checkbox",
        )

        if st.button(
            "Elimina definitivamente il cliente",
            use_container_width=True,
            key="hard_delete_customer_button",
        ):
            if typed_confirmation.strip() != confirmation_text:
                st.error("La frase di conferma non coincide.")
            elif not accept_permanent_delete:
                st.error("Devi confermare l'eliminazione definitiva.")
            else:
                try:
                    elimina_cliente_definitivamente(
                        db,
                        {
                            "azienda_id": load_company()["id"],
                            "cliente_id": customer_id,
                            "conferma": confirmation_text,
                        },
                    )
                    st.session_state.selected_customer_id = None
                    clear_data_cache()
                    st.success("Cliente eliminato definitivamente.")
                    goto("Clienti", "Elenco clienti")
                except Exception as exc:
                    st.error(f"Eliminazione non riuscita: {exc}")


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
# ABBONAMENTI
# ============================================================

def subscription_selector(
    label: str,
    *,
    include_closed: bool = True,
) -> dict[str, Any] | None:
    rows = load_subscriptions()

    if not include_closed:
        rows = [
            row for row in rows
            if row.get("stato") not in (
                "terminato",
                "chiuso_anticipatamente",
                "annullato",
            )
        ]

    if not rows:
        st.info("Nessun abbonamento disponibile.")
        return None

    labels = {
        (
            f"{row['cliente']} · {row['pacchetto']} · "
            f"{format_date_it(row['data_inizio'])}"
        ): row
        for row in rows
    }

    selected_id = st.session_state.get("selected_subscription_id")
    selected_label = next(
        (
            label_value
            for label_value, row in labels.items()
            if row["abbonamento_id"] == selected_id
        ),
        list(labels)[0],
    )

    selected = labels[
        st.selectbox(
            label,
            list(labels),
            index=list(labels).index(selected_label),
        )
    ]
    st.session_state.selected_subscription_id = selected["abbonamento_id"]
    return selected


def subscription_plan_form(
    *,
    form_key: str,
    initial_package_id: str | None = None,
    initial_start: date | None = None,
    initial_price: float | None = None,
    initial_lessons: int | None = None,
    initial_payment_type: str = "Mensile",
) -> dict[str, Any] | None:
    packages = [
        package for package in load_packages()
        if package.get("attivo")
    ]

    if not packages:
        st.warning("Prima devi registrare almeno un pacchetto attivo.")
        return None

    package_map = {package["nome"]: package for package in packages}
    names = list(package_map)

    package_index = 0
    if initial_package_id:
        package_index = next(
            (
                index
                for index, package_name in enumerate(names)
                if package_map[package_name]["id"] == initial_package_id
            ),
            0,
        )

    package_name = st.selectbox(
        "Pacchetto *",
        names,
        index=package_index,
        key=f"{form_key}_package",
    )
    package = package_map[package_name]

    start_date = st.date_input(
        "Data inizio",
        value=initial_start or date.today(),
        format="DD/MM/YYYY",
        key=f"{form_key}_start",
    )

    proposed_end = calculate_package_end(
        start_date,
        package["periodicita"],
    )
    end_date = st.date_input(
        "Data fine prevista",
        value=proposed_end,
        format="DD/MM/YYYY",
        key=f"{form_key}_end",
    )

    c1, c2 = st.columns(2)
    price = c1.number_input(
        "Prezzo concordato",
        min_value=0.0,
        step=10.0,
        value=float(
            initial_price
            if initial_price is not None
            else package["prezzo_standard"]
        ),
        key=f"{form_key}_price",
    )
    lessons = c2.number_input(
        "Lezioni iniziali",
        min_value=0,
        step=1,
        value=int(
            initial_lessons
            if initial_lessons is not None
            else package["lezioni_standard"]
        ),
        key=f"{form_key}_lessons",
    )

    payment_types = [
        "Soluzione unica",
        "Mensile",
        "Trimestrale",
        "Semestrale",
        "Personalizzato",
    ]
    payment_type = st.selectbox(
        "Tipologia pagamento",
        payment_types,
        index=(
            payment_types.index(initial_payment_type)
            if initial_payment_type in payment_types
            else 1
        ),
        key=f"{form_key}_payment_type",
    )

    if payment_type == "Soluzione unica":
        installment_count = 1
        month_step = 0
    else:
        installment_count = st.number_input(
            "Numero rate",
            min_value=1,
            step=1,
            value=1,
            key=f"{form_key}_installment_count",
        )
        month_step = {
            "Mensile": 1,
            "Trimestrale": 3,
            "Semestrale": 6,
            "Personalizzato": 1,
        }[payment_type]

    first_due = st.date_input(
        "Prima scadenza",
        value=start_date,
        format="DD/MM/YYYY",
        key=f"{form_key}_first_due",
    )

    plan = st.data_editor(
        pd.DataFrame(
            build_installment_plan(
                float(price),
                int(installment_count),
                first_due,
                month_step,
            )
        ),
        use_container_width=True,
        hide_index=True,
        key=f"{form_key}_rate_editor",
        column_config={
            "numero_rata": st.column_config.NumberColumn(
                "N. rata",
                min_value=1,
                step=1,
            ),
            "data_scadenza": st.column_config.DateColumn(
                "Scadenza",
                format="DD/MM/YYYY",
            ),
            "importo_previsto": st.column_config.NumberColumn(
                "Importo previsto",
                format="€ %.2f",
                min_value=0.0,
            ),
        },
    )

    c3, c4 = st.columns(2)
    initial_payment = c3.number_input(
        "Acconto / pagamento iniziale",
        min_value=0.0,
        max_value=float(price),
        step=10.0,
        value=0.0,
        key=f"{form_key}_initial_payment",
    )
    payment_method = c4.selectbox(
        "Metodo pagamento iniziale",
        ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
        key=f"{form_key}_payment_method",
    )

    notes = st.text_area(
        "Note abbonamento",
        key=f"{form_key}_notes",
    )

    return {
        "package": package,
        "data_inizio": start_date,
        "data_fine_prevista": end_date,
        "prezzo_concordato": float(price),
        "lezioni_iniziali": int(lessons),
        "tipologia_pagamento": payment_type,
        "rate": plan,
        "pagamento_iniziale": float(initial_payment),
        "metodo_pagamento": payment_method,
        "note": notes.strip() or None,
    }


def new_subscription_page() -> None:
    clients = [
        row for row in load_clients()
        if row.get("stato_cliente", "attivo") != "inattivo"
    ]

    if not clients:
        st.info("Nessun cliente disponibile.")
        return

    labels = {
        f"{row['cognome']} {row['nome']}": row
        for row in clients
    }
    selected_client = labels[
        st.selectbox("Cliente *", list(labels))
    ]

    form_data = subscription_plan_form(
        form_key="new_subscription",
    )
    if not form_data:
        return

    if st.button(
        "Crea abbonamento",
        use_container_width=True,
    ):
        total_installments = float(
            form_data["rate"]["importo_previsto"].sum()
        )

        if abs(
            total_installments - form_data["prezzo_concordato"]
        ) > 0.01:
            st.error(
                "La somma delle rate deve coincidere "
                "con il prezzo concordato."
            )
            return

        if (
            form_data["data_fine_prevista"]
            < form_data["data_inizio"]
        ):
            st.error(
                "La data fine non può precedere la data inizio."
            )
            return

        try:
            result = crea_abbonamento_cliente(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "cliente_id": selected_client["cliente_id"],
                    "pacchetto_id": form_data["package"]["id"],
                    "data_inizio": form_data["data_inizio"].isoformat(),
                    "data_fine_prevista": (
                        form_data["data_fine_prevista"].isoformat()
                    ),
                    "prezzo_concordato": (
                        form_data["prezzo_concordato"]
                    ),
                    "lezioni_iniziali": form_data["lezioni_iniziali"],
                    "tipologia_pagamento": (
                        form_data["tipologia_pagamento"]
                    ),
                    "note": form_data["note"],
                    "rate": [
                        {
                            "numero_rata": int(row["numero_rata"]),
                            "data_scadenza": (
                                row["data_scadenza"].isoformat()
                            ),
                            "importo_previsto": float(
                                row["importo_previsto"]
                            ),
                        }
                        for _, row in form_data["rate"].iterrows()
                    ],
                    "pagamento_iniziale": (
                        {
                            "data_incasso": (
                                form_data["data_inizio"].isoformat()
                            ),
                            "importo": form_data["pagamento_iniziale"],
                            "metodo_pagamento": (
                                form_data["metodo_pagamento"]
                            ),
                            "causale": "Acconto nuovo abbonamento",
                        }
                        if form_data["pagamento_iniziale"] > 0
                        else None
                    ),
                },
            )
            clear_data_cache()
            st.session_state.selected_subscription_id = (
                result["abbonamento_id"]
            )
            st.success("Abbonamento creato.")
            st.rerun()
        except Exception as exc:
            st.error(f"Errore durante la creazione: {exc}")


def manage_subscription_page() -> None:
    selected = subscription_selector(
        "Abbonamento da gestire",
        include_closed=True,
    )
    if not selected:
        return

    detail = get_abbonamento_dettaglio(
        db,
        selected["abbonamento_id"],
    )
    subscription = detail["abbonamento"]
    rates = detail.get("rate") or []
    receipts = detail.get("incassi") or []
    events = detail.get("eventi_stato") or []
    lesson_movements = detail.get("movimenti_lezioni") or []

    st.subheader(
        f"{subscription['cliente']} · "
        f"{subscription['pacchetto']}"
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Valore",
        money(float(subscription.get("prezzo_concordato") or 0)),
    )
    m2.metric(
        "Pagato",
        money(float(subscription.get("pagato") or 0)),
    )
    m3.metric(
        "Residuo",
        money(float(subscription.get("residuo") or 0)),
    )
    m4.metric(
        "Stato",
        subscription.get("stato_visuale") or subscription.get("stato"),
    )

    tabs = st.tabs([
        "Situazione",
        "Cambia stato",
        "Rate",
        "Incassi",
        "Lezioni",
        "Storico stati",
    ])

    with tabs[0]:
        st.write(
            f"Periodo: **{format_date_it(subscription['data_inizio'])} "
            f"– {format_date_it(subscription['data_fine_prevista'])}**"
        )
        st.write(
            f"Tipologia pagamento: "
            f"**{subscription.get('tipologia_pagamento') or '—'}**"
        )
        st.write(
            f"Lezioni iniziali: "
            f"**{subscription.get('lezioni_iniziali') or 0}**"
        )
        lesson_cols = st.columns(3)
        lesson_cols[0].metric(
            "Lezioni iniziali",
            int(subscription.get("lezioni_iniziali") or 0),
        )
        lesson_cols[1].metric(
            "Movimenti netti",
            int(subscription.get("movimenti_lezioni_netto") or 0),
        )
        lesson_cols[2].metric(
            "Lezioni disponibili",
            int(subscription.get("saldo_lezioni") or 0),
        )

        if subscription.get("note"):
            st.caption(subscription["note"])

    with tabs[1]:
        current_state = subscription.get("stato")
        allowed_actions = []

        if current_state in ("da_attivare", "attivo"):
            allowed_actions.extend([
                "Sospendi",
                "Chiudi anticipatamente",
                "Termina",
            ])
        elif current_state == "sospeso":
            allowed_actions.extend([
                "Riattiva",
                "Chiudi anticipatamente",
                "Termina",
            ])
        elif current_state in (
            "terminato",
            "chiuso_anticipatamente",
        ):
            st.info(
                "L'abbonamento è chiuso. Può essere rinnovato, "
                "ma non riaperto modificando lo storico."
            )

        if allowed_actions:
            action = st.selectbox(
                "Azione",
                allowed_actions,
            )
            action_date = st.date_input(
                "Data operazione",
                value=date.today(),
                format="DD/MM/YYYY",
            )
            reason = st.text_area(
                "Motivazione *",
            )

            suspension_end = None
            extend_end = False

            if action == "Sospendi":
                suspension_end = st.date_input(
                    "Fine sospensione prevista",
                    value=date.today() + relativedelta(months=1),
                    format="DD/MM/YYYY",
                )
                extend_end = st.checkbox(
                    "Prolunga la scadenza per i giorni di sospensione",
                    value=True,
                )

            if st.button(
                "Conferma cambio stato",
                use_container_width=True,
            ):
                if not reason.strip():
                    st.error("La motivazione è obbligatoria.")
                else:
                    try:
                        cambia_stato_abbonamento(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "abbonamento_id": (
                                    subscription["abbonamento_id"]
                                ),
                                "azione": action,
                                "data_evento": action_date.isoformat(),
                                "fine_sospensione_prevista": (
                                    suspension_end.isoformat()
                                    if suspension_end
                                    else None
                                ),
                                "prolunga_scadenza": extend_end,
                                "motivo": reason.strip(),
                            },
                        )
                        clear_data_cache()
                        st.success("Stato abbonamento aggiornato.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore durante l'operazione: {exc}")

    with tabs[2]:
        if rates:
            render_installment_cards(rates)
        else:
            st.info("Nessuna rata.")

    with tabs[3]:
        if receipts:
            render_receipt_cards(receipts)
        else:
            st.info("Nessun incasso.")

    with tabs[4]:
        if lesson_movements:
            for movement in lesson_movements:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(
                        [1.1, 1.5, 1, 2.5]
                    )
                    with c1:
                        st.caption("DATA")
                        st.write(
                            f"**{format_date_it(movement.get('data_movimento'))}**"
                        )
                    with c2:
                        st.caption("TIPO")
                        st.write(
                            f"**{movement.get('tipo') or '—'}**"
                        )
                    with c3:
                        st.caption("QUANTITÀ")
                        quantity = int(
                            movement.get("quantita") or 0
                        )
                        st.write(f"**{quantity:+d}**")
                    with c4:
                        st.caption("CAUSALE")
                        st.write(movement.get("causale") or "—")
        else:
            st.info("Nessun movimento lezione registrato.")

    with tabs[5]:
        if events:
            for event in events:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.2, 1.4, 2.5])
                    with c1:
                        st.caption("DATA")
                        st.write(
                            f"**{format_date_it(event.get('data_evento'))}**"
                        )
                    with c2:
                        st.caption("OPERAZIONE")
                        st.write(
                            f"**{event.get('azione') or '—'}**"
                        )
                    with c3:
                        st.caption("MOTIVO")
                        st.write(event.get("motivo") or "—")
        else:
            st.info("Nessun cambio di stato registrato.")


def renew_subscription_page() -> None:
    selected = subscription_selector(
        "Abbonamento da rinnovare",
        include_closed=True,
    )
    if not selected:
        return

    old_detail = get_abbonamento_dettaglio(
        db,
        selected["abbonamento_id"],
    )
    old_subscription = old_detail["abbonamento"]

    default_start = (
        date.fromisoformat(old_subscription["data_fine_prevista"])
        + relativedelta(days=1)
    )

    st.info(
        "Il rinnovo crea un nuovo abbonamento. "
        "Quello precedente resta invariato nello storico."
    )

    form_data = subscription_plan_form(
        form_key="renew_subscription",
        initial_package_id=old_subscription["pacchetto_id"],
        initial_start=default_start,
        initial_price=float(old_subscription["prezzo_concordato"]),
        initial_lessons=int(old_subscription["lezioni_iniziali"]),
        initial_payment_type=old_subscription["tipologia_pagamento"],
    )
    if not form_data:
        return

    close_previous = st.checkbox(
        "Segna il precedente come terminato alla data di inizio del rinnovo",
        value=True,
    )

    if st.button(
        "Conferma rinnovo",
        use_container_width=True,
    ):
        total_installments = float(
            form_data["rate"]["importo_previsto"].sum()
        )

        if abs(
            total_installments - form_data["prezzo_concordato"]
        ) > 0.01:
            st.error(
                "La somma delle rate deve coincidere "
                "con il prezzo concordato."
            )
            return

        try:
            result = rinnova_abbonamento_cliente(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "cliente_id": old_subscription["cliente_id"],
                    "abbonamento_precedente_id": (
                        old_subscription["abbonamento_id"]
                    ),
                    "chiudi_precedente": close_previous,
                    "pacchetto_id": form_data["package"]["id"],
                    "data_inizio": form_data["data_inizio"].isoformat(),
                    "data_fine_prevista": (
                        form_data["data_fine_prevista"].isoformat()
                    ),
                    "prezzo_concordato": (
                        form_data["prezzo_concordato"]
                    ),
                    "lezioni_iniziali": form_data["lezioni_iniziali"],
                    "tipologia_pagamento": (
                        form_data["tipologia_pagamento"]
                    ),
                    "note": form_data["note"],
                    "rate": [
                        {
                            "numero_rata": int(row["numero_rata"]),
                            "data_scadenza": (
                                row["data_scadenza"].isoformat()
                            ),
                            "importo_previsto": float(
                                row["importo_previsto"]
                            ),
                        }
                        for _, row in form_data["rate"].iterrows()
                    ],
                    "pagamento_iniziale": (
                        {
                            "data_incasso": (
                                form_data["data_inizio"].isoformat()
                            ),
                            "importo": form_data["pagamento_iniziale"],
                            "metodo_pagamento": (
                                form_data["metodo_pagamento"]
                            ),
                            "causale": "Acconto rinnovo abbonamento",
                        }
                        if form_data["pagamento_iniziale"] > 0
                        else None
                    ),
                },
            )
            clear_data_cache()
            st.session_state.selected_subscription_id = (
                result["abbonamento_id"]
            )
            st.success("Rinnovo creato senza sovrascrivere lo storico.")
            st.rerun()
        except Exception as exc:
            st.error(f"Errore durante il rinnovo: {exc}")


def subscription_history_page() -> None:
    rows = load_subscriptions()
    clients = sorted({
        row["cliente"]
        for row in rows
    })

    if not clients:
        st.info("Nessuno storico disponibile.")
        return

    selected_client = st.selectbox(
        "Cliente",
        clients,
    )
    history = [
        row for row in rows
        if row["cliente"] == selected_client
    ]

    render_subscription_cards(
        history,
        show_actions=False,
    )


def page_subscriptions() -> None:
    header(
        "Abbonamenti",
        "Attivazioni, rinnovi, sospensioni e storico.",
    )

    actions = [
        "Elenco",
        "Nuovo abbonamento",
        "Gestisci",
        "Rinnova",
        "Storico cliente",
    ]

    pending = st.session_state.get("pending_subscription_action")
    if pending in actions:
        st.session_state.subscription_action = pending
        st.session_state.pending_subscription_action = None
    elif "subscription_action" not in st.session_state:
        st.session_state.subscription_action = "Elenco"

    action = st.selectbox(
        "Operazione",
        actions,
        key="subscription_action",
    )

    if action == "Elenco":
        rows = load_subscriptions()

        c1, c2 = st.columns(2)
        state_filter = c1.selectbox(
            "Stato",
            [
                "Tutti",
                "Attivi",
                "In scadenza",
                "Scaduti",
                "Sospesi",
                "Chiusi",
            ],
        )
        search = c2.text_input(
            "Cerca",
            placeholder="Cliente o pacchetto",
        )

        filtered = rows
        if state_filter == "Attivi":
            filtered = [
                row for row in filtered
                if row.get("stato_visuale") == "Attivo"
            ]
        elif state_filter == "In scadenza":
            filtered = [
                row for row in filtered
                if row.get("stato_visuale") == "In scadenza"
            ]
        elif state_filter == "Scaduti":
            filtered = [
                row for row in filtered
                if row.get("stato_visuale") == "Scaduto"
            ]
        elif state_filter == "Sospesi":
            filtered = [
                row for row in filtered
                if row.get("stato") == "sospeso"
            ]
        elif state_filter == "Chiusi":
            filtered = [
                row for row in filtered
                if row.get("stato") in (
                    "terminato",
                    "chiuso_anticipatamente",
                    "annullato",
                )
            ]

        if search:
            lowered = search.lower()
            filtered = [
                row for row in filtered
                if lowered in (
                    f"{row.get('cliente', '')} "
                    f"{row.get('pacchetto', '')}"
                ).lower()
            ]

        active_count = sum(
            1 for row in rows
            if row.get("stato_visuale") == "Attivo"
        )
        expiring_count = sum(
            1 for row in rows
            if row.get("stato_visuale") == "In scadenza"
        )
        suspended_count = sum(
            1 for row in rows
            if row.get("stato") == "sospeso"
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Attivi", active_count)
        m2.metric("In scadenza", expiring_count)
        m3.metric("Sospesi", suspended_count)

        if filtered:
            render_subscription_cards(filtered)
        else:
            st.info("Nessun abbonamento con i filtri selezionati.")

    elif action == "Nuovo abbonamento":
        new_subscription_page()
    elif action == "Gestisci":
        manage_subscription_page()
    elif action == "Rinnova":
        renew_subscription_page()
    else:
        subscription_history_page()


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
    "Abbonamenti": page_subscriptions,
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
