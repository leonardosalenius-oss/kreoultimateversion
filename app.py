from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta


APP_NAME = "Gestionale"
APP_VERSION = "0.5.0"
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
    surface_soft: str = "#14171A"
    text: str = "#F6F2E8"
    text_secondary: str = "#AAA59A"
    gold: str = "#BFA15A"
    gold_hover: str = "#D4B96F"
    border: str = "#34383D"
    success: str = "#3E8E68"
    warning: str = "#D69B32"
    danger: str = "#C85C5C"
    neutral: str = "#6F7680"


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
            --surface-soft: {theme.surface_soft};
            --text: {theme.text};
            --text-secondary: {theme.text_secondary};
            --gold: {theme.gold};
            --gold-hover: {theme.gold_hover};
            --border: {theme.border};
            --success: {theme.success};
            --warning: {theme.warning};
            --danger: {theme.danger};
            --neutral: {theme.neutral};
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
            padding-top: 1rem;
            padding-bottom: 2rem;
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

        .client-card {{
            background: linear-gradient(180deg, var(--surface) 0%, var(--surface-soft) 100%);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 14px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.14);
        }}

        .client-card:hover {{
            border-color: var(--gold);
        }}

        .client-grid {{
            display: grid;
            grid-template-columns: 1.35fr 1.15fr 1fr 1fr 1fr 0.95fr;
            gap: 16px;
            align-items: start;
        }}

        .client-name {{
            font-size: 1.06rem;
            font-weight: 800;
            margin-bottom: 4px;
        }}

        .client-label {{
            color: var(--text-secondary);
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 4px;
        }}

        .client-value {{
            color: var(--text);
            font-size: 0.95rem;
            font-weight: 700;
        }}

        .client-subvalue {{
            color: var(--text-secondary);
            font-size: 0.82rem;
            margin-top: 3px;
        }}

        .status-pill {{
            display: inline-block;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.76rem;
            font-weight: 800;
            border: 1px solid transparent;
            margin-top: 3px;
        }}

        .status-success {{
            color: #A8E3C4;
            background: rgba(62, 142, 104, 0.16);
            border-color: rgba(62, 142, 104, 0.45);
        }}

        .status-warning {{
            color: #FFD48A;
            background: rgba(214, 155, 50, 0.16);
            border-color: rgba(214, 155, 50, 0.45);
        }}

        .status-danger {{
            color: #FFB3B3;
            background: rgba(200, 92, 92, 0.16);
            border-color: rgba(200, 92, 92, 0.45);
        }}

        .status-neutral {{
            color: #D3D6DB;
            background: rgba(111, 118, 128, 0.16);
            border-color: rgba(111, 118, 128, 0.45);
        }}

        .summary-bar {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 14px;
        }}

        div.stButton > button,
        div.stFormSubmitButton > button,
        div.stDownloadButton > button {{
            background: var(--surface) !important;
            color: var(--text) !important;
            border: 1px solid var(--gold) !important;
            border-radius: 8px !important;
            font-weight: 650 !important;
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
            border-color: var(--gold-hover) !important;
            color: #111111 !important;
        }}

        div.stButton > button:hover *,
        div.stFormSubmitButton > button:hover *,
        div.stDownloadButton > button:hover * {{
            color: #111111 !important;
        }}

        .footer {{
            color: var(--text-secondary);
            text-align: center;
            margin-top: 2rem;
            font-size: 0.82rem;
        }}

        @media (max-width: 1200px) {{
            .client-grid {{
                grid-template-columns: 1fr 1fr 1fr;
            }}
        }}

        @media (max-width: 800px) {{
            .client-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_theme(THEME)


def init_state() -> None:
    defaults: dict[str, Any] = {
        "azienda_nome": "KREO",
        "utente_nome": "Pentti Salenius",
        "utente_ruolo": "Super Admin",
        "menu": "Reception",
        "pending_menu": None,
        "pacchetti": [
            {
                "id": "pkg-luxury",
                "nome": "Luxury",
                "prezzo_standard": 500.0,
                "durata_numero": 1,
                "durata_unita": "mesi",
                "lezioni_standard": 12,
                "attivo": True,
            },
            {
                "id": "pkg-gold",
                "nome": "Gold",
                "prezzo_standard": 750.0,
                "durata_numero": 1,
                "durata_unita": "mesi",
                "lezioni_standard": 12,
                "attivo": True,
            },
            {
                "id": "pkg-vip",
                "nome": "VIP",
                "prezzo_standard": 900.0,
                "durata_numero": 1,
                "durata_unita": "mesi",
                "lezioni_standard": 12,
                "attivo": True,
            },
        ],
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


init_state()


def money(value: float) -> str:
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def package_by_name(name: str) -> dict[str, Any] | None:
    return next((p for p in st.session_state.pacchetti if p["nome"] == name), None)


def customer_by_id(customer_id: str) -> dict[str, Any] | None:
    return next((c for c in st.session_state.clienti if c["id"] == customer_id), None)


def subscriptions_for_customer(customer_id: str) -> list[dict[str, Any]]:
    return [
        a for a in st.session_state.abbonamenti
        if a["cliente_id"] == customer_id and a.get("stato") != "annullato"
    ]


def active_subscription_for_customer(customer_id: str) -> dict[str, Any] | None:
    subscriptions = subscriptions_for_customer(customer_id)
    if not subscriptions:
        return None

    subscriptions = sorted(
        subscriptions,
        key=lambda item: item.get("data_inizio", date.min),
        reverse=True,
    )
    return subscriptions[0]


def end_date_for_package(start: date, package: dict[str, Any]) -> date:
    number = package["durata_numero"]
    unit = package["durata_unita"]

    if unit == "giorni":
        return start + relativedelta(days=number) - relativedelta(days=1)
    if unit == "settimane":
        return start + relativedelta(weeks=number) - relativedelta(days=1)
    if unit == "mesi":
        return start + relativedelta(months=number) - relativedelta(days=1)
    if unit == "anni":
        return start + relativedelta(years=number) - relativedelta(days=1)

    return start


def build_installments(total: float, count: int, first_due: date, months_step: int) -> list[dict[str, Any]]:
    count = max(int(count), 1)
    base = round(total / count, 2)
    amounts = [base] * count
    amounts[-1] = round(amounts[-1] + round(total - sum(amounts), 2), 2)

    return [
        {
            "numero": index + 1,
            "data_scadenza": first_due + relativedelta(months=index * months_step),
            "importo_previsto": amounts[index],
        }
        for index in range(count)
    ]


def valid_receipts_for_subscription(subscription_id: str) -> list[dict[str, Any]]:
    return [
        item for item in st.session_state.incassi
        if item.get("abbonamento_id") == subscription_id and item.get("stato") == "valido"
    ]


def subscription_paid(subscription_id: str) -> float:
    return sum(item["importo"] for item in valid_receipts_for_subscription(subscription_id))


def subscription_residual(subscription_id: str) -> float:
    subscription = next(
        (item for item in st.session_state.abbonamenti if item["id"] == subscription_id),
        None,
    )
    if not subscription:
        return 0.0
    return max(subscription["prezzo_concordato"] - subscription_paid(subscription_id), 0.0)


def open_installments(subscription_id: str) -> list[dict[str, Any]]:
    installments = [
        item for item in st.session_state.rate
        if item["abbonamento_id"] == subscription_id and not item.get("annullata", False)
    ]

    paid_total = subscription_paid(subscription_id)
    remaining_paid = paid_total
    result = []

    for installment in sorted(installments, key=lambda item: item["data_scadenza"]):
        covered = min(remaining_paid, installment["importo_previsto"])
        remaining_paid -= covered
        residual = round(installment["importo_previsto"] - covered, 2)

        if residual > 0:
            result.append({**installment, "residuo_rata": residual})

    return result


def next_installment(subscription_id: str) -> dict[str, Any] | None:
    open_items = open_installments(subscription_id)
    return open_items[0] if open_items else None


def certificate_for_customer(customer_id: str) -> dict[str, Any] | None:
    certificates = [
        item for item in st.session_state.documenti
        if item["cliente_id"] == customer_id
        and item["tipo"] == "Certificato medico"
        and item.get("stato") != "annullato"
    ]

    if not certificates:
        return None

    certificates = sorted(
        certificates,
        key=lambda item: item.get("data_scadenza") or date.min,
        reverse=True,
    )
    return certificates[0]


def certificate_status(customer_id: str) -> tuple[str, str]:
    certificate = certificate_for_customer(customer_id)

    if not certificate:
        return "Mancante", "danger"

    expiry = certificate.get("data_scadenza")
    if not expiry:
        return "Da verificare", "neutral"

    days = (expiry - date.today()).days

    if days < 0:
        return f"Scaduto il {expiry.strftime('%d/%m/%Y')}", "danger"
    if days <= 30:
        return f"In scadenza · {expiry.strftime('%d/%m/%Y')}", "warning"

    return f"Valido fino al {expiry.strftime('%d/%m/%Y')}", "success"


def customer_overall_status(customer_id: str) -> tuple[str, str]:
    subscription = active_subscription_for_customer(customer_id)
    cert_label, cert_tone = certificate_status(customer_id)

    if not subscription:
        return "Senza abbonamento", "neutral"

    if subscription["data_fine_prevista"] < date.today():
        return "Abbonamento scaduto", "danger"

    overdue = [
        item for item in open_installments(subscription["id"])
        if item["data_scadenza"] < date.today()
    ]

    if overdue:
        return "Rata scaduta", "danger"

    if cert_tone == "danger":
        return "Certificato irregolare", "danger"

    days_to_expiry = (subscription["data_fine_prevista"] - date.today()).days
    if days_to_expiry <= 15 or cert_tone == "warning":
        return "Attenzione", "warning"

    return "Regolare", "success"


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

        if st.session_state.get("pending_menu"):
            st.session_state["menu"] = st.session_state["pending_menu"]
            st.session_state["pending_menu"] = None

        selected = st.radio(
            "Menu",
            ["Reception", "Pacchetti", "Abbonamenti", "Clienti", "Contabilità", "Admin", "Azienda"],
            key="menu",
            label_visibility="collapsed",
        )

        st.divider()
        st.write(st.session_state.utente_nome)
        st.caption(st.session_state.utente_ruolo)
        st.caption(f"Versione {APP_VERSION}")

    return selected


def goto(page: str, action_key: str | None = None, action_value: str | None = None) -> None:
    st.session_state["pending_menu"] = page
    if action_key and action_value:
        st.session_state[action_key] = action_value
    st.rerun()


def page_reception() -> None:
    page_header("Reception", "Agenda, clienti, incassi, presenze, badge e alert.")

    rows = [
        ["Nuovo cliente", "Modifica cliente", "Registra incasso", "Accesso tornello"],
        ["Agenda / Calendario", "Stampa ricevuta", "Messaggio cliente", "Associa badge"],
        ["Sincronizza badge", "Ricalcolo settimanale", "Aggiungi prenotazione", "Conferma presenza"],
        ["Carica documento", "Accesso manuale", "Storico cliente", "Situazione cliente"],
    ]

    for row in rows:
        columns = st.columns(4)
        for column, label in zip(columns, row):
            with column:
                if label == "Nuovo cliente":
                    if st.button(label, use_container_width=True):
                        goto("Clienti", "clienti_action", "Nuovo cliente")
                elif label == "Registra incasso":
                    if st.button(label, use_container_width=True):
                        goto("Contabilità", "contabilita_action", "Nuovo incasso")
                elif label == "Situazione cliente":
                    if st.button(label, use_container_width=True):
                        goto("Clienti", "clienti_action", "Elenco clienti")
                else:
                    st.button(label, use_container_width=True, disabled=True)


def page_packages() -> None:
    page_header("Pacchetti", "Listino generale dei servizi.")

    action = st.selectbox(
        "Operazione",
        ["Elenco pacchetti", "Nuovo pacchetto", "Modifica pacchetto"],
    )

    if action == "Elenco pacchetti":
        st.dataframe(pd.DataFrame(st.session_state.pacchetti), use_container_width=True, hide_index=True)

    elif action == "Nuovo pacchetto":
        with st.form("new_package"):
            name = st.text_input("Nome pacchetto *")
            c1, c2, c3 = st.columns(3)
            price = c1.number_input("Prezzo standard", min_value=0.0, step=10.0)
            duration = c2.number_input("Durata", min_value=1, step=1)
            unit = c3.selectbox("Unità", ["giorni", "settimane", "mesi", "anni"])
            lessons = st.number_input("Lezioni standard", min_value=0, step=1)
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
                        "durata_numero": int(duration),
                        "durata_unita": unit,
                        "lezioni_standard": int(lessons),
                        "attivo": True,
                    }
                )
                st.success("Pacchetto salvato.")

    else:
        st.info("Funzione in sviluppo.")


def save_complete_customer(
    customer_data: dict[str, Any],
    subscription_data: dict[str, Any] | None,
    installment_plan: pd.DataFrame,
    documents: list[dict[str, Any]],
) -> None:
    customer_id = str(uuid4())
    customer_data["id"] = customer_id
    customer_data["stato"] = "attivo"
    customer_data["creato_il"] = datetime.now()
    st.session_state.clienti.append(customer_data)

    subscription_id = None

    if subscription_data:
        subscription_id = str(uuid4())
        st.session_state.abbonamenti.append(
            {
                "id": subscription_id,
                "cliente_id": customer_id,
                "pacchetto_id": subscription_data["package"]["id"],
                "pacchetto_nome": subscription_data["package"]["nome"],
                "data_inizio": subscription_data["start_date"],
                "data_fine_prevista": subscription_data["end_date"],
                "prezzo_concordato": subscription_data["agreed_price"],
                "lezioni_iniziali": subscription_data["initial_lessons"],
                "tipologia_pagamento": subscription_data["payment_type"],
                "stato": "attivo",
                "creato_il": datetime.now(),
            }
        )

        for _, row in installment_plan.iterrows():
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

        if subscription_data["initial_payment"] > 0:
            st.session_state.incassi.append(
                {
                    "id": str(uuid4()),
                    "cliente_id": customer_id,
                    "abbonamento_id": subscription_id,
                    "data_incasso": date.today(),
                    "importo": subscription_data["initial_payment"],
                    "metodo_pagamento": subscription_data["payment_method"],
                    "stato": "valido",
                }
            )

    for document in documents:
        if not document["presente"]:
            continue

        st.session_state.documenti.append(
            {
                "id": str(uuid4()),
                "cliente_id": customer_id,
                "abbonamento_id": subscription_id if document["tipo"] == "Contratto" else None,
                "tipo": document["tipo"],
                "file_name": document["file_name"],
                "data_documento": document["data_documento"],
                "data_scadenza": document["data_scadenza"],
                "stato": "valido" if document["file_name"] else "da verificare",
            }
        )


def new_customer_flow() -> None:
    st.subheader("1. Anagrafica")

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

    st.divider()
    st.subheader("2. Pacchetto e abbonamento")

    assign_subscription = st.checkbox(
        "Associa subito un pacchetto e crea l'abbonamento",
        value=True,
    )

    subscription_data = None
    edited_plan = pd.DataFrame()

    if assign_subscription:
        active_packages = [item for item in st.session_state.pacchetti if item.get("attivo", True)]
        package_name = st.selectbox("Pacchetto *", [item["nome"] for item in active_packages])
        package = package_by_name(package_name)
        assert package is not None

        c8, c9 = st.columns(2)
        start_date = c8.date_input("Data inizio", value=date.today())
        automatic_end = end_date_for_package(start_date, package)
        end_date = c9.date_input("Data fine prevista", value=automatic_end)

        c10, c11 = st.columns(2)
        agreed_price = c10.number_input(
            "Prezzo concordato",
            min_value=0.0,
            step=10.0,
            value=float(package["prezzo_standard"]),
        )
        initial_lessons = c11.number_input(
            "Lezioni iniziali",
            min_value=0,
            step=1,
            value=int(package["lezioni_standard"]),
        )

        payment_type = st.selectbox(
            "Tipologia abbonamento / pagamento",
            ["Soluzione unica", "Mensile", "Trimestrale", "Semestrale", "Personalizzato"],
        )

        if payment_type == "Soluzione unica":
            installment_count = 1
            months_step = 0
        else:
            installment_count = st.number_input("Numero rate", min_value=1, step=1, value=1)
            months_step = {
                "Mensile": 1,
                "Trimestrale": 3,
                "Semestrale": 6,
                "Personalizzato": 1,
            }[payment_type]

        first_due = st.date_input("Data prima scadenza", value=start_date)
        suggested_plan = build_installments(
            float(agreed_price),
            int(installment_count),
            first_due,
            months_step,
        )

        edited_plan = st.data_editor(
            pd.DataFrame(suggested_plan),
            use_container_width=True,
            hide_index=True,
            column_config={
                "numero": st.column_config.NumberColumn("N. rata", min_value=1, step=1),
                "data_scadenza": st.column_config.DateColumn("Scadenza"),
                "importo_previsto": st.column_config.NumberColumn("Importo previsto", format="€ %.2f"),
            },
        )

        plan_total = float(edited_plan["importo_previsto"].sum()) if not edited_plan.empty else 0.0
        difference = round(float(agreed_price) - plan_total, 2)

        m1, m2, m3 = st.columns(3)
        m1.metric("Prezzo concordato", money(float(agreed_price)))
        m2.metric("Totale rate", money(plan_total))
        m3.metric("Differenza", money(difference))

        initial_payment = st.number_input(
            "Incasso iniziale",
            min_value=0.0,
            max_value=float(agreed_price),
            step=10.0,
            value=0.0,
        )
        payment_method = st.selectbox(
            "Metodo pagamento iniziale",
            ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
        )

        subscription_data = {
            "package": package,
            "start_date": start_date,
            "end_date": end_date,
            "agreed_price": float(agreed_price),
            "initial_lessons": int(initial_lessons),
            "payment_type": payment_type,
            "initial_payment": float(initial_payment),
            "payment_method": payment_method,
            "difference": difference,
        }

    st.divider()
    st.subheader("3. Documenti")

    documents = []

    for document_type, default_expiry in [
        ("Certificato medico", True),
        ("Privacy", False),
        ("Contratto", False),
    ]:
        with st.expander(document_type, expanded=(document_type == "Certificato medico")):
            present = st.checkbox(f"{document_type} presente", key=f"{document_type}_present")
            file = st.file_uploader(
                f"Carica {document_type.lower()}",
                type=["pdf", "png", "jpg", "jpeg"],
                key=f"{document_type}_file",
                disabled=not present,
            )
            document_date = st.date_input(
                "Data documento",
                value=date.today(),
                key=f"{document_type}_date",
                disabled=not present,
            )
            expiry_date = None

            if default_expiry:
                expiry_date = document_date + relativedelta(years=1) - relativedelta(days=1)

            has_expiry = st.checkbox(
                "Documento con scadenza",
                value=default_expiry,
                key=f"{document_type}_has_expiry",
                disabled=not present,
            )

            final_expiry = st.date_input(
                "Data scadenza",
                value=expiry_date or document_date,
                key=f"{document_type}_expiry",
                disabled=(not present or not has_expiry),
            )

            documents.append(
                {
                    "tipo": document_type,
                    "presente": present,
                    "file_name": file.name if file else None,
                    "data_documento": document_date if present else None,
                    "data_scadenza": final_expiry if present and has_expiry else None,
                }
            )

    if st.button("Salva cliente completo", use_container_width=True):
        if not first_name.strip() or not last_name.strip():
            st.error("Nome e cognome sono obbligatori.")
            return

        if subscription_data:
            if subscription_data["agreed_price"] <= 0:
                st.error("Il prezzo concordato deve essere maggiore di zero.")
                return
            if abs(subscription_data["difference"]) > 0.01:
                st.error("La somma delle rate deve coincidere con il prezzo concordato.")
                return

        customer_data = {
            "nome": first_name.strip(),
            "cognome": last_name.strip(),
            "telefono": phone.strip(),
            "whatsapp": whatsapp.strip(),
            "email": email.strip(),
            "codice_fiscale": tax_code.strip(),
            "partita_iva": vat_number.strip(),
            "indirizzo": address.strip(),
            "note": notes.strip(),
        }

        save_complete_customer(
            customer_data=customer_data,
            subscription_data=subscription_data,
            installment_plan=edited_plan,
            documents=documents,
        )

        st.success("Cliente completo salvato.")
        st.balloons()


def render_client_cards() -> None:
    if not st.session_state.clienti:
        st.info("Nessun cliente registrato.")
        return

    st.subheader("Vista clienti")

    c1, c2, c3, c4 = st.columns([1.8, 1, 1, 1])
    search = c1.text_input("Cerca", placeholder="Nome, telefono, WhatsApp o badge")
    package_filter = c2.selectbox(
        "Pacchetto",
        ["Tutti"] + sorted({a["pacchetto_nome"] for a in st.session_state.abbonamenti}),
    )
    certificate_filter = c3.selectbox(
        "Certificato",
        ["Tutti", "Valido", "In scadenza", "Scaduto", "Mancante", "Da verificare"],
    )
    status_filter = c4.selectbox(
        "Stato",
        ["Tutti", "Regolare", "Attenzione", "Rata scaduta", "Abbonamento scaduto", "Senza abbonamento", "Certificato irregolare"],
    )

    quick = st.radio(
        "Filtro rapido",
        ["Tutti", "Regolari", "Residuo aperto", "Rate scadute", "Certificati irregolari", "Abbonamenti in scadenza"],
        horizontal=True,
    )

    filtered = []

    for customer in st.session_state.clienti:
        subscription = active_subscription_for_customer(customer["id"])
        certificate_label, certificate_tone = certificate_status(customer["id"])
        overall_label, overall_tone = customer_overall_status(customer["id"])

        searchable = " ".join(
            [
                customer.get("nome", ""),
                customer.get("cognome", ""),
                customer.get("telefono", ""),
                customer.get("whatsapp", ""),
                customer.get("badge", ""),
            ]
        ).lower()

        if search and search.lower() not in searchable:
            continue

        if package_filter != "Tutti":
            if not subscription or subscription["pacchetto_nome"] != package_filter:
                continue

        if certificate_filter != "Tutti":
            if certificate_filter == "Valido" and not certificate_label.startswith("Valido"):
                continue
            if certificate_filter == "In scadenza" and not certificate_label.startswith("In scadenza"):
                continue
            if certificate_filter == "Scaduto" and not certificate_label.startswith("Scaduto"):
                continue
            if certificate_filter == "Mancante" and certificate_label != "Mancante":
                continue
            if certificate_filter == "Da verificare" and certificate_label != "Da verificare":
                continue

        if status_filter != "Tutti" and overall_label != status_filter:
            continue

        if quick == "Regolari" and overall_label != "Regolare":
            continue

        if quick == "Residuo aperto":
            if not subscription or subscription_residual(subscription["id"]) <= 0:
                continue

        if quick == "Rate scadute":
            if overall_label != "Rata scaduta":
                continue

        if quick == "Certificati irregolari":
            if certificate_tone != "danger":
                continue

        if quick == "Abbonamenti in scadenza":
            if not subscription:
                continue
            days = (subscription["data_fine_prevista"] - date.today()).days
            if not (0 <= days <= 15):
                continue

        filtered.append((customer, subscription, certificate_label, certificate_tone, overall_label, overall_tone))

    total_residual = sum(
        subscription_residual(subscription["id"])
        for _, subscription, *_ in filtered
        if subscription
    )

    st.markdown(
        f"""
        <div class="summary-bar">
            <strong>{len(filtered)}</strong> clienti visualizzati
            &nbsp;&nbsp;•&nbsp;&nbsp;
            Residuo complessivo: <strong>{money(total_residual)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for customer, subscription, cert_label, cert_tone, overall_label, overall_tone in filtered:
        if subscription:
            residual = subscription_residual(subscription["id"])
            paid = subscription_paid(subscription["id"])
            next_rate = next_installment(subscription["id"])
            expiry = subscription["data_fine_prevista"]
            days_to_expiry = (expiry - date.today()).days

            if days_to_expiry < 0:
                expiry_sub = f"Scaduto da {abs(days_to_expiry)} giorni"
            elif days_to_expiry == 0:
                expiry_sub = "Scade oggi"
            else:
                expiry_sub = f"Scade tra {days_to_expiry} giorni"

            next_rate_date = next_rate["data_scadenza"].strftime("%d/%m/%Y") if next_rate else "—"
            next_rate_value = money(next_rate["residuo_rata"]) if next_rate else "Nessuna rata aperta"
            package_name = subscription["pacchetto_nome"]
            payment_type = subscription["tipologia_pagamento"]
            initial_value = money(subscription["prezzo_concordato"])
            residual_value = money(residual)
            lessons = subscription.get("lezioni_iniziali", 0)
        else:
            package_name = "Nessun pacchetto"
            payment_type = "—"
            expiry = None
            expiry_sub = "—"
            next_rate_date = "—"
            next_rate_value = "—"
            initial_value = money(0)
            residual_value = money(0)
            paid = 0.0
            lessons = 0

        status_class = f"status-{overall_tone}"
        cert_class = f"status-{cert_tone}"

        st.markdown(
            f"""
            <div class="client-card">
                <div class="client-grid">
                    <div>
                        <div class="client-label">Cliente</div>
                        <div class="client-name">{customer["cognome"]} {customer["nome"]}</div>
                        <div class="client-subvalue">
                            {customer.get("telefono") or "Telefono non inserito"}
                            {" · " + customer.get("whatsapp") if customer.get("whatsapp") else ""}
                        </div>
                        <span class="status-pill {status_class}">{overall_label}</span>
                    </div>

                    <div>
                        <div class="client-label">Abbonamento</div>
                        <div class="client-value">{package_name}</div>
                        <div class="client-subvalue">{payment_type} · {lessons} lezioni iniziali</div>
                    </div>

                    <div>
                        <div class="client-label">Scadenza abbonamento</div>
                        <div class="client-value">{expiry.strftime("%d/%m/%Y") if expiry else "—"}</div>
                        <div class="client-subvalue">{expiry_sub}</div>
                    </div>

                    <div>
                        <div class="client-label">Situazione economica</div>
                        <div class="client-value">Iniziale {initial_value}</div>
                        <div class="client-subvalue">Pagato {money(paid)}</div>
                        <div class="client-subvalue">Residuo <strong>{residual_value}</strong></div>
                    </div>

                    <div>
                        <div class="client-label">Prossima rata</div>
                        <div class="client-value">{next_rate_date}</div>
                        <div class="client-subvalue">{next_rate_value}</div>
                    </div>

                    <div>
                        <div class="client-label">Certificato</div>
                        <span class="status-pill {cert_class}">{cert_label}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        action_cols = st.columns([1, 1, 1, 1, 4])
        with action_cols[0]:
            st.button("Apri", key=f"open_{customer['id']}", use_container_width=True, disabled=True)
        with action_cols[1]:
            st.button("Modifica", key=f"edit_{customer['id']}", use_container_width=True, disabled=True)
        with action_cols[2]:
            st.button("Incasso", key=f"cash_{customer['id']}", use_container_width=True, disabled=True)
        with action_cols[3]:
            st.button("Documenti", key=f"docs_{customer['id']}", use_container_width=True, disabled=True)


def page_customers() -> None:
    page_header("Clienti", "Anagrafiche, abbonamenti, documenti e storico.")

    action = st.selectbox(
        "Operazione",
        ["Elenco clienti", "Nuovo cliente", "Modifica cliente", "Scheda cliente"],
        key="clienti_action",
    )

    if action == "Nuovo cliente":
        new_customer_flow()
    elif action == "Elenco clienti":
        render_client_cards()
    else:
        st.info("Funzione in sviluppo.")


def page_subscriptions() -> None:
    page_header("Abbonamenti", "Pacchetti assegnati ai clienti.")

    rows = []
    for subscription in st.session_state.abbonamenti:
        customer = customer_by_id(subscription["cliente_id"])
        rows.append(
            {
                "Cliente": f'{customer["cognome"]} {customer["nome"]}' if customer else "—",
                "Pacchetto": subscription["pacchetto_nome"],
                "Tipologia": subscription["tipologia_pagamento"],
                "Inizio": subscription["data_inizio"],
                "Fine prevista": subscription["data_fine_prevista"],
                "Importo iniziale": subscription["prezzo_concordato"],
                "Residuo": subscription_residual(subscription["id"]),
            }
        )

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun abbonamento registrato.")


def page_accounting() -> None:
    page_header("Contabilità", "Incassi, rate, ricevute, spese e fornitori.")

    action = st.selectbox(
        "Operazione",
        ["Nuovo incasso", "Elenco incassi", "Rate", "Ricevute", "Nuova spesa", "Elenco spese", "Nuovo fornitore", "Elenco fornitori"],
        key="contabilita_action",
    )

    if action == "Elenco incassi":
        st.dataframe(pd.DataFrame(st.session_state.incassi), use_container_width=True, hide_index=True)
    elif action == "Rate":
        st.dataframe(pd.DataFrame(st.session_state.rate), use_container_width=True, hide_index=True)
    else:
        st.info("Funzione in sviluppo.")


def page_admin() -> None:
    page_header("Admin", "Utenti, permessi, audit e dispositivi.")
    st.info("Sezione in sviluppo.")


def page_company() -> None:
    page_header("Azienda", "Anagrafica e logo.")
    with st.form("company"):
        company_name = st.text_input("Ragione sociale", value=st.session_state.azienda_nome)
        logo = st.file_uploader("Logo", type=["png", "jpg", "jpeg", "webp"])
        submitted = st.form_submit_button("Salva", use_container_width=True)

    if submitted:
        st.session_state.azienda_nome = company_name.strip() or "Azienda"
        st.session_state.logo_name = logo.name if logo else None
        st.success("Dati aggiornati.")


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
    st.markdown(f'<div class="footer">{DEVELOPER_CREDIT}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
