from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta


# ============================================================
# CONFIGURAZIONE
# ============================================================

APP_NAME = "Gestionale"
APP_VERSION = "0.2.0"
DEVELOPER_CREDIT = "Developed by Pentti Salenius © 2026"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@dataclass(frozen=True)
class Theme:
    background: str = "#0D0F11"
    sidebar: str = "#08090A"
    surface: str = "#171A1E"
    surface_alt: str = "#20242A"
    text: str = "#F6F2E8"
    text_secondary: str = "#AAA59A"
    gold: str = "#BFA15A"
    gold_hover: str = "#D4B96F"
    border: str = "#3A3D42"
    success: str = "#3E8E68"
    warning: str = "#D69B32"
    danger: str = "#C85C5C"
    info: str = "#4A7FA8"


THEME = Theme()


def apply_theme(theme: Theme) -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --background: {theme.background};
            --sidebar: {theme.sidebar};
            --surface: {theme.surface};
            --surface-alt: {theme.surface_alt};
            --text: {theme.text};
            --text-secondary: {theme.text_secondary};
            --gold: {theme.gold};
            --gold-hover: {theme.gold_hover};
            --border: {theme.border};
            --success: {theme.success};
            --warning: {theme.warning};
            --danger: {theme.danger};
            --info: {theme.info};
        }}

        .stApp {{
            background: var(--background);
            color: var(--text);
        }}

        [data-testid="stSidebar"] {{
            background: var(--sidebar);
            border-right: 1px solid var(--border);
        }}

        [data-testid="stSidebar"] * {{
            color: var(--text) !important;
        }}

        h1, h2, h3, h4, h5, h6, p, span, label {{
            color: var(--text);
        }}

        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }}

        .app-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
        }}

        .app-card-gold {{
            background: var(--surface);
            border: 1px solid var(--gold);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
        }}

        .muted {{
            color: var(--text-secondary);
        }}

        .company-pill {{
            display: inline-block;
            border: 1px solid var(--gold);
            color: var(--gold);
            border-radius: 999px;
            padding: 5px 11px;
            font-size: 0.8rem;
            font-weight: 700;
        }}

        div[data-testid="stMetric"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px 16px;
        }}

        div[data-testid="stMetric"] label {{
            color: var(--text-secondary) !important;
        }}

        div[data-testid="stMetricValue"] {{
            color: var(--text) !important;
        }}

        div.stButton > button,
        div.stFormSubmitButton > button,
        div.stDownloadButton > button {{
            background: var(--surface) !important;
            color: var(--text) !important;
            border: 1px solid var(--gold) !important;
            border-radius: 8px !important;
            font-weight: 650 !important;
            transition: 0.18s ease-in-out !important;
        }}

        div.stButton > button *,
        div.stFormSubmitButton > button *,
        div.stDownloadButton > button * {{
            color: var(--text) !important;
        }}

        div.stButton > button:hover,
        div.stFormSubmitButton > button:hover,
        div.stDownloadButton > button:hover {{
            background: var(--gold) !important;
            border-color: var(--gold-hover) !important;
            color: #111111 !important;
        }}

        div.stButton > button:hover *,
        div.stFormSubmitButton > button:hover *,
        div.stDownloadButton > button:hover * {{
            color: #111111 !important;
        }}

        div.stButton > button:disabled,
        div.stFormSubmitButton > button:disabled {{
            background: #2A2D31 !important;
            color: #777777 !important;
            border-color: #4A4D52 !important;
        }}

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] > div {{
            background: var(--surface-alt) !important;
            border-color: var(--border) !important;
            color: var(--text) !important;
        }}

        .footer {{
            color: var(--text-secondary);
            text-align: center;
            margin-top: 2rem;
            font-size: 0.82rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_theme(THEME)


# ============================================================
# DATI DEMO IN SESSIONE
# ============================================================

def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "azienda_nome": "KREO",
        "utente_nome": "Pentti Salenius",
        "utente_ruolo": "Super Admin",
        "menu": "Reception",
        "pacchetti": [],
        "clienti": [],
        "abbonamenti": [],
        "rate": [],
        "incassi": [],
        "documenti": [],
        "fornitori": [],
        "spese": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.pacchetti:
        st.session_state.pacchetti = [
            {
                "id": "pkg-luxury",
                "nome": "Luxury",
                "prezzo_standard": 500.0,
                "durata_numero": 1,
                "durata_unita": "mesi",
                "lezioni_standard": 12,
                "frequenza_settimanale": 3,
                "partecipanti_massimi": 1,
                "attivo": True,
            },
            {
                "id": "pkg-gold",
                "nome": "Gold",
                "prezzo_standard": 750.0,
                "durata_numero": 1,
                "durata_unita": "mesi",
                "lezioni_standard": 12,
                "frequenza_settimanale": 3,
                "partecipanti_massimi": 2,
                "attivo": True,
            },
            {
                "id": "pkg-vip",
                "nome": "VIP",
                "prezzo_standard": 900.0,
                "durata_numero": 1,
                "durata_unita": "mesi",
                "lezioni_standard": 12,
                "frequenza_settimanale": 3,
                "partecipanti_massimi": 3,
                "attivo": True,
            },
        ]


initialize_state()


# ============================================================
# UTILITÀ
# ============================================================

def format_currency(value: float) -> str:
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def package_by_name(name: str) -> dict[str, Any] | None:
    return next((p for p in st.session_state.pacchetti if p["nome"] == name), None)


def customer_by_id(customer_id: str) -> dict[str, Any] | None:
    return next((c for c in st.session_state.clienti if c["id"] == customer_id), None)


def calculate_end_date(start: date, duration_number: int, duration_unit: str) -> date:
    if duration_unit == "giorni":
        return start + relativedelta(days=duration_number) - relativedelta(days=1)
    if duration_unit == "settimane":
        return start + relativedelta(weeks=duration_number) - relativedelta(days=1)
    if duration_unit == "mesi":
        return start + relativedelta(months=duration_number) - relativedelta(days=1)
    if duration_unit == "anni":
        return start + relativedelta(years=duration_number) - relativedelta(days=1)
    return start


def active_installments_for_subscription(subscription_id: str) -> list[dict[str, Any]]:
    return [
        r
        for r in st.session_state.rate
        if r["abbonamento_id"] == subscription_id and not r.get("annullata", False)
    ]


def valid_receipts_for_subscription(subscription_id: str) -> list[dict[str, Any]]:
    return [
        i
        for i in st.session_state.incassi
        if i.get("abbonamento_id") == subscription_id and i.get("stato") == "valido"
    ]


def subscription_residual(subscription_id: str) -> float:
    subscription = next(
        (a for a in st.session_state.abbonamenti if a["id"] == subscription_id),
        None,
    )
    if not subscription:
        return 0.0
    paid = sum(i["importo"] for i in valid_receipts_for_subscription(subscription_id))
    return max(subscription["prezzo_concordato"] - paid, 0.0)


def build_installment_plan(
    total: float,
    count: int,
    first_due_date: date,
    frequency_months: int,
) -> list[dict[str, Any]]:
    if count < 1:
        return []

    base = round(total / count, 2)
    amounts = [base] * count
    difference = round(total - sum(amounts), 2)
    amounts[-1] = round(amounts[-1] + difference, 2)

    return [
        {
            "numero": idx + 1,
            "data_scadenza": first_due_date + relativedelta(months=frequency_months * idx),
            "importo_previsto": amount,
        }
        for idx, amount in enumerate(amounts)
    ]


def add_document(
    cliente_id: str,
    abbonamento_id: str | None,
    tipo: str,
    data_documento: date | None,
    data_scadenza: date | None,
    note: str,
    file_name: str | None,
) -> None:
    st.session_state.documenti.append(
        {
            "id": str(uuid4()),
            "cliente_id": cliente_id,
            "abbonamento_id": abbonamento_id,
            "tipo": tipo,
            "data_documento": data_documento,
            "data_scadenza": data_scadenza,
            "note": note,
            "file_name": file_name,
            "creato_il": datetime.now(),
            "annullato": False,
        }
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:1rem;">
            <div>
                <h1 style="margin-bottom:0.2rem;">{title}</h1>
                <div class="muted">{subtitle}</div>
            </div>
            <span class="company-pill">{st.session_state.azienda_nome}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str, gold: bool = False) -> None:
    class_name = "app-card-gold" if gold else "app-card"
    st.markdown(
        f"""
        <div class="{class_name}">
            <h3 style="margin-top:0;">{title}</h3>
            <div class="muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:0.5rem 0 1rem 0;">
                <div style="font-size:1.65rem;font-weight:800;">{st.session_state.azienda_nome}</div>
                <div class="muted">Gestionale aziendale</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        st.markdown(
            f"""
            <div class="app-card" style="padding:12px;">
                <strong>{st.session_state.utente_nome}</strong><br>
                <span class="muted">{st.session_state.utente_ruolo}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"Versione {APP_VERSION}")

    return selected


# ============================================================
# RECEPTION
# ============================================================

def page_reception() -> None:
    page_header("Reception", "Agenda, clienti, incassi, presenze e alert.")

    total_clients = len(st.session_state.clienti)
    today_receipts = sum(
        i["importo"]
        for i in st.session_state.incassi
        if i["data_incasso"] == date.today() and i["stato"] == "valido"
    )
    open_residuals = sum(
        subscription_residual(a["id"])
        for a in st.session_state.abbonamenti
        if a.get("stato") != "annullato"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clienti", total_clients)
    c2.metric("Prenotazioni oggi", "—")
    c3.metric("Incassi oggi", format_currency(today_receipts))
    c4.metric("Residui aperti", format_currency(open_residuals))

    st.subheader("Azioni rapide")
    cols = st.columns(4)
    with cols[0]:
        if st.button("Nuovo cliente", use_container_width=True):
            st.session_state.menu = "Clienti"
            st.session_state.clienti_action = "Nuovo cliente"
            st.rerun()
    with cols[1]:
        if st.button("Nuovo incasso", use_container_width=True):
            st.session_state.menu = "Contabilità"
            st.session_state.contabilita_action = "Nuovo incasso"
            st.rerun()
    with cols[2]:
        st.button("Associa badge", use_container_width=True, disabled=True)
    with cols[3]:
        st.button("Conferma presenza", use_container_width=True, disabled=True)

    col1, col2 = st.columns([2.2, 1])
    with col1:
        info_card(
            "Agenda settimanale",
            "La vista agenda sarà collegata alle prenotazioni, alle disponibilità dello staff e alle presenze.",
            gold=True,
        )
    with col2:
        info_card(
            "Alert operativi",
            "Rate scadute, certificati mancanti o in scadenza, badge da associare e anomalie.",
        )


# ============================================================
# PACCHETTI
# ============================================================

def page_packages() -> None:
    page_header("Pacchetti", "Listino generale dei servizi venduti dall'azienda.")

    action = st.selectbox(
        "Operazione",
        ["Elenco pacchetti", "Nuovo pacchetto", "Modifica pacchetto esistente"],
    )

    if action == "Elenco pacchetti":
        if not st.session_state.pacchetti:
            st.info("Nessun pacchetto registrato.")
            return

        df = pd.DataFrame(st.session_state.pacchetti)
        df = df[
            [
                "nome",
                "prezzo_standard",
                "durata_numero",
                "durata_unita",
                "lezioni_standard",
                "frequenza_settimanale",
                "partecipanti_massimi",
                "attivo",
            ]
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif action == "Nuovo pacchetto":
        with st.form("new_package_form"):
            name = st.text_input("Nome pacchetto *")
            description = st.text_area("Descrizione")
            c1, c2, c3 = st.columns(3)
            price = c1.number_input("Prezzo standard", min_value=0.0, step=10.0)
            duration_number = c2.number_input("Durata", min_value=1, step=1)
            duration_unit = c3.selectbox("Unità durata", ["giorni", "settimane", "mesi", "anni"])

            c4, c5, c6 = st.columns(3)
            lessons = c4.number_input("Lezioni standard", min_value=0, step=1)
            weekly_frequency = c5.number_input("Frequenza settimanale", min_value=0, step=1)
            participants = c6.number_input("Partecipanti massimi", min_value=1, step=1)

            c7, c8 = st.columns(2)
            requires_booking = c7.checkbox("Richiede prenotazione", value=True)
            occupies_trainer = c8.checkbox("Occupa agenda trainer", value=True)

            c9, c10 = st.columns(2)
            generates_presence = c9.checkbox("Genera presenza", value=True)
            consumes_lesson = c10.checkbox("Consuma lezione", value=True)

            free_access = st.checkbox("Consente accesso libero", value=False)
            active = st.checkbox("Pacchetto attivo", value=True)
            notes = st.text_area("Note")

            submitted = st.form_submit_button("Salva pacchetto", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Il nome del pacchetto è obbligatorio.")
            elif any(p["nome"].lower() == name.strip().lower() for p in st.session_state.pacchetti):
                st.error("Esiste già un pacchetto con questo nome.")
            else:
                st.session_state.pacchetti.append(
                    {
                        "id": str(uuid4()),
                        "nome": name.strip(),
                        "descrizione": description.strip(),
                        "prezzo_standard": float(price),
                        "durata_numero": int(duration_number),
                        "durata_unita": duration_unit,
                        "lezioni_standard": int(lessons),
                        "frequenza_settimanale": int(weekly_frequency),
                        "partecipanti_massimi": int(participants),
                        "richiede_prenotazione": requires_booking,
                        "occupa_agenda_trainer": occupies_trainer,
                        "genera_presenza": generates_presence,
                        "consuma_lezione": consumes_lesson,
                        "consente_accesso_libero": free_access,
                        "attivo": active,
                        "note": notes.strip(),
                    }
                )
                st.success("Pacchetto registrato.")

    else:
        names = [p["nome"] for p in st.session_state.pacchetti]
        selected_name = st.selectbox("Pacchetto da modificare", names)
        package = package_by_name(selected_name)
        if package:
            st.info(
                "La modifica dei dati standard avrà effetto sui nuovi abbonamenti, non su quelli già creati."
            )
            with st.form("edit_package_form"):
                price = st.number_input(
                    "Prezzo standard",
                    min_value=0.0,
                    step=10.0,
                    value=float(package["prezzo_standard"]),
                )
                duration_number = st.number_input(
                    "Durata",
                    min_value=1,
                    step=1,
                    value=int(package["durata_numero"]),
                )
                duration_unit = st.selectbox(
                    "Unità durata",
                    ["giorni", "settimane", "mesi", "anni"],
                    index=["giorni", "settimane", "mesi", "anni"].index(package["durata_unita"]),
                )
                lessons = st.number_input(
                    "Lezioni standard",
                    min_value=0,
                    step=1,
                    value=int(package["lezioni_standard"]),
                )
                active = st.checkbox("Pacchetto attivo", value=bool(package["attivo"]))
                submitted = st.form_submit_button("Salva modifiche", use_container_width=True)

            if submitted:
                package["prezzo_standard"] = float(price)
                package["durata_numero"] = int(duration_number)
                package["durata_unita"] = duration_unit
                package["lezioni_standard"] = int(lessons)
                package["attivo"] = active
                st.success("Pacchetto aggiornato.")


# ============================================================
# ABBONAMENTI
# ============================================================

def create_subscription_ui(preselected_customer_id: str | None = None, form_key: str = "subscription") -> str | None:
    if not st.session_state.clienti:
        st.warning("Prima devi registrare almeno un cliente.")
        return None
    if not st.session_state.pacchetti:
        st.warning("Prima devi registrare almeno un pacchetto.")
        return None

    customer_options = {
        f'{c["cognome"]} {c["nome"]}': c["id"] for c in st.session_state.clienti
    }
    customer_labels = list(customer_options.keys())

    default_customer_index = 0
    if preselected_customer_id:
        for idx, label in enumerate(customer_labels):
            if customer_options[label] == preselected_customer_id:
                default_customer_index = idx
                break

    selected_customer_label = st.selectbox(
        "Cliente *",
        customer_labels,
        index=default_customer_index,
        key=f"{form_key}_customer",
    )
    customer_id = customer_options[selected_customer_label]

    active_packages = [p for p in st.session_state.pacchetti if p.get("attivo", True)]
    package_names = [p["nome"] for p in active_packages]
    selected_package_name = st.selectbox(
        "Pacchetto *",
        package_names,
        key=f"{form_key}_package",
    )
    package = package_by_name(selected_package_name)
    assert package is not None

    st.caption(
        f'Prezzo standard: {format_currency(package["prezzo_standard"])} · '
        f'Durata: {package["durata_numero"]} {package["durata_unita"]} · '
        f'Lezioni: {package["lezioni_standard"]}'
    )

    c1, c2 = st.columns(2)
    start_date = c1.date_input("Data inizio *", value=date.today(), key=f"{form_key}_start")
    calculated_end = calculate_end_date(
        start_date,
        package["durata_numero"],
        package["durata_unita"],
    )
    manual_end = c2.date_input(
        "Data fine prevista",
        value=calculated_end,
        key=f"{form_key}_end",
        help="È proposta automaticamente dal pacchetto, ma può essere modificata.",
    )

    c3, c4 = st.columns(2)
    agreed_price = c3.number_input(
        "Prezzo concordato *",
        min_value=0.0,
        step=10.0,
        value=float(package["prezzo_standard"]),
        key=f"{form_key}_price",
    )
    initial_lessons = c4.number_input(
        "Lezioni iniziali",
        min_value=0,
        step=1,
        value=int(package["lezioni_standard"]),
        key=f"{form_key}_lessons",
    )

    st.subheader("Piano rate")
    payment_type = st.selectbox(
        "Tipologia pagamento",
        ["Soluzione unica", "Mensile", "Trimestrale", "Semestrale", "Personalizzato"],
        key=f"{form_key}_payment_type",
    )

    if payment_type == "Soluzione unica":
        installment_count = 1
        frequency_months = 0
    elif payment_type == "Mensile":
        installment_count = st.number_input(
            "Numero rate",
            min_value=1,
            step=1,
            value=max(package["durata_numero"], 1) if package["durata_unita"] == "mesi" else 1,
            key=f"{form_key}_installment_count",
        )
        frequency_months = 1
    elif payment_type == "Trimestrale":
        installment_count = st.number_input(
            "Numero rate",
            min_value=1,
            step=1,
            value=1,
            key=f"{form_key}_installment_count",
        )
        frequency_months = 3
    elif payment_type == "Semestrale":
        installment_count = st.number_input(
            "Numero rate",
            min_value=1,
            step=1,
            value=1,
            key=f"{form_key}_installment_count",
        )
        frequency_months = 6
    else:
        installment_count = st.number_input(
            "Numero rate",
            min_value=1,
            step=1,
            value=2,
            key=f"{form_key}_installment_count",
        )
        frequency_months = st.number_input(
            "Intervallo tra le rate, in mesi",
            min_value=0,
            step=1,
            value=1,
            key=f"{form_key}_frequency",
        )

    first_due_date = st.date_input(
        "Data prima scadenza",
        value=start_date,
        key=f"{form_key}_first_due",
    )

    suggested_plan = build_installment_plan(
        float(agreed_price),
        int(installment_count),
        first_due_date,
        int(frequency_months),
    )

    st.caption("Piano proposto, modificabile prima del salvataggio")
    edited_plan = st.data_editor(
        pd.DataFrame(suggested_plan),
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key=f"{form_key}_plan_editor",
        column_config={
            "numero": st.column_config.NumberColumn("N. rata", min_value=1, step=1),
            "data_scadenza": st.column_config.DateColumn("Scadenza"),
            "importo_previsto": st.column_config.NumberColumn(
                "Importo previsto",
                min_value=0.0,
                step=10.0,
                format="€ %.2f",
            ),
        },
    )

    plan_total = float(edited_plan["importo_previsto"].sum()) if not edited_plan.empty else 0.0
    difference = round(float(agreed_price) - plan_total, 2)

    c5, c6, c7 = st.columns(3)
    c5.metric("Prezzo abbonamento", format_currency(float(agreed_price)))
    c6.metric("Totale rate", format_currency(plan_total))
    c7.metric("Differenza", format_currency(difference))

    notes = st.text_area("Note abbonamento", key=f"{form_key}_notes")

    if st.button("Crea abbonamento", use_container_width=True, key=f"{form_key}_submit"):
        if agreed_price <= 0:
            st.error("Il prezzo concordato deve essere maggiore di zero.")
            return None
        if abs(difference) > 0.01:
            st.error("La somma delle rate deve coincidere con il prezzo concordato.")
            return None
        if manual_end < start_date:
            st.error("La data di fine non può precedere la data di inizio.")
            return None

        subscription_id = str(uuid4())
        st.session_state.abbonamenti.append(
            {
                "id": subscription_id,
                "cliente_id": customer_id,
                "pacchetto_id": package["id"],
                "pacchetto_nome": package["nome"],
                "data_inizio": start_date,
                "data_fine_prevista": manual_end,
                "prezzo_concordato": float(agreed_price),
                "lezioni_iniziali": int(initial_lessons),
                "tipologia_pagamento": payment_type,
                "stato": "attivo",
                "note": notes.strip(),
                "creato_il": datetime.now(),
            }
        )

        for _, row in edited_plan.iterrows():
            st.session_state.rate.append(
                {
                    "id": str(uuid4()),
                    "abbonamento_id": subscription_id,
                    "numero_rata": int(row["numero"]),
                    "data_scadenza": row["data_scadenza"],
                    "importo_previsto": float(row["importo_previsto"]),
                    "annullata": False,
                }
            )

        st.success("Abbonamento e piano rate creati.")
        return subscription_id

    return None


def page_subscriptions() -> None:
    page_header("Abbonamenti", "Gestione dei pacchetti assegnati ai clienti.")

    action = st.selectbox(
        "Operazione",
        [
            "Elenco abbonamenti",
            "Aggiungi abbonamento cliente",
            "Modifica abbonamento cliente",
            "Rinnovi e sospensioni",
        ],
        key="subscription_action",
    )

    if action == "Elenco abbonamenti":
        if not st.session_state.abbonamenti:
            st.info("Nessun abbonamento registrato.")
            return

        rows = []
        for a in st.session_state.abbonamenti:
            customer = customer_by_id(a["cliente_id"])
            rows.append(
                {
                    "Cliente": f'{customer["cognome"]} {customer["nome"]}' if customer else "—",
                    "Pacchetto": a["pacchetto_nome"],
                    "Inizio": a["data_inizio"],
                    "Fine prevista": a["data_fine_prevista"],
                    "Prezzo": a["prezzo_concordato"],
                    "Residuo": subscription_residual(a["id"]),
                    "Stato": a["stato"],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif action == "Aggiungi abbonamento cliente":
        create_subscription_ui(form_key="subscription_page")

    else:
        info_card(
            action,
            "La funzione sarà collegata allo storico, agli annullamenti e alle sospensioni tracciate.",
            gold=True,
        )


# ============================================================
# CLIENTI
# ============================================================

DOCUMENT_TYPES = [
    "Certificato medico",
    "Privacy",
    "Contratto",
    "Documento di identità",
    "Codice fiscale",
    "Altro",
]


def customer_documents_section(customer_id: str, subscription_id: str | None, key_prefix: str) -> None:
    st.subheader("Documenti")

    document_type = st.selectbox(
        "Tipo documento",
        DOCUMENT_TYPES,
        key=f"{key_prefix}_doc_type",
    )
    uploaded_file = st.file_uploader(
        "Carica documento",
        type=["pdf", "png", "jpg", "jpeg"],
        key=f"{key_prefix}_doc_file",
    )

    c1, c2 = st.columns(2)
    document_date = c1.date_input(
        "Data documento",
        value=date.today(),
        key=f"{key_prefix}_doc_date",
    )

    automatic_expiry = None
    if document_type == "Certificato medico":
        automatic_expiry = document_date + relativedelta(years=1) - relativedelta(days=1)

    expiry_enabled = c2.checkbox(
        "Documento con scadenza",
        value=document_type == "Certificato medico",
        key=f"{key_prefix}_expiry_enabled",
    )
    expiry_date = st.date_input(
        "Data scadenza",
        value=automatic_expiry or document_date,
        disabled=not expiry_enabled,
        key=f"{key_prefix}_expiry_date",
    )
    notes = st.text_area("Note documento", key=f"{key_prefix}_doc_notes")

    if st.button("Aggiungi documento", key=f"{key_prefix}_add_document"):
        add_document(
            cliente_id=customer_id,
            abbonamento_id=subscription_id if document_type == "Contratto" else None,
            tipo=document_type,
            data_documento=document_date,
            data_scadenza=expiry_date if expiry_enabled else None,
            note=notes,
            file_name=uploaded_file.name if uploaded_file else None,
        )
        st.success("Documento aggiunto alla sessione.")


def page_customers() -> None:
    page_header("Clienti", "Anagrafiche, abbonamenti, documenti e storico.")

    action = st.selectbox(
        "Operazione",
        ["Elenco clienti", "Nuovo cliente", "Modifica cliente", "Scheda cliente"],
        key="clienti_action",
    )

    if action == "Elenco clienti":
        if not st.session_state.clienti:
            st.info("Nessun cliente registrato.")
            return
        st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True, hide_index=True)

    elif action == "Nuovo cliente":
        st.subheader("1. Anagrafica")

        with st.form("new_customer_form"):
            c1, c2 = st.columns(2)
            first_name = c1.text_input("Nome *")
            last_name = c2.text_input("Cognome *")

            c3, c4, c5 = st.columns(3)
            phone = c3.text_input("Telefono")
            whatsapp = c4.text_input("WhatsApp")
            email = c5.text_input("Email")

            c6, c7 = st.columns(2)
            tax_code = c6.text_input("Codice fiscale")
            vat_number = c7.text_input("Partita IVA")

            address = st.text_input("Indirizzo")
            notes = st.text_area("Note cliente")
            save_customer = st.form_submit_button("Salva anagrafica", use_container_width=True)

        if save_customer:
            if not first_name.strip() or not last_name.strip():
                st.error("Nome e cognome sono obbligatori.")
            else:
                customer_id = str(uuid4())
                st.session_state.clienti.append(
                    {
                        "id": customer_id,
                        "nome": first_name.strip(),
                        "cognome": last_name.strip(),
                        "telefono": phone.strip(),
                        "whatsapp": whatsapp.strip(),
                        "email": email.strip(),
                        "codice_fiscale": tax_code.strip(),
                        "partita_iva": vat_number.strip(),
                        "indirizzo": address.strip(),
                        "note": notes.strip(),
                        "stato": "attivo",
                        "creato_il": datetime.now(),
                    }
                )
                st.session_state["new_customer_id"] = customer_id
                st.success("Anagrafica cliente creata.")

        customer_id = st.session_state.get("new_customer_id")
        if customer_id:
            customer = customer_by_id(customer_id)
            st.divider()
            st.subheader("2. Pacchetto e abbonamento")
            assign_now = st.checkbox(
                "Assegna subito un pacchetto al cliente",
                value=True,
                key="assign_package_now",
            )

            subscription_id = st.session_state.get("new_customer_subscription_id")
            if assign_now and not subscription_id:
                created_id = create_subscription_ui(
                    preselected_customer_id=customer_id,
                    form_key="new_customer_subscription",
                )
                if created_id:
                    st.session_state["new_customer_subscription_id"] = created_id
                    subscription_id = created_id

            st.divider()
            customer_documents_section(
                customer_id=customer_id,
                subscription_id=subscription_id,
                key_prefix="new_customer",
            )

            st.divider()
            info_card(
                "Residuo automatico",
                "Il residuo viene calcolato come prezzo concordato meno incassi validi. Non è modificabile manualmente.",
                gold=True,
            )

    else:
        info_card(
            action,
            "La scheda cliente riunirà anagrafica, abbonamenti, rate, incassi, documenti, prenotazioni, presenze e badge.",
            gold=True,
        )


# ============================================================
# CONTABILITÀ
# ============================================================

def page_accounting() -> None:
    page_header("Contabilità", "Incassi, rate, ricevute, spese e fornitori.")

    action = st.selectbox(
        "Operazione",
        [
            "Nuovo incasso",
            "Elenco incassi",
            "Rate",
            "Ricevute",
            "Nuova spesa",
            "Elenco spese",
            "Nuovo fornitore",
            "Elenco fornitori",
            "Categorie di spesa",
        ],
        key="contabilita_action",
    )

    if action == "Nuovo incasso":
        if not st.session_state.clienti:
            st.warning("Prima devi registrare almeno un cliente.")
            return

        customer_options = {
            f'{c["cognome"]} {c["nome"]}': c["id"] for c in st.session_state.clienti
        }
        selected_customer_label = st.selectbox("Cliente *", list(customer_options.keys()))
        customer_id = customer_options[selected_customer_label]

        customer_subscriptions = [
            a
            for a in st.session_state.abbonamenti
            if a["cliente_id"] == customer_id and a["stato"] != "annullato"
        ]

        subscription_id = None
        if customer_subscriptions:
            subscription_options = {
                f'{a["pacchetto_nome"]} · {a["data_inizio"]} · residuo {format_currency(subscription_residual(a["id"]))}': a["id"]
                for a in customer_subscriptions
            }
            selected_subscription_label = st.selectbox(
                "Abbonamento",
                list(subscription_options.keys()),
            )
            subscription_id = subscription_options[selected_subscription_label]
            st.metric("Residuo attuale", format_currency(subscription_residual(subscription_id)))
        else:
            st.info("Il cliente non ha abbonamenti attivi.")

        with st.form("new_receipt_form"):
            c1, c2 = st.columns(2)
            amount = c1.number_input("Importo *", min_value=0.0, step=10.0)
            receipt_date = c2.date_input("Data incasso", value=date.today())

            method = st.selectbox(
                "Metodo di pagamento",
                ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
            )
            reason = st.text_input("Causale")
            notes = st.text_area("Note")
            generate_receipt = st.checkbox("Genera ricevuta", value=True)
            submitted = st.form_submit_button("Registra incasso", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("L'importo deve essere maggiore di zero.")
            elif subscription_id and amount > subscription_residual(subscription_id) + 0.01:
                st.error("L'importo supera il residuo dell'abbonamento.")
            else:
                st.session_state.incassi.append(
                    {
                        "id": str(uuid4()),
                        "cliente_id": customer_id,
                        "abbonamento_id": subscription_id,
                        "data_incasso": receipt_date,
                        "importo": float(amount),
                        "metodo_pagamento": method,
                        "causale": reason.strip(),
                        "note": notes.strip(),
                        "genera_ricevuta": generate_receipt,
                        "stato": "valido",
                        "registrato_il": datetime.now(),
                    }
                )
                st.success("Incasso registrato.")

    elif action == "Elenco incassi":
        if not st.session_state.incassi:
            st.info("Nessun incasso registrato.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.incassi), use_container_width=True, hide_index=True)

    elif action == "Rate":
        if not st.session_state.rate:
            st.info("Nessuna rata registrata.")
        else:
            rows = []
            for rate in st.session_state.rate:
                subscription = next(
                    (a for a in st.session_state.abbonamenti if a["id"] == rate["abbonamento_id"]),
                    None,
                )
                if not subscription:
                    continue
                customer = customer_by_id(subscription["cliente_id"])
                paid = sum(
                    i["importo"]
                    for i in valid_receipts_for_subscription(subscription["id"])
                )
                rows.append(
                    {
                        "Cliente": f'{customer["cognome"]} {customer["nome"]}' if customer else "—",
                        "Pacchetto": subscription["pacchetto_nome"],
                        "N. rata": rate["numero_rata"],
                        "Scadenza": rate["data_scadenza"],
                        "Importo previsto": rate["importo_previsto"],
                        "Totale incassato abbonamento": paid,
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif action == "Nuova spesa":
        with st.form("new_expense_form"):
            c1, c2 = st.columns(2)
            expense_date = c1.date_input("Data spesa", value=date.today())
            amount = c2.number_input("Importo *", min_value=0.0, step=10.0)

            supplier_names = [f["ragione_sociale"] for f in st.session_state.fornitori]
            supplier = st.selectbox(
                "Fornitore",
                ["Nessun fornitore"] + supplier_names,
            )
            category = st.text_input("Categoria")
            description = st.text_input("Descrizione")
            method = st.selectbox(
                "Metodo di pagamento",
                ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
            )
            competence = st.text_input("Mese di competenza")
            attachment = st.file_uploader("Allegato", type=["pdf", "png", "jpg", "jpeg"])
            notes = st.text_area("Note")
            submitted = st.form_submit_button("Registra spesa", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("L'importo deve essere maggiore di zero.")
            else:
                st.session_state.spese.append(
                    {
                        "id": str(uuid4()),
                        "data_spesa": expense_date,
                        "importo": float(amount),
                        "fornitore": supplier,
                        "categoria": category.strip(),
                        "descrizione": description.strip(),
                        "metodo_pagamento": method,
                        "competenza": competence.strip(),
                        "allegato": attachment.name if attachment else None,
                        "note": notes.strip(),
                        "stato": "registrata",
                    }
                )
                st.success("Spesa registrata.")

    elif action == "Elenco spese":
        if not st.session_state.spese:
            st.info("Nessuna spesa registrata.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.spese), use_container_width=True, hide_index=True)

    elif action == "Nuovo fornitore":
        with st.form("new_supplier_form"):
            company_name = st.text_input("Ragione sociale *")
            trade_name = st.text_input("Nome commerciale")
            c1, c2 = st.columns(2)
            vat_number = c1.text_input("Partita IVA")
            tax_code = c2.text_input("Codice fiscale")
            address = st.text_input("Indirizzo")
            c3, c4, c5 = st.columns(3)
            city = c3.text_input("Città")
            postal_code = c4.text_input("CAP")
            province = c5.text_input("Provincia")
            phone = st.text_input("Telefono")
            email = st.text_input("Email")
            pec = st.text_input("PEC")
            sdi = st.text_input("Codice SDI")
            iban = st.text_input("IBAN")
            contact = st.text_input("Referente")
            notes = st.text_area("Note")
            submitted = st.form_submit_button("Salva fornitore", use_container_width=True)

        if submitted:
            if not company_name.strip():
                st.error("La ragione sociale è obbligatoria.")
            else:
                st.session_state.fornitori.append(
                    {
                        "id": str(uuid4()),
                        "ragione_sociale": company_name.strip(),
                        "nome_commerciale": trade_name.strip(),
                        "partita_iva": vat_number.strip(),
                        "codice_fiscale": tax_code.strip(),
                        "indirizzo": address.strip(),
                        "citta": city.strip(),
                        "cap": postal_code.strip(),
                        "provincia": province.strip(),
                        "telefono": phone.strip(),
                        "email": email.strip(),
                        "pec": pec.strip(),
                        "sdi": sdi.strip(),
                        "iban": iban.strip(),
                        "referente": contact.strip(),
                        "note": notes.strip(),
                        "stato": "attivo",
                    }
                )
                st.success("Fornitore registrato.")

    elif action == "Elenco fornitori":
        if not st.session_state.fornitori:
            st.info("Nessun fornitore registrato.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.fornitori), use_container_width=True, hide_index=True)

    else:
        info_card(
            action,
            "Questa sezione sarà collegata alle relative tabelle del database.",
            gold=True,
        )


# ============================================================
# ADMIN / AZIENDA
# ============================================================

def page_admin() -> None:
    page_header("Admin", "Utenti, permessi, audit, importazioni e dispositivi.")

    c1, c2 = st.columns(2)
    with c1:
        info_card("Utenti e ruoli", "Super Admin, Admin azienda, Reception, Trainer e operatori.", gold=True)
        info_card("Audit log", "Creazioni, modifiche, annullamenti e cancellazioni riservate all'Admin.")
    with c2:
        info_card("Importazioni", "Migrazione controllata di clienti, abbonamenti, incassi, badge e documenti.")
        info_card("Dispositivi", "Tornelli, lettori badge e sincronizzazioni.")


def page_company() -> None:
    page_header("Azienda", "Anagrafica aziendale, logo e configurazioni.")

    with st.form("company_form"):
        company_name = st.text_input("Ragione sociale", value=st.session_state.azienda_nome)
        vat_number = st.text_input("Partita IVA")
        tax_code = st.text_input("Codice fiscale")
        legal_address = st.text_input("Sede legale")
        operating_address = st.text_input("Sede operativa")
        phone = st.text_input("Telefono")
        email = st.text_input("Email")
        logo = st.file_uploader("Logo aziendale", type=["png", "jpg", "jpeg", "webp"])
        submitted = st.form_submit_button("Salva dati azienda", use_container_width=True)

    if submitted:
        st.session_state.azienda_nome = company_name.strip() or "Azienda"
        if logo:
            st.session_state["logo_file_name"] = logo.name
        st.success("Dati azienda aggiornati nella sessione.")

    logo_name = st.session_state.get("logo_file_name")
    if logo_name:
        st.info(f"Logo caricato: {logo_name}")
    else:
        st.caption("Nessun logo ancora caricato: viene mostrato il nome dell'azienda.")


# ============================================================
# AVVIO
# ============================================================

PAGES = {
    "Reception": page_reception,
    "Pacchetti": page_packages,
    "Abbonamenti": page_subscriptions,
    "Clienti": page_customers,
    "Contabilità": page_accounting,
    "Admin": page_admin,
    "Azienda": page_company,
}


def main() -> None:
    selected = sidebar()
    PAGES[selected]()
    st.markdown(
        f'<div class="footer">{DEVELOPER_CREDIT}</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
