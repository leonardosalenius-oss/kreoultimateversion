from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta


APP_VERSION = "0.6.0"
DEVELOPER_CREDIT = "Developed by Pentti Salenius © 2026"

st.set_page_config(
    page_title="Gestionale",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# TEMA
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --bg: #0D0F11;
        --sidebar: #08090A;
        --surface: #171A1E;
        --surface2: #20242A;
        --text: #F6F2E8;
        --muted: #AAA59A;
        --gold: #BFA15A;
        --gold2: #D4B96F;
        --border: #34383D;
        --success: #3E8E68;
        --warning: #D69B32;
        --danger: #C85C5C;
    }

    .stApp {
        background: var(--bg);
        color: var(--text);
    }

    [data-testid="stSidebar"] {
        background: var(--sidebar);
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] * {
        color: var(--text) !important;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, h4, h5, h6, p, span, label {
        color: var(--text);
    }

    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px 14px;
    }

    div.stButton > button,
    div.stFormSubmitButton > button,
    div.stDownloadButton > button {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--gold) !important;
        border-radius: 8px !important;
        min-height: 2.7rem;
        font-weight: 650 !important;
    }

    div.stButton > button *,
    div.stFormSubmitButton > button *,
    div.stDownloadButton > button * {
        color: var(--text) !important;
    }

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover,
    div.stDownloadButton > button:hover {
        background: var(--gold) !important;
        border-color: var(--gold2) !important;
        color: #111 !important;
    }

    div.stButton > button:hover *,
    div.stFormSubmitButton > button:hover *,
    div.stDownloadButton > button:hover * {
        color: #111 !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--border) !important;
        background: linear-gradient(180deg, #171A1E 0%, #14171A 100%);
        border-radius: 14px;
    }

    .small-muted {
        color: var(--muted);
        font-size: 0.82rem;
    }

    .footer {
        text-align: center;
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# STATO
# ============================================================

def init_state() -> None:
    defaults: dict[str, Any] = {
        "azienda_nome": "KREO",
        "utente_nome": "Pentti Salenius",
        "utente_ruolo": "Super Admin",
        "menu": "Reception",
        "pending_menu": None,
        "pending_actions": {},
        "flash_message": None,
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


# ============================================================
# UTILITÀ
# ============================================================

def money(value: float) -> str:
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def package_by_name(name: str) -> dict[str, Any] | None:
    return next((p for p in st.session_state.pacchetti if p["nome"] == name), None)


def customer_by_id(customer_id: str) -> dict[str, Any] | None:
    return next((c for c in st.session_state.clienti if c["id"] == customer_id), None)


def active_subscription(customer_id: str) -> dict[str, Any] | None:
    items = [
        a for a in st.session_state.abbonamenti
        if a["cliente_id"] == customer_id and a.get("stato") != "annullato"
    ]
    if not items:
        return None
    return sorted(items, key=lambda x: x["data_inizio"], reverse=True)[0]


def subscription_receipts(subscription_id: str) -> list[dict[str, Any]]:
    return [
        i for i in st.session_state.incassi
        if i.get("abbonamento_id") == subscription_id and i.get("stato") == "valido"
    ]


def subscription_paid(subscription_id: str) -> float:
    return sum(i["importo"] for i in subscription_receipts(subscription_id))


def subscription_residual(subscription_id: str) -> float:
    sub = next((a for a in st.session_state.abbonamenti if a["id"] == subscription_id), None)
    if not sub:
        return 0.0
    return max(sub["prezzo_concordato"] - subscription_paid(subscription_id), 0.0)


def calculate_end(start: date, package: dict[str, Any]) -> date:
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


def build_installments(total: float, count: int, first_due: date, month_step: int) -> list[dict[str, Any]]:
    count = max(int(count), 1)
    base = round(total / count, 2)
    amounts = [base] * count
    amounts[-1] = round(amounts[-1] + round(total - sum(amounts), 2), 2)

    return [
        {
            "numero": idx + 1,
            "data_scadenza": first_due + relativedelta(months=idx * month_step),
            "importo_previsto": amounts[idx],
        }
        for idx in range(count)
    ]


def open_installments(subscription_id: str) -> list[dict[str, Any]]:
    installments = sorted(
        [
            r for r in st.session_state.rate
            if r["abbonamento_id"] == subscription_id and not r.get("annullata", False)
        ],
        key=lambda x: x["data_scadenza"],
    )

    paid_left = subscription_paid(subscription_id)
    result: list[dict[str, Any]] = []

    for installment in installments:
        covered = min(paid_left, installment["importo_previsto"])
        paid_left -= covered
        residual = round(installment["importo_previsto"] - covered, 2)
        if residual > 0:
            result.append({**installment, "residuo_rata": residual})

    return result


def next_installment(subscription_id: str) -> dict[str, Any] | None:
    items = open_installments(subscription_id)
    return items[0] if items else None


def certificate_status(customer_id: str) -> tuple[str, str]:
    docs = [
        d for d in st.session_state.documenti
        if d["cliente_id"] == customer_id
        and d["tipo"] == "Certificato medico"
        and d.get("stato") != "annullato"
    ]

    if not docs:
        return "Mancante", "🔴"

    doc = sorted(docs, key=lambda x: x.get("data_scadenza") or date.min, reverse=True)[0]
    expiry = doc.get("data_scadenza")

    if not expiry:
        return "Da verificare", "⚪"

    days = (expiry - date.today()).days
    if days < 0:
        return f"Scaduto {expiry.strftime('%d/%m/%Y')}", "🔴"
    if days <= 30:
        return f"In scadenza {expiry.strftime('%d/%m/%Y')}", "🟠"
    return f"Valido fino al {expiry.strftime('%d/%m/%Y')}", "🟢"


def overall_status(customer_id: str) -> tuple[str, str]:
    sub = active_subscription(customer_id)
    cert_text, cert_icon = certificate_status(customer_id)

    if not sub:
        return "Senza abbonamento", "⚪"
    if sub["data_fine_prevista"] < date.today():
        return "Abbonamento scaduto", "🔴"
    if any(r["data_scadenza"] < date.today() for r in open_installments(sub["id"])):
        return "Rata scaduta", "🔴"
    if cert_icon == "🔴":
        return "Certificato irregolare", "🔴"
    if (sub["data_fine_prevista"] - date.today()).days <= 15 or cert_icon == "🟠":
        return "Attenzione", "🟠"
    return "Regolare", "🟢"


def request_navigation(page: str, action_key: str | None = None, action_value: str | None = None) -> None:
    st.session_state.pending_menu = page
    if action_key and action_value:
        st.session_state.pending_actions[action_key] = action_value
    st.rerun()


def apply_pending_action(key: str, default: str) -> None:
    if key in st.session_state.pending_actions:
        st.session_state[key] = st.session_state.pending_actions.pop(key)
    elif key not in st.session_state:
        st.session_state[key] = default


def set_flash(message: str) -> None:
    st.session_state.flash_message = message


def show_flash() -> None:
    message = st.session_state.get("flash_message")
    if message:
        st.info(message)
        st.session_state.flash_message = None


# ============================================================
# LAYOUT
# ============================================================

def header(title: str, subtitle: str) -> None:
    left, right = st.columns([5, 1])
    with left:
        st.title(title)
        st.caption(subtitle)
    with right:
        st.markdown(f"**{st.session_state.azienda_nome}**")


def sidebar() -> str:
    with st.sidebar:
        st.header(st.session_state.azienda_nome)
        st.caption("Gestionale aziendale")

        if st.session_state.pending_menu:
            st.session_state.menu = st.session_state.pending_menu
            st.session_state.pending_menu = None

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


# ============================================================
# RECEPTION
# ============================================================

def page_reception() -> None:
    header("Reception", "Agenda, clienti, incassi, presenze, badge e alert.")
    show_flash()

    actions = [
        ("Nuovo cliente", "Clienti", "clienti_action", "Nuovo cliente"),
        ("Modifica cliente", "Clienti", "clienti_action", "Modifica cliente"),
        ("Registra incasso", "Contabilità", "contabilita_action", "Nuovo incasso"),
        ("Accesso tornello", None, None, None),
        ("Agenda / Calendario", None, None, None),
        ("Stampa ricevuta", "Contabilità", "contabilita_action", "Ricevute"),
        ("Messaggio cliente", None, None, None),
        ("Associa badge", None, None, None),
        ("Sincronizza badge", None, None, None),
        ("Ricalcolo settimanale", None, None, None),
        ("Aggiungi prenotazione", None, None, None),
        ("Conferma presenza", None, None, None),
        ("Carica documento", "Clienti", "clienti_action", "Scheda cliente"),
        ("Accesso manuale", None, None, None),
        ("Storico cliente", "Clienti", "clienti_action", "Scheda cliente"),
        ("Situazione cliente", "Clienti", "clienti_action", "Elenco clienti"),
    ]

    for start in range(0, len(actions), 4):
        cols = st.columns(4)
        for col, action in zip(cols, actions[start:start + 4]):
            label, page, action_key, action_value = action
            with col:
                if st.button(label, key=f"reception_{label}", use_container_width=True):
                    if page:
                        request_navigation(page, action_key, action_value)
                    else:
                        set_flash(f"'{label}' è previsto nella struttura ed entrerà nella prossima fase.")
                        st.rerun()

    st.divider()
    a, b = st.columns([2, 1])
    with a:
        with st.container(border=True):
            st.subheader("Agenda settimanale")
            st.caption("La vista agenda verrà collegata a prenotazioni e disponibilità dello staff.")
    with b:
        with st.container(border=True):
            st.subheader("Alert")
            st.write("Rate scadute")
            st.write("Certificati mancanti o in scadenza")
            st.write("Badge da associare")


# ============================================================
# PACCHETTI
# ============================================================

def page_packages() -> None:
    header("Pacchetti", "Listino generale dei servizi.")

    action = st.selectbox(
        "Operazione",
        ["Elenco pacchetti", "Nuovo pacchetto", "Modifica pacchetto"],
    )

    if action == "Elenco pacchetti":
        st.dataframe(pd.DataFrame(st.session_state.pacchetti), use_container_width=True, hide_index=True)

    elif action == "Nuovo pacchetto":
        with st.form("package_form"):
            name = st.text_input("Nome pacchetto *")
            c1, c2, c3 = st.columns(3)
            price = c1.number_input("Prezzo standard", min_value=0.0, step=10.0)
            duration = c2.number_input("Durata", min_value=1, step=1)
            unit = c3.selectbox("Unità", ["giorni", "settimane", "mesi", "anni"])
            lessons = st.number_input("Lezioni standard", min_value=0, step=1)
            submitted = st.form_submit_button("Salva pacchetto", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Il nome è obbligatorio.")
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
        st.info("Modifica pacchetto prevista nella prossima fase.")


# ============================================================
# NUOVO CLIENTE
# ============================================================

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
    notes = st.text_area("Note")

    st.divider()
    st.subheader("2. Pacchetto e abbonamento")

    assign_sub = st.checkbox("Associa subito un pacchetto", value=True)

    subscription_data = None
    edited_plan = pd.DataFrame()

    if assign_sub:
        active_packages = [p for p in st.session_state.pacchetti if p.get("attivo", True)]
        package_name = st.selectbox("Pacchetto *", [p["nome"] for p in active_packages])
        package = package_by_name(package_name)
        assert package is not None

        c8, c9 = st.columns(2)
        start_date = c8.date_input("Data inizio", value=date.today())
        auto_end = calculate_end(start_date, package)
        end_date = c9.date_input("Data fine prevista", value=auto_end)

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
            count = 1
            month_step = 0
        else:
            count = st.number_input("Numero rate", min_value=1, step=1, value=1)
            month_step = {
                "Mensile": 1,
                "Trimestrale": 3,
                "Semestrale": 6,
                "Personalizzato": 1,
            }[payment_type]

        first_due = st.date_input("Data prima scadenza", value=start_date)

        plan = build_installments(float(agreed_price), int(count), first_due, month_step)
        edited_plan = st.data_editor(
            pd.DataFrame(plan),
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

        # Aggiornamento live: ogni modifica al campo genera un rerun di Streamlit.
        live_residual = max(float(agreed_price) - float(initial_payment), 0.0)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Prezzo concordato", money(float(agreed_price)))
        m2.metric("Totale rate", money(plan_total))
        m3.metric("Incasso iniziale", money(float(initial_payment)))
        m4.metric("Residuo aggiornato", money(live_residual))

        if abs(difference) > 0.01:
            st.warning(f"Differenza piano rate: {money(difference)}")

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

    documents: list[dict[str, Any]] = []

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
            doc_date = st.date_input(
                "Data documento",
                value=date.today(),
                key=f"doc_date_{doc_type}",
                disabled=not present,
            )
            has_expiry = st.checkbox(
                "Documento con scadenza",
                value=default_expiry,
                key=f"doc_expiry_flag_{doc_type}",
                disabled=not present,
            )
            default_date = (
                doc_date + relativedelta(years=1) - relativedelta(days=1)
                if default_expiry
                else doc_date
            )
            expiry = st.date_input(
                "Data scadenza",
                value=default_date,
                key=f"doc_expiry_{doc_type}",
                disabled=(not present or not has_expiry),
            )

            documents.append(
                {
                    "tipo": doc_type,
                    "presente": present,
                    "file_name": uploaded.name if uploaded else None,
                    "data_documento": doc_date if present else None,
                    "data_scadenza": expiry if present and has_expiry else None,
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

        if subscription_data:
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
                    }
                )

        for doc in documents:
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
                }
            )

        st.success("Cliente, abbonamento, rate, incasso e documenti salvati.")
        st.balloons()


# ============================================================
# ELENCO CLIENTI
# ============================================================

def client_list() -> None:
    if not st.session_state.clienti:
        st.info("Nessun cliente registrato.")
        return

    c1, c2, c3, c4 = st.columns([1.7, 1, 1, 1])
    search = c1.text_input("Cerca", placeholder="Nome, telefono o WhatsApp")
    packages = sorted({a["pacchetto_nome"] for a in st.session_state.abbonamenti})
    package_filter = c2.selectbox("Pacchetto", ["Tutti"] + packages)
    cert_filter = c3.selectbox(
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

    filtered: list[dict[str, Any]] = []

    for customer in st.session_state.clienti:
        sub = active_subscription(customer["id"])
        cert_text, cert_icon = certificate_status(customer["id"])
        state_text, state_icon = overall_status(customer["id"])

        searchable = " ".join(
            [
                customer.get("nome", ""),
                customer.get("cognome", ""),
                customer.get("telefono", ""),
                customer.get("whatsapp", ""),
            ]
        ).lower()

        if search and search.lower() not in searchable:
            continue
        if package_filter != "Tutti" and (not sub or sub["pacchetto_nome"] != package_filter):
            continue
        if cert_filter != "Tutti":
            if cert_filter == "Valido" and not cert_text.startswith("Valido"):
                continue
            if cert_filter == "In scadenza" and not cert_text.startswith("In scadenza"):
                continue
            if cert_filter == "Scaduto" and not cert_text.startswith("Scaduto"):
                continue
            if cert_filter in {"Mancante", "Da verificare"} and cert_text != cert_filter:
                continue
        if status_filter != "Tutti" and state_text != status_filter:
            continue

        if quick == "Regolari" and state_text != "Regolare":
            continue
        if quick == "Residuo aperto" and (not sub or subscription_residual(sub["id"]) <= 0):
            continue
        if quick == "Rate scadute" and state_text != "Rata scaduta":
            continue
        if quick == "Certificati irregolari" and cert_icon != "🔴":
            continue
        if quick == "Abbonamenti in scadenza":
            if not sub:
                continue
            days = (sub["data_fine_prevista"] - date.today()).days
            if not 0 <= days <= 15:
                continue

        filtered.append(
            {
                "customer": customer,
                "subscription": sub,
                "certificate_text": cert_text,
                "certificate_icon": cert_icon,
                "state_text": state_text,
                "state_icon": state_icon,
            }
        )

    total_residual = sum(
        subscription_residual(item["subscription"]["id"])
        for item in filtered
        if item["subscription"]
    )

    st.info(f"{len(filtered)} clienti visualizzati · Residuo complessivo {money(total_residual)}")

    for item in filtered:
        customer = item["customer"]
        sub = item["subscription"]

        with st.container(border=True):
            top_left, top_right = st.columns([4, 1])

            with top_left:
                st.subheader(f'{customer["cognome"]} {customer["nome"]}')
                contacts = " · ".join(
                    x for x in [customer.get("telefono"), customer.get("whatsapp")] if x
                )
                st.caption(contacts or "Contatti non inseriti")

            with top_right:
                st.markdown(f'### {item["state_icon"]} {item["state_text"]}')

            if sub:
                residual = subscription_residual(sub["id"])
                paid = subscription_paid(sub["id"])
                next_rate = next_installment(sub["id"])
                expiry_days = (sub["data_fine_prevista"] - date.today()).days

                c1, c2, c3, c4, c5 = st.columns(5)

                with c1:
                    st.caption("ABBONAMENTO")
                    st.write(f'**{sub["pacchetto_nome"]}**')
                    st.caption(sub["tipologia_pagamento"])

                with c2:
                    st.caption("SCADENZA")
                    st.write(f'**{sub["data_fine_prevista"].strftime("%d/%m/%Y")}**')
                    if expiry_days < 0:
                        st.caption(f"Scaduto da {abs(expiry_days)} giorni")
                    elif expiry_days == 0:
                        st.caption("Scade oggi")
                    else:
                        st.caption(f"Scade tra {expiry_days} giorni")

                with c3:
                    st.caption("SITUAZIONE ECONOMICA")
                    st.write(f'Iniziale **{money(sub["prezzo_concordato"])}**')
                    st.caption(f'Pagato {money(paid)}')
                    st.write(f'Residuo **{money(residual)}**')

                with c4:
                    st.caption("PROSSIMA RATA")
                    if next_rate:
                        st.write(f'**{next_rate["data_scadenza"].strftime("%d/%m/%Y")}**')
                        st.caption(money(next_rate["residuo_rata"]))
                    else:
                        st.write("**Nessuna rata aperta**")

                with c5:
                    st.caption("CERTIFICATO")
                    st.write(f'**{item["certificate_icon"]} {item["certificate_text"]}**')
            else:
                st.warning("Cliente senza abbonamento.")

            actions = st.columns(4)
            with actions[0]:
                if st.button("Apri scheda", key=f'open_{customer["id"]}', use_container_width=True):
                    st.session_state.selected_customer_id = customer["id"]
                    st.session_state.clienti_action = "Scheda cliente"
                    st.rerun()
            with actions[1]:
                if st.button("Modifica", key=f'edit_{customer["id"]}', use_container_width=True):
                    st.session_state.selected_customer_id = customer["id"]
                    st.session_state.clienti_action = "Modifica cliente"
                    st.rerun()
            with actions[2]:
                if st.button("Registra incasso", key=f'cash_{customer["id"]}', use_container_width=True):
                    st.session_state.selected_customer_id = customer["id"]
                    request_navigation("Contabilità", "contabilita_action", "Nuovo incasso")
            with actions[3]:
                if st.button("Documenti", key=f'docs_{customer["id"]}', use_container_width=True):
                    st.session_state.selected_customer_id = customer["id"]
                    st.session_state.clienti_action = "Scheda cliente"
                    st.rerun()


# ============================================================
# MODIFICA / SCHEDA CLIENTE
# ============================================================

def modify_customer() -> None:
    if not st.session_state.clienti:
        st.info("Nessun cliente registrato.")
        return

    labels = {
        f'{c["cognome"]} {c["nome"]}': c["id"] for c in st.session_state.clienti
    }

    selected_id = st.session_state.get("selected_customer_id")
    selected_label = next((k for k, v in labels.items() if v == selected_id), list(labels.keys())[0])

    label = st.selectbox(
        "Cliente da modificare",
        list(labels.keys()),
        index=list(labels.keys()).index(selected_label),
    )
    customer = customer_by_id(labels[label])
    assert customer is not None

    with st.form("modify_customer_form"):
        c1, c2 = st.columns(2)
        first_name = c1.text_input("Nome", value=customer["nome"])
        last_name = c2.text_input("Cognome", value=customer["cognome"])
        phone = st.text_input("Telefono", value=customer.get("telefono", ""))
        whatsapp = st.text_input("WhatsApp", value=customer.get("whatsapp", ""))
        email = st.text_input("Email", value=customer.get("email", ""))
        notes = st.text_area("Note", value=customer.get("note", ""))
        submitted = st.form_submit_button("Salva modifiche", use_container_width=True)

    if submitted:
        customer["nome"] = first_name.strip()
        customer["cognome"] = last_name.strip()
        customer["telefono"] = phone.strip()
        customer["whatsapp"] = whatsapp.strip()
        customer["email"] = email.strip()
        customer["note"] = notes.strip()
        st.success("Cliente aggiornato.")


def customer_sheet() -> None:
    if not st.session_state.clienti:
        st.info("Nessun cliente registrato.")
        return

    labels = {
        f'{c["cognome"]} {c["nome"]}': c["id"] for c in st.session_state.clienti
    }
    selected_id = st.session_state.get("selected_customer_id")
    selected_label = next((k for k, v in labels.items() if v == selected_id), list(labels.keys())[0])

    label = st.selectbox(
        "Cliente",
        list(labels.keys()),
        index=list(labels.keys()).index(selected_label),
    )
    customer = customer_by_id(labels[label])
    assert customer is not None

    sub = active_subscription(customer["id"])

    st.subheader(f'{customer["cognome"]} {customer["nome"]}')
    st.write(customer)

    st.divider()
    st.subheader("Abbonamento")
    if sub:
        st.write(sub)
        st.metric("Residuo", money(subscription_residual(sub["id"])))
    else:
        st.info("Nessun abbonamento.")

    st.divider()
    st.subheader("Documenti")
    docs = [d for d in st.session_state.documenti if d["cliente_id"] == customer["id"]]
    if docs:
        st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun documento.")


# ============================================================
# CLIENTI
# ============================================================

def page_customers() -> None:
    header("Clienti", "Anagrafiche, abbonamenti, documenti e storico.")

    apply_pending_action("clienti_action", "Elenco clienti")

    action = st.selectbox(
        "Operazione",
        ["Elenco clienti", "Nuovo cliente", "Modifica cliente", "Scheda cliente"],
        key="clienti_action",
    )

    if action == "Elenco clienti":
        client_list()
    elif action == "Nuovo cliente":
        new_customer_flow()
    elif action == "Modifica cliente":
        modify_customer()
    else:
        customer_sheet()


# ============================================================
# ABBONAMENTI
# ============================================================

def page_subscriptions() -> None:
    header("Abbonamenti", "Pacchetti assegnati ai clienti.")

    rows = []
    for sub in st.session_state.abbonamenti:
        customer = customer_by_id(sub["cliente_id"])
        rows.append(
            {
                "Cliente": f'{customer["cognome"]} {customer["nome"]}' if customer else "—",
                "Pacchetto": sub["pacchetto_nome"],
                "Tipologia": sub["tipologia_pagamento"],
                "Inizio": sub["data_inizio"],
                "Fine prevista": sub["data_fine_prevista"],
                "Importo iniziale": sub["prezzo_concordato"],
                "Pagato": subscription_paid(sub["id"]),
                "Residuo": subscription_residual(sub["id"]),
            }
        )

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun abbonamento registrato.")


# ============================================================
# CONTABILITÀ
# ============================================================

def new_receipt() -> None:
    if not st.session_state.clienti:
        st.info("Nessun cliente registrato.")
        return

    labels = {
        f'{c["cognome"]} {c["nome"]}': c["id"] for c in st.session_state.clienti
    }
    selected_id = st.session_state.get("selected_customer_id")
    selected_label = next((k for k, v in labels.items() if v == selected_id), list(labels.keys())[0])

    label = st.selectbox(
        "Cliente",
        list(labels.keys()),
        index=list(labels.keys()).index(selected_label),
    )
    customer_id = labels[label]
    sub = active_subscription(customer_id)

    if sub:
        st.metric("Residuo attuale", money(subscription_residual(sub["id"])))
    else:
        st.warning("Il cliente non ha un abbonamento attivo.")

    with st.form("receipt_form"):
        amount = st.number_input("Importo", min_value=0.0, step=10.0)
        payment_date = st.date_input("Data incasso", value=date.today())
        method = st.selectbox("Metodo", ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"])
        submitted = st.form_submit_button("Registra incasso", use_container_width=True)

    if submitted:
        if amount <= 0:
            st.error("L'importo deve essere maggiore di zero.")
            return

        if sub and amount > subscription_residual(sub["id"]) + 0.01:
            st.error("L'importo supera il residuo dell'abbonamento.")
            return

        st.session_state.incassi.append(
            {
                "id": str(uuid4()),
                "cliente_id": customer_id,
                "abbonamento_id": sub["id"] if sub else None,
                "data_incasso": payment_date,
                "importo": float(amount),
                "metodo_pagamento": method,
                "stato": "valido",
            }
        )
        st.success("Incasso registrato.")
        if sub:
            st.metric("Nuovo residuo", money(subscription_residual(sub["id"])))


def page_accounting() -> None:
    header("Contabilità", "Incassi, rate, ricevute, spese e fornitori.")

    apply_pending_action("contabilita_action", "Nuovo incasso")

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
        ],
        key="contabilita_action",
    )

    if action == "Nuovo incasso":
        new_receipt()
    elif action == "Elenco incassi":
        if st.session_state.incassi:
            st.dataframe(pd.DataFrame(st.session_state.incassi), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun incasso.")
    elif action == "Rate":
        if st.session_state.rate:
            st.dataframe(pd.DataFrame(st.session_state.rate), use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna rata.")
    elif action == "Ricevute":
        st.info("Generazione e stampa ricevute prevista nella prossima fase.")
    elif action == "Nuovo fornitore":
        with st.form("supplier_form"):
            name = st.text_input("Ragione sociale *")
            vat = st.text_input("Partita IVA")
            email = st.text_input("Email")
            submitted = st.form_submit_button("Salva fornitore", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("La ragione sociale è obbligatoria.")
            else:
                st.session_state.fornitori.append(
                    {
                        "id": str(uuid4()),
                        "ragione_sociale": name.strip(),
                        "partita_iva": vat.strip(),
                        "email": email.strip(),
                    }
                )
                st.success("Fornitore salvato.")
    else:
        st.info("Funzione prevista nella struttura.")


# ============================================================
# ADMIN / AZIENDA
# ============================================================

def page_admin() -> None:
    header("Admin", "Utenti, permessi, audit e dispositivi.")
    st.info("Sezione prevista nella struttura.")


def page_company() -> None:
    header("Azienda", "Anagrafica e logo.")

    with st.form("company_form"):
        name = st.text_input("Ragione sociale", value=st.session_state.azienda_nome)
        logo = st.file_uploader("Logo", type=["png", "jpg", "jpeg", "webp"])
        submitted = st.form_submit_button("Salva", use_container_width=True)

    if submitted:
        st.session_state.azienda_nome = name.strip() or "Azienda"
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
