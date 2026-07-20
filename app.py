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
    crea_cliente_completo,
    crea_incasso_completo,
    crea_pacchetto,
    elenco_clienti_operativo,
    elenco_incassi_operativo,
    elenco_pacchetti,
    elenco_rate_operativo,
    get_azienda_kreo,
    get_cliente_dettaglio,
    modifica_anagrafica_cliente,
    salva_documento_cliente,
    carica_file_documento,
    elimina_file_documento,
    crea_url_documento,
)


APP_VERSION = "0.11.0"
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
def load_company() -> dict[str, Any]:
    return get_azienda_kreo(db)


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


def clear_data_cache() -> None:
    load_company.clear()
    load_packages.clear()
    load_clients.clear()
    load_receipts.clear()
    load_installments.clear()


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


def header(title: str, subtitle: str) -> None:
    left, right = st.columns([5, 1])
    with left:
        st.title(title)
        st.caption(subtitle)
    with right:
        st.markdown(f"**{load_company()['nome_visualizzato']}**")


def sidebar() -> str:
    with st.sidebar:
        st.header(load_company()["nome_visualizzato"])
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
        st.write("Pentti Salenius")
        st.caption("Super Admin")
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

        view = [
            {
                "Nome": row["nome"],
                "Periodicità": row["periodicita"],
                "Prezzo": row["prezzo_standard"],
                "Modalità lezioni": row["modalita_lezioni"],
                "Lezioni per periodo": row["lezioni_per_periodo"],
                "Lezioni totali": row["lezioni_totali"],
                "Attivo": row["attivo"],
            }
            for row in rows
        ]
        st.dataframe(pd.DataFrame(view), use_container_width=True, hide_index=True)
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
                if st.button("Apri scheda", key=f"open_{customer['cliente_id']}", use_container_width=True):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    st.session_state.client_action = "Scheda cliente"
                    st.rerun()
            with actions[1]:
                if st.button("Modifica", key=f"edit_{customer['cliente_id']}", use_container_width=True):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    st.session_state.client_action = "Modifica cliente"
                    st.rerun()
            with actions[2]:
                if st.button("Registra incasso", key=f"cash_{customer['cliente_id']}", use_container_width=True):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    goto("Contabilità", "Nuovo incasso")
            with actions[3]:
                if st.button("Documenti", key=f"docs_{customer['cliente_id']}", use_container_width=True):
                    st.session_state.selected_customer_id = customer["cliente_id"]
                    st.session_state.client_action = "Modifica cliente"
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
            for document in active_docs:
                with st.container(border=True):
                    left, middle, right = st.columns([2.4, 1.5, 1])
                    with left:
                        st.write(f"**{document['tipo']}**")
                        st.caption(document.get("nome_documento") or "Nome file non disponibile")
                    with middle:
                        st.write(f"Data: **{format_date_it(document.get('data_documento'))}**")
                        st.caption(
                            f"Scadenza: {format_date_it(document.get('data_scadenza'))} · "
                            f"Stato: {document.get('stato') or '—'}"
                        )
                    with right:
                        if document.get("file_path"):
                            try:
                                signed_url = crea_url_documento(
                                    db,
                                    document["file_path"],
                                    expires_in=300,
                                )
                                st.link_button(
                                    "Apri file",
                                    signed_url,
                                    use_container_width=True,
                                )
                            except Exception as exc:
                                st.caption(f"File non apribile: {exc}")
                        else:
                            st.caption("File non caricato")
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
            st.dataframe(pd.DataFrame(receipts), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun incasso.")
        st.caption("Gli incassi non si modificano: si annullano e si registrano nuovamente.")

    with tabs[5]:
        if audit:
            st.dataframe(pd.DataFrame(audit), use_container_width=True, hide_index=True)
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
        st.dataframe(pd.DataFrame(installments), use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna rata.")

    st.subheader("Incassi")
    if receipts:
        st.dataframe(pd.DataFrame(receipts), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun incasso.")

    st.subheader("Documenti")
    if documents:
        st.dataframe(pd.DataFrame(documents), use_container_width=True, hide_index=True)
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
    eligible = [r for r in rows if r.get("abbonamento_id") and float(r.get("residuo") or 0) > 0]
    if not eligible:
        st.info("Nessun cliente con residuo aperto.")
        return

    labels = {f"{r['cognome']} {r['nome']}": r for r in eligible}
    selected_id = st.session_state.get("selected_customer_id")
    selected_label = next(
        (label for label, row in labels.items() if row["cliente_id"] == selected_id),
        list(labels)[0],
    )
    customer = labels[
        st.selectbox("Cliente", list(labels), index=list(labels).index(selected_label))
    ]

    summary = st.columns(4)
    summary[0].metric("Prezzo iniziale", money(float(customer.get("prezzo_concordato") or 0)))
    summary[1].metric("Già pagato", money(float(customer.get("pagato") or 0)))
    summary[2].metric("Residuo", money(float(customer.get("residuo") or 0)))
    summary[3].metric(
        "Prossima rata",
        f"{format_date_it(customer.get('prossima_rata_data'))} · "
        f"{money(float(customer.get('prossima_rata_importo') or 0))}",
    )

    with st.form("new_receipt_form"):
        c1, c2 = st.columns(2)
        importo = c1.number_input(
            "Importo",
            min_value=0.0,
            max_value=float(customer.get("residuo") or 0),
            step=10.0,
        )
        data_incasso = c2.date_input("Data incasso", value=date.today(), format="DD/MM/YYYY")

        c3, c4 = st.columns(2)
        metodo = c3.selectbox("Metodo", ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"])
        c4.write("Allocazione automatica alle rate più vecchie")

        causale = st.text_input("Causale", value="Pagamento abbonamento")
        note = st.text_area("Note")
        genera_ricevuta = st.checkbox("Genera ricevuta", value=True)
        submitted = st.form_submit_button("Registra incasso", use_container_width=True)

    if submitted:
        if importo <= 0:
            st.error("L'importo deve essere maggiore di zero.")
            return

        try:
            result = crea_incasso_completo(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "cliente_id": customer["cliente_id"],
                    "abbonamento_id": customer["abbonamento_id"],
                    "data_incasso": data_incasso.isoformat(),
                    "importo": float(importo),
                    "metodo_pagamento": metodo,
                    "causale": causale.strip() or None,
                    "note": note.strip() or None,
                    "genera_ricevuta": genera_ricevuta,
                },
            )
            clear_data_cache()
            st.success(f"Incasso registrato. Nuovo residuo: {money(float(result['nuovo_residuo']))}")
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


def receipts_list_page() -> None:
    rows = load_receipts()
    if not rows:
        st.info("Nessun incasso registrato.")
        return

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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
            st.success(f"Incasso annullato. Nuovo residuo: {money(float(result['nuovo_residuo']))}")
        except Exception as exc:
            st.error(f"Errore durante l'annullamento: {exc}")


def installments_page() -> None:
    rows = load_installments()
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna rata registrata.")


def receipts_print_page() -> None:
    rows = [r for r in load_receipts() if r.get("ricevuta_numero")]
    if not rows:
        st.info("Nessuna ricevuta disponibile.")
        return

    labels = {
        f"{r['ricevuta_numero']} · {r['cliente']} · {money(float(r['importo']))}": r
        for r in rows
    }
    selected = labels[st.selectbox("Ricevuta", list(labels))]

    st.subheader(f"Ricevuta n. {selected['ricevuta_numero']}")
    st.write(f"Cliente: **{selected['cliente']}**")
    st.write(f"Data: **{format_date_it(selected['data_incasso'])}**")
    st.write(f"Importo: **{money(float(selected['importo']))}**")
    st.write(f"Metodo: **{selected['metodo_pagamento']}**")
    st.caption("La generazione PDF definitiva entrerà nel blocco documentale.")


def page_accounting() -> None:
    header("Contabilità", "Incassi, rate, ricevute, spese e fornitori.")

    actions = ["Nuovo incasso", "Elenco incassi", "Rate", "Ricevute"]
    apply_pending_action("accounting_action", actions, "Nuovo incasso")

    action = st.selectbox("Operazione", actions, key="accounting_action")

    if action == "Nuovo incasso":
        new_receipt_page()
    elif action == "Elenco incassi":
        receipts_list_page()
    elif action == "Rate":
        installments_page()
    else:
        receipts_print_page()


# ============================================================
# ALTRE PAGINE
# ============================================================

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
    "Azienda": lambda: placeholder_page("Azienda"),
}


def main() -> None:
    selected = sidebar()
    PAGES[selected]()
    st.markdown(f'<div class="footer">{DEVELOPER_CREDIT}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
