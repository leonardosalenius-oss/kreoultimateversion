from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta


APP_NAME = "Gestionale"
APP_VERSION = "0.4.1"
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
            padding-top: 1.1rem;
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


def end_date_for_package(start: date, package: dict[str, Any]) -> date:
    n = package["durata_numero"]
    unit = package["durata_unita"]

    if unit == "giorni":
        return start + relativedelta(days=n) - relativedelta(days=1)
    if unit == "settimane":
        return start + relativedelta(weeks=n) - relativedelta(days=1)
    if unit == "mesi":
        return start + relativedelta(months=n) - relativedelta(days=1)
    if unit == "anni":
        return start + relativedelta(years=n) - relativedelta(days=1)
    return start


def build_installments(total: float, count: int, first_due: date, months_step: int) -> list[dict[str, Any]]:
    count = max(int(count), 1)
    base = round(total / count, 2)
    amounts = [base] * count
    amounts[-1] = round(amounts[-1] + round(total - sum(amounts), 2), 2)

    return [
        {
            "numero": i + 1,
            "data_scadenza": first_due + relativedelta(months=i * months_step),
            "importo_previsto": amounts[i],
        }
        for i in range(count)
    ]


def subscription_residual(subscription_id: str) -> float:
    subscription = next((a for a in st.session_state.abbonamenti if a["id"] == subscription_id), None)
    if not subscription:
        return 0.0
    paid = sum(
        i["importo"]
        for i in st.session_state.incassi
        if i.get("abbonamento_id") == subscription_id and i.get("stato") == "valido"
    )
    return max(subscription["prezzo_concordato"] - paid, 0.0)


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


def card(title: str, body: str, gold: bool = False) -> None:
    klass = "app-card-gold" if gold else "app-card"
    st.markdown(
        f"""
        <div class="{klass}">
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


def page_reception() -> None:
    page_header("Reception", "Agenda, clienti, incassi, presenze, badge e alert.")

    row1 = st.columns(4)
    row2 = st.columns(4)
    row3 = st.columns(4)
    row4 = st.columns(4)

    labels = [
        "Nuovo cliente", "Modifica cliente", "Registra incasso", "Accesso tornello",
        "Agenda / Calendario", "Stampa ricevuta", "Messaggio cliente", "Associa badge",
        "Sincronizza badge", "Ricalcolo settimanale", "Aggiungi prenotazione", "Conferma presenza",
        "Carica documento", "Accesso manuale", "Storico cliente", "Situazione cliente",
    ]

    for idx, label in enumerate(labels):
        target_row = [row1, row2, row3, row4][idx // 4]
        with target_row[idx % 4]:
            if label == "Nuovo cliente":
                if st.button(label, use_container_width=True):
                    st.session_state["pending_menu"] = "Clienti"
                    st.session_state["clienti_action"] = "Nuovo cliente"
                    st.rerun()
            elif label == "Registra incasso":
                if st.button(label, use_container_width=True):
                    st.session_state["pending_menu"] = "Contabilità"
                    st.session_state["contabilita_action"] = "Nuovo incasso"
                    st.rerun()
            else:
                st.button(label, use_container_width=True, disabled=True)

    st.divider()
    c1, c2 = st.columns([2.2, 1])
    with c1:
        card("Agenda settimanale", "Vista settimanale collegata a prenotazioni e staff.", gold=True)
    with c2:
        card("Alert", "Rate, certificati, residui e badge.")


def page_packages() -> None:
    page_header("Pacchetti", "Listino generale dei servizi.")

    action = st.selectbox("Operazione", ["Elenco pacchetti", "Nuovo pacchetto", "Modifica pacchetto"])
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
        card("Modifica pacchetto", "Funzione in sviluppo.", gold=True)


def new_customer_complete_flow() -> None:
    st.subheader("1. Anagrafica cliente")

    c1, c2 = st.columns(2)
    first_name = c1.text_input("Nome *", key="nc_nome")
    last_name = c2.text_input("Cognome *", key="nc_cognome")

    c3, c4, c5 = st.columns(3)
    phone = c3.text_input("Telefono", key="nc_telefono")
    whatsapp = c4.text_input("WhatsApp", key="nc_whatsapp")
    email = c5.text_input("Email", key="nc_email")

    c6, c7 = st.columns(2)
    tax_code = c6.text_input("Codice fiscale", key="nc_cf")
    vat_number = c7.text_input("Partita IVA", key="nc_piva")

    address = st.text_input("Indirizzo", key="nc_indirizzo")
    notes = st.text_area("Note cliente", key="nc_note")

    st.divider()
    st.subheader("2. Pacchetto e abbonamento")

    assign_subscription = st.checkbox(
        "Associa subito un pacchetto e crea l'abbonamento",
        value=True,
        key="nc_assign_subscription",
    )

    selected_package = None
    subscription_data: dict[str, Any] | None = None
    edited_plan = pd.DataFrame()

    if assign_subscription:
        active_packages = [p for p in st.session_state.pacchetti if p.get("attivo", True)]
        package_name = st.selectbox(
            "Pacchetto *",
            [p["nome"] for p in active_packages],
            key="nc_package",
        )
        selected_package = package_by_name(package_name)
        assert selected_package is not None

        st.caption(
            f'Prezzo standard {money(selected_package["prezzo_standard"])} · '
            f'Durata {selected_package["durata_numero"]} {selected_package["durata_unita"]} · '
            f'Lezioni {selected_package["lezioni_standard"]}'
        )

        c8, c9 = st.columns(2)
        start_date = c8.date_input("Data inizio *", value=date.today(), key="nc_start")
        auto_end = end_date_for_package(start_date, selected_package)
        end_date = c9.date_input(
            "Data fine prevista",
            value=auto_end,
            key="nc_end",
            help="Calcolata automaticamente dal pacchetto, ma modificabile.",
        )

        c10, c11 = st.columns(2)
        agreed_price = c10.number_input(
            "Prezzo concordato *",
            min_value=0.0,
            step=10.0,
            value=float(selected_package["prezzo_standard"]),
            key="nc_price",
        )
        initial_lessons = c11.number_input(
            "Lezioni iniziali",
            min_value=0,
            step=1,
            value=int(selected_package["lezioni_standard"]),
            key="nc_lessons",
        )

        payment_type = st.selectbox(
            "Tipologia abbonamento / pagamento",
            ["Soluzione unica", "Mensile", "Trimestrale", "Semestrale", "Personalizzato"],
            key="nc_payment_type",
        )

        if payment_type == "Soluzione unica":
            installment_count = 1
            months_step = 0
        else:
            installment_count = st.number_input(
                "Numero rate",
                min_value=1,
                step=1,
                value=1,
                key="nc_installment_count",
            )
            months_step = {
                "Mensile": 1,
                "Trimestrale": 3,
                "Semestrale": 6,
                "Personalizzato": 1,
            }[payment_type]

        first_due = st.date_input("Data prima scadenza", value=start_date, key="nc_first_due")
        suggested_plan = build_installments(float(agreed_price), int(installment_count), first_due, months_step)

        st.caption("Piano rate proposto e modificabile")
        edited_plan = st.data_editor(
            pd.DataFrame(suggested_plan),
            use_container_width=True,
            hide_index=True,
            key="nc_rate_editor",
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
            key="nc_initial_payment",
        )
        payment_method = st.selectbox(
            "Metodo pagamento iniziale",
            ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
            key="nc_initial_method",
        )
        st.metric("Residuo dopo incasso iniziale", money(float(agreed_price) - float(initial_payment)))

        subscription_data = {
            "package": selected_package,
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

    document_rows: list[dict[str, Any]] = []

    for doc_type, default_expiry in [
        ("Certificato medico", True),
        ("Privacy", False),
        ("Contratto", False),
    ]:
        with st.expander(doc_type, expanded=(doc_type == "Certificato medico")):
            present = st.checkbox(f"{doc_type} presente", key=f"doc_present_{doc_type}")
            uploaded = st.file_uploader(
                f"Carica {doc_type.lower()}",
                type=["pdf", "png", "jpg", "jpeg"],
                key=f"doc_file_{doc_type}",
                disabled=not present,
            )
            document_date = st.date_input(
                "Data documento",
                value=date.today(),
                key=f"doc_date_{doc_type}",
                disabled=not present,
            )

            automatic_expiry = (
                document_date + relativedelta(years=1) - relativedelta(days=1)
                if default_expiry
                else document_date
            )
            has_expiry = st.checkbox(
                "Documento con scadenza",
                value=default_expiry,
                key=f"doc_has_expiry_{doc_type}",
                disabled=not present,
            )
            expiry_date = st.date_input(
                "Data scadenza",
                value=automatic_expiry,
                key=f"doc_expiry_{doc_type}",
                disabled=(not present or not has_expiry),
            )
            document_rows.append(
                {
                    "tipo": doc_type,
                    "presente": present,
                    "file_name": uploaded.name if uploaded else None,
                    "data_documento": document_date if present else None,
                    "data_scadenza": expiry_date if present and has_expiry else None,
                }
            )

    with st.expander("Altro documento"):
        other_present = st.checkbox("Aggiungi altro documento", key="doc_other_present")
        other_name = st.text_input("Nome documento", key="doc_other_name", disabled=not other_present)
        other_file = st.file_uploader(
            "Carica altro documento",
            type=["pdf", "png", "jpg", "jpeg"],
            key="doc_other_file",
            disabled=not other_present,
        )
        other_date = st.date_input(
            "Data documento",
            value=date.today(),
            key="doc_other_date",
            disabled=not other_present,
        )
        other_has_expiry = st.checkbox(
            "Documento con scadenza",
            key="doc_other_has_expiry",
            disabled=not other_present,
        )
        other_expiry = st.date_input(
            "Data scadenza",
            value=date.today(),
            key="doc_other_expiry",
            disabled=(not other_present or not other_has_expiry),
        )

        if other_present and other_name.strip():
            document_rows.append(
                {
                    "tipo": other_name.strip(),
                    "presente": True,
                    "file_name": other_file.name if other_file else None,
                    "data_documento": other_date,
                    "data_scadenza": other_expiry if other_has_expiry else None,
                }
            )

    st.divider()

    if st.button("Salva cliente completo", use_container_width=True):
        if not first_name.strip() or not last_name.strip():
            st.error("Nome e cognome sono obbligatori.")
            return

        if assign_subscription and subscription_data:
            if subscription_data["agreed_price"] <= 0:
                st.error("Il prezzo concordato deve essere maggiore di zero.")
                return
            if abs(subscription_data["difference"]) > 0.01:
                st.error("La somma delle rate deve coincidere con il prezzo concordato.")
                return
            if subscription_data["end_date"] < subscription_data["start_date"]:
                st.error("La data fine non può precedere la data inizio.")
                return

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

        subscription_id = None

        if assign_subscription and subscription_data:
            subscription_id = str(uuid4())
            package = subscription_data["package"]

            st.session_state.abbonamenti.append(
                {
                    "id": subscription_id,
                    "cliente_id": customer_id,
                    "pacchetto_id": package["id"],
                    "pacchetto_nome": package["nome"],
                    "data_inizio": subscription_data["start_date"],
                    "data_fine_prevista": subscription_data["end_date"],
                    "prezzo_concordato": subscription_data["agreed_price"],
                    "lezioni_iniziali": subscription_data["initial_lessons"],
                    "tipologia_pagamento": subscription_data["payment_type"],
                    "stato": "attivo",
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
                        "registrato_il": datetime.now(),
                    }
                )

        for doc in document_rows:
            if not doc["presente"]:
                continue

            st.session_state.documenti.append(
                {
                    "id": str(uuid4()),
                    "cliente_id": customer_id,
                    "abbonamento_id": subscription_id if doc["tipo"] == "Contratto" else None,
                    "tipo": doc["tipo"],
                    "file_name": doc["file_name"],
                    "data_documento": doc["data_documento"],
                    "data_scadenza": doc["data_scadenza"],
                    "stato": "valido" if doc["file_name"] else "da verificare",
                    "creato_il": datetime.now(),
                }
            )

        st.success("Cliente, abbonamento, rate, incasso iniziale e documenti salvati.")
        st.balloons()


def page_customers() -> None:
    page_header("Clienti", "Anagrafiche, abbonamenti, documenti e storico.")

    action = st.selectbox(
        "Operazione",
        ["Elenco clienti", "Nuovo cliente", "Modifica cliente", "Scheda cliente"],
        key="clienti_action",
    )

    if action == "Nuovo cliente":
        new_customer_complete_flow()
    elif action == "Elenco clienti":
        st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True, hide_index=True)
    else:
        card(action, "Funzione in sviluppo.", gold=True)


def page_subscriptions() -> None:
    page_header("Abbonamenti", "Pacchetti assegnati ai clienti.")

    rows = []
    for sub in st.session_state.abbonamenti:
        customer = customer_by_id(sub["cliente_id"])
        rows.append(
            {
                "Cliente": f'{customer["cognome"]} {customer["nome"]}' if customer else "—",
                "Pacchetto": sub["pacchetto_nome"],
                "Inizio": sub["data_inizio"],
                "Fine prevista": sub["data_fine_prevista"],
                "Prezzo": sub["prezzo_concordato"],
                "Residuo": subscription_residual(sub["id"]),
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
    elif action == "Nuovo fornitore":
        with st.form("supplier"):
            name = st.text_input("Ragione sociale *")
            vat = st.text_input("Partita IVA")
            email = st.text_input("Email")
            submitted = st.form_submit_button("Salva fornitore", use_container_width=True)

        if submitted:
            st.session_state.fornitori.append(
                {"id": str(uuid4()), "ragione_sociale": name.strip(), "partita_iva": vat.strip(), "email": email.strip()}
            )
            st.success("Fornitore salvato.")
    else:
        card(action, "Funzione in sviluppo.", gold=True)


def page_admin() -> None:
    page_header("Admin", "Utenti, permessi, audit e dispositivi.")
    card("Admin", "Sezione in sviluppo.", gold=True)


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
