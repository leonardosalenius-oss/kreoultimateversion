
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

import streamlit as st


# ============================================================
# CONFIGURAZIONE GENERALE
# ============================================================

APP_NAME = "Gestionale"
APP_VERSION = "0.1.0"
DEVELOPER_CREDIT = "Developed by Pentti Salenius © 2026"


@dataclass(frozen=True)
class Theme:
    background: str = "#0F1113"
    sidebar: str = "#090A0C"
    surface: str = "#171A1E"
    surface_alt: str = "#1E2227"
    text: str = "#F4F4F2"
    text_secondary: str = "#A8ADB4"
    gold: str = "#B99A55"
    gold_hover: str = "#D2B96F"
    border: str = "#34383D"
    success: str = "#3E8E68"
    warning: str = "#D5972C"
    danger: str = "#C05252"
    info: str = "#4A7FA8"


THEME = Theme()


st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# TEMA GRAFICO
# ============================================================

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
            color: var(--text);
        }}

        h1, h2, h3, h4, h5, h6, p, span, label {{
            color: var(--text);
        }}

        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
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

        .kreo-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
        }}

        .kreo-card-gold {{
            background: var(--surface);
            border: 1px solid var(--gold);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
        }}

        .kreo-subtle {{
            color: var(--text-secondary);
            font-size: 0.92rem;
        }}

        .kreo-badge {{
            display: inline-block;
            border: 1px solid var(--gold);
            border-radius: 999px;
            padding: 4px 10px;
            color: var(--gold);
            font-size: 0.78rem;
            font-weight: 600;
        }}

        .kreo-title-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 1rem;
        }}

        div.stButton > button,
        div.stDownloadButton > button {{
            background: var(--surface);
            color: var(--text);
            border: 1px solid var(--gold);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: 0.2s ease-in-out;
        }}

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {{
            background: var(--gold);
            color: #111111;
            border-color: var(--gold-hover);
        }}

        div.stButton > button:focus,
        div.stDownloadButton > button:focus {{
            box-shadow: 0 0 0 0.15rem rgba(185, 154, 85, 0.25);
        }}

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] > div {{
            background: var(--surface-alt);
            border-color: var(--border);
            color: var(--text);
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
        }}

        hr {{
            border-color: var(--border);
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
# SESSIONE
# ============================================================

def initialize_session() -> None:
    defaults = {
        "azienda_nome": "KREO",
        "utente_nome": "Pentti Salenius",
        "utente_ruolo": "Super Admin",
        "menu_principale": "Reception",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session()


# ============================================================
# COMPONENTI UI
# ============================================================

def page_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="kreo-title-row">
            <div>
                <h1 style="margin-bottom: 0.2rem;">{title}</h1>
                {f'<div class="kreo-subtle">{subtitle}</div>' if subtitle else ''}
            </div>
            <span class="kreo-badge">{st.session_state["azienda_nome"]}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, body: str, gold_border: bool = False) -> None:
    css_class = "kreo-card-gold" if gold_border else "kreo-card"
    st.markdown(
        f"""
        <div class="{css_class}">
            <h3 style="margin-top: 0;">{title}</h3>
            <div class="kreo-subtle">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_navigation() -> str:
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 0.5rem 0 1.2rem 0;">
                <h2 style="margin-bottom: 0.2rem;">{st.session_state["azienda_nome"]}</h2>
                <div class="kreo-subtle">Gestionale aziendale</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        menu = st.radio(
            "Navigazione",
            options=[
                "Reception",
                "Pacchetti",
                "Abbonamenti",
                "Clienti",
                "Contabilità",
                "Admin",
                "Azienda",
            ],
            key="menu_principale",
            label_visibility="collapsed",
        )

        st.divider()

        st.markdown(
            f"""
            <div class="kreo-card" style="padding: 12px;">
                <strong>{st.session_state["utente_nome"]}</strong><br>
                <span class="kreo-subtle">{st.session_state["utente_ruolo"]}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"Versione {APP_VERSION}")

    return menu


# ============================================================
# PAGINE
# ============================================================

def page_reception() -> None:
    page_header(
        "Reception",
        "Agenda, presenze, incassi e alert operativi.",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clienti attivi", "—")
    c2.metric("Prenotazioni oggi", "—")
    c3.metric("Presenze oggi", "—")
    c4.metric("Incassi oggi", "€ —")

    st.subheader("Azioni rapide")
    cols = st.columns(4)

    with cols[0]:
        st.button("Nuovo cliente", use_container_width=True)
        st.button("Aggiungi prenotazione", use_container_width=True)

    with cols[1]:
        st.button("Registra incasso", use_container_width=True)
        st.button("Accesso manuale", use_container_width=True)

    with cols[2]:
        st.button("Associa badge", use_container_width=True)
        st.button("Carica documento", use_container_width=True)

    with cols[3]:
        st.button("Conferma presenza", use_container_width=True)
        st.button("Messaggio cliente", use_container_width=True)

    st.divider()

    col_agenda, col_alert = st.columns([2.2, 1])

    with col_agenda:
        card(
            "Agenda settimanale",
            "La vista agenda verrà collegata alla tabella prenotazioni e alla disponibilità dello staff.",
            gold_border=True,
        )

    with col_alert:
        card(
            "Alert",
            "Rate scadute, certificati in scadenza, badge da associare e anomalie operative.",
        )


def page_pacchetti() -> None:
    page_header(
        "Pacchetti",
        "Gestione del listino generale dell’azienda.",
    )

    action = st.selectbox(
        "Operazione",
        [
            "Elenco pacchetti",
            "Nuovo pacchetto",
            "Modifica pacchetto esistente",
        ],
    )

    if action == "Elenco pacchetti":
        card(
            "Elenco pacchetti",
            "Qui verranno visualizzati Luxury, Gold, VIP, Coaching in sede e i pacchetti personalizzati.",
            gold_border=True,
        )

    elif action == "Nuovo pacchetto":
        with st.form("form_nuovo_pacchetto"):
            nome = st.text_input("Nome pacchetto")
            descrizione = st.text_area("Descrizione")
            c1, c2, c3 = st.columns(3)
            prezzo = c1.number_input("Prezzo standard", min_value=0.0, step=10.0)
            durata = c2.number_input("Durata", min_value=1, step=1)
            unita = c3.selectbox("Unità durata", ["giorni", "settimane", "mesi", "anni"])

            c4, c5, c6 = st.columns(3)
            lezioni = c4.number_input("Lezioni standard", min_value=0, step=1)
            frequenza = c5.number_input("Frequenza settimanale", min_value=0, step=1)
            partecipanti = c6.number_input("Partecipanti massimi", min_value=1, step=1)

            st.checkbox("Richiede prenotazione", value=True)
            st.checkbox("Occupa agenda trainer", value=True)
            st.checkbox("Genera presenza", value=True)
            st.checkbox("Consuma lezione", value=True)
            st.checkbox("Consente accesso libero", value=False)

            note = st.text_area("Note")
            submitted = st.form_submit_button("Salva pacchetto", use_container_width=True)

            if submitted:
                st.info(
                    "Struttura pronta. Il salvataggio su database verrà collegato nella fase Supabase."
                )

    else:
        card(
            "Modifica pacchetto esistente",
            "La modifica avrà effetto sui nuovi abbonamenti e non altererà quelli già sottoscritti.",
            gold_border=True,
        )


def page_abbonamenti() -> None:
    page_header(
        "Abbonamenti",
        "Pacchetti assegnati ai singoli clienti.",
    )

    action = st.selectbox(
        "Operazione",
        [
            "Elenco abbonamenti",
            "Aggiungi abbonamento cliente",
            "Modifica abbonamento cliente",
            "Rinnovi e sospensioni",
        ],
    )

    if action == "Aggiungi abbonamento cliente":
        with st.form("form_abbonamento_cliente"):
            cliente = st.selectbox("Cliente", ["Seleziona cliente"])
            pacchetto = st.selectbox("Pacchetto", ["Seleziona pacchetto"])

            c1, c2, c3 = st.columns(3)
            data_inizio = c1.date_input("Data inizio")
            data_fine = c2.date_input("Data fine prevista")
            prezzo = c3.number_input("Prezzo concordato", min_value=0.0, step=10.0)

            c4, c5 = st.columns(2)
            lezioni = c4.number_input("Lezioni iniziali", min_value=0, step=1)
            trainer = c5.selectbox("Trainer principale", ["Da assegnare"])

            st.subheader("Piano di pagamento")
            modalita = st.selectbox(
                "Modalità",
                [
                    "Soluzione unica",
                    "Rate mensili",
                    "Rate trimestrali",
                    "Rate personalizzate",
                ],
            )

            numero_rate = st.number_input("Numero rate", min_value=1, step=1)
            note = st.text_area("Note")

            submitted = st.form_submit_button(
                "Crea abbonamento",
                use_container_width=True,
            )

            if submitted:
                st.info(
                    "La creazione genererà il record abbonamento e i relativi record rata."
                )

    else:
        card(
            action,
            "Questa sezione sarà collegata alle tabelle abbonamenti, rate, incassi e sospensioni.",
            gold_border=True,
        )


def page_clienti() -> None:
    page_header(
        "Clienti",
        "Anagrafiche, storico, documenti e situazione complessiva.",
    )

    action = st.selectbox(
        "Operazione",
        [
            "Elenco clienti",
            "Nuovo cliente",
            "Modifica cliente",
            "Scheda cliente",
        ],
    )

    if action == "Nuovo cliente":
        with st.form("form_nuovo_cliente"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome")
            cognome = c2.text_input("Cognome")

            c3, c4, c5 = st.columns(3)
            telefono = c3.text_input("Telefono")
            whatsapp = c4.text_input("WhatsApp")
            email = c5.text_input("Email")

            c6, c7 = st.columns(2)
            codice_fiscale = c6.text_input("Codice fiscale")
            partita_iva = c7.text_input("Partita IVA")

            note = st.text_area("Note")
            submitted = st.form_submit_button("Salva cliente", use_container_width=True)

            if submitted:
                st.info("Il cliente verrà salvato nella tabella clienti.")

    else:
        card(
            action,
            "La scheda cliente riunirà anagrafica, abbonamenti, rate, incassi, documenti, prenotazioni, presenze e badge.",
            gold_border=True,
        )


def page_contabilita() -> None:
    page_header(
        "Contabilità",
        "Incassi, rate, ricevute, spese e fornitori.",
    )

    action = st.selectbox(
        "Operazione",
        [
            "Incassi",
            "Rate",
            "Ricevute",
            "Nuova spesa",
            "Elenco spese",
            "Fornitori",
            "Categorie di spesa",
        ],
    )

    if action == "Nuova spesa":
        with st.form("form_nuova_spesa"):
            c1, c2 = st.columns(2)
            data_spesa = c1.date_input("Data spesa")
            importo = c2.number_input("Importo", min_value=0.0, step=10.0)

            c3, c4 = st.columns(2)
            categoria = c3.selectbox("Categoria", ["Seleziona categoria"])
            fornitore = c4.selectbox("Fornitore", ["Seleziona fornitore"])

            descrizione = st.text_input("Descrizione")
            metodo = st.selectbox(
                "Metodo di pagamento",
                ["Contanti", "Carta", "Bonifico", "Assegno", "Altro"],
            )
            competenza = st.text_input("Mese di competenza")
            allegato = st.file_uploader("Allegato")
            note = st.text_area("Note")

            submitted = st.form_submit_button("Registra spesa", use_container_width=True)

            if submitted:
                st.info("La spesa verrà salvata nella tabella spese.")

    else:
        card(
            action,
            "Questa sezione sarà collegata a incassi, rate, ricevute, spese, categorie e fornitori.",
            gold_border=True,
        )


def page_admin() -> None:
    page_header(
        "Admin",
        "Utenti, ruoli, permessi, audit e configurazioni operative.",
    )

    c1, c2 = st.columns(2)

    with c1:
        card(
            "Utenti e permessi",
            "Gestione di Super Admin, Admin azienda, Reception, Trainer e operatori.",
            gold_border=True,
        )
        card(
            "Audit log",
            "Storico di creazioni, modifiche, annullamenti, cancellazioni e operazioni sensibili.",
        )

    with c2:
        card(
            "Importazioni",
            "Importazione controllata di clienti, abbonamenti, incassi, badge, presenze e documenti.",
        )
        card(
            "Dispositivi",
            "Gestione tornelli, lettori badge e sincronizzazioni.",
        )


def page_azienda() -> None:
    page_header(
        "Azienda",
        "Anagrafica aziendale e configurazione generale.",
    )

    with st.form("form_azienda"):
        ragione_sociale = st.text_input("Ragione sociale")
        partita_iva = st.text_input("Partita IVA")
        codice_fiscale = st.text_input("Codice fiscale")
        sede_legale = st.text_input("Sede legale")
        sede_operativa = st.text_input("Sede operativa")
        telefono = st.text_input("Telefono")
        email = st.text_input("Email")
        logo = st.file_uploader("Logo aziendale", type=["png", "jpg", "jpeg", "webp"])
        note = st.text_area("Note")

        submitted = st.form_submit_button(
            "Salva dati azienda",
            use_container_width=True,
        )

        if submitted:
            st.info("I dati verranno salvati nella tabella aziende.")


PAGES: Dict[str, Callable[[], None]] = {
    "Reception": page_reception,
    "Pacchetti": page_pacchetti,
    "Abbonamenti": page_abbonamenti,
    "Clienti": page_clienti,
    "Contabilità": page_contabilita,
    "Admin": page_admin,
    "Azienda": page_azienda,
}


# ============================================================
# AVVIO APP
# ============================================================

def main() -> None:
    selected_page = sidebar_navigation()
    page = PAGES.get(selected_page)

    if page is None:
        st.error("Pagina non disponibile.")
        return

    page()

    st.markdown(
        f'<div class="footer">{DEVELOPER_CREDIT}</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
