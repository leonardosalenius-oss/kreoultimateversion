from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from db import get_db
from services import (
    crea_cliente_completo,
    crea_incasso,
    crea_pacchetto,
    elenco_clienti_operativo,
    elenco_pacchetti,
    get_azienda_kreo,
)


APP_VERSION = "0.8.0"
DEVELOPER_CREDIT = "Developed by Pentti Salenius © 2026"

PERIODICITA = {
    "Mensile": 1,
    "Semestrale": 6,
    "Annuale": 12,
}

MODALITA_LEZIONI = [
    "Settimanale",
    "Mensile",
    "Pacchetto lezioni",
]

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
        --text:#F6F2E8;
        --muted:#AAA59A;
        --gold:#BFA15A;
        --gold2:#D4B96F;
        --border:#34383D;
    }

    .stApp { background:var(--bg); color:var(--text); }

    [data-testid="stSidebar"] {
        background:var(--sidebar);
        border-right:1px solid var(--border);
    }

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


def money(value: float) -> str:
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_date(value: Any) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return value.strftime("%d/%m/%Y")


def package_end_date(start: date, package: dict[str, Any]) -> date:
    periodicita = package["periodicita"]
    if periodicita not in PERIODICITA:
        raise ValueError("Periodicità pacchetto non valida.")
    return start + relativedelta(months=PERIODICITA[periodicita]) - relativedelta(days=1)


def calculated_lessons(package: dict[str, Any]) -> int:
    modalita = package["modalita_lezioni"]
    periodicita = package["periodicita"]
    valore = int(package["lezioni_per_periodo"])

    if modalita == "Pacchetto lezioni":
        return int(package["lezioni_totali"])

    months = PERIODICITA[periodicita]

    if modalita == "Settimanale":
        # Regola commerciale semplice e dichiarata: 4 settimane per mese.
        return valore * months * 4

    if modalita == "Mensile":
        return valore * months

    raise ValueError("Modalità lezioni non valida.")


def build_installments(
    total: float,
    count: int,
    first_due: date,
    month_step: int,
) -> list[dict[str, Any]]:
    count = max(int(count), 1)
    base = round(total / count, 2)
    amounts = [base] * count
    amounts[-1] = round(amounts[-1] + round(total - sum(amounts), 2), 2)

    return [
        {
            "numero_rata": idx + 1,
            "data_scadenza": first_due + relativedelta(months=idx * month_step),
            "importo_previsto": float(amounts[idx]),
        }
        for idx in range(count)
    ]


def init_state() -> None:
    defaults = {
        "menu": "Reception",
        "pending_menu": None,
        "pending_action": None,
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


@st.cache_data(ttl=15)
def load_clients() -> list[dict[str, Any]]:
    return elenco_clienti_operativo(db, load_company()["id"])


def clear_data_cache() -> None:
    load_packages.clear()
    load_clients.clear()
    load_company.clear()


def goto(page: str, action: str | None = None) -> None:
    st.session_state.pending_menu = page
    st.session_state.pending_action = action
    st.rerun()


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
        st.caption("Super Admin")
        st.caption(f"Versione {APP_VERSION}")

    return selected


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
        ("Carica documento", "Clienti", "Scheda cliente"),
        ("Accesso manuale", None, None),
        ("Storico cliente", "Clienti", "Scheda cliente"),
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
                        st.info(f"'{label}' entrerà nella prossima fase.")


def page_packages() -> None:
    header("Pacchetti", "Listino generale dei servizi.")

    action = st.selectbox(
        "Operazione",
        ["Elenco pacchetti", "Nuovo pacchetto"],
    )

    if action == "Elenco pacchetti":
        rows = load_packages()
        if rows:
            view = []
            for row in rows:
                view.append(
                    {
                        "Nome": row["nome"],
                        "Periodicità": row["periodicita"],
                        "Prezzo": row["prezzo_standard"],
                        "Modalità lezioni": row["modalita_lezioni"],
                        "Lezioni per periodo": row["lezioni_per_periodo"],
                        "Lezioni totali": row["lezioni_totali"],
                        "Attivo": row["attivo"],
                    }
                )
            st.dataframe(pd.DataFrame(view), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun pacchetto registrato.")
        return

    with st.form("new_package_form"):
        nome = st.text_input("Nome pacchetto *")

        c1, c2 = st.columns(2)
        periodicita = c1.selectbox(
            "Periodicità *",
            ["Mensile", "Semestrale", "Annuale"],
        )
        prezzo = c2.number_input(
            "Prezzo standard",
            min_value=0.0,
            step=10.0,
        )

        modalita = st.selectbox(
            "Modalità lezioni *",
            MODALITA_LEZIONI,
        )

        if modalita == "Settimanale":
            lezioni_per_periodo = st.number_input(
                "Lezioni a settimana",
                min_value=1,
                step=1,
                value=3,
            )
            lezioni_totali = 0
            st.caption(
                "Il totale iniziale viene calcolato come lezioni settimanali × 4 settimane × mesi del pacchetto."
            )
        elif modalita == "Mensile":
            lezioni_per_periodo = st.number_input(
                "Lezioni al mese",
                min_value=1,
                step=1,
                value=12,
            )
            lezioni_totali = 0
        else:
            lezioni_per_periodo = 0
            lezioni_totali = st.number_input(
                "Numero totale di lezioni",
                min_value=1,
                step=1,
                value=20,
            )

        submitted = st.form_submit_button(
            "Salva pacchetto",
            use_container_width=True,
        )

    if submitted:
        try:
            if not nome.strip():
                raise ValueError("Il nome del pacchetto è obbligatorio.")

            payload = {
                "azienda_id": load_company()["id"],
                "nome": nome.strip(),
                "periodicita": periodicita,
                "prezzo_standard": float(prezzo),
                "durata_numero": PERIODICITA[periodicita],
                "durata_unita": "mesi",
                "modalita_lezioni": modalita,
                "lezioni_per_periodo": int(lezioni_per_periodo),
                "lezioni_totali": int(lezioni_totali),
                "lezioni_standard": (
                    int(lezioni_totali)
                    if modalita == "Pacchetto lezioni"
                    else int(lezioni_per_periodo) * PERIODICITA[periodicita] * (
                        4 if modalita == "Settimanale" else 1
                    )
                ),
                "attivo": True,
            }

            crea_pacchetto(db, payload)
            clear_data_cache()
            st.success("Pacchetto salvato nel database.")
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


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
    data_inizio = c8.date_input(
        "Data inizio",
        value=date.today(),
        format="DD/MM/YYYY",
    )
    data_fine = c9.date_input(
        "Data fine prevista",
        value=package_end_date(data_inizio, package),
        format="DD/MM/YYYY",
    )

    default_lessons = calculated_lessons(package)

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
        value=int(default_lessons),
        help="Valore calcolato dal pacchetto, ma modificabile.",
    )

    tipologia_pagamento = st.selectbox(
        "Tipologia pagamento",
        [
            "Soluzione unica",
            "Mensile",
            "Trimestrale",
            "Semestrale",
            "Personalizzato",
        ],
    )

    if tipologia_pagamento == "Soluzione unica":
        numero_rate = 1
        step_mesi = 0
    else:
        numero_rate = st.number_input(
            "Numero rate",
            min_value=1,
            step=1,
            value=1,
        )
        step_mesi = {
            "Mensile": 1,
            "Trimestrale": 3,
            "Semestrale": 6,
            "Personalizzato": 1,
        }[tipologia_pagamento]

    prima_scadenza = st.date_input(
        "Data prima scadenza",
        value=data_inizio,
        format="DD/MM/YYYY",
    )

    suggested_plan = build_installments(
        float(prezzo_concordato),
        int(numero_rate),
        prima_scadenza,
        step_mesi,
    )

    # La colonna data contiene veri oggetti date: evita l'errore di compatibilità
    # del precedente data_editor, causato da stringhe ISO configurate come DateColumn.
    piano_rate = st.data_editor(
        pd.DataFrame(suggested_plan),
        use_container_width=True,
        hide_index=True,
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

    st.divider()
    st.subheader("3. Acconto iniziale")

    c12, c13 = st.columns(2)
    acconto_iniziale = c12.number_input(
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

    residuo_live = max(float(prezzo_concordato) - float(acconto_iniziale), 0.0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Prezzo pacchetto", money(float(prezzo_concordato)))
    m2.metric("Acconto iniziale", money(float(acconto_iniziale)))
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
            presente = st.checkbox(
                f"{tipo} presente",
                key=f"{tipo}_presente",
            )
            data_documento = st.date_input(
                "Data documento",
                value=date.today(),
                format="DD/MM/YYYY",
                key=f"{tipo}_data",
                disabled=not presente,
            )
            ha_scadenza = st.checkbox(
                "Documento con scadenza",
                value=default_expiry,
                key=f"{tipo}_scadenza_flag",
                disabled=not presente,
            )
            scadenza_default = (
                data_documento + relativedelta(years=1) - relativedelta(days=1)
                if default_expiry
                else data_documento
            )
            data_scadenza = st.date_input(
                "Data scadenza",
                value=scadenza_default,
                format="DD/MM/YYYY",
                key=f"{tipo}_scadenza",
                disabled=(not presente or not ha_scadenza),
            )

            documents.append(
                {
                    "tipo": tipo,
                    "presente": presente,
                    "data_documento": (
                        data_documento.isoformat() if presente else None
                    ),
                    "data_scadenza": (
                        data_scadenza.isoformat()
                        if presente and ha_scadenza
                        else None
                    ),
                }
            )

    if st.button("Salva cliente completo", use_container_width=True):
        total_rate = (
            float(piano_rate["importo_previsto"].sum())
            if not piano_rate.empty
            else 0.0
        )

        if not nome.strip() or not cognome.strip():
            st.error("Nome e cognome sono obbligatori.")
            return

        if abs(total_rate - float(prezzo_concordato)) > 0.01:
            st.error(
                "La somma delle rate deve coincidere con il prezzo concordato."
            )
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
                    "data_scadenza": (
                        row["data_scadenza"].isoformat()
                        if hasattr(row["data_scadenza"], "isoformat")
                        else date.fromisoformat(
                            str(row["data_scadenza"])
                        ).isoformat()
                    ),
                    "importo_previsto": float(row["importo_previsto"]),
                }
                for _, row in piano_rate.iterrows()
            ],
            "incasso_iniziale": (
                {
                    "importo": float(acconto_iniziale),
                    "metodo_pagamento": metodo_acconto,
                    "causale": "Acconto iniziale",
                }
                if acconto_iniziale > 0
                else None
            ),
            "documenti": [
                d for d in documents if d["presente"]
            ],
        }

        try:
            result = crea_cliente_completo(db, payload)
            clear_data_cache()
            st.success(
                f"Cliente salvato. Residuo iniziale: {money(residuo_live)}"
            )
            st.balloons()
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


def client_list() -> None:
    rows = load_clients()

    if not rows:
        st.info("Nessun cliente registrato.")
        return

    search = st.text_input(
        "Cerca",
        placeholder="Nome, cognome, telefono o WhatsApp",
    )

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
        f"Residuo complessivo "
        f"{money(sum(float(r.get('residuo') or 0) for r in filtered))}"
    )

    for customer in filtered:
        with st.container(border=True):
            top_left, top_right = st.columns([4, 1])

            with top_left:
                st.subheader(
                    f"{customer['cognome']} {customer['nome']}"
                )
                st.caption(
                    " · ".join(
                        x
                        for x in [
                            customer.get("telefono"),
                            customer.get("whatsapp"),
                        ]
                        if x
                    )
                    or "Contatti non inseriti"
                )

            with top_right:
                st.markdown(
                    f"### {customer.get('stato_complessivo') or '—'}"
                )

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.caption("ABBONAMENTO")
            c1.write(
                f"**{customer.get('pacchetto_nome') or '—'}**"
            )
            c1.caption(
                customer.get("tipologia_pagamento") or "—"
            )

            c2.caption("SCADENZA")
            c2.write(
                f"**{format_date(customer.get('data_fine_prevista'))}**"
            )

            c3.caption("SITUAZIONE ECONOMICA")
            c3.write(
                f"Iniziale "
                f"**{money(float(customer.get('prezzo_concordato') or 0))}**"
            )
            c3.caption(
                f"Pagato "
                f"{money(float(customer.get('pagato') or 0))}"
            )
            c3.write(
                f"Residuo "
                f"**{money(float(customer.get('residuo') or 0))}**"
            )

            c4.caption("PROSSIMA RATA")
            c4.write(
                f"**{format_date(customer.get('prossima_rata_data'))}**"
            )
            c4.caption(
                money(
                    float(customer.get("prossima_rata_importo") or 0)
                )
            )

            c5.caption("CERTIFICATO")
            c5.write(
                f"**{customer.get('certificato_stato') or 'Mancante'}**"
            )


def page_customers() -> None:
    header(
        "Clienti",
        "Anagrafiche, abbonamenti, documenti e storico.",
    )

    actions = [
        "Elenco clienti",
        "Nuovo cliente",
        "Modifica cliente",
        "Scheda cliente",
    ]

    if st.session_state.pending_action in actions:
        st.session_state.client_action = (
            st.session_state.pending_action
        )
        st.session_state.pending_action = None

    if "client_action" not in st.session_state:
        st.session_state.client_action = "Elenco clienti"

    action = st.selectbox(
        "Operazione",
        actions,
        key="client_action",
    )

    if action == "Nuovo cliente":
        new_customer_flow()
    elif action == "Elenco clienti":
        client_list()
    else:
        st.info(
            "Questa funzione entrerà nella prossima versione persistente."
        )


def page_accounting() -> None:
    header(
        "Contabilità",
        "Incassi, rate, ricevute, spese e fornitori.",
    )

    clients = load_clients()

    if not clients:
        st.info("Nessun cliente registrato.")
        return

    labels = {
        f"{c['cognome']} {c['nome']}": c
        for c in clients
        if c.get("abbonamento_id")
    }

    if not labels:
        st.info("Nessun cliente con abbonamento.")
        return

    selected = st.selectbox("Cliente", list(labels))
    customer = labels[selected]

    st.metric(
        "Residuo attuale",
        money(float(customer.get("residuo") or 0)),
    )

    with st.form("new_receipt_form"):
        importo = st.number_input(
            "Importo",
            min_value=0.0,
            max_value=float(customer.get("residuo") or 0),
            step=10.0,
        )
        metodo = st.selectbox(
            "Metodo",
            [
                "Contanti",
                "Carta",
                "Bonifico",
                "Assegno",
                "Altro",
            ],
        )
        submitted = st.form_submit_button(
            "Registra incasso",
            use_container_width=True,
        )

    if submitted:
        try:
            crea_incasso(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "cliente_id": customer["cliente_id"],
                    "abbonamento_id": customer["abbonamento_id"],
                    "importo": float(importo),
                    "metodo_pagamento": metodo,
                    "tipo_incasso": "abbonamento",
                    "stato": "valido",
                },
            )
            clear_data_cache()
            st.success("Incasso salvato nel database.")
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")


def placeholder_page(title: str) -> None:
    header(title, "Sezione prevista nella struttura.")
    st.info("Questa sezione entrerà nella prossima fase.")


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
    st.markdown(
        f'<div class="footer">{DEVELOPER_CREDIT}</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
