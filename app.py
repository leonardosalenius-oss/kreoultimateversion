from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta


APP_NAME = "Gestionale"
APP_VERSION = "0.3.0"
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
            min-height: 2.8rem;
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
            border-color: var(--gold_hover) !important;
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
            background: var(--surface_alt) !important;
            border-color: var(--border) !important;
            color: var(--text) !important;
        }}

        .footer {{
            color: var(--text_secondary);
            text-align: center;
            margin-top: 2rem;
            font-size: 0.82rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_theme(THEME)


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


def format_currency(value: float) -> str:
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def package_by_name(name: str) -> dict[str, Any] | None:
    return next((p for p in st.session_state.pacchetti if p["nome"] == name), None)


def customer_by_id(customer_id: str) -> dict[str, Any] | None:
    return next((c for c in st.session_state.clienti if c["id"] == customer_id), None)


def calculate_end_date(start: date, number: int, unit: str) -> date:
    if unit == "giorni":
        return start + relativedelta(days=number) - relativedelta(days=1)
    if unit == "settimane":
        return start + relativedelta(weeks=number) - relativedelta(days=1)
    if unit == "mesi":
        return start + relativedelta(months=number) - relativedelta(days=1)
    if unit == "anni":
        return start + relativedelta(years=number) - relativedelta(days=1)
    return start


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
    amounts[-1] = round(amounts[-1] + round(total - sum(amounts), 2), 2)

    return [
        {
            "numero": idx + 1,
            "data_scadenza": first_due_date + relativedelta(months=frequency_months * idx),
            "importo_previsto": amount,
        }
        for idx, amount in enumerate(amounts)
    ]


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


def go_to(page: str, action_key: str | None = None, action_value: str | None = None) -> None:
    st.session_state.menu = page
    if action_key and action_value:
        st.session_state[action_key] = action_value
    st.rerun()


def page_reception() -> None:
    page_header("Reception", "Agenda, clienti, incassi, presenze, badge e alert.")

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

    row1 = st.columns(4)
    with row1[0]:
        if st.button("Nuovo cliente", use_container_width=True):
            go_to("Clienti", "clienti_action", "Nuovo cliente")
    with row1[1]:
        if st.button("Modifica cliente", use_container_width=True):
            go_to("Clienti", "clienti_action", "Modifica cliente")
    with row1[2]:
        if st.button("Registra incasso", use_container_width=True):
            go_to("Contabilità", "contabilita_action", "Nuovo incasso")
    with row1[3]:
        st.button("Accesso tornello", use_container_width=True, disabled=True)

    row2 = st.columns(4)
    with row2[0]:
        st.button("Agenda / Calendario", use_container_width=True, disabled=True)
    with row2[1]:
        st.button("Stampa ricevuta", use_container_width=True, disabled=True)
    with row2[2]:
        st.button("Messaggio cliente", use_container_width=True, disabled=True)
    with row2[3]:
        st.button("Associa badge", use_container_width=True, disabled=True)

    row3 = st.columns(4)
    with row3[0]:
        st.button("Sincronizza badge", use_container_width=True, disabled=True)
    with row3[1]:
        st.button("Ricalcolo settimanale", use_container_width=True, disabled=True)
    with row3[2]:
        st.button("Aggiungi prenotazione", use_container_width=True, disabled=True)
    with row3[3]:
        st.button("Conferma presenza", use_container_width=True, disabled=True)

    row4 = st.columns(4)
    with row4[0]:
        st.button("Carica documento", use_container_width=True, disabled=True)
    with row4[1]:
        st.button("Accesso manuale", use_container_width=True, disabled=True)
    with row4[2]:
        st.button("Storico cliente", use_container_width=True, disabled=True)
    with row4[3]:
        st.button("Situazione cliente", use_container_width=True, disabled=True)

    st.divider()

    col1, col2 = st.columns([2.2, 1])
    with col1:
        info_card(
            "Agenda settimanale",
            "Vista sette giorni dalle 07:00 alle 21:00, collegata a prenotazioni e disponibilità dello staff.",
            gold=True,
        )
    with col2:
        info_card(
            "Alert operativi",
            "Rate scadute, certificati mancanti o in scadenza, badge da associare e anomalie.",
        )
        info_card(
            "Incassi di oggi",
            format_currency(today_receipts),
        )
        info_card(
            "Accessi di oggi",
            "—",
        )


def page_packages() -> None:
    page_header("Pacchetti", "Listino generale dei servizi venduti dall'azienda.")

    action = st.selectbox(
        "Operazione",
        ["Elenco pacchetti", "Nuovo pacchetto", "Modifica pacchetto esistente"],
    )

    if action == "Elenco pacchetti":
        st.dataframe(pd.DataFrame(st.session_state.pacchetti), use_container_width=True, hide_index=True)
        return

    if action == "Nuovo pacchetto":
        with st.form("new_package_form"):
            name = st.text_input("Nome pacchetto *")
            c1, c2, c3 = st.columns(3)
            price = c1.number_input("Prezzo standard", min_value=0.0, step=10.0)
            duration_number = c2.number_input("Durata", min_value=1, step=1)
            duration_unit = c3.selectbox("Unità durata", ["giorni", "settimane", "mesi", "anni"])

            c4, c5, c6 = st.columns(3)
            lessons = c4.number_input("Lezioni standard", min_value=0, step=1)
            weekly_frequency = c5.number_input("Frequenza settimanale", min_value=0, step=1)
            participants = c6.number_input("Partecipanti massimi", min_value=1, step=1)
            active = st.checkbox("Pacchetto attivo", value=True)
            submitted = st.form_submit_button("Salva pacchetto", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Il nome del pacchetto è obbligatorio.")
            else:
                st.session_state.pacchetti.append(
                    {
                        "id": str(uuid4()),
                        "nome": name.strip(),
                        "prezzo_standard": float(price),
                        "durata_numero": int(duration_number),
                        "durata_unita": duration_unit,
                        "lezioni_standard": int(lessons),
                        "frequenza_settimanale": int(weekly_frequency),
                        "partecipanti_massimi": int(participants),
                        "attivo": active,
                    }
                )
                st.success("Pacchetto registrato.")
        return

    names = [p["nome"] for p in st.session_state.pacchetti]
    selected_name = st.selectbox("Pacchetto da modificare", names)
    package = package_by_name(selected_name)
    if package:
        st.write(package)


def create_subscription_ui(preselected_customer_id: str | None = None, form_key: str = "subscription") -> str | None:
    if not st.session_state.clienti:
        st.warning("Prima devi registrare almeno un cliente.")
        return None

    customer_options = {
        f'{c["cognome"]} {c["nome"]}': c["id"] for c in st.session_state.clienti
    }
    customer_labels = list(customer_options.keys())

    default_index = 0
    if preselected_customer_id:
        for idx, label in enumerate(customer_labels):
            if customer_options[label] == preselected_customer_id:
                default_index = idx
                break

    customer_label = st.selectbox(
        "Cliente *",
        customer_labels,
        index=default_index,
        key=f"{form_key}_customer",
    )
    customer_id = customer_options[customer_label]

    active_packages = [p for p in st.session_state.pacchetti if p.get("attivo", True)]
    package_name = st.selectbox(
        "Pacchetto *",
        [p["nome"] for p in active_packages],
        key=f"{form_key}_package",
    )
    package = package_by_name(package_name)
    assert package is not None

    c1, c2 = st.columns(2)
    start_date = c1.date_input("Data inizio *", value=date.today(), key=f"{form_key}_start")
    end_date = calculate_end_date(
        start_date,
        package["durata_numero"],
        package["durata_unita"],
    )
    expected_end = c2.date_input(
        "Data fine prevista",
        value=end_date,
        key=f"{form_key}_end",
        help="Calcolata automaticamente dal pacchetto e modificabile.",
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

    payment_type = st.selectbox(
        "Tipologia pagamento",
        ["Soluzione unica", "Mensile", "Trimestrale", "Semestrale", "Personalizzato"],
        key=f"{form_key}_payment_type",
    )

    if payment_type == "Soluzione unica":
        installment_count = 1
        months = 0
    else:
        installment_count = st.number_input(
            "Numero rate",
            min_value=1,
            step=1,
            value=1,
            key=f"{form_key}_installment_count",
        )
        months = {"Mensile": 1, "Trimestrale": 3, "Semestrale": 6}.get(payment_type, 1)

    first_due = st.date_input(
        "Data prima scadenza",
        value=start_date,
        key=f"{form_key}_first_due",
    )

    plan = build_installment_plan(float(agreed_price), int(installment_count), first_due, months)
    edited = st.data_editor(
        pd.DataFrame(plan),
        use_container_width=True,
        hide_index=True,
        key=f"{form_key}_plan",
    )

    total = float(edited["importo_previsto"].sum()) if not edited.empty else 0.0
    st.metric("Totale rate", format_currency(total))

    if st.button("Crea abbonamento", use_container_width=True, key=f"{form_key}_save"):
        if abs(total - float(agreed_price)) > 0.01:
            st.error("La somma delle rate deve coincidere con il prezzo concordato.")
            return None

        subscription_id = str(uuid4())
        st.session_state.abbonamenti.append(
            {
                "id": subscription_id,
                "cliente_id": customer_id,
                "pacchetto_id": package["id"],
                "pacchetto_nome": package["nome"],
                "data_inizio": start_date,
                "data_fine_prevista": expected_end,
                "prezzo_concordato": float(agreed_price),
                "lezioni_iniziali": int(initial_lessons),
                "tipologia_pagamento": payment_type,
                "stato": "attivo",
            }
        )

        for _, row in edited.iterrows():
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

        st.success("Abbonamento creato.")
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
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    elif action == "Aggiungi abbonamento cliente":
        create_subscription_ui()
    else:
        info_card(action, "Funzione prevista nella struttura definitiva.", gold=True)


def page_customers() -> None:
    page_header("Clienti", "Anagrafiche, abbonamenti, documenti e storico.")

    action = st.selectbox(
        "Operazione",
        ["Elenco clienti", "Nuovo cliente", "Modifica cliente", "Scheda cliente"],
        key="clienti_action",
    )

    if action == "Elenco clienti":
        st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True, hide_index=True)
        return

    if action == "Nuovo cliente":
        with st.form("new_customer_form"):
            c1, c2 = st.columns(2)
            first_name = c1.text_input("Nome *")
            last_name = c2.text_input("Cognome *")
            phone = st.text_input("Telefono")
            email = st.text_input("Email")
            submitted = st.form_submit_button("Salva anagrafica", use_container_width=True)

        if submitted:
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
                        "email": email.strip(),
                        "stato": "attivo",
                    }
                )
                st.session_state["new_customer_id"] = customer_id
                st.success("Cliente registrato.")

        customer_id = st.session_state.get("new_customer_id")
        if customer_id:
            st.divider()
            st.subheader("Pacchetto e abbonamento")
            create_subscription_ui(preselected_customer_id=customer_id, form_key="customer_subscription")

            st.divider()
            st.subheader("Documenti")
            doc_type = st.selectbox(
                "Tipo documento",
                [
                    "Certificato medico",
                    "Privacy",
                    "Contratto",
                    "Documento di identità",
                    "Codice fiscale",
                    "Altro",
                ],
            )
            doc_file = st.file_uploader("Carica documento", type=["pdf", "png", "jpg", "jpeg"])
            doc_date = st.date_input("Data documento", value=date.today())
            expiry = (
                doc_date + relativedelta(years=1) - relativedelta(days=1)
                if doc_type == "Certificato medico"
                else doc_date
            )
            has_expiry = st.checkbox(
                "Documento con scadenza",
                value=doc_type == "Certificato medico",
            )
            expiry_date = st.date_input("Data scadenza", value=expiry, disabled=not has_expiry)

            if st.button("Aggiungi documento", use_container_width=True):
                st.session_state.documenti.append(
                    {
                        "id": str(uuid4()),
                        "cliente_id": customer_id,
                        "tipo": doc_type,
                        "file_name": doc_file.name if doc_file else None,
                        "data_documento": doc_date,
                        "data_scadenza": expiry_date if has_expiry else None,
                    }
                )
                st.success("Documento aggiunto.")
        return

    info_card(action, "Funzione prevista nella struttura definitiva.", gold=True)


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
        customer_label = st.selectbox("Cliente *", list(customer_options.keys()))
        customer_id = customer_options[customer_label]

        subscriptions = [a for a in st.session_state.abbonamenti if a["cliente_id"] == customer_id]
        subscription_id = None
        if subscriptions:
            options = {
                f'{a["pacchetto_nome"]} · residuo {format_currency(subscription_residual(a["id"]))}': a["id"]
                for a in subscriptions
            }
            label = st.selectbox("Abbonamento", list(options.keys()))
            subscription_id = options[label]
            st.metric("Residuo", format_currency(subscription_residual(subscription_id)))

        with st.form("new_receipt_form"):
            amount = st.number_input("Importo *", min_value=0.0, step=10.0)
            payment_date = st.date_input("Data incasso", value=date.today())
            method = st.selectbox("Metodo", ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"])
            submitted = st.form_submit_button("Registra incasso", use_container_width=True)

        if submitted:
            st.session_state.incassi.append(
                {
                    "id": str(uuid4()),
                    "cliente_id": customer_id,
                    "abbonamento_id": subscription_id,
                    "data_incasso": payment_date,
                    "importo": float(amount),
                    "metodo_pagamento": method,
                    "stato": "valido",
                }
            )
            st.success("Incasso registrato.")
        return

    if action == "Nuovo fornitore":
        with st.form("new_supplier_form"):
            company_name = st.text_input("Ragione sociale *")
            vat_number = st.text_input("Partita IVA")
            email = st.text_input("Email")
            phone = st.text_input("Telefono")
            submitted = st.form_submit_button("Salva fornitore", use_container_width=True)

        if submitted:
            st.session_state.fornitori.append(
                {
                    "id": str(uuid4()),
                    "ragione_sociale": company_name.strip(),
                    "partita_iva": vat_number.strip(),
                    "email": email.strip(),
                    "telefono": phone.strip(),
                }
            )
            st.success("Fornitore registrato.")
        return

    if action == "Nuova spesa":
        with st.form("new_expense_form"):
            expense_date = st.date_input("Data spesa", value=date.today())
            amount = st.number_input("Importo *", min_value=0.0, step=10.0)
            supplier = st.selectbox(
                "Fornitore",
                ["Nessun fornitore"] + [f["ragione_sociale"] for f in st.session_state.fornitori],
            )
            description = st.text_input("Descrizione")
            submitted = st.form_submit_button("Registra spesa", use_container_width=True)

        if submitted:
            st.session_state.spese.append(
                {
                    "id": str(uuid4()),
                    "data_spesa": expense_date,
                    "importo": float(amount),
                    "fornitore": supplier,
                    "descrizione": description.strip(),
                    "stato": "registrata",
                }
            )
            st.success("Spesa registrata.")
        return

    info_card(action, "Funzione prevista nella struttura definitiva.", gold=True)


def page_admin() -> None:
    page_header("Admin", "Utenti, permessi, audit, importazioni e dispositivi.")
    info_card("Utenti e ruoli", "Gestione accessi e permessi.", gold=True)
    info_card("Audit log", "Tracciamento modifiche, annullamenti e cancellazioni Admin.")
    info_card("Dispositivi", "Tornelli e lettori badge.")


def page_company() -> None:
    page_header("Azienda", "Anagrafica aziendale, logo e configurazioni.")

    with st.form("company_form"):
        name = st.text_input("Ragione sociale", value=st.session_state.azienda_nome)
        logo = st.file_uploader("Logo aziendale", type=["png", "jpg", "jpeg", "webp"])
        submitted = st.form_submit_button("Salva dati azienda", use_container_width=True)

    if submitted:
        st.session_state.azienda_nome = name.strip() or "Azienda"
        if logo:
            st.session_state.logo_file_name = logo.name
        st.success("Dati azienda aggiornati.")

    if st.session_state.get("logo_file_name"):
        st.info(f'Logo caricato: {st.session_state.logo_file_name}')
    else:
        st.caption("Nessun logo ancora caricato: viene mostrato il nome dell'azienda.")


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
