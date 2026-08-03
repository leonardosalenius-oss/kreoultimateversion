from __future__ import annotations

from datetime import date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from db import get_auth_client, get_db
from domain import (
    PERIODICITA_MESI,
    build_installment_plan,
    calculate_package_end,
    calculate_package_lessons,
    format_date_it,
    money,
)
from services import (
    bootstrap_super_admin,
    elenco_accessi_utente,
    elenco_ruoli_accesso,
    elenco_utenti_azienda,
    crea_utente_auth_con_password,
    crea_accesso_app_cliente,
    get_accesso_app_cliente,
    aggiorna_accesso_app_cliente,
    reimposta_password_utente_auth,
    registra_audit_accesso,
    salva_accesso_utente,
    annulla_documento_cliente,
    annulla_incasso,
    aggiorna_abbonamento_cliente,
    aggiorna_rate_abbonamento,
    rimodula_rate_residue,
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
    crea_regola_spesa_ricorrente,
    modifica_spesa,
    annulla_spesa,
    modifica_regola_spesa_ricorrente,
    elimina_regola_spesa_ricorrente,
    genera_spese_ricorrenti,
    cambia_stato_regola_spesa_ricorrente,
    elenco_regole_spese_ricorrenti,
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
    elenco_indisponibilita_operatori,
    salva_indisponibilita_operatore,
    elimina_indisponibilita_operatore,
    rigenera_slot_operatori,
    elenco_alert_prenotazioni_cliente,
    segna_alert_prenotazione_letto,
    elenco_slot_app_cliente,
    salva_slot_app_cliente,
    cambia_stato_slot_app_cliente,
    imposta_blocco_prenotazioni_cliente,
    elenco_ordini_cliente,
    aggiorna_stato_ordine_cliente,
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
    calcola_lezioni_contrattuali,
    genera_ricevuta_incasso,
    salva_pacchetto,
    annulla_movimento_magazzino,
    elenco_movimenti_magazzino,
    elenco_prodotti_magazzino,
    registra_acquisto_magazzino,
    registra_rettifica_magazzino,
    registra_vendita_magazzino,
    salva_prodotto_magazzino,
)
from receipts import build_receipt_pdf
from export_utils import (
    ExportColumn,
    build_csv_bytes,
    build_excel_bytes,
    build_pdf_bytes,
)

from weekly_report_mail import send_weekly_reports_email


APP_VERSION = "0.30.9"
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

    /* Tabelle Admin - stile Executive Card.
       Regole isolate: nessun selettore globale su table/dataframe. */
    .kreo-admin-table-wrap {
        width:100%;
        overflow-x:auto;
        margin:.35rem 0 1.35rem 0;
        padding:1px;
        border-radius:12px;
        background:
            linear-gradient(
                135deg,
                rgba(191,161,90,.78),
                rgba(191,161,90,.10) 35%,
                rgba(191,161,90,.38)
            );
        box-shadow:
            0 14px 34px rgba(0,0,0,.22),
            inset 0 1px 0 rgba(255,255,255,.025);
    }

    .kreo-admin-table {
        min-width:760px;
        border-radius:11px;
        overflow:hidden;
        background:#111417;
    }

    .kreo-admin-thead,
    .kreo-admin-tr {
        display:grid;
        grid-template-columns:var(--kreo-admin-columns);
        align-items:stretch;
    }

    .kreo-admin-thead {
        background:
            linear-gradient(
                180deg,
                #202429 0%,
                #181c20 100%
            );
        border-bottom:1px solid rgba(191,161,90,.44);
    }

    .kreo-admin-th {
        padding:14px 16px;
        color:#D8BC73;
        font-size:.79rem;
        font-weight:700;
        letter-spacing:.015em;
        text-transform:none;
        white-space:nowrap;
    }

    .kreo-admin-tr {
        min-height:51px;
        background:
            linear-gradient(
                90deg,
                rgba(255,255,255,.017),
                rgba(255,255,255,.006)
            );
        border-bottom:1px solid rgba(255,255,255,.065);
        transition:
            background .16s ease,
            transform .16s ease;
    }

    .kreo-admin-tr:nth-child(even) {
        background:
            linear-gradient(
                90deg,
                rgba(255,255,255,.032),
                rgba(255,255,255,.012)
            );
    }

    .kreo-admin-tr:last-child {
        border-bottom:0;
    }

    .kreo-admin-tr:hover {
        background:
            linear-gradient(
                90deg,
                rgba(191,161,90,.115),
                rgba(191,161,90,.025)
            );
    }

    .kreo-admin-td {
        display:flex;
        align-items:center;
        padding:13px 16px;
        color:#F2EEE5;
        font-size:.84rem;
        line-height:1.25;
        border-right:1px solid rgba(255,255,255,.035);
        overflow-wrap:anywhere;
    }

    .kreo-admin-td:last-child {
        border-right:0;
    }

    .kreo-admin-td.is-number {
        justify-content:flex-end;
        text-align:right;
        font-variant-numeric:tabular-nums;
        white-space:nowrap;
    }

    .kreo-admin-td.is-date {
        font-variant-numeric:tabular-nums;
        white-space:nowrap;
    }

    .kreo-admin-td.is-highlight {
        color:#D8B45D;
        font-weight:700;
    }

    .kreo-status {
        display:inline-flex;
        align-items:center;
        gap:7px;
        min-height:26px;
        padding:4px 10px;
        border-radius:999px;
        font-size:.75rem;
        font-weight:650;
        white-space:nowrap;
        border:1px solid rgba(191,161,90,.38);
        background:rgba(191,161,90,.07);
        color:#E2C87F;
    }

    .kreo-status-dot {
        width:7px;
        height:7px;
        flex:0 0 7px;
        border-radius:50%;
        background:currentColor;
        box-shadow:0 0 8px currentColor;
    }

    .kreo-status.is-danger {
        color:#FF8D82;
        border-color:rgba(255,92,80,.36);
        background:rgba(255,92,80,.08);
    }

    .kreo-status.is-warning {
        color:#E2BE64;
        border-color:rgba(226,190,100,.40);
        background:rgba(226,190,100,.08);
    }

    .kreo-status.is-success {
        color:#86D39A;
        border-color:rgba(91,193,117,.34);
        background:rgba(91,193,117,.08);
    }

    .kreo-status.is-neutral {
        color:#C8C5BE;
        border-color:rgba(200,197,190,.22);
        background:rgba(200,197,190,.06);
    }

    @media (max-width:900px) {
        .kreo-admin-th,
        .kreo-admin-td {
            padding-left:12px;
            padding-right:12px;
        }
    }
    [data-testid="stSidebar"] { background:var(--sidebar); border-right:1px solid var(--border); }
    [data-testid="stSidebar"] * { color:var(--text) !important; }

    /* Sidebar definitiva: select azienda coerente con il tema. */
    [data-testid="stSidebar"] [data-testid="stSelectbox"]
    div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background:#171A1E !important;
        background-color:#171A1E !important;
        border:1px solid var(--gold) !important;
        border-radius:8px !important;
        box-shadow:none !important;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"]
    div[data-baseweb="select"] > div > div,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div > div {
        background:transparent !important;
        background-color:transparent !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-baseweb="select"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] svg {
        color:var(--text) !important;
        fill:var(--text) !important;
        -webkit-text-fill-color:var(--text) !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div:hover,
    [data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
        border-color:var(--gold2) !important;
        box-shadow:0 0 0 1px var(--gold2) inset !important;
    }


    /* Motore unico pulsanti: normale, submit e download con lo stesso contrasto. */
    div.stButton > button,
    div.stFormSubmitButton > button,
    div[data-testid="stDownloadButton"] button,
    div[data-testid="stDownloadButton"] a,
    [data-testid="stDownloadButton"] > button {
        background:var(--surface) !important;
        color:var(--text) !important;
        border:1px solid var(--gold) !important;
        border-radius:8px !important;
        min-height:2.7rem;
        font-weight:650 !important;
    }
    div.stButton > button *,
    div.stFormSubmitButton > button *,
    div[data-testid="stDownloadButton"] button *,
    div[data-testid="stDownloadButton"] a *,
    [data-testid="stDownloadButton"] > button * {
        color:var(--text) !important;
    }
    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover,
    div[data-testid="stDownloadButton"] button:hover,
    div[data-testid="stDownloadButton"] a:hover,
    [data-testid="stDownloadButton"] > button:hover {
        background:var(--gold) !important;
        border-color:var(--gold2) !important;
        color:#111 !important;
    }
    div.stButton > button:hover *,
    div.stFormSubmitButton > button:hover *,
    div[data-testid="stDownloadButton"] button:hover *,
    div[data-testid="stDownloadButton"] a:hover *,
    [data-testid="stDownloadButton"] > button:hover * {
        color:#111 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border:1px solid var(--gold) !important;
        background:linear-gradient(180deg,#171A1E 0%,#14171A 100%);
        border-radius:14px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color:var(--gold2) !important;
    }
    .reception-section-title {
        font-size:1.15rem;
        font-weight:750;
        margin:0 0 .55rem 0;
        color:var(--text);
    }
    .prospect-status {
        display:inline-block;
        border:1px solid var(--gold);
        border-radius:999px;
        padding:.15rem .55rem;
        font-size:.78rem;
        color:var(--text);
        background:rgba(191,161,90,.10);
    }

    .active-company-card {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:.75rem;
        width:100%;
        min-height:2.7rem;
        padding:.62rem .78rem;
        margin:.15rem 0 .45rem 0;
        border:1px solid var(--gold);
        border-radius:8px;
        background:linear-gradient(180deg,#1A1E22 0%,#14171A 100%);
        color:var(--text);
        font-weight:700;
        box-sizing:border-box;
    }
    .active-company-card .company-chevron {
        color:var(--gold2);
        font-size:.85rem;
    }

    /* Quando esistono più aziende, il radio sostituisce il fragile
       select BaseWeb e mantiene lo stesso tema scuro. */
    [data-testid="stSidebar"] [data-testid="stRadio"] {
        border:1px solid var(--gold);
        border-radius:8px;
        padding:.4rem .55rem;
        background:linear-gradient(180deg,#1A1E22 0%,#14171A 100%);
    }

    .quick-action-icon {
        text-align:center;
        color:var(--gold2);
        font-size:2rem;
        line-height:1;
        margin:.35rem 0 .15rem 0;
    }
    .quick-action-label {
        text-align:center;
        color:var(--text);
        font-weight:700;
        min-height:2.2rem;
        display:flex;
        align-items:center;
        justify-content:center;
    }
    .agenda-heading {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:1rem;
        margin-bottom:.7rem;
    }
    [data-testid="stMetric"] {
        background:linear-gradient(180deg,#171A1E 0%,#121518 100%);
        border:1px solid rgba(191,161,90,.55);
        border-radius:10px;
        padding:.65rem .8rem;
    }
    [data-testid="stMetricValue"] {
        color:var(--text) !important;
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
    /* Override definitivo del solo selettore azienda attiva. */
    .st-key-active_company_selector div[data-baseweb="select"] > div,
    .st-key-active_company_selector [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .st-key-active_company_selector
    div[data-baseweb="select"] > div {
        background:#171A1E !important;
        background-color:#171A1E !important;
        border:1px solid #BFA15A !important;
        color:#F6F2E8 !important;
        box-shadow:none !important;
    }
    .st-key-active_company_selector div[data-baseweb="select"] > div *,
    .st-key-active_company_selector [data-baseweb="select"] span,
    .st-key-active_company_selector [data-baseweb="select"] input,
    .st-key-active_company_selector [data-baseweb="select"] svg {
        background:transparent !important;
        background-color:transparent !important;
        color:#F6F2E8 !important;
        fill:#F6F2E8 !important;
        -webkit-text-fill-color:#F6F2E8 !important;
    }
    


    
    /* =========================================================
       KREO UI 0.30.5 — REGOLE DI CONTRASTO SCOPED
       Nessuna regola globale su span, label o interi popover.
       ========================================================= */

    /* Testi della pagina, senza coinvolgere calendari e menu portal. */
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4,
    [data-testid="stAppViewContainer"] h5,
    [data-testid="stAppViewContainer"] h6,
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] label {
        color:var(--text);
    }

    /* Tab, radio e checkbox della pagina principale. */
    [data-testid="stAppViewContainer"] [data-testid="stTabs"] button,
    [data-testid="stAppViewContainer"] [data-testid="stTabs"] button p,
    [data-testid="stAppViewContainer"] [data-testid="stRadio"] label,
    [data-testid="stAppViewContainer"] [data-testid="stCheckbox"] label {
        color:var(--text) !important;
    }

    /* Campi della pagina principale: chiari con testo scuro. */
    [data-testid="stAppViewContainer"] [data-testid="stTextInput"]
    [data-baseweb="input"] > div,
    [data-testid="stAppViewContainer"] [data-testid="stNumberInput"]
    [data-baseweb="input"] > div,
    [data-testid="stAppViewContainer"] [data-testid="stDateInput"]
    [data-baseweb="input"] > div,
    [data-testid="stAppViewContainer"] [data-testid="stTextArea"]
    [data-baseweb="textarea"] > div,
    [data-testid="stAppViewContainer"] [data-testid="stSelectbox"]
    [data-baseweb="select"] > div {
        background:#F3F4F6 !important;
        background-color:#F3F4F6 !important;
        color:#111827 !important;
        border-color:#CBD1D8 !important;
    }

    [data-testid="stAppViewContainer"] [data-testid="stTextInput"] input,
    [data-testid="stAppViewContainer"] [data-testid="stNumberInput"] input,
    [data-testid="stAppViewContainer"] [data-testid="stDateInput"] input,
    [data-testid="stAppViewContainer"] [data-testid="stTextArea"] textarea,
    [data-testid="stAppViewContainer"] [data-testid="stSelectbox"]
    [data-baseweb="select"] span,
    [data-testid="stAppViewContainer"] [data-testid="stSelectbox"]
    [data-baseweb="select"] input {
        color:#111827 !important;
        -webkit-text-fill-color:#111827 !important;
        caret-color:#111827 !important;
    }

    [data-testid="stAppViewContainer"] [data-testid="stSelectbox"]
    [data-baseweb="select"] svg {
        color:#111827 !important;
        fill:#111827 !important;
    }

    /* Il selettore azienda in sidebar resta nero e oro. */
    [data-testid="stSidebar"] [data-testid="stSelectbox"]
    [data-baseweb="select"] > div,
    .st-key-active_company_selector [data-baseweb="select"] > div {
        background:#171A1E !important;
        background-color:#171A1E !important;
        color:#F6F2E8 !important;
        border:1px solid var(--gold) !important;
    }

    [data-testid="stSidebar"] [data-testid="stSelectbox"]
    [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-testid="stSelectbox"]
    [data-baseweb="select"] input,
    .st-key-active_company_selector [data-baseweb="select"] span,
    .st-key-active_company_selector [data-baseweb="select"] input {
        color:#F6F2E8 !important;
        -webkit-text-fill-color:#F6F2E8 !important;
    }

    [data-testid="stSidebar"] [data-testid="stSelectbox"]
    [data-baseweb="select"] svg,
    .st-key-active_company_selector [data-baseweb="select"] svg {
        color:#F6F2E8 !important;
        fill:#F6F2E8 !important;
    }

    /* Menu a tendina: tocchiamo soltanto listbox e opzioni. */
    [data-baseweb="popover"] [role="listbox"] {
        background:#FFFFFF !important;
        background-color:#FFFFFF !important;
        border:1px solid #BFA15A !important;
        border-radius:8px !important;
        box-shadow:0 12px 30px rgba(0,0,0,.28) !important;
    }

    [data-baseweb="popover"] [role="option"] {
        background:#FFFFFF !important;
        color:#111827 !important;
        -webkit-text-fill-color:#111827 !important;
    }

    [data-baseweb="popover"] [role="option"] span,
    [data-baseweb="popover"] [role="option"] div {
        color:#111827 !important;
        -webkit-text-fill-color:#111827 !important;
    }

    [data-baseweb="popover"] [role="option"]:hover,
    [data-baseweb="popover"] [role="option"][aria-selected="true"] {
        background:#E9EDF2 !important;
        color:#111827 !important;
    }

    /* Calendario: tocchiamo soltanto il calendario, non il popover intero. */
    [data-baseweb="calendar"] {
        background:#FFFFFF !important;
        background-color:#FFFFFF !important;
        color:#111827 !important;
        border:1px solid #BFA15A !important;
    }

    [data-baseweb="calendar"] [role="grid"],
    [data-baseweb="calendar"] [role="row"],
    [data-baseweb="calendar"] [role="columnheader"],
    [data-baseweb="calendar"] [role="gridcell"],
    [data-baseweb="calendar"] button,
    [data-baseweb="calendar"] span {
        color:#111827 !important;
        -webkit-text-fill-color:#111827 !important;
    }

    [data-baseweb="calendar"] button {
        background:transparent !important;
        border-color:transparent !important;
    }

    [data-baseweb="calendar"] button:hover {
        background:#E9EDF2 !important;
    }

    [data-baseweb="calendar"] button[aria-selected="true"] {
        background:#FF5C50 !important;
        color:#FFFFFF !important;
        -webkit-text-fill-color:#FFFFFF !important;
        border-radius:999px !important;
    }

    [data-baseweb="calendar"] button[aria-selected="true"] * {
        color:#FFFFFF !important;
        -webkit-text-fill-color:#FFFFFF !important;
    }

    /* Expander scuri, ma senza wildcard che altera i campi interni. */
    [data-testid="stExpander"] {
        background:#11161D !important;
        border:1px solid rgba(191,161,90,.65) !important;
        border-radius:8px !important;
    }

    [data-testid="stExpander"] summary {
        background:#11161D !important;
        color:var(--text) !important;
        border-radius:8px !important;
    }

    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary svg {
        color:var(--text) !important;
        fill:var(--text) !important;
    }

    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background:#0B0F14 !important;
        border-top:1px solid rgba(191,161,90,.35) !important;
        padding:.8rem !important;
    }

    [data-testid="stExpander"] [data-testid="stExpanderDetails"] > div > p,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] label {
        color:var(--text) !important;
    }

    /* Alert coerenti e leggibili. */
    [data-testid="stAlert"] {
        color:var(--text) !important;
    }

    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span {
        color:inherit !important;
    }

    /* Pulsanti disabilitati: contrasto sufficiente, niente bianco su bianco. */
    div.stButton > button:disabled,
    div.stFormSubmitButton > button:disabled,
    [data-testid="stDownloadButton"] button:disabled {
        background:#252A31 !important;
        color:#9EA4AD !important;
        border-color:#555B64 !important;
        opacity:1 !important;
    }

    div.stButton > button:disabled *,
    div.stFormSubmitButton > button:disabled *,
    [data-testid="stDownloadButton"] button:disabled * {
        color:#9EA4AD !important;
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
        "selected_prospect_id": None,
        "pending_prospect_conversion": None,
        "auth_user": None,
        "auth_email": None,
        "auth_accesses": [],
        "auth_permissions": [],
        "auth_role": None,
        "auth_name": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


@st.cache_resource
def init_db():
    return get_db()


@st.cache_resource
def init_auth_client():
    return get_auth_client()


db = init_db()
auth_client = init_auth_client()

ITALY_TIMEZONE = ZoneInfo("Europe/Rome")


def now_italy() -> datetime:
    """Ora corrente italiana con ora legale automatica."""
    return datetime.now(ITALY_TIMEZONE)


def today_italy() -> date:
    """Data corrente secondo il fuso Europe/Rome."""
    return now_italy().date()


def to_italy_datetime(value: Any) -> datetime | None:
    """
    Converte timestamp Supabase/UTC nell'ora italiana.

    I datetime privi di fuso vengono trattati come UTC, perché
    Streamlit Cloud e Supabase lavorano normalmente in UTC.
    """
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))

    return parsed.astimezone(ITALY_TIMEZONE)


def format_datetime_italy(value: Any) -> str:
    parsed = to_italy_datetime(value)
    return parsed.strftime("%d/%m/%Y · %H:%M") if parsed else "—"


@st.cache_data(ttl=30)
def load_companies() -> list[dict[str, Any]]:
    email = st.session_state.get("auth_email")
    if not email:
        return []

    accesses = elenco_accessi_utente(db, email)
    st.session_state.auth_accesses = accesses
    allowed_ids = {row["azienda_id"] for row in accesses}
    return [
        company for company in elenco_aziende(db)
        if company["id"] in allowed_ids
    ]



PAGE_PERMISSIONS = {
    "Reception": "reception.visualizza",
    "Pacchetti": "pacchetti.gestisci",
    "Abbonamenti": "abbonamenti.gestisci",
    "Clienti": "clienti.visualizza",
    "Contabilità": "contabilita.visualizza",
    "Magazzino": "magazzino.visualizza",
    "Report": "report.visualizza",
    "Admin": "admin.visualizza",
    "Azienda": "azienda.modifica",
}


def current_access() -> dict[str, Any] | None:
    company_id = st.session_state.get("active_company_id")
    accesses = st.session_state.get("auth_accesses") or []
    for access in accesses:
        if access.get("azienda_id") == company_id:
            return access
    return None


def refresh_current_permissions() -> None:
    access = current_access()
    st.session_state.auth_permissions = (
        access.get("permessi") or [] if access else []
    )
    st.session_state.auth_role = access.get("ruolo_nome") if access else None
    st.session_state.auth_name = access.get("nome_visualizzato") if access else None


def has_permission(code: str) -> bool:
    return code in (st.session_state.get("auth_permissions") or [])


def require_permission(code: str) -> None:
    if not has_permission(code):
        st.error("Non hai il permesso per eseguire questa operazione.")
        st.stop()


def logout() -> None:
    try:
        auth_client.auth.sign_out()
    except Exception:
        pass
    for key in (
        "auth_user", "auth_email", "auth_accesses",
        "auth_permissions", "auth_role", "auth_name",
        "active_company_id",
    ):
        st.session_state[key] = None if key != "auth_accesses" else []
    load_companies.clear()
    st.rerun()


def login_page() -> None:
    st.markdown("<div style='max-width:520px;margin:7vh auto 0 auto'>", unsafe_allow_html=True)
    st.title("KREO")
    st.caption("Accesso al gestionale")

    login_tab, setup_tab = st.tabs(["Accedi", "Prima configurazione"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email").strip().lower()
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Accedi", use_container_width=True)
        if submitted:
            try:
                result = auth_client.auth.sign_in_with_password({
                    "email": email,
                    "password": password,
                })
                user = getattr(result, "user", None)
                if not user:
                    raise RuntimeError("Credenziali non valide.")
                st.session_state.auth_user = str(user.id)
                st.session_state.auth_email = str(user.email).lower()
                load_companies.clear()
                accesses = elenco_accessi_utente(db, st.session_state.auth_email)
                st.session_state.auth_accesses = accesses
                if not accesses:
                    st.warning("Utente autenticato, ma non ancora abilitato a nessuna azienda.")
                else:
                    st.session_state.active_company_id = accesses[0]["azienda_id"]
                    refresh_current_permissions()
                    registra_audit_accesso(db, {
                        "azienda_id": accesses[0]["azienda_id"],
                        "email": st.session_state.auth_email,
                        "azione": "login",
                    })
                    st.rerun()
            except Exception as exc:
                st.error(f"Accesso non riuscito: {exc}")

    with setup_tab:
        st.caption("Usare soltanto per creare il primo Super Admin del gestionale.")
        with st.form("setup_form"):
            name = st.text_input("Nome e cognome", key="setup_name")
            email = st.text_input("Email", key="setup_email").strip().lower()
            password = st.text_input("Password", type="password", key="setup_password")
            submitted = st.form_submit_button("Crea primo Super Admin", use_container_width=True)
        if submitted:
            try:
                signup = auth_client.auth.sign_up({"email": email, "password": password})
                user = getattr(signup, "user", None)
                if not user:
                    raise RuntimeError("Utente Auth non creato. Controlla la conferma email di Supabase.")
                companies = elenco_aziende(db)
                if not companies:
                    raise RuntimeError("Nessuna azienda configurata.")
                bootstrap_super_admin(db, {
                    "azienda_id": companies[0]["id"],
                    "auth_user_id": str(user.id),
                    "email": email,
                    "nome_visualizzato": name or email,
                })
                st.success("Super Admin creato. Se Supabase richiede la conferma email, confermala prima di accedere.")
            except Exception as exc:
                st.error(f"Configurazione non completata: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)


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
def load_lesson_availability() -> list[dict[str, Any]]:
    response = (
        db.table("vista_disponibilita_lezioni")
        .select("*")
        .eq("azienda_id", load_company()["id"])
        .order("data_inizio", desc=True)
        .execute()
    )
    return response.data or []


def _lesson_availability_maps() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    by_subscription: dict[str, dict[str, Any]] = {}
    by_client: dict[str, dict[str, Any]] = {}

    for row in load_lesson_availability():
        subscription_id = row.get("abbonamento_id")
        client_id = row.get("cliente_id")

        if subscription_id:
            by_subscription[str(subscription_id)] = row

        if client_id and (
            str(client_id) not in by_client
            or row.get("corrente")
        ):
            by_client[str(client_id)] = row

    return by_subscription, by_client


def merge_lesson_availability(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_subscription, by_client = _lesson_availability_maps()
    merged: list[dict[str, Any]] = []

    for original in rows:
        row = dict(original)
        availability = None

        if row.get("abbonamento_id"):
            availability = by_subscription.get(
                str(row["abbonamento_id"])
            )

        if availability is None and row.get("cliente_id"):
            availability = by_client.get(str(row["cliente_id"]))

        if availability:
            row.update(availability)

        merged.append(row)

    return merged


@st.cache_data(ttl=10)
def load_clients() -> list[dict[str, Any]]:
    rows = elenco_clienti_operativo(
        db,
        load_company()["id"],
    )
    return merge_lesson_availability(rows)


@st.cache_data(ttl=10)
def load_prospects() -> list[dict[str, Any]]:
    response = (
        db.table("prospect")
        .select("*")
        .eq("azienda_id", load_company()["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


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
def load_recurring_expense_rules() -> list[dict[str, Any]]:
    return elenco_regole_spese_ricorrenti(
        db,
        load_company()["id"],
    )


@st.cache_data(ttl=10)
def load_expense_deadlines() -> list[dict[str, Any]]:
    return elenco_scadenze_spesa(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_expense_payments() -> list[dict[str, Any]]:
    return elenco_pagamenti_spesa(db, load_company()["id"])


@st.cache_data(ttl=10)
def load_subscriptions() -> list[dict[str, Any]]:
    rows = elenco_abbonamenti_operativo(
        db,
        load_company()["id"],
    )
    return merge_lesson_availability(rows)


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
    start_date = today_italy() - timedelta(days=days_back)
    return elenco_accessi(
        db,
        load_company()["id"],
        start_date.isoformat(),
        today_italy().isoformat(),
    )


@st.cache_data(ttl=10)
def load_inventory_products() -> list[dict[str, Any]]:
    return elenco_prodotti_magazzino(
        db,
        load_company()["id"],
    )


@st.cache_data(ttl=10)
def load_inventory_movements(
    product_id: str | None = None,
) -> list[dict[str, Any]]:
    return elenco_movimenti_magazzino(
        db,
        load_company()["id"],
        product_id,
    )


def clear_data_cache() -> None:
    load_companies.clear()
    load_company_cached.clear()
    load_prospects.clear()
    load_lesson_availability.clear()
    load_company_logo_url.clear()
    load_packages.clear()
    load_clients.clear()
    load_receipts.clear()
    load_installments.clear()
    load_suppliers.clear()
    load_expense_categories.clear()
    load_expenses.clear()
    load_recurring_expense_rules.clear()
    load_expense_deadlines.clear()
    load_expense_payments.clear()
    load_subscriptions.clear()
    load_agenda_operators.clear()
    load_bookings.clear()
    load_lesson_movements.clear()
    load_badges.clear()
    load_access_devices.clear()
    load_access_log.clear()
    load_inventory_products.clear()
    load_inventory_movements.clear()



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
    refresh_current_permissions()
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
            st.caption(
                f"Regola: {lesson_rule_text(package)} · "
                f"Stato: {'Attivo' if package.get('attivo') else 'Inattivo'}"
            )


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
    suppliers = load_suppliers()
    categories = load_expense_categories()
    supplier_map = {
        (
            supplier.get("nome_commerciale")
            or supplier.get("ragione_sociale")
            or str(supplier["id"])
        ): supplier
        for supplier in suppliers
    }
    category_map = {
        category["nome"]: category
        for category in categories
    }

    for expense in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2.1, 1.4, 1.1, 1.2, 1.2])
            with c1:
                st.write(f"**{expense.get('descrizione') or 'Spesa'}**")
                st.caption(
                    f"{expense.get('fornitore') or 'Senza fornitore'} · "
                    f"{expense.get('categoria') or 'Senza categoria'}"
                )
                if expense.get("ricorrente"):
                    st.caption("↻ Generata da regola ricorrente")
            with c2:
                st.caption("DOCUMENTO / COMPETENZA")
                st.write(f"**{expense.get('numero_documento') or '—'}**")
                st.caption(
                    f"{format_date_it(expense.get('data_documento') or expense.get('data_spesa'))}"
                    f" · {format_date_it(expense.get('competenza_mese'))}"
                )
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

            controls = st.columns([1, 1, 1])
            if expense.get("allegato_path"):
                try:
                    url = crea_url_documento_spesa(
                        db,
                        expense["allegato_path"],
                        expires_in=300,
                    )
                    controls[0].link_button(
                        "Apri documento",
                        url,
                        use_container_width=True,
                    )
                except Exception as exc:
                    controls[0].caption(f"Documento non apribile: {exc}")

            if expense.get("stato") != "annullata":
                with controls[1].popover(
                    "Modifica",
                    use_container_width=True,
                ):
                    supplier_names = list(supplier_map)
                    category_names = list(category_map)
                    current_supplier = expense.get("fornitore")
                    current_category = expense.get("categoria")

                    with st.form(
                        f"edit_expense_{expense['spesa_id']}"
                    ):
                        supplier_name = st.selectbox(
                            "Fornitore",
                            supplier_names,
                            index=(
                                supplier_names.index(current_supplier)
                                if current_supplier in supplier_names
                                else 0
                            ),
                        )
                        category_name = st.selectbox(
                            "Categoria",
                            category_names,
                            index=(
                                category_names.index(current_category)
                                if current_category in category_names
                                else 0
                            ),
                        )
                        description = st.text_input(
                            "Descrizione",
                            value=expense.get("descrizione") or "",
                        )
                        d1, d2, d3 = st.columns(3)
                        expense_date = d1.date_input(
                            "Data spesa",
                            value=date.fromisoformat(
                                str(expense.get("data_spesa"))[:10]
                            ),
                            format="DD/MM/YYYY",
                        )
                        document_date = d2.date_input(
                            "Data documento",
                            value=date.fromisoformat(
                                str(
                                    expense.get("data_documento")
                                    or expense.get("data_spesa")
                                )[:10]
                            ),
                            format="DD/MM/YYYY",
                        )
                        competence = d3.date_input(
                            "Mese competenza",
                            value=date.fromisoformat(
                                str(
                                    expense.get("competenza_mese")
                                    or expense.get("data_spesa")
                                )[:10]
                            ),
                            format="DD/MM/YYYY",
                        )
                        a1, a2, a3 = st.columns(3)
                        taxable = a1.number_input(
                            "Imponibile",
                            min_value=0.0,
                            value=float(expense.get("imponibile") or 0),
                            step=10.0,
                        )
                        vat = a2.number_input(
                            "IVA",
                            min_value=0.0,
                            value=float(expense.get("iva") or 0),
                            step=1.0,
                        )
                        total = a3.number_input(
                            "Totale",
                            min_value=0.01,
                            value=float(expense.get("totale") or 0),
                            step=10.0,
                        )
                        document_number = st.text_input(
                            "Numero documento",
                            value=expense.get("numero_documento") or "",
                        )
                        document_type = st.text_input(
                            "Tipo documento",
                            value=expense.get("tipo_documento") or "",
                        )
                        due_date = st.date_input(
                            "Nuova scadenza del residuo",
                            value=document_date,
                            format="DD/MM/YYYY",
                            help=(
                                "La modifica storicizza le vecchie scadenze "
                                "e crea una nuova scadenza per il residuo."
                            ),
                        )
                        notes = st.text_area(
                            "Note",
                            value=expense.get("note") or "",
                        )
                        reason = st.text_area(
                            "Motivo della modifica",
                            placeholder="Es. importo o competenza errati",
                        )
                        submit_edit = st.form_submit_button(
                            "Salva modifica",
                            use_container_width=True,
                        )

                    if submit_edit:
                        try:
                            if not description.strip():
                                raise ValueError(
                                    "La descrizione è obbligatoria."
                                )
                            modifica_spesa(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "spesa_id": expense["spesa_id"],
                                    "fornitore_id": supplier_map[
                                        supplier_name
                                    ]["id"],
                                    "categoria_spesa_id": category_map[
                                        category_name
                                    ]["id"],
                                    "data_spesa": expense_date.isoformat(),
                                    "descrizione": description.strip(),
                                    "imponibile": float(taxable),
                                    "iva": float(vat),
                                    "totale": float(total),
                                    "numero_documento": (
                                        document_number.strip() or None
                                    ),
                                    "tipo_documento": (
                                        document_type.strip() or None
                                    ),
                                    "data_documento": (
                                        document_date.isoformat()
                                    ),
                                    "competenza_mese": (
                                        competence.replace(day=1).isoformat()
                                    ),
                                    "data_scadenza": due_date.isoformat(),
                                    "note": notes.strip() or None,
                                    "motivo": reason.strip() or None,
                                    "utente_id": st.session_state.get(
                                        "auth_user_id"
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.success("Spesa modificata.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Spesa non modificata: {exc}")

                with controls[2].popover(
                    "Elimina",
                    use_container_width=True,
                ):
                    st.warning(
                        "La spesa verrà annullata retroattivamente, "
                        "esclusa dal conto economico e dallo scadenziario. "
                        "Gli eventuali pagamenti verranno stornati."
                    )
                    with st.form(
                        f"delete_expense_{expense['spesa_id']}"
                    ):
                        delete_reason = st.text_area(
                            "Motivo obbligatorio"
                        )
                        confirm = st.checkbox(
                            "Confermo l'eliminazione della spesa"
                        )
                        submit_delete = st.form_submit_button(
                            "Elimina definitivamente dai conteggi",
                            use_container_width=True,
                        )

                    if submit_delete:
                        try:
                            if not confirm:
                                raise ValueError(
                                    "Devi confermare l'eliminazione."
                                )
                            annulla_spesa(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "spesa_id": expense["spesa_id"],
                                    "motivo": delete_reason.strip(),
                                    "utente_id": st.session_state.get(
                                        "auth_user_id"
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.success(
                                "Spesa eliminata dai conteggi e storicizzata."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Spesa non eliminata: {exc}")


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

        st.markdown("**Azienda attiva**")

        if len(company_labels) == 1:
            selected_company_label = current_label
            st.markdown(
                '<div class="active-company-card">'
                f'<span>{selected_company_label}</span>'
                '<span class="company-chevron">◆</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            selected_company_label = st.radio(
                "Seleziona azienda",
                list(company_labels),
                index=list(company_labels).index(current_label),
                key="active_company_selector",
                label_visibility="collapsed",
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

        refresh_current_permissions()
        menu_items = [
            name for name in PAGES
            if has_permission(PAGE_PERMISSIONS[name])
        ]

        if st.session_state.get("menu") not in menu_items:
            st.session_state.menu = menu_items[0]

        selected = st.radio(
            "Menu",
            menu_items,
            key="menu",
            label_visibility="collapsed",
        )

        st.divider()
        st.write(st.session_state.get("auth_name") or st.session_state.get("auth_email") or "Utente")
        st.caption(st.session_state.get("auth_role") or "Accesso aziendale")
        st.caption(f"Versione {APP_VERSION}")
        if st.button("Esci", use_container_width=True, key="logout_button"):
            logout()

    return selected




def contractual_lessons(
    package_id: str,
    start_date: date,
    end_date: date | None,
) -> int:
    try:
        result = calcola_lezioni_contrattuali(
            db,
            {
                "pacchetto_id": package_id,
                "data_inizio": start_date.isoformat(),
                "data_fine": (
                    end_date.isoformat()
                    if end_date is not None
                    else None
                ),
            },
        )
        return int(result["lezioni_contrattuali"])
    except Exception:
        return 0


def lesson_rule_text(package: dict[str, Any]) -> str:
    mode = package.get("modalita_lezioni")

    if mode == "Settimanale":
        return (
            f"{int(package.get('lezioni_per_periodo') or 0)} "
            "lezioni a settimana"
        )

    if mode == "Mensile":
        return (
            f"{int(package.get('lezioni_per_periodo') or 0)} "
            "lezioni al mese"
        )

    return (
        f"{int(package.get('lezioni_totali') or 0)} "
        "lezioni complessive"
    )


def lesson_primary_text(
    row: dict[str, Any] | None,
) -> str:
    if not row:
        return "—"

    text = row.get("disponibilita_principale")
    if text:
        return str(text)

    balance = row.get("saldo_lezioni")
    if balance is not None:
        return f"{int(balance)} lezioni disponibili"

    return "—"


def lesson_secondary_text(
    row: dict[str, Any] | None,
) -> str:
    if not row:
        return ""

    return str(
        row.get("disponibilita_secondaria")
        or ""
    )


def render_lesson_availability(
    row: dict[str, Any] | None,
    *,
    compact: bool = False,
) -> None:
    if not row:
        st.info("Disponibilità lezioni non disponibile.")
        return

    mode = row.get("modalita_lezioni")

    if mode in ("Settimanale", "Mensile"):
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Quota del periodo",
            int(row.get("quota_periodo") or 0),
        )
        c2.metric(
            "Utilizzate nel periodo",
            int(row.get("utilizzate_periodo") or 0),
        )
        c3.metric(
            "Disponibili nel periodo",
            int(row.get("disponibili_periodo") or 0),
        )

        if not compact:
            st.caption(
                lesson_secondary_text(row)
                or (
                    f"{int(row.get('presenze_totali') or 0)} "
                    f"effettuate su "
                    f"{int(row.get('lezioni_contrattuali') or 0)} "
                    "previste nell'intero abbonamento."
                )
            )
        return

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Lezioni contrattuali",
        int(row.get("lezioni_contrattuali") or 0),
    )
    c2.metric(
        "Lezioni effettuate",
        int(row.get("presenze_totali") or 0),
    )
    c3.metric(
        "Lezioni residue",
        int(row.get("saldo_complessivo") or 0),
    )


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
            availability_text = lesson_primary_text(booking)
            if availability_text != "—":
                st.caption(availability_text)

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
            today_italy() + timedelta(days=7)
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

    booking_requests = elenco_alert_prenotazioni_cliente(
        db,
        load_company()["id"],
        solo_aperti=True,
    )

    return {
        "richieste_prenotazione": booking_requests,
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
            "Richieste prenotazione App Cliente",
            alerts["richieste_prenotazione"],
            "🔔",
            "Reception",
            "Richieste App Cliente",
        ),
        ("Rate scadute", alerts["rate_scadute"], "🔴", "Contabilità", "Rate clienti"),
        ("Rate nei prossimi 7 giorni", alerts["rate_in_scadenza"], "🟡", "Contabilità", "Rate clienti"),
        ("Certificati scaduti o mancanti", alerts["certificati_scaduti"], "🔴", "Clienti", "Elenco clienti"),
        ("Certificati in scadenza", alerts["certificati_in_scadenza"], "🟡", "Clienti", "Elenco clienti"),
        ("Abbonamenti scaduti", alerts["abbonamenti_scaduti"], "🔴", "Abbonamenti", "Elenco"),
        ("Abbonamenti in scadenza", alerts["abbonamenti_in_scadenza"], "🟡", "Abbonamenti", "Elenco"),
    ]

    st.markdown(
        '<div class="reception-section-title">Alert operativi</div>',
        unsafe_allow_html=True,
    )

    for index, (title, rows, icon, page, action) in enumerate(groups):
        with st.container(border=True):
            c1, c2, c3 = st.columns([.55, 3.4, 1.15])
            with c1:
                st.markdown(f"### {icon} {len(rows)}")
            with c2:
                st.write(f"**{title}**")
                if not rows:
                    st.caption("Nessuna segnalazione.")
                else:
                    details = []
                    for row in rows[:2]:
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
                        detail = (
                            row.get("data_scadenza")
                            or row.get("data_fine_prevista")
                            or row.get("certificato_stato")
                            or ""
                        )
                        if detail and str(detail)[:4].isdigit():
                            detail = format_date_it(detail)
                        details.append(
                            name + (f" · {detail}" if detail else "")
                        )
                    st.caption("  \n".join(details))
                    if len(rows) > 2:
                        st.caption(f"+ altri {len(rows) - 2}")
            with c3:
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
        "Disponibilità App Cliente",
        "Indisponibilità trainer",
        "Richieste App Cliente",
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
        today = today_italy()
        rows = load_bookings(
            today.isoformat(),
            today.isoformat(),
        )
        active_rows = [
            row for row in rows
            if row.get("stato") != "annullata"
        ]

        st.markdown(
            '<div class="reception-section-title">Azioni rapide</div>',
            unsafe_allow_html=True,
        )
        quick_actions = [
            ("👤＋", "Nuovo cliente", "goto", ("Clienti", "Nuovo cliente")),
            ("🧑‍💼＋", "Nuovo prospect", "goto", ("Clienti", "Nuovo prospect")),
            ("€", "Registra incasso", "goto", ("Contabilità", "Nuovo incasso")),
            ("🚪", "Accesso tornello", "reception", "Tornello e accessi"),
            ("📅", "Agenda", "reception", "Agenda settimanale"),
            ("🖨", "Stampa ricevuta", "goto", ("Contabilità", "Ricevute")),
            ("✈", "Messaggio cliente", "future", None),
        ]
        quick_cols = st.columns(len(quick_actions), gap="small")
        for index, (
            icon,
            label,
            action_type,
            target,
        ) in enumerate(quick_actions):
            with quick_cols[index]:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="quick-action-icon">{icon}</div>'
                        f'<div class="quick-action-label">{label}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Apri",
                        key=f"quick_reception_{index}",
                        use_container_width=True,
                    ):
                        if action_type == "goto":
                            goto(target[0], target[1])
                        elif action_type == "reception":
                            st.session_state.pending_reception_action = target
                            st.rerun()
                        else:
                            st.info("Funzione in preparazione.")

        st.divider()

        left, right = st.columns([2.15, 1.05], gap="large")

        with left:
            st.markdown(
                '<div class="agenda-heading">'
                '<div class="reception-section-title">Agenda di oggi</div>'
                f'<div style="color:var(--gold2);font-weight:700;">'
                f'📅 {format_date_it(today.isoformat())}</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Prenotazioni", len(active_rows))
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

            if rows:
                for booking in rows:
                    booking_card(
                        booking,
                        key_prefix="dashboard",
                    )
            else:
                st.info("Nessuna prenotazione per oggi.")

            if st.button(
                "Apri agenda completa",
                key="dashboard_open_full_agenda",
                use_container_width=True,
            ):
                st.session_state.pending_reception_action = (
                    "Agenda settimanale"
                )
                st.rerun()

        with right:
            render_reception_alerts()

        return

    elif action == "Agenda giornaliera":
        selected_day = st.date_input(
            "Giorno",
            value=today_italy(),
            format="DD/MM/YYYY",
            key="daily_agenda_date",
        )
        daily_agenda(selected_day)

    elif action == "Agenda settimanale":
        selected_day = st.date_input(
            "Settimana contenente il giorno",
            value=today_italy(),
            format="DD/MM/YYYY",
            key="weekly_agenda_date",
        )
        week_start, week_end = week_bounds(selected_day)
        st.caption(
            f"Settimana {week_start.strftime('%d/%m/%Y')} – "
            f"{week_end.strftime('%d/%m/%Y')}"
        )
        weekly_agenda(selected_day)

    elif action == "Disponibilità App Cliente":
        st.subheader("Slot prenotabili dall'App Cliente")
        st.caption(
            "Enzo e Federica hanno disponibilità automatica tutti i giorni "
            "dalle 07:30 alle 20:30, con lezioni da 60 minuti. "
            "Prenotazioni e indisponibilità aggiornano automaticamente "
            "gli slot visibili al cliente."
        )

        operators = [
            row for row in load_agenda_operators()
            if row.get("attivo", True)
        ]
        if not operators:
            st.warning(
                "Crea prima almeno un operatore attivo "
                "in Operatori agenda."
            )
            return

        operator_labels = {
            row["nome_visualizzato"]: row
            for row in operators
        }

        with st.form("create_customer_app_slot"):
            c1, c2, c3 = st.columns(3)
            slot_date = c1.date_input(
                "Data primo slot",
                value=today_italy(),
                format="DD/MM/YYYY",
            )
            operator_label = c2.selectbox(
                "Operatore",
                list(operator_labels),
            )
            capacity = c3.number_input(
                "Capienza",
                min_value=1,
                max_value=20,
                value=1,
                step=1,
            )

            t1, t2, t3 = st.columns(3)
            start_time = t1.time_input(
                "Ora inizio",
                value=time(9, 0),
                step=900,
            )
            end_time = t2.time_input(
                "Ora fine",
                value=time(10, 0),
                step=900,
            )
            repetitions = t3.number_input(
                "Ripeti ogni settimana",
                min_value=1,
                max_value=52,
                value=1,
                step=1,
                help="1 crea soltanto la data selezionata.",
            )

            booking_type = st.text_input(
                "Tipologia",
                value="Lezione",
            )
            notes = st.text_input("Note interne")

            save_slot = st.form_submit_button(
                "Pubblica disponibilità",
                use_container_width=True,
            )

        if save_slot:
            try:
                result = salva_slot_app_cliente(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "operatore_id": operator_labels[
                            operator_label
                        ]["id"],
                        "data_slot": slot_date.isoformat(),
                        "ora_inizio": start_time.strftime("%H:%M:%S"),
                        "ora_fine": end_time.strftime("%H:%M:%S"),
                        "capienza": int(capacity),
                        "tipologia": booking_type.strip() or "Lezione",
                        "note": notes.strip() or None,
                        "ripetizioni_settimanali": int(repetitions),
                    },
                )
                clear_data_cache()
                st.success(
                    f"Disponibilità pubblicata: "
                    f"{result.get('slot_generati_o_aggiornati', repetitions)} "
                    "slot."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Slot non salvato: {exc}")

        range_start = today_italy()
        range_end = range_start + timedelta(days=60)
        slots = elenco_slot_app_cliente(
            db,
            load_company()["id"],
            range_start.isoformat(),
            range_end.isoformat(),
        )

        st.subheader("Prossimi slot pubblicati")
        if not slots:
            st.info("Nessuno slot pubblicato nei prossimi 60 giorni.")
        else:
            for slot in slots:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(
                        [1.25, 1.35, 1, .75]
                    )
                    c1.write(
                        f"**{format_date_it(slot['data_slot'])}**"
                    )
                    c1.caption(
                        f"{format_time_it(slot['ora_inizio'])} – "
                        f"{format_time_it(slot['ora_fine'])}"
                    )
                    c2.write(
                        f"**{slot.get('operatore') or 'Operatore'}**"
                    )
                    c2.caption(slot.get("tipologia") or "Lezione")
                    c3.metric(
                        "Posti",
                        (
                            f"{slot.get('posti_disponibili', 0)} / "
                            f"{slot.get('capienza', 1)}"
                        ),
                    )

                    desired_active = not bool(slot.get("attivo"))
                    label = (
                        "Riattiva"
                        if desired_active
                        else "Disattiva"
                    )
                    if c4.button(
                        label,
                        key=f"toggle_slot_{slot['slot_id']}",
                        use_container_width=True,
                    ):
                        try:
                            cambia_stato_slot_app_cliente(
                                db,
                                {
                                    "slot_id": slot["slot_id"],
                                    "attivo": desired_active,
                                },
                            )
                            clear_data_cache()
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Stato slot non aggiornato: {exc}"
                            )

    elif action == "Indisponibilità trainer":
        st.subheader("Ferie, permessi e indisponibilità")
        st.caption(
            "Enzo e Federica sono disponibili tutti i giorni dalle "
            "07:30 alle 20:30. Le prenotazioni già presenti, anche se "
            "create dalla Reception o dai trainer, occupano "
            "automaticamente il relativo orario."
        )

        if not has_permission("agenda.indisponibilita"):
            st.warning(
                "Non hai il permesso per modificare le disponibilità."
            )
            return

        operators = [
            row for row in load_agenda_operators()
            if row.get("attivo", True)
        ]
        operator_map = {
            row["nome_visualizzato"]: row
            for row in operators
        }

        with st.form("trainer_unavailability_form"):
            c1, c2, c3 = st.columns(3)
            operator_name = c1.selectbox(
                "Trainer",
                list(operator_map),
            )
            start_date = c2.date_input(
                "Dal",
                value=today_italy(),
                format="DD/MM/YYYY",
            )
            end_date = c3.date_input(
                "Al",
                value=today_italy(),
                format="DD/MM/YYYY",
            )

            full_day = st.checkbox(
                "Giornata intera",
                value=True,
            )

            t1, t2 = st.columns(2)
            start_time = t1.time_input(
                "Dalle",
                value=time(7, 30),
                step=1800,
                disabled=full_day,
            )
            end_time = t2.time_input(
                "Alle",
                value=time(20, 30),
                step=1800,
                disabled=full_day,
            )

            reason = st.selectbox(
                "Motivo",
                [
                    "Ferie",
                    "Malattia",
                    "Infortunio",
                    "Permesso",
                    "Formazione",
                    "Altro",
                ],
            )
            notes = st.text_area("Note")
            save = st.form_submit_button(
                "Escludi disponibilità",
                use_container_width=True,
            )

        if save:
            try:
                if end_date < start_date:
                    raise ValueError(
                        "La data finale non può precedere quella iniziale."
                    )

                salva_indisponibilita_operatore(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "operatore_id": operator_map[
                            operator_name
                        ]["id"],
                        "data_inizio": start_date.isoformat(),
                        "data_fine": end_date.isoformat(),
                        "giornata_intera": full_day,
                        "ora_inizio": start_time.strftime("%H:%M:%S"),
                        "ora_fine": end_time.strftime("%H:%M:%S"),
                        "motivo": reason,
                        "note": notes.strip() or None,
                        "utente_id": st.session_state.get(
                            "auth_user_id"
                        ),
                    },
                )
                clear_data_cache()
                st.success("Indisponibilità registrata.")
                st.rerun()
            except Exception as exc:
                st.error(
                    f"Indisponibilità non registrata: {exc}"
                )

        range_start = today_italy() - timedelta(days=30)
        range_end = today_italy() + timedelta(days=180)
        exclusions = elenco_indisponibilita_operatori(
            db,
            load_company()["id"],
            range_start.isoformat(),
            range_end.isoformat(),
        )

        st.subheader("Indisponibilità attive")
        if not exclusions:
            st.info("Nessuna indisponibilità registrata.")
        else:
            for item in exclusions:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(
                        [1.4, 1.4, 1.7, .8]
                    )
                    c1.write(
                        f"**{item.get('operatore') or 'Trainer'}**"
                    )
                    c2.write(
                        f"**{format_date_it(item['data_inizio'])} – "
                        f"{format_date_it(item['data_fine'])}**"
                    )
                    if item.get("giornata_intera"):
                        c2.caption("Giornata intera")
                    else:
                        c2.caption(
                            f"{format_time_it(item.get('ora_inizio'))} – "
                            f"{format_time_it(item.get('ora_fine'))}"
                        )
                    c3.write(f"**{item.get('motivo')}**")
                    c3.caption(item.get("note") or "—")

                    if c4.button(
                        "Rimuovi",
                        key=(
                            "remove_unavailability_"
                            f"{item['indisponibilita_id']}"
                        ),
                        use_container_width=True,
                    ):
                        try:
                            elimina_indisponibilita_operatore(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "indisponibilita_id": item[
                                        "indisponibilita_id"
                                    ],
                                },
                            )
                            clear_data_cache()
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Indisponibilità non rimossa: {exc}"
                            )

        st.divider()
        st.subheader("Rigenerazione disponibilità")
        st.caption(
            "Ricrea gli slot standard dei prossimi 90 giorni. "
            "Prenotazioni e indisponibilità continuano a prevalere."
        )
        if st.button(
            "Rigenera disponibilità Enzo e Federica",
            use_container_width=True,
        ):
            try:
                result = rigenera_slot_operatori(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "dal": today_italy().isoformat(),
                        "al": (
                            today_italy() + timedelta(days=90)
                        ).isoformat(),
                    },
                )
                clear_data_cache()
                st.success(
                    f"Disponibilità aggiornate: "
                    f"{result.get('slot_generati_o_aggiornati', 0)} slot."
                )
            except Exception as exc:
                st.error(
                    f"Disponibilità non rigenerate: {exc}"
                )

    elif action == "Richieste App Cliente":
        st.subheader("Richieste di prenotazione")
        st.caption(
            "Le richieste inviate dall'Area Cliente restano in attesa "
            "finché Reception o trainer non le confermano o rifiutano."
        )

        requests = elenco_alert_prenotazioni_cliente(
            db,
            load_company()["id"],
            solo_aperti=True,
        )

        if not requests:
            st.success("Nessuna richiesta di prenotazione da gestire.")
        else:
            st.metric("Richieste aperte", len(requests))

            for request in requests:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.7, 1.4, 1.1])
                    with c1:
                        st.write(
                            f"**{request.get('cliente') or 'Cliente'}**"
                        )
                        st.caption(
                            request.get("email")
                            or request.get("telefono")
                            or "Nessun recapito"
                        )
                    with c2:
                        st.write(
                            f"**{format_date_it(request.get('data_prenotazione'))}**"
                        )
                        st.caption(
                            f"{format_time_it(request.get('ora_inizio'))} – "
                            f"{format_time_it(request.get('ora_fine'))} · "
                            f"{request.get('operatore') or 'Trainer da definire'}"
                        )
                    with c3:
                        st.write("**In attesa**")
                        st.caption(
                            format_datetime_italy(
                                request.get("created_at")
                            )
                        )

                    if request.get("tipologia"):
                        st.caption(
                            f"Tipologia: {request['tipologia']}"
                        )

                    reason = st.text_input(
                        "Motivazione del rifiuto",
                        key=f"reject_reason_{request['alert_id']}",
                        placeholder=(
                            "Compilare soltanto in caso di rifiuto"
                        ),
                    )

                    actions_cols = st.columns(3)

                    if actions_cols[0].button(
                        "Conferma",
                        key=f"confirm_app_request_{request['alert_id']}",
                        use_container_width=True,
                    ):
                        try:
                            cambia_stato_prenotazione(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "prenotazione_id": request[
                                        "prenotazione_id"
                                    ],
                                    "stato": "confermata",
                                    "motivo": (
                                        "Confermata da Reception/Trainer"
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.success("Prenotazione confermata.")
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Prenotazione non confermata: {exc}"
                            )

                    if actions_cols[1].button(
                        "Rifiuta",
                        key=f"reject_app_request_{request['alert_id']}",
                        use_container_width=True,
                    ):
                        try:
                            if not reason.strip():
                                raise ValueError(
                                    "Inserisci la motivazione del rifiuto."
                                )
                            cambia_stato_prenotazione(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "prenotazione_id": request[
                                        "prenotazione_id"
                                    ],
                                    "stato": "annullata",
                                    "motivo": (
                                        "Rifiutata da KREO: "
                                        + reason.strip()
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.success("Richiesta rifiutata.")
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Richiesta non rifiutata: {exc}"
                            )

                    if actions_cols[2].button(
                        "Segna letta",
                        key=f"read_app_request_{request['alert_id']}",
                        use_container_width=True,
                        disabled=bool(request.get("letto")),
                    ):
                        try:
                            segna_alert_prenotazione_letto(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "alert_id": request["alert_id"],
                                    "utente_id": st.session_state.get(
                                        "auth_user_id"
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Alert non aggiornato: {exc}"
                            )

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
            value=today_italy(),
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
        today = today_italy()
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
                value=today_italy(),
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


def package_form(
    *,
    form_key: str,
    package: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    package = package or {}

    with st.form(form_key):
        nome = st.text_input(
            "Nome pacchetto *",
            value=package.get("nome") or "",
        )

        c1, c2 = st.columns(2)
        periodicita_values = list(PERIODICITA_MESI)
        periodicita_current = package.get("periodicita") or periodicita_values[0]
        periodicita = c1.selectbox(
            "Periodicità *",
            periodicita_values,
            index=(
                periodicita_values.index(periodicita_current)
                if periodicita_current in periodicita_values
                else 0
            ),
        )
        prezzo = c2.number_input(
            "Prezzo standard",
            min_value=0.0,
            step=10.0,
            value=float(package.get("prezzo_standard") or 0),
        )

        modes = ["Settimanale", "Mensile", "Pacchetto lezioni"]
        current_mode = package.get("modalita_lezioni") or "Settimanale"
        modalita = st.selectbox(
            "Modalità lezioni *",
            modes,
            index=modes.index(current_mode) if current_mode in modes else 0,
        )

        if modalita == "Settimanale":
            lezioni_per_periodo = st.number_input(
                "Lezioni a settimana",
                min_value=1,
                step=1,
                value=int(package.get("lezioni_per_periodo") or 3),
            )
            lezioni_totali = 0
            senza_scadenza = False

        elif modalita == "Mensile":
            lezioni_per_periodo = st.number_input(
                "Lezioni al mese",
                min_value=1,
                step=1,
                value=int(package.get("lezioni_per_periodo") or 12),
            )
            lezioni_totali = 0
            senza_scadenza = False

        else:
            lezioni_per_periodo = 0
            lezioni_totali = st.number_input(
                "Numero totale di lezioni",
                min_value=1,
                step=1,
                value=int(package.get("lezioni_totali") or 20),
            )
            senza_scadenza = True
            st.info(
                "Il pacchetto a lezioni non ha una scadenza temporale: "
                "termina quando il saldo raggiunge zero."
            )

        attivo = st.checkbox(
            "Pacchetto attivo",
            value=bool(package.get("attivo", True)),
        )

        submitted = st.form_submit_button(
            "Salva pacchetto",
            use_container_width=True,
        )

    if not submitted:
        return None

    if not nome.strip():
        raise ValueError("Il nome del pacchetto è obbligatorio.")

    return {
        "azienda_id": load_company()["id"],
        "pacchetto_id": package.get("id"),
        "nome": nome.strip(),
        "periodicita": periodicita,
        "prezzo_standard": float(prezzo),
        "durata_numero": PERIODICITA_MESI[periodicita],
        "durata_unita": "mesi",
        "modalita_lezioni": modalita,
        "lezioni_per_periodo": int(lezioni_per_periodo),
        "lezioni_totali": int(lezioni_totali),
        "lezioni_standard": (
            int(lezioni_totali)
            if modalita == "Pacchetto lezioni"
            else 0
        ),
        "senza_scadenza": senza_scadenza,
        "attivo": attivo,
    }


def page_packages() -> None:
    header(
        "Pacchetti",
        "Listino generale, regole lezioni e modifica pacchetti.",
    )

    action = st.selectbox(
        "Operazione",
        [
            "Elenco pacchetti",
            "Nuovo pacchetto",
            "Modifica pacchetto",
        ],
    )

    if action == "Elenco pacchetti":
        rows = load_packages()
        if not rows:
            st.info("Nessun pacchetto registrato.")
            return
        render_packages_cards(rows)
        return

    if action == "Nuovo pacchetto":
        try:
            payload = package_form(
                form_key="new_package_form",
            )
            if payload:
                salva_pacchetto(db, payload)
                clear_data_cache()
                st.success("Pacchetto salvato.")
                st.rerun()
        except Exception as exc:
            st.error(f"Errore durante il salvataggio: {exc}")
        return

    packages = load_packages()
    if not packages:
        st.info("Nessun pacchetto da modificare.")
        return

    package_map = {
        package["nome"]: package
        for package in packages
    }
    selected_name = st.selectbox(
        "Pacchetto da modificare",
        list(package_map),
    )
    selected_package = package_map[selected_name]

    try:
        payload = package_form(
            form_key=f"edit_package_{selected_package['id']}",
            package=selected_package,
        )
        if payload:
            salva_pacchetto(db, payload)
            clear_data_cache()
            st.success("Pacchetto aggiornato.")
            st.rerun()
    except Exception as exc:
        st.error(f"Errore durante la modifica: {exc}")



# ============================================================
# PROSPECT
# ============================================================

PROSPECT_STATES = [
    "Nuovo",
    "Da ricontattare",
    "Interessato",
    "In valutazione",
    "Non interessato",
    "Convertito",
]


def prospect_label(row: dict[str, Any]) -> str:
    return (
        f"{row.get('cognome') or ''} "
        f"{row.get('nome') or ''}"
    ).strip()


def save_prospect(payload: dict[str, Any]) -> dict[str, Any]:
    record = {
        **payload,
        "azienda_id": load_company()["id"],
        "updated_at": now_italy().isoformat(),
    }
    prospect_id = record.pop("id", None)

    if prospect_id:
        result = (
            db.table("prospect")
            .update(record)
            .eq("id", prospect_id)
            .eq("azienda_id", load_company()["id"])
            .execute()
        )
    else:
        record["created_at"] = now_italy().isoformat()
        result = db.table("prospect").insert(record).execute()

    load_prospects.clear()
    return (result.data or [{}])[0]


def prospect_form(
    prospect: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    prospect = prospect or {}
    suffix = prospect.get("id", "new")
    c1, c2 = st.columns(2)
    nome = c1.text_input(
        "Nome *",
        value=str(prospect.get("nome") or ""),
        key=f"prospect_nome_{suffix}",
    )
    cognome = c2.text_input(
        "Cognome *",
        value=str(prospect.get("cognome") or ""),
        key=f"prospect_cognome_{suffix}",
    )

    c3, c4, c5 = st.columns(3)
    telefono = c3.text_input(
        "Telefono",
        value=str(prospect.get("telefono") or ""),
        key=f"prospect_phone_{suffix}",
    )
    whatsapp = c4.text_input(
        "WhatsApp",
        value=str(prospect.get("whatsapp") or ""),
        key=f"prospect_whatsapp_{suffix}",
    )
    email = c5.text_input(
        "Email",
        value=str(prospect.get("email") or ""),
        key=f"prospect_email_{suffix}",
    )

    c6, c7, c8 = st.columns(3)
    fonte = c6.text_input(
        "Fonte / provenienza",
        value=str(prospect.get("fonte") or ""),
        placeholder="Passaparola, Instagram, sito...",
        key=f"prospect_source_{suffix}",
    )
    interesse = c7.text_input(
        "Interesse",
        value=str(prospect.get("interesse") or ""),
        placeholder="Personal training, coaching...",
        key=f"prospect_interest_{suffix}",
    )
    stato = c8.selectbox(
        "Stato",
        PROSPECT_STATES[:-1],
        index=(
            PROSPECT_STATES[:-1].index(prospect.get("stato"))
            if prospect.get("stato") in PROSPECT_STATES[:-1]
            else 0
        ),
        key=f"prospect_state_{suffix}",
    )

    c9, c10 = st.columns(2)
    operatore = c9.text_input(
        "Operatore assegnato",
        value=str(prospect.get("operatore_assegnato") or ""),
        key=f"prospect_operator_{suffix}",
    )
    data_primo_contatto = c10.date_input(
        "Data primo contatto",
        value=(
            date.fromisoformat(str(prospect["data_primo_contatto"]))
            if prospect.get("data_primo_contatto")
            else today_italy()
        ),
        format="DD/MM/YYYY",
        key=f"prospect_date_{suffix}",
    )

    note = st.text_area(
        "Note",
        value=str(prospect.get("note") or ""),
        key=f"prospect_notes_{suffix}",
    )

    if st.button(
        "Salva prospect",
        use_container_width=True,
        key=f"save_prospect_{suffix}",
    ):
        if not nome.strip() or not cognome.strip():
            st.error("Nome e cognome sono obbligatori.")
            return None
        return {
            "id": prospect.get("id"),
            "nome": nome.strip(),
            "cognome": cognome.strip(),
            "telefono": telefono.strip() or None,
            "whatsapp": whatsapp.strip() or None,
            "email": email.strip() or None,
            "fonte": fonte.strip() or None,
            "interesse": interesse.strip() or None,
            "stato": stato,
            "operatore_assegnato": operatore.strip() or None,
            "data_primo_contatto": data_primo_contatto.isoformat(),
            "note": note.strip() or None,
        }
    return None


def prospect_list() -> None:
    rows = [
        row for row in load_prospects()
        if row.get("stato") != "Convertito"
    ]

    c1, c2, c3 = st.columns([2.5, 1.2, 1.2])
    search = c1.text_input(
        "Cerca prospect",
        placeholder="Nome, telefono, WhatsApp o email",
        key="prospect_search",
    )
    status_filter = c2.selectbox(
        "Stato",
        ["Tutti"] + PROSPECT_STATES[:-1],
        key="prospect_status_filter",
    )
    source_filter = c3.text_input(
        "Fonte",
        key="prospect_source_filter",
    )

    filtered = []
    for row in rows:
        searchable = " ".join(
            str(row.get(key) or "")
            for key in [
                "nome", "cognome", "telefono",
                "whatsapp", "email", "fonte", "interesse",
            ]
        ).lower()
        if search and search.lower() not in searchable:
            continue
        if status_filter != "Tutti" and row.get("stato") != status_filter:
            continue
        if source_filter and source_filter.lower() not in str(
            row.get("fonte") or ""
        ).lower():
            continue
        filtered.append(row)

    st.info(f"{len(filtered)} prospect visualizzati")

    if not filtered:
        st.info("Nessun prospect con i filtri selezionati.")
        return

    for row in filtered:
        with st.container(border=True):
            c_name, c_contact, c_state, c_actions = st.columns(
                [2.1, 1.7, 1.25, 2.4]
            )
            with c_name:
                st.markdown(f"### {prospect_label(row)}")
                tags = [
                    value for value in [
                        row.get("fonte"),
                        row.get("interesse"),
                    ]
                    if value
                ]
                if tags:
                    st.caption(" · ".join(tags))
            with c_contact:
                st.caption("CONTATTI")
                st.write(
                    row.get("whatsapp")
                    or row.get("telefono")
                    or "—"
                )
                st.caption(row.get("email") or "")
            with c_state:
                st.caption("STATO")
                st.markdown(
                    f'<span class="prospect-status">'
                    f'{row.get("stato") or "Nuovo"}</span>',
                    unsafe_allow_html=True,
                )
                if row.get("data_primo_contatto"):
                    st.caption(
                        "Dal "
                        + format_date_it(
                            row["data_primo_contatto"]
                        )
                    )
            with c_actions:
                a1, a2 = st.columns(2)
                if a1.button(
                    "Modifica",
                    key=f"edit_prospect_{row['id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_prospect_id = row["id"]
                    goto("Clienti", "Modifica prospect")
                if a2.button(
                    "Trasforma in cliente",
                    key=f"convert_prospect_{row['id']}",
                    use_container_width=True,
                ):
                    st.session_state.pending_prospect_conversion = row
                    goto("Clienti", "Nuovo cliente")


def prospect_page(action: str) -> None:
    if action == "Prospect":
        top1, top2 = st.columns([4, 1])
        with top1:
            st.subheader("Prospect")
            st.caption(
                "Contatti acquisiti che non hanno ancora "
                "attivato un abbonamento."
            )
        with top2:
            if st.button(
                "Nuovo prospect",
                use_container_width=True,
                key="new_prospect_top",
            ):
                goto("Clienti", "Nuovo prospect")
        prospect_list()
        return

    if action == "Nuovo prospect":
        st.subheader("Nuovo prospect")
        payload = prospect_form()
        if payload:
            try:
                save_prospect(payload)
                st.toast("Prospect salvato.", icon="✅")
                goto("Clienti", "Prospect")
            except Exception as exc:
                st.error(f"Errore durante il salvataggio: {exc}")
        return

    prospects = load_prospects()
    if not prospects:
        st.info("Nessun prospect da modificare.")
        return
    selected_id = st.session_state.get("selected_prospect_id")
    options = {
        prospect_label(row): row
        for row in prospects
        if row.get("stato") != "Convertito"
    }
    if not options:
        st.info("Nessun prospect attivo da modificare.")
        return

    default_index = 0
    if selected_id:
        for index, row in enumerate(options.values()):
            if row["id"] == selected_id:
                default_index = index
                break

    selected_label = st.selectbox(
        "Prospect",
        list(options),
        index=default_index,
        key="prospect_edit_selector",
    )
    selected = options[selected_label]
    payload = prospect_form(selected)
    if payload:
        try:
            save_prospect(payload)
            st.toast("Prospect aggiornato.", icon="✅")
            goto("Clienti", "Prospect")
        except Exception as exc:
            st.error(f"Errore durante la modifica: {exc}")


# ============================================================
# CLIENTI - REGISTRAZIONE
# ============================================================

def new_customer_flow() -> None:
    prospect_source = st.session_state.get(
        "pending_prospect_conversion"
    ) or {}

    if prospect_source:
        st.info(
            "Conversione prospect in cliente: "
            f"{prospect_label(prospect_source)}. "
            "Completa pacchetto, abbonamento e pagamenti."
        )

    packages = load_packages()
    if not packages:
        st.warning("Prima devi registrare almeno un pacchetto.")
        return

    st.subheader("1. Anagrafica")
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome *", value=str(prospect_source.get("nome") or ""))
    cognome = c2.text_input("Cognome *", value=str(prospect_source.get("cognome") or ""))

    c3, c4, c5 = st.columns(3)
    telefono = c3.text_input("Telefono", value=str(prospect_source.get("telefono") or ""))
    whatsapp = c4.text_input("WhatsApp", value=str(prospect_source.get("whatsapp") or ""))
    email = c5.text_input("Email", value=str(prospect_source.get("email") or ""))

    c6, c7 = st.columns(2)
    codice_fiscale = c6.text_input("Codice fiscale")
    partita_iva = c7.text_input("Partita IVA")

    indirizzo = st.text_input("Indirizzo")
    note = st.text_area("Note", value=str(prospect_source.get("note") or ""))

    st.divider()
    st.subheader("2. Pacchetto e abbonamento")

    package_map = {p["nome"]: p for p in packages}
    package_name = st.selectbox("Pacchetto *", list(package_map))
    package = package_map[package_name]

    c8, c9 = st.columns(2)
    data_inizio = c8.date_input(
        "Data inizio",
        value=today_italy(),
        format="DD/MM/YYYY",
    )

    package_without_expiry = (
        package.get("modalita_lezioni") == "Pacchetto lezioni"
        or package.get("senza_scadenza")
    )

    if package_without_expiry:
        data_fine = None
        c9.metric(
            "Scadenza",
            "Nessuna",
            help="Il pacchetto termina quando finiscono le lezioni.",
        )
    else:
        data_fine = c9.date_input(
            "Data fine prevista",
            value=calculate_package_end(
                data_inizio,
                package["periodicita"],
            ),
            format="DD/MM/YYYY",
        )

    c10, c11 = st.columns(2)
    prezzo_concordato = c10.number_input(
        "Prezzo concordato",
        min_value=0.0,
        step=10.0,
        value=float(package["prezzo_standard"]),
    )

    lezioni_iniziali = contractual_lessons(
        package["id"],
        data_inizio,
        data_fine,
    )
    c11.metric(
        "Lezioni contrattuali",
        lezioni_iniziali,
        help=(
            f"{lesson_rule_text(package)}. "
            "Il valore è calcolato dal database sulle date effettive."
        ),
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
    genera_ricevuta_acconto = st.checkbox(
        "Genera ricevuta per l'acconto iniziale",
        value=True,
        disabled=acconto <= 0,
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
                value=today_italy(),
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
        if data_fine is not None and data_fine < data_inizio:
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
                "data_fine_prevista": (
                    data_fine.isoformat()
                    if data_fine is not None
                    else None
                ),
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

            receipt_message = ""
            if (
                acconto > 0
                and genera_ricevuta_acconto
                and result.get("incasso_id")
            ):
                receipt_result = genera_ricevuta_incasso(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "incasso_id": result["incasso_id"],
                    },
                )
                if receipt_result.get("ricevuta_id"):
                    ensure_receipt_pdf(
                        receipt_result["ricevuta_id"]
                    )
                    receipt_message = (
                        " Ricevuta dell'acconto generata."
                    )

            if prospect_source.get("id"):
                (
                    db.table("prospect")
                    .update({
                        "stato": "Convertito",
                        "cliente_id": result["cliente_id"],
                        "converted_at": now_italy().isoformat(),
                        "updated_at": now_italy().isoformat(),
                    })
                    .eq("id", prospect_source["id"])
                    .eq("azienda_id", load_company()["id"])
                    .execute()
                )
                st.session_state.pending_prospect_conversion = None
                load_prospects.clear()

            clear_data_cache()
            st.session_state.selected_customer_id = result["cliente_id"]
            st.success(
                f"Cliente salvato. Residuo iniziale: "
                f"{money(residuo_live)}.{receipt_message}"
            )
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

    residual_total = sum(
        float(row.get("residuo") or 0)
        for row in filtered
    )
    st.info(
        f"{len(filtered)} clienti visualizzati · "
        f"Residuo complessivo {money(residual_total)}"
    )

    view_mode = st.radio(
        "Visualizzazione",
        ["Schede", "Elenco"],
        horizontal=True,
        key="client_list_view_mode",
    )

    exported_clients = client_export_rows(filtered)
    render_export_controls(
        report_key="client_list",
        title="Elenco clienti",
        columns=client_export_columns(),
        rows=exported_clients,
        filters=[
            f"Stato cliente: {status_filter}",
            f"Ricerca: {search or 'nessuna'}",
        ],
        totals={
            "Numero clienti": len(exported_clients),
            "Residuo complessivo": residual_total,
        },
    )

    if view_mode == "Elenco":
        st.dataframe(
            pd.DataFrame(exported_clients),
            use_container_width=True,
            hide_index=True,
            column_config={
                "prezzo": st.column_config.NumberColumn(
                    "Prezzo iniziale",
                    format="€ %.2f",
                ),
                "pagato": st.column_config.NumberColumn(
                    "Pagato",
                    format="€ %.2f",
                ),
                "residuo": st.column_config.NumberColumn(
                    "Residuo",
                    format="€ %.2f",
                ),
                "importo_prossima_rata": (
                    st.column_config.NumberColumn(
                        "Importo prossima rata",
                        format="€ %.2f",
                    )
                ),
            },
        )
        return

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

            c1, c2, c3, c4, c5, c6 = st.columns(
                [1.35, 1, 1.35, 1, 1.25, 1.25]
            )
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

            c5.caption("LEZIONI")
            c5.write(
                f"**{lesson_primary_text(customer)}**"
            )
            secondary_lessons = lesson_secondary_text(customer)
            if secondary_lessons:
                c5.caption(secondary_lessons)

            c6.caption("CERTIFICATO")
            c6.write(
                f"**{customer.get('certificato_stato') or 'Mancante'}**"
            )

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
        "Lezioni",
        "App Cliente",
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

                package_without_expiry = (
                    package.get("modalita_lezioni")
                    == "Pacchetto lezioni"
                    or package.get("senza_scadenza")
                )

                if package_without_expiry:
                    data_fine = None
                    c2.metric(
                        "Scadenza",
                        "Nessuna",
                        help=(
                            "L'abbonamento termina con l'esaurimento "
                            "delle lezioni."
                        ),
                    )
                else:
                    stored_end = subscription.get(
                        "data_fine_reale"
                    ) or subscription.get("data_fine_prevista")
                    data_fine = c2.date_input(
                        "Data fine prevista",
                        value=(
                            date.fromisoformat(stored_end)
                            if stored_end
                            else calculate_package_end(
                                data_inizio,
                                package["periodicita"],
                            )
                        ),
                        format="DD/MM/YYYY",
                    )

                c3, c4 = st.columns(2)
                prezzo = c3.number_input(
                    "Prezzo concordato",
                    min_value=0.0,
                    step=10.0,
                    value=float(subscription["prezzo_concordato"]),
                )

                lezioni = contractual_lessons(
                    package["id"],
                    data_inizio,
                    data_fine,
                )
                c4.metric(
                    "Lezioni contrattuali ricalcolate",
                    lezioni,
                    help=(
                        f"{lesson_rule_text(package)}. "
                        "Il dato viene salvato dalla funzione centrale."
                    ),
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
                            "data_fine_prevista": (
                                data_fine.isoformat()
                                if data_fine is not None
                                else None
                            ),
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
            rate_tabs = st.tabs([
                "Piano rate attuale",
                "Rimodula rate residue",
            ])

            with rate_tabs[0]:
                rate_df = pd.DataFrame([
                    {
                        "rata_id": r["rata_id"],
                        "numero_rata": r["numero_rata"],
                        "data_scadenza": date.fromisoformat(
                            r["data_scadenza"]
                        ),
                        "importo_previsto": float(
                            r["importo_previsto"]
                        ),
                        "importo_pagato": float(
                            r["importo_pagato"]
                        ),
                        "residuo_rata": float(
                            r["residuo_rata"]
                        ),
                        "stato": r["stato"],
                        "annullata": r.get("annullata", False),
                    }
                    for r in installments
                ])

                edited_rates = st.data_editor(
                    rate_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=[
                        "rata_id",
                        "numero_rata",
                        "importo_pagato",
                        "residuo_rata",
                        "stato",
                    ],
                    column_config={
                        "rata_id": None,
                        "numero_rata": (
                            st.column_config.NumberColumn("N. rata")
                        ),
                        "data_scadenza": (
                            st.column_config.DateColumn(
                                "Scadenza",
                                format="DD/MM/YYYY",
                            )
                        ),
                        "importo_previsto": (
                            st.column_config.NumberColumn(
                                "Importo previsto",
                                format="€ %.2f",
                            )
                        ),
                        "importo_pagato": (
                            st.column_config.NumberColumn(
                                "Pagato",
                                format="€ %.2f",
                            )
                        ),
                        "residuo_rata": (
                            st.column_config.NumberColumn(
                                "Residuo",
                                format="€ %.2f",
                            )
                        ),
                        "stato": st.column_config.TextColumn("Stato"),
                        "annullata": (
                            st.column_config.CheckboxColumn("Annullata")
                        ),
                    },
                )

                motivo_rate = st.text_area(
                    "Motivo della modifica rate *",
                    key="rate_manual_edit_reason",
                )

                if st.button(
                    "Salva piano rate",
                    use_container_width=True,
                    key="save_manual_rate_plan",
                ):
                    if not motivo_rate.strip():
                        st.error(
                            "Il motivo della modifica è obbligatorio."
                        )
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
                                            "data_scadenza": (
                                                row["data_scadenza"]
                                                .isoformat()
                                            ),
                                            "importo_previsto": float(
                                                row["importo_previsto"]
                                            ),
                                            "annullata": bool(
                                                row["annullata"]
                                            ),
                                        }
                                        for _, row
                                        in edited_rates.iterrows()
                                    ],
                                },
                            )
                            clear_data_cache()
                            st.success(
                                "Piano rate aggiornato e "
                                "allocazioni ricalcolate."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Errore durante la modifica: {exc}"
                            )

            with rate_tabs[1]:
                active_installments = [
                    row for row in installments
                    if not row.get("annullata", False)
                ]
                residual_total = round(
                    sum(
                        float(row.get("residuo_rata") or 0)
                        for row in active_installments
                    ),
                    2,
                )
                paid_total = round(
                    sum(
                        float(row.get("importo_pagato") or 0)
                        for row in active_installments
                    ),
                    2,
                )

                m1, m2, m3 = st.columns(3)
                m1.metric("Già pagato", money(paid_total))
                m2.metric("Residuo da rimodulare", money(residual_total))
                m3.metric(
                    "Prezzo concordato",
                    money(float(subscription["prezzo_concordato"])),
                )

                st.info(
                    "La rimodulazione non modifica gli incassi già "
                    "registrati. Consolida le quote pagate, chiude le "
                    "vecchie quote residue e crea un nuovo piano pari "
                    "esattamente al residuo reale."
                )

                if residual_total <= 0:
                    st.success(
                        "L'abbonamento è già completamente saldato."
                    )
                else:
                    c1, c2, c3 = st.columns(3)
                    new_rate_count = c1.number_input(
                        "Numero nuove rate",
                        min_value=1,
                        max_value=24,
                        value=1,
                        step=1,
                        key="remodulation_rate_count",
                    )
                    first_due_date = c2.date_input(
                        "Prima nuova scadenza",
                        value=today_italy(),
                        format="DD/MM/YYYY",
                        key="remodulation_first_due",
                    )
                    cadence_months = c3.number_input(
                        "Mesi tra le rate",
                        min_value=1,
                        max_value=12,
                        value=1,
                        step=1,
                        key="remodulation_cadence",
                    )

                    proposed_plan = pd.DataFrame(
                        build_installment_plan(
                            residual_total,
                            int(new_rate_count),
                            first_due_date,
                            int(cadence_months),
                        )
                    )

                    edited_new_plan = st.data_editor(
                        proposed_plan,
                        use_container_width=True,
                        hide_index=True,
                        key="remodulation_plan_editor",
                        column_config={
                            "numero_rata": (
                                st.column_config.NumberColumn(
                                    "Nuova rata",
                                    min_value=1,
                                    step=1,
                                )
                            ),
                            "data_scadenza": (
                                st.column_config.DateColumn(
                                    "Scadenza",
                                    format="DD/MM/YYYY",
                                )
                            ),
                            "importo_previsto": (
                                st.column_config.NumberColumn(
                                    "Importo",
                                    min_value=0.01,
                                    format="€ %.2f",
                                )
                            ),
                        },
                    )

                    new_plan_total = round(
                        float(
                            edited_new_plan[
                                "importo_previsto"
                            ].sum()
                        ),
                        2,
                    )
                    difference = round(
                        new_plan_total - residual_total,
                        2,
                    )

                    s1, s2 = st.columns(2)
                    s1.metric(
                        "Totale nuovo piano",
                        money(new_plan_total),
                    )
                    s2.metric(
                        "Differenza",
                        money(difference),
                    )

                    remodulation_reason = st.text_area(
                        "Motivazione della rimodulazione *",
                        placeholder=(
                            "Es. Accordo con il cliente: "
                            "residuo consolidato in unica rata."
                        ),
                        key="remodulation_reason",
                    )

                    confirmation = st.checkbox(
                        "Confermo che gli importi già pagati "
                        "restano invariati.",
                        key="remodulation_confirmation",
                    )

                    if st.button(
                        "Conferma rimodulazione",
                        use_container_width=True,
                        key="confirm_rate_remodulation",
                    ):
                        if abs(difference) > 0.01:
                            st.error(
                                "Il totale del nuovo piano deve "
                                "coincidere con il residuo reale."
                            )
                        elif not remodulation_reason.strip():
                            st.error(
                                "La motivazione è obbligatoria."
                            )
                        elif not confirmation:
                            st.error(
                                "Devi confermare la conservazione "
                                "degli importi già pagati."
                            )
                        else:
                            try:
                                result = rimodula_rate_residue(
                                    db,
                                    {
                                        "azienda_id": (
                                            load_company()["id"]
                                        ),
                                        "cliente_id": customer_id,
                                        "abbonamento_id": (
                                            subscription["id"]
                                        ),
                                        "motivo": (
                                            remodulation_reason.strip()
                                        ),
                                        "nuove_rate": [
                                            {
                                                "data_scadenza": (
                                                    row[
                                                        "data_scadenza"
                                                    ].isoformat()
                                                ),
                                                "importo_previsto": (
                                                    float(
                                                        row[
                                                            "importo_previsto"
                                                        ]
                                                    )
                                                ),
                                            }
                                            for _, row
                                            in edited_new_plan.iterrows()
                                        ],
                                    },
                                )
                                clear_data_cache()
                                st.success(
                                    "Rate residue rimodulate. "
                                    f"Nuovo residuo pianificato: "
                                    f"{money(float(result['residuo']))}."
                                )
                                st.rerun()
                            except Exception as exc:
                                st.error(
                                    "Errore durante la rimodulazione: "
                                    f"{exc}"
                                )

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
            value=today_italy(),
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
        st.subheader("Lezioni del cliente")

        if not subscription:
            st.info("Nessun abbonamento operativo.")
        else:
            subscription_detail = get_abbonamento_dettaglio(
                db,
                subscription["id"],
            )
            current_subscription = (
                subscription_detail.get("abbonamento") or {}
            )
            movements = (
                subscription_detail.get("movimenti_lezioni") or []
            )

            availability = next(
                (
                    row for row in load_lesson_availability()
                    if str(row.get("abbonamento_id"))
                    == str(subscription.get("id"))
                ),
                None,
            )
            render_lesson_availability(
                availability or current_subscription
            )

            st.info(
                "La modifica non sovrascrive il saldo: crea un "
                "movimento tracciato e reversibile nello storico."
            )

            c1, c2 = st.columns(2)
            operation = c1.selectbox(
                "Operazione",
                [
                    "Aggiungi lezioni",
                    "Scala lezioni",
                ],
                key="customer_lesson_operation",
            )
            quantity = c2.number_input(
                "Numero lezioni",
                min_value=1,
                step=1,
                value=1,
                key="customer_lesson_quantity",
            )
            reason = st.text_area(
                "Motivazione obbligatoria",
                key="customer_lesson_reason",
            )

            if st.button(
                "Registra modifica lezioni",
                use_container_width=True,
            ):
                signed_quantity = (
                    int(quantity)
                    if operation == "Aggiungi lezioni"
                    else -int(quantity)
                )
                current_balance = int(
                    (
                        availability
                        or current_subscription
                    ).get(
                        "saldo_complessivo",
                        current_subscription.get(
                            "saldo_lezioni"
                        ) or 0,
                    )
                )

                if not reason.strip():
                    st.error("La motivazione è obbligatoria.")
                elif signed_quantity < 0 and abs(
                    signed_quantity
                ) > current_balance:
                    st.error(
                        "Non puoi scalare più lezioni di quelle disponibili."
                    )
                else:
                    try:
                        registra_movimento_lezioni(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "cliente_id": customer_id,
                                "abbonamento_id": subscription["id"],
                                "data_movimento": today_italy().isoformat(),
                                "tipo": (
                                    "Carico amministrativo"
                                    if signed_quantity > 0
                                    else "Scarico amministrativo"
                                ),
                                "quantita": signed_quantity,
                                "causale": reason.strip(),
                            },
                        )
                        clear_data_cache()
                        st.success("Saldo lezioni aggiornato.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore: {exc}")

            st.divider()
            st.subheader("Storico movimenti")

            if movements:
                for movement in movements:
                    with st.container(border=True):
                        c3, c4, c5 = st.columns([1.2, 1.3, 3])
                        c3.write(
                            f"**{format_date_it(movement.get('data_movimento'))}**"
                        )
                        qty = int(movement.get("quantita") or 0)
                        c4.write(f"**{qty:+d}**")
                        c5.write(
                            movement.get("causale")
                            or movement.get("tipo")
                            or "—"
                        )
            else:
                st.caption("Nessun movimento registrato.")

    with tabs[7]:
        st.subheader("Accesso App Cliente")
        st.caption(
            "Crea e gestisce l'account personale collegato "
            "esclusivamente a questa anagrafica."
        )

        company_id = load_company()["id"]

        st.subheader("Autorizzazione prenotazioni")
        current_block = bool(
            customer.get("prenotazioni_bloccate", False)
        )
        current_reason = (
            customer.get("motivo_blocco_prenotazioni") or ""
        )

        if current_block:
            st.warning(
                "Prenotazioni bloccate"
                + (
                    f": {current_reason}"
                    if current_reason
                    else ""
                )
            )
        else:
            st.success("Cliente abilitato alle prenotazioni.")

        if has_permission("clienti.blocca_prenotazioni"):
            with st.form(
                f"booking_block_customer_{customer_id}"
            ):
                desired_block = st.checkbox(
                    "Blocca le prenotazioni dall'App Cliente",
                    value=current_block,
                )
                block_reason = st.text_area(
                    "Motivo",
                    value=current_reason,
                    disabled=not desired_block,
                    help=(
                        "Esempi: morosità, sospensione disciplinare, "
                        "verifiche amministrative, richiesta direzione."
                    ),
                )
                save_block = st.form_submit_button(
                    "Salva autorizzazione prenotazioni",
                    use_container_width=True,
                )

            if save_block:
                try:
                    imposta_blocco_prenotazioni_cliente(
                        db,
                        {
                            "azienda_id": company_id,
                            "cliente_id": customer_id,
                            "bloccato": desired_block,
                            "motivo": (
                                block_reason.strip()
                                if desired_block
                                else None
                            ),
                            "utente_id": st.session_state.get(
                                "auth_user_id"
                            ),
                        },
                    )
                    clear_data_cache()
                    st.success(
                        "Autorizzazione prenotazioni aggiornata."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(
                        f"Autorizzazione non aggiornata: {exc}"
                    )
        else:
            st.caption(
                "Il blocco prenotazioni può essere modificato "
                "solo da Direzione o Super Admin."
            )

        st.divider()

        app_access = get_accesso_app_cliente(
            db,
            azienda_id=company_id,
            cliente_id=customer_id,
        )

        if app_access:
            status_label = (
                "Attivo" if app_access.get("attivo") else "Disattivato"
            )
            s1, s2, s3 = st.columns(3)
            s1.metric("Stato accesso", status_label)
            s2.metric(
                "Account collegato",
                str(app_access.get("auth_user_id") or "—")[:8] + "…",
            )
            s3.metric(
                "Creato il",
                format_datetime_italy(
                    app_access.get("created_at")
                ),
            )

            st.info(
                "La password non viene mai salvata né mostrata "
                "nel gestionale."
            )

            action_cols = st.columns(2)
            desired_active = not bool(app_access.get("attivo"))
            action_label = (
                "Riattiva accesso"
                if desired_active
                else "Disattiva accesso"
            )

            if action_cols[0].button(
                action_label,
                use_container_width=True,
                key=f"toggle_customer_app_{customer_id}",
            ):
                try:
                    aggiorna_accesso_app_cliente(
                        db,
                        accesso_id=str(app_access["id"]),
                        attivo=desired_active,
                    )
                    clear_data_cache()
                    st.success("Stato accesso aggiornato.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Accesso non aggiornato: {exc}")

            with action_cols[1].popover(
                "Reimposta password",
                use_container_width=True,
            ):
                with st.form(
                    f"reset_customer_app_password_{customer_id}"
                ):
                    new_password = st.text_input(
                        "Nuova password",
                        type="password",
                    )
                    confirm_password = st.text_input(
                        "Conferma nuova password",
                        type="password",
                    )
                    reset_submit = st.form_submit_button(
                        "Salva nuova password",
                        use_container_width=True,
                    )

                if reset_submit:
                    try:
                        if new_password != confirm_password:
                            raise ValueError(
                                "Le password non coincidono."
                            )
                        reimposta_password_utente_auth(
                            db,
                            auth_user_id=str(
                                app_access["auth_user_id"]
                            ),
                            nuova_password=new_password,
                        )
                        st.success("Password aggiornata.")
                    except Exception as exc:
                        st.error(f"Password non aggiornata: {exc}")

        else:
            default_email = (
                customer.get("email") or ""
            ).strip().lower()

            with st.form(
                f"create_customer_app_access_{customer_id}"
            ):
                st.write(
                    f"Cliente: **{customer.get('cognome')} "
                    f"{customer.get('nome')}**"
                )
                app_email = st.text_input(
                    "Email / username",
                    value=default_email,
                    help=(
                        "Sarà usata dal cliente per accedere "
                        "alla PWA KREO."
                    ),
                ).strip().lower()
                password = st.text_input(
                    "Password temporanea",
                    type="password",
                    help="Minimo 8 caratteri.",
                )
                password_confirm = st.text_input(
                    "Conferma password",
                    type="password",
                )
                create_submit = st.form_submit_button(
                    "Crea accesso App Cliente",
                    use_container_width=True,
                )

            if create_submit:
                try:
                    if not app_email:
                        raise ValueError(
                            "Inserisci l'email usata come username."
                        )
                    if password != password_confirm:
                        raise ValueError(
                            "Le password non coincidono."
                        )

                    crea_accesso_app_cliente(
                        db,
                        azienda_id=company_id,
                        cliente_id=customer_id,
                        email=app_email,
                        password=password,
                        nome_visualizzato=(
                            f"{customer.get('nome', '')} "
                            f"{customer.get('cognome', '')}"
                        ).strip(),
                    )

                    if (
                        not customer.get("email")
                        or customer.get("email").strip().lower()
                        != app_email
                    ):
                        modifica_anagrafica_cliente(
                            db,
                            {
                                "azienda_id": company_id,
                                "cliente_id": customer_id,
                                "nome": customer.get("nome"),
                                "cognome": customer.get("cognome"),
                                "telefono": customer.get("telefono"),
                                "whatsapp": customer.get("whatsapp"),
                                "email": app_email,
                                "codice_fiscale": customer.get(
                                    "codice_fiscale"
                                ),
                                "partita_iva": customer.get(
                                    "partita_iva"
                                ),
                                "indirizzo": customer.get("indirizzo"),
                                "stato": customer.get("stato") or "attivo",
                                "note": customer.get("note"),
                            },
                        )

                    clear_data_cache()
                    st.success(
                        "Accesso creato. Il cliente può entrare "
                        "subito nella PWA."
                    )
                    st.rerun()
                except Exception as exc:
                    message = str(exc)
                    if "already" in message.lower():
                        st.error(
                            "Questa email è già registrata in Supabase "
                            "Auth. Usa un'altra email."
                        )
                    else:
                        st.error(f"Accesso non creato: {message}")

    with tabs[8]:
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

        availability = next(
            (
                row for row in load_lesson_availability()
                if str(row.get("abbonamento_id"))
                == str(subscription.get("abbonamento_id"))
            ),
            None,
        )
        st.subheader("Disponibilità lezioni")
        render_lesson_availability(availability)
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
    header(
        "Clienti e Prospect",
        "Anagrafiche, prospect, conversioni, abbonamenti e storico.",
    )

    actions = [
        "Elenco clienti",
        "Nuovo cliente",
        "Modifica cliente",
        "Scheda cliente",
        "Prospect",
        "Nuovo prospect",
        "Modifica prospect",
    ]
    apply_pending_action("client_action", actions, "Elenco clienti")

    action = st.selectbox("Operazione", actions, key="client_action")

    if action in {
        "Prospect",
        "Nuovo prospect",
        "Modifica prospect",
    }:
        prospect_page(action)
        return

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
        value=initial_start or today_italy(),
        format="DD/MM/YYYY",
        key=f"{form_key}_start",
    )

    package_without_expiry = (
        package.get("modalita_lezioni") == "Pacchetto lezioni"
        or package.get("senza_scadenza")
    )

    if package_without_expiry:
        end_date = None
        st.metric(
            "Scadenza",
            "Nessuna",
            help="Il pacchetto termina quando il saldo lezioni arriva a zero.",
        )
    else:
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

    lessons = contractual_lessons(
        package["id"],
        start_date,
        end_date,
    )
    c2.metric(
        "Lezioni contrattuali",
        lessons,
        help=(
            f"{lesson_rule_text(package)}. "
            "Il numero dipende dalle date effettive."
        ),
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
    generate_initial_receipt = st.checkbox(
        "Genera ricevuta per il pagamento iniziale",
        value=True,
        disabled=initial_payment <= 0,
        key=f"{form_key}_generate_receipt",
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
        "genera_ricevuta_iniziale": generate_initial_receipt,
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
                        if form_data["data_fine_prevista"] is not None
                        else None
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
            receipt_message = ""
            if (
                form_data["pagamento_iniziale"] > 0
                and form_data["genera_ricevuta_iniziale"]
                and result.get("incasso_id")
            ):
                receipt_result = genera_ricevuta_incasso(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "incasso_id": result["incasso_id"],
                    },
                )
                if receipt_result.get("ricevuta_id"):
                    ensure_receipt_pdf(
                        receipt_result["ricevuta_id"]
                    )
                    receipt_message = " Ricevuta generata."

            clear_data_cache()
            st.session_state.selected_subscription_id = (
                result["abbonamento_id"]
            )
            st.success(
                f"Abbonamento creato.{receipt_message}"
            )
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
        render_lesson_availability(subscription)

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
                value=today_italy(),
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
                    value=today_italy() + relativedelta(months=1),
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
                        if form_data["data_fine_prevista"] is not None
                        else None
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
            receipt_message = ""
            if (
                form_data["pagamento_iniziale"] > 0
                and form_data["genera_ricevuta_iniziale"]
                and result.get("incasso_id")
            ):
                receipt_result = genera_ricevuta_incasso(
                    db,
                    {
                        "azienda_id": load_company()["id"],
                        "incasso_id": result["incasso_id"],
                    },
                )
                if receipt_result.get("ricevuta_id"):
                    ensure_receipt_pdf(
                        receipt_result["ricevuta_id"]
                    )
                    receipt_message = " Ricevuta generata."

            clear_data_cache()
            st.session_state.selected_subscription_id = (
                result["abbonamento_id"]
            )
            st.success(
                "Rinnovo creato senza sovrascrivere lo storico."
                f"{receipt_message}"
            )
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
# MAGAZZINO
# ============================================================

def render_inventory_products(
    rows: list[dict[str, Any]],
) -> None:
    for product in rows:
        with st.container(border=True):
            left, right = st.columns([3.5, 1.2])

            with left:
                st.subheader(product.get("nome") or "Prodotto")
                details = [
                    product.get("codice"),
                    product.get("categoria"),
                    product.get("marca"),
                ]
                st.caption(
                    " · ".join(
                        str(value)
                        for value in details
                        if value
                    )
                    or "Prodotto di magazzino"
                )

            with right:
                stock = float(product.get("giacenza") or 0)
                minimum = float(product.get("scorta_minima") or 0)
                if stock <= 0:
                    st.write("**🔴 Esaurito**")
                elif minimum > 0 and stock <= minimum:
                    st.write("**🟡 Scorta bassa**")
                else:
                    st.write("**🟢 Disponibile**")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric(
                "Giacenza iniziale",
                f"{float(product.get('giacenza_iniziale') or 0):g}",
            )
            c2.metric(
                "Giacenza attuale",
                f"{float(product.get('giacenza') or 0):g}",
            )
            c3.metric(
                "Prezzo vendita",
                money(float(product.get("prezzo_vendita") or 0)),
            )
            c4.metric(
                "Costo medio",
                money(float(product.get("costo_medio") or 0)),
            )

            if product.get("barcode"):
                st.caption(f"Barcode: {product['barcode']}")
            if product.get("note"):
                st.caption(product["note"])


def render_inventory_movements(
    rows: list[dict[str, Any]],
) -> None:
    for movement in rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns(
                [1.2, 2.2, 1.4, 1.2, 2.4]
            )
            c1.write(
                f"**{format_date_it(movement.get('data_movimento'))}**"
            )
            c1.caption(
                str(movement.get("created_at") or "")[11:16]
            )
            c2.write(f"**{movement.get('prodotto') or 'Prodotto'}**")
            c2.caption(movement.get("tipo") or "—")
            quantity = float(movement.get("quantita") or 0)
            c3.write(f"**{quantity:+g}**")
            c3.caption(movement.get("unita_misura") or "pz")
            c4.write(
                f"**{movement.get('stato') or 'valido'}**"
            )
            c5.write(
                movement.get("causale")
                or movement.get("documento")
                or "—"
            )


def inventory_product_form(
    *,
    form_key: str,
    product: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    product = product or {}

    with st.form(form_key):
        c1, c2 = st.columns(2)
        code = c1.text_input(
            "Codice prodotto *",
            value=product.get("codice") or "",
        )
        barcode = c2.text_input(
            "Barcode",
            value=product.get("barcode") or "",
        )

        name = st.text_input(
            "Nome prodotto *",
            value=product.get("nome") or "",
        )

        c3, c4, c5 = st.columns(3)
        category = c3.text_input(
            "Categoria",
            value=product.get("categoria") or "Integratori",
        )
        brand = c4.text_input(
            "Marca",
            value=product.get("marca") or "",
        )
        unit = c5.selectbox(
            "Unità di misura",
            ["pz", "confezione", "kg", "litro"],
            index=(
                ["pz", "confezione", "kg", "litro"].index(
                    product.get("unita_misura")
                )
                if product.get("unita_misura")
                in ["pz", "confezione", "kg", "litro"]
                else 0
            ),
        )

        c6, c7, c8 = st.columns(3)
        sale_price = c6.number_input(
            "Prezzo di vendita",
            min_value=0.0,
            step=1.0,
            value=float(product.get("prezzo_vendita") or 0),
        )
        standard_cost = c7.number_input(
            "Costo standard",
            min_value=0.0,
            step=1.0,
            value=float(product.get("costo_standard") or 0),
        )
        minimum_stock = c8.number_input(
            "Scorta minima",
            min_value=0.0,
            step=1.0,
            value=float(product.get("scorta_minima") or 0),
        )

        if product:
            st.metric(
                "Giacenza iniziale registrata",
                f"{float(product.get('giacenza_iniziale') or 0):g}",
                help=(
                    "La giacenza iniziale non viene sovrascritta. "
                    "Per correggere il saldo si usa una rettifica, "
                    "così lo storico resta integro."
                ),
            )
            initial_stock = None
        else:
            initial_stock = st.number_input(
                "Giacenza iniziale",
                min_value=0.0,
                step=1.0,
                value=0.0,
            )

        notes = st.text_area(
            "Note",
            value=product.get("note") or "",
        )

        st.markdown("#### Catalogo App Cliente")
        visible_customer_app = st.checkbox(
            "Mostra questo prodotto nell'App Cliente",
            value=bool(
                product.get("visibile_app_cliente", False)
            ),
        )
        customer_description = st.text_area(
            "Descrizione commerciale App Cliente",
            value=(
                product.get("descrizione_app_cliente")
                or ""
            ),
        )
        image_url_customer = st.text_input(
            "URL immagine prodotto",
            value=(
                product.get("immagine_url_app_cliente")
                or ""
            ),
        )
        customer_order = st.number_input(
            "Ordine nel catalogo",
            min_value=0,
            max_value=9999,
            value=int(
                product.get("ordine_app_cliente") or 100
            ),
            step=1,
        )

        active = st.checkbox(
            "Prodotto attivo",
            value=bool(product.get("attivo", True)),
        )

        submitted = st.form_submit_button(
            "Salva prodotto",
            use_container_width=True,
        )

    if not submitted:
        return None

    if not code.strip() or not name.strip():
        raise ValueError(
            "Codice e nome prodotto sono obbligatori."
        )

    return {
        "azienda_id": load_company()["id"],
        "prodotto_id": product.get("prodotto_id"),
        "codice": code.strip(),
        "barcode": barcode.strip() or None,
        "nome": name.strip(),
        "categoria": category.strip() or None,
        "marca": brand.strip() or None,
        "unita_misura": unit,
        "prezzo_vendita": float(sale_price),
        "costo_standard": float(standard_cost),
        "scorta_minima": float(minimum_stock),
        "giacenza_iniziale": (
            float(initial_stock)
            if initial_stock is not None
            else None
        ),
        "note": notes.strip() or None,
        "visibile_app_cliente": visible_customer_app,
        "descrizione_app_cliente": (
            customer_description.strip() or None
        ),
        "immagine_url_app_cliente": (
            image_url_customer.strip() or None
        ),
        "ordine_app_cliente": int(customer_order),
        "attivo": active,
    }



def inventory_sale_page() -> None:
    products = [
        row for row in load_inventory_products()
        if row.get("attivo")
        and float(row.get("giacenza") or 0) > 0
    ]
    clients = [
        row for row in load_clients()
        if (
            row.get("stato_cliente")
            or row.get("stato")
            or "attivo"
        ) == "attivo"
    ]

    if "inventory_sale_cart" not in st.session_state:
        st.session_state.inventory_sale_cart = []

    if not products:
        st.info(
            "Non ci sono prodotti attivi con giacenza disponibile."
        )
        return
    if not clients:
        st.info("Nessun cliente attivo disponibile.")
        return

    product_map = {
        (
            f"{row['codice']} · {row['nome']} · "
            f"disponibili {float(row.get('giacenza') or 0):g}"
        ): row
        for row in products
    }
    client_map = {
        f"{row['cognome']} {row['nome']}": row
        for row in clients
    }

    st.subheader("Componi vendita")

    selected_product = product_map[
        st.selectbox(
            "Prodotto",
            list(product_map),
            key="sale_cart_product",
        )
    ]
    available = float(selected_product.get("giacenza") or 0)

    c1, c2, c3 = st.columns(3)
    quantity = c1.number_input(
        "Quantità",
        min_value=1.0,
        max_value=max(available, 1.0),
        step=1.0,
        value=1.0,
        key="sale_cart_quantity",
    )
    unit_price = c2.number_input(
        "Prezzo unitario",
        min_value=0.0,
        step=1.0,
        value=float(
            selected_product.get("prezzo_vendita") or 0
        ),
        key=(
            "sale_cart_price_"
            f"{selected_product['prodotto_id']}"
        ),
    )
    c3.metric(
        "Disponibilità",
        f"{available:g} "
        f"{selected_product.get('unita_misura') or 'pz'}",
    )

    if st.button(
        "Aggiungi alla vendita",
        use_container_width=True,
        key="add_sale_cart_line",
    ):
        existing_quantity = sum(
            float(line["quantita"])
            for line in st.session_state.inventory_sale_cart
            if line["prodotto_id"]
            == selected_product["prodotto_id"]
        )
        if existing_quantity + float(quantity) > available:
            st.error(
                "La quantità complessiva nel carrello supera "
                "la giacenza disponibile."
            )
        elif float(unit_price) <= 0:
            st.error("Il prezzo unitario deve essere positivo.")
        else:
            existing_index = next(
                (
                    index
                    for index, line in enumerate(
                        st.session_state.inventory_sale_cart
                    )
                    if line["prodotto_id"]
                    == selected_product["prodotto_id"]
                    and float(line["prezzo_unitario"])
                    == float(unit_price)
                ),
                None,
            )
            if existing_index is None:
                st.session_state.inventory_sale_cart.append({
                    "prodotto_id": (
                        selected_product["prodotto_id"]
                    ),
                    "codice": selected_product["codice"],
                    "prodotto": selected_product["nome"],
                    "quantita": float(quantity),
                    "prezzo_unitario": float(unit_price),
                    "giacenza_disponibile": available,
                })
            else:
                st.session_state.inventory_sale_cart[
                    existing_index
                ]["quantita"] += float(quantity)
            st.rerun()

    cart = st.session_state.inventory_sale_cart

    if not cart:
        st.info(
            "Aggiungi uno o più prodotti per comporre la vendita."
        )
        return

    st.divider()
    st.subheader("Riepilogo prodotti")

    cart_df = pd.DataFrame([
        {
            "riga": index + 1,
            "codice": line["codice"],
            "prodotto": line["prodotto"],
            "quantita": float(line["quantita"]),
            "prezzo_unitario": float(line["prezzo_unitario"]),
            "totale": round(
                float(line["quantita"])
                * float(line["prezzo_unitario"]),
                2,
            ),
        }
        for index, line in enumerate(cart)
    ])

    edited_cart = st.data_editor(
        cart_df,
        use_container_width=True,
        hide_index=True,
        key="sale_cart_editor",
        disabled=["riga", "codice", "prodotto", "totale"],
        column_config={
            "riga": st.column_config.NumberColumn("Riga"),
            "codice": st.column_config.TextColumn("Codice"),
            "prodotto": st.column_config.TextColumn("Prodotto"),
            "quantita": st.column_config.NumberColumn(
                "Quantità",
                min_value=0.0,
                step=1.0,
            ),
            "prezzo_unitario": st.column_config.NumberColumn(
                "Prezzo unitario",
                min_value=0.0,
                format="€ %.2f",
            ),
            "totale": st.column_config.NumberColumn(
                "Totale",
                format="€ %.2f",
            ),
        },
    )

    c4, c5 = st.columns(2)
    if c4.button(
        "Aggiorna quantità e prezzi",
        use_container_width=True,
        key="update_sale_cart",
    ):
        updated_cart = []
        errors = []
        for index, row in edited_cart.iterrows():
            original = cart[int(row["riga"]) - 1]
            new_quantity = float(row["quantita"])
            new_price = float(row["prezzo_unitario"])
            if new_quantity <= 0:
                continue
            if new_quantity > float(
                original["giacenza_disponibile"]
            ):
                errors.append(
                    f"{original['prodotto']}: quantità superiore "
                    "alla giacenza."
                )
            elif new_price <= 0:
                errors.append(
                    f"{original['prodotto']}: prezzo non valido."
                )
            else:
                updated_cart.append({
                    **original,
                    "quantita": new_quantity,
                    "prezzo_unitario": new_price,
                })

        if errors:
            for error in errors:
                st.error(error)
        else:
            st.session_state.inventory_sale_cart = updated_cart
            st.rerun()

    if c5.button(
        "Svuota vendita",
        use_container_width=True,
        key="clear_sale_cart",
    ):
        st.session_state.inventory_sale_cart = []
        st.rerun()

    gross_total = round(
        sum(
            float(line["quantita"])
            * float(line["prezzo_unitario"])
            for line in cart
        ),
        2,
    )

    st.divider()
    st.subheader("Chiusura vendita")

    selected_client = client_map[
        st.selectbox(
            "Cliente",
            list(client_map),
            key="sale_cart_client",
        )
    ]

    c6, c7, c8 = st.columns(3)
    sale_date = c6.date_input(
        "Data vendita",
        value=today_italy(),
        format="DD/MM/YYYY",
        key="sale_cart_date",
    )
    payment_method = c7.selectbox(
        "Metodo di pagamento",
        ["Contanti", "Carta", "Bonifico", "Altro"],
        key="sale_cart_payment",
    )
    generate_receipt = c8.checkbox(
        "Genera ricevuta",
        value=True,
        key="sale_cart_receipt",
    )

    d1, d2 = st.columns(2)
    discount = d1.number_input(
        "Sconto complessivo",
        min_value=0.0,
        max_value=max(gross_total, 0.0),
        step=1.0,
        value=0.0,
        key="sale_cart_discount",
    )
    discount_reason = d2.text_input(
        "Motivo dello sconto",
        key="sale_cart_discount_reason",
        disabled=float(discount) <= 0,
    )

    net_total = round(gross_total - float(discount), 2)

    t1, t2, t3 = st.columns(3)
    t1.metric("Totale prodotti", money(gross_total))
    t2.metric("Sconto", money(float(discount)))
    t3.metric("Totale da incassare", money(net_total))

    low_stock_after_sale = []
    products_by_id = {
        row["prodotto_id"]: row
        for row in products
    }
    for line in cart:
        product = products_by_id.get(line["prodotto_id"])
        if not product:
            continue
        final_stock = (
            float(product.get("giacenza") or 0)
            - float(line["quantita"])
        )
        minimum = float(product.get("scorta_minima") or 0)
        if minimum > 0 and final_stock <= minimum:
            low_stock_after_sale.append(
                f"{product['nome']}: giacenza prevista "
                f"{final_stock:g}"
            )

    if low_stock_after_sale:
        st.warning(
            "Dopo la vendita saranno sotto scorta: "
            + "; ".join(low_stock_after_sale)
        )

    notes = st.text_area(
        "Note vendita",
        key="sale_cart_notes",
    )

    if st.button(
        "Registra vendita completa",
        use_container_width=True,
        key="confirm_multi_product_sale",
    ):
        if net_total <= 0:
            st.error(
                "Il totale da incassare deve essere positivo."
            )
            return
        if float(discount) > 0 and not discount_reason.strip():
            st.error(
                "La motivazione è obbligatoria quando applichi "
                "uno sconto."
            )
            return

        try:
            result = registra_vendita_magazzino(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "cliente_id": selected_client["cliente_id"],
                    "data_vendita": sale_date.isoformat(),
                    "metodo_pagamento": payment_method,
                    "genera_ricevuta": generate_receipt,
                    "sconto": float(discount),
                    "motivo_sconto": (
                        discount_reason.strip() or None
                    ),
                    "note": notes.strip() or None,
                    "righe": [
                        {
                            "prodotto_id": line["prodotto_id"],
                            "quantita": float(line["quantita"]),
                            "prezzo_unitario": float(
                                line["prezzo_unitario"]
                            ),
                        }
                        for line in cart
                    ],
                },
            )

            pdf_message = ""
            if result.get("ricevuta_id"):
                try:
                    ensure_receipt_pdf(result["ricevuta_id"])
                    pdf_message = " Ricevuta PDF generata."
                except Exception as pdf_exc:
                    pdf_message = (
                        " Vendita registrata; PDF da rigenerare: "
                        f"{pdf_exc}."
                    )

            st.session_state.inventory_sale_cart = []
            clear_data_cache()
            st.success(
                f"Vendita registrata: {int(result['numero_righe'])} "
                f"prodotti, totale {money(float(result['totale']))}."
                f"{pdf_message}"
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Errore durante la vendita: {exc}")


def inventory_purchase_page() -> None:
    products = [
        row for row in load_inventory_products()
        if row.get("attivo")
    ]
    suppliers = [
        row for row in load_suppliers()
        if row.get("stato") == "attivo"
    ]

    if not products:
        st.info("Prima registra almeno un prodotto.")
        return

    product_map = {
        row["nome"]: row
        for row in products
    }
    supplier_map = {
        "Nessun fornitore": None,
        **{
            (
                row.get("nome_commerciale")
                or row["ragione_sociale"]
            ): row
            for row in suppliers
        },
    }

    selected_product = product_map[
        st.selectbox("Prodotto *", list(product_map))
    ]
    selected_supplier = supplier_map[
        st.selectbox("Fornitore", list(supplier_map))
    ]

    with st.form("inventory_purchase_form"):
        c1, c2, c3 = st.columns(3)
        quantity = c1.number_input(
            "Quantità acquistata",
            min_value=0.01,
            step=1.0,
            value=1.0,
        )
        unit_cost = c2.number_input(
            "Costo unitario",
            min_value=0.0,
            step=1.0,
            value=float(
                selected_product.get("costo_standard") or 0
            ),
        )
        purchase_date = c3.date_input(
            "Data acquisto / carico",
            value=today_italy(),
            format="DD/MM/YYYY",
        )

        c4, c5 = st.columns(2)
        document = c4.text_input(
            "Documento / fattura",
            placeholder="Numero documento facoltativo",
        )
        lot = c5.text_input("Lotto")
        expiry = st.date_input(
            "Scadenza prodotto",
            value=None,
            format="DD/MM/YYYY",
        )
        notes = st.text_area("Note")

        submitted = st.form_submit_button(
            "Registra acquisto e carico",
            use_container_width=True,
        )

    if submitted:
        try:
            result = registra_acquisto_magazzino(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "prodotto_id": selected_product["prodotto_id"],
                    "fornitore_id": (
                        selected_supplier["fornitore_id"]
                        if selected_supplier
                        else None
                    ),
                    "data_movimento": purchase_date.isoformat(),
                    "quantita": float(quantity),
                    "costo_unitario": float(unit_cost),
                    "documento": document.strip() or None,
                    "lotto": lot.strip() or None,
                    "data_scadenza_lotto": (
                        expiry.isoformat()
                        if expiry
                        else None
                    ),
                    "note": notes.strip() or None,
                },
            )
            clear_data_cache()
            st.success(
                f"Carico registrato. Nuova giacenza: "
                f"{float(result['nuova_giacenza']):g}."
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Errore durante il carico: {exc}")


def inventory_adjustment_page() -> None:
    products = load_inventory_products()
    if not products:
        st.info("Nessun prodotto disponibile.")
        return

    product_map = {
        (
            f"{row['nome']} · giacenza "
            f"{float(row.get('giacenza') or 0):g}"
        ): row
        for row in products
    }
    selected = product_map[
        st.selectbox("Prodotto", list(product_map))
    ]

    with st.form("inventory_adjustment_form"):
        operation = st.selectbox(
            "Operazione",
            ["Aggiungi giacenza", "Riduci giacenza"],
        )
        quantity = st.number_input(
            "Quantità",
            min_value=0.01,
            step=1.0,
            value=1.0,
        )
        reason = st.text_area(
            "Motivazione obbligatoria",
            placeholder=(
                "Es. conteggio fisico, rottura, omaggio, "
                "merce scaduta, correzione inventario."
            ),
        )
        submitted = st.form_submit_button(
            "Registra rettifica",
            use_container_width=True,
        )

    if submitted:
        signed_quantity = (
            float(quantity)
            if operation == "Aggiungi giacenza"
            else -float(quantity)
        )
        if not reason.strip():
            st.error("La motivazione è obbligatoria.")
            return

        try:
            result = registra_rettifica_magazzino(
                db,
                {
                    "azienda_id": load_company()["id"],
                    "prodotto_id": selected["prodotto_id"],
                    "data_movimento": today_italy().isoformat(),
                    "quantita": signed_quantity,
                    "causale": reason.strip(),
                },
            )
            clear_data_cache()
            st.success(
                f"Rettifica registrata. Nuova giacenza: "
                f"{float(result['nuova_giacenza']):g}."
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Errore durante la rettifica: {exc}")


def page_inventory() -> None:
    header(
        "Magazzino",
        "Inventario integratori, acquisti, vendite e giacenze.",
    )

    actions = [
        "Inventario",
        "Nuovo prodotto",
        "Modifica prodotto",
        "Nuova vendita",
        "Ordini App Cliente",
        "Nuovo acquisto",
        "Rettifica",
        "Movimenti",
    ]
    apply_pending_action(
        "inventory_action",
        actions,
        "Inventario",
    )

    action = st.selectbox(
        "Operazione",
        actions,
        key="inventory_action",
    )

    if action == "Inventario":
        products = load_inventory_products()
        if not products:
            st.info("Nessun prodotto registrato.")
            return

        search = st.text_input(
            "Cerca prodotto",
            placeholder="Nome, codice, barcode o marca",
        )
        state_filter = st.selectbox(
            "Filtro",
            [
                "Tutti",
                "Disponibili",
                "Scorta bassa",
                "Esauriti",
                "Inattivi",
            ],
        )

        filtered = products
        if search:
            lowered = search.lower()
            filtered = [
                row for row in filtered
                if lowered in " ".join(
                    str(row.get(field) or "")
                    for field in [
                        "nome",
                        "codice",
                        "barcode",
                        "marca",
                        "categoria",
                    ]
                ).lower()
            ]

        if state_filter == "Disponibili":
            filtered = [
                row for row in filtered
                if float(row.get("giacenza") or 0)
                > float(row.get("scorta_minima") or 0)
                and row.get("attivo")
            ]
        elif state_filter == "Scorta bassa":
            filtered = [
                row for row in filtered
                if 0 < float(row.get("giacenza") or 0)
                <= float(row.get("scorta_minima") or 0)
                and row.get("attivo")
            ]
        elif state_filter == "Esauriti":
            filtered = [
                row for row in filtered
                if float(row.get("giacenza") or 0) <= 0
                and row.get("attivo")
            ]
        elif state_filter == "Inattivi":
            filtered = [
                row for row in filtered
                if not row.get("attivo")
            ]

        total_value = sum(
            float(row.get("giacenza") or 0)
            * float(row.get("costo_medio") or 0)
            for row in products
        )
        low_stock = sum(
            1 for row in products
            if row.get("attivo")
            and float(row.get("giacenza") or 0)
            <= float(row.get("scorta_minima") or 0)
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Prodotti", len(products))
        m2.metric("Scorte da controllare", low_stock)
        m3.metric("Valore giacenza", money(total_value))

        inventory_view = st.radio(
            "Visualizzazione",
            ["Schede", "Elenco"],
            horizontal=True,
            key="inventory_view_mode",
        )

        exported_inventory = inventory_export_rows(filtered)
        render_export_controls(
            report_key="inventory_list",
            title="Inventario valorizzato",
            columns=inventory_export_columns(),
            rows=exported_inventory,
            filters=[
                f"Filtro: {state_filter}",
                f"Ricerca: {search or 'nessuna'}",
            ],
            totals={
                "Numero prodotti": len(exported_inventory),
                "Valore giacenza": sum(
                    row["valore_giacenza"]
                    for row in exported_inventory
                ),
            },
        )

        if filtered:
            if inventory_view == "Elenco":
                st.dataframe(
                    pd.DataFrame(exported_inventory),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "costo_medio": (
                            st.column_config.NumberColumn(
                                "Costo medio",
                                format="€ %.2f",
                            )
                        ),
                        "valore_giacenza": (
                            st.column_config.NumberColumn(
                                "Valore giacenza",
                                format="€ %.2f",
                            )
                        ),
                        "prezzo_vendita": (
                            st.column_config.NumberColumn(
                                "Prezzo vendita",
                                format="€ %.2f",
                            )
                        ),
                    },
                )
            else:
                render_inventory_products(filtered)
        else:
            st.info("Nessun prodotto con i filtri selezionati.")

    elif action == "Nuovo prodotto":
        try:
            payload = inventory_product_form(
                form_key="new_inventory_product",
            )
            if payload:
                existing_products = load_inventory_products()
                duplicate = next(
                    (
                        row for row in existing_products
                        if str(row.get("codice") or "").strip().lower()
                        == payload["codice"].strip().lower()
                    ),
                    None,
                )

                if duplicate:
                    st.session_state.inventory_duplicate_product_id = (
                        duplicate["prodotto_id"]
                    )
                    st.error(
                        "Esiste già un prodotto con questo codice: "
                        f"{duplicate['codice']} · {duplicate['nome']}."
                    )
                    st.info(
                        "Per evitare duplicazioni, usa "
                        "'Modifica prodotto'."
                    )
                    if st.button(
                        "Apri il prodotto esistente",
                        use_container_width=True,
                        key="open_existing_inventory_product",
                    ):
                        st.session_state.inventory_action = (
                            "Modifica prodotto"
                        )
                        st.rerun()
                else:
                    salva_prodotto_magazzino(db, payload)
                    clear_data_cache()
                    st.success("Prodotto creato.")
                    st.rerun()
        except Exception as exc:
            message = str(exc)
            if (
                "prodotti_magazzino_azienda_id_codice_key"
                in message
                or "Codice prodotto già esistente"
                in message
            ):
                st.error(
                    "Il codice prodotto è già utilizzato. "
                    "Apri 'Modifica prodotto' e aggiorna "
                    "l'articolo esistente."
                )
            elif "barcode" in message.lower() and "duplicate" in message.lower():
                st.error(
                    "Il barcode è già associato a un altro prodotto."
                )
            else:
                st.error(f"Errore durante il salvataggio: {exc}")

    elif action == "Modifica prodotto":
        products = load_inventory_products()
        if not products:
            st.info("Nessun prodotto da modificare.")
            return

        product_map = {
            f"{row['codice']} · {row['nome']}": row
            for row in products
        }
        product_labels = list(product_map)
        pending_product_id = st.session_state.pop(
            "inventory_duplicate_product_id",
            None,
        )
        default_index = next(
            (
                index
                for index, label in enumerate(product_labels)
                if product_map[label]["prodotto_id"]
                == pending_product_id
            ),
            0,
        )

        selected = product_map[
            st.selectbox(
                "Prodotto da modificare",
                product_labels,
                index=default_index,
            )
        ]
        try:
            payload = inventory_product_form(
                form_key=f"edit_product_{selected['prodotto_id']}",
                product=selected,
            )
            if payload:
                salva_prodotto_magazzino(db, payload)
                clear_data_cache()
                st.success("Prodotto aggiornato.")
                st.rerun()
        except Exception as exc:
            st.error(f"Errore durante la modifica: {exc}")

    elif action == "Nuova vendita":
        inventory_sale_page()

    elif action == "Ordini App Cliente":
        st.subheader("Ordini ricevuti dall'App Cliente")
        orders = elenco_ordini_cliente(
            db,
            load_company()["id"],
        )

        if not orders:
            st.info("Nessun ordine cliente.")
        else:
            for order in orders:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.6, 1, 1])
                    c1.write(
                        f"**{order.get('cliente') or 'Cliente'}**"
                    )
                    c1.caption(
                        format_datetime_italy(
                            order.get("created_at")
                        )
                    )
                    c2.metric(
                        "Totale",
                        money(float(order.get("totale") or 0)),
                    )
                    c3.metric(
                        "Stato",
                        str(order.get("stato") or "richiesto").title(),
                    )

                    products = order.get("prodotti") or []
                    for item in products:
                        st.write(
                            f"• {item.get('nome')} · "
                            f"{float(item.get('quantita') or 0):g} × "
                            f"{money(float(item.get('prezzo_unitario') or 0))}"
                        )

                    states = [
                        "richiesto",
                        "confermato",
                        "pronto",
                        "consegnato",
                        "annullato",
                    ]
                    current_state = str(
                        order.get("stato") or "richiesto"
                    )
                    state = st.selectbox(
                        "Nuovo stato",
                        states,
                        index=(
                            states.index(current_state)
                            if current_state in states
                            else 0
                        ),
                        key=f"order_state_{order['ordine_id']}",
                    )
                    internal_note = st.text_input(
                        "Nota interna",
                        value=order.get("note_interne") or "",
                        key=f"order_note_{order['ordine_id']}",
                    )
                    if st.button(
                        "Aggiorna ordine",
                        use_container_width=True,
                        key=f"update_order_{order['ordine_id']}",
                    ):
                        try:
                            aggiorna_stato_ordine_cliente(
                                db,
                                {
                                    "ordine_id": order["ordine_id"],
                                    "stato": state,
                                    "note_interne": (
                                        internal_note.strip() or None
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.success("Ordine aggiornato.")
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Ordine non aggiornato: {exc}"
                            )

    elif action == "Nuovo acquisto":
        inventory_purchase_page()

    elif action == "Rettifica":
        inventory_adjustment_page()

    else:
        products = load_inventory_products()
        product_map = {
            "Tutti i prodotti": None,
            **{
                row["nome"]: row
                for row in products
            },
        }
        selected = product_map[
            st.selectbox("Prodotto", list(product_map))
        ]
        rows = load_inventory_movements(
            selected["prodotto_id"]
            if selected
            else None
        )

        if rows:
            exported_movements = (
                inventory_movement_export_rows(rows)
            )
            render_export_controls(
                report_key="inventory_movements",
                title="Movimenti magazzino",
                columns=inventory_movement_columns(),
                rows=exported_movements,
                filters=[
                    (
                        f"Prodotto: {selected['nome']}"
                        if selected
                        else "Tutti i prodotti"
                    )
                ],
                totals={
                    "Numero movimenti": len(exported_movements)
                },
            )
            render_inventory_movements(rows)

            cancellable = [
                row for row in rows
                if row.get("stato") == "valido"
                and row.get("tipo") != "storno"
            ]
            if cancellable:
                st.divider()
                labels = {
                    (
                        f"{format_date_it(row['data_movimento'])} · "
                        f"{row['prodotto']} · "
                        f"{float(row['quantita']):+g} · "
                        f"{row.get('tipo')}"
                    ): row
                    for row in cancellable
                }
                selected_label = st.selectbox(
                    "Movimento da annullare",
                    list(labels),
                )
                movement = labels[selected_label]
                reason = st.text_area(
                    "Motivo annullamento",
                )
                if st.button(
                    "Annulla movimento",
                    use_container_width=True,
                ):
                    if not reason.strip():
                        st.error("Il motivo è obbligatorio.")
                    else:
                        try:
                            annulla_movimento_magazzino(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "movimento_id": (
                                        movement["movimento_id"]
                                    ),
                                    "motivo": reason.strip(),
                                },
                            )
                            clear_data_cache()
                            st.success(
                                "Movimento annullato con storno."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Errore: {exc}")
        else:
            st.info("Nessun movimento registrato.")


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

    if tipo_incasso == "vendita_prodotto":
        st.info(
            "Le vendite di prodotti si registrano dalla sezione "
            "Magazzino, così incasso, ricevuta e giacenza vengono "
            "aggiornati con una sola operazione."
        )
        if st.button(
            "Apri nuova vendita prodotto",
            use_container_width=True,
        ):
            goto("Magazzino", "Nuova vendita")
        return

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
            value=today_italy(),
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
        value=today_italy(),
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
                value=today_italy(),
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


RECURRENCE_OPTIONS = {
    "Mensile": 1,
    "Bimestrale": 2,
    "Trimestrale": 3,
    "Semestrale": 6,
    "Annuale": 12,
    "Personalizzata": None,
}


def recurring_expenses_page() -> None:
    st.subheader("Spese ricorrenti")
    st.caption(
        "La regola genera una sola spesa per ciascun periodo di "
        "competenza. La rigenerazione è idempotente: i mesi già "
        "creati non vengono duplicati."
    )

    tabs = st.tabs(["Nuova regola", "Regole esistenti"])

    with tabs[0]:
        suppliers = [
            row for row in load_suppliers()
            if row.get("stato") == "attivo"
        ]
        categories = [
            row for row in load_expense_categories()
            if row.get("attiva")
        ]

        if not suppliers:
            st.warning(
                "Prima devi registrare almeno un fornitore attivo."
            )
        elif not categories:
            st.warning(
                "Prima devi registrare almeno una categoria di spesa."
            )
        else:
            supplier_map = {
                (
                    supplier.get("nome_commerciale")
                    or supplier["ragione_sociale"]
                ): supplier
                for supplier in suppliers
            }
            category_map = {
                category["nome"]: category
                for category in categories
            }

            c1, c2 = st.columns(2)
            supplier_name = c1.selectbox(
                "Fornitore *",
                list(supplier_map),
                key="recurring_supplier",
            )
            category_name = c2.selectbox(
                "Categoria *",
                list(category_map),
                key="recurring_category",
            )

            description = st.text_input(
                "Descrizione *",
                placeholder="Es. Affitto palestra",
                key="recurring_description",
            )

            c3, c4, c5 = st.columns(3)
            taxable = c3.number_input(
                "Imponibile per ricorrenza",
                min_value=0.0,
                step=10.0,
                key="recurring_taxable",
            )
            vat = c4.number_input(
                "IVA per ricorrenza",
                min_value=0.0,
                step=1.0,
                key="recurring_vat",
            )
            total = c5.number_input(
                "Totale per ricorrenza *",
                min_value=0.0,
                step=10.0,
                value=float(taxable + vat),
                key="recurring_total",
            )

            c6, c7 = st.columns(2)
            recurrence_name = c6.selectbox(
                "Frequenza",
                list(RECURRENCE_OPTIONS),
                key="recurring_frequency",
            )
            configured_months = RECURRENCE_OPTIONS[recurrence_name]
            every_months = (
                c7.number_input(
                    "Ripeti ogni quanti mesi",
                    min_value=1,
                    max_value=60,
                    value=1,
                    step=1,
                    key="recurring_custom_months",
                )
                if configured_months is None
                else configured_months
            )
            if configured_months is not None:
                c7.text_input(
                    "Intervallo",
                    value=f"Ogni {configured_months} mese/i",
                    disabled=True,
                    key="recurring_interval_display",
                )

            current_year = today_italy().year
            c8, c9, c10 = st.columns(3)
            start_date = c8.date_input(
                "Inizio competenza",
                value=date(current_year, 1, 1),
                format="DD/MM/YYYY",
                key="recurring_start",
            )
            end_date = c9.date_input(
                "Fine competenza",
                value=date(current_year, 12, 31),
                format="DD/MM/YYYY",
                key="recurring_end",
            )
            due_day = c10.number_input(
                "Giorno di scadenza",
                min_value=1,
                max_value=31,
                value=5,
                step=1,
                key="recurring_due_day",
            )

            document_type = st.selectbox(
                "Tipo documento generato",
                [
                    "Costo ricorrente",
                    "Fattura",
                    "Ricevuta",
                    "Altro",
                ],
                key="recurring_document_type",
            )
            notes = st.text_area(
                "Note",
                key="recurring_notes",
            )

            if start_date <= end_date:
                occurrences = 0
                cursor = start_date.replace(day=1)
                final_month = end_date.replace(day=1)
                while cursor <= final_month:
                    occurrences += 1
                    cursor += relativedelta(months=int(every_months))
                m1, m2, m3 = st.columns(3)
                m1.metric("Ricorrenze previste", occurrences)
                m2.metric("Costo per ricorrenza", money(float(total)))
                m3.metric(
                    "Costo totale previsto",
                    money(float(total) * occurrences),
                )

            if st.button(
                "Salva e genera spese",
                use_container_width=True,
                key="save_recurring_expense",
            ):
                if not description.strip():
                    st.error("La descrizione è obbligatoria.")
                elif total <= 0:
                    st.error("Il totale deve essere maggiore di zero.")
                elif start_date > end_date:
                    st.error(
                        "La data iniziale non può superare quella finale."
                    )
                else:
                    try:
                        result = crea_regola_spesa_ricorrente(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "fornitore_id": supplier_map[
                                    supplier_name
                                ]["id"],
                                "categoria_spesa_id": category_map[
                                    category_name
                                ]["id"],
                                "descrizione": description.strip(),
                                "imponibile": float(taxable),
                                "iva": float(vat),
                                "totale": float(total),
                                "intervallo_mesi": int(every_months),
                                "data_inizio": start_date.isoformat(),
                                "data_fine": end_date.isoformat(),
                                "giorno_scadenza": int(due_day),
                                "tipo_documento": document_type,
                                "note": notes.strip() or None,
                            },
                        )
                        clear_data_cache()
                        st.success(
                            "Regola salvata. Spese generate: "
                            f"{int(result.get('spese_generate') or 0)}."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(
                            "Errore durante la creazione della regola: "
                            f"{exc}"
                        )

    with tabs[1]:
        rules = load_recurring_expense_rules()
        if not rules:
            st.info("Nessuna regola ricorrente registrata.")
            return

        for rule in rules:
            state = rule.get("stato") or "attiva"
            supplier = rule.get("fornitore") or "Fornitore"
            interval = int(rule.get("intervallo_mesi") or 1)
            with st.container(border=True):
                top, actions = st.columns([4, 1.4])
                top.markdown(
                    f"### {rule.get('descrizione') or 'Spesa ricorrente'}"
                )
                top.caption(
                    f"{supplier} · {rule.get('categoria') or 'Categoria'} · "
                    f"ogni {interval} mese/i"
                )
                actions.markdown(
                    f"**{state.upper()}**"
                )

                m1, m2, m3, m4 = st.columns(4)
                m1.metric(
                    "Importo",
                    money(float(rule.get("totale") or 0)),
                )
                m2.metric(
                    "Periodo",
                    (
                        f"{format_date_it(rule.get('data_inizio'))} – "
                        f"{format_date_it(rule.get('data_fine'))}"
                    ),
                )
                m3.metric(
                    "Spese generate",
                    int(rule.get("spese_generate") or 0),
                )
                m4.metric(
                    "Totale generato",
                    money(float(rule.get("totale_generato") or 0)),
                )

                b1, b2, b3, b4 = st.columns(4)
                if b1.button(
                    "Genera eventuali periodi mancanti",
                    use_container_width=True,
                    key=f"generate_rule_{rule['regola_id']}",
                    disabled=state != "attiva",
                ):
                    try:
                        result = genera_spese_ricorrenti(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "regola_id": rule["regola_id"],
                            },
                        )
                        clear_data_cache()
                        st.success(
                            "Nuove spese generate: "
                            f"{int(result.get('spese_generate') or 0)}."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore di generazione: {exc}")

                new_state = "disattivata" if state == "attiva" else "attiva"
                if b2.button(
                    "Disattiva regola" if state == "attiva" else "Riattiva regola",
                    use_container_width=True,
                    key=f"toggle_rule_{rule['regola_id']}",
                ):
                    try:
                        cambia_stato_regola_spesa_ricorrente(
                            db,
                            {
                                "azienda_id": load_company()["id"],
                                "regola_id": rule["regola_id"],
                                "stato": new_state,
                            },
                        )
                        clear_data_cache()
                        st.success("Stato della regola aggiornato.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Errore aggiornamento regola: {exc}")

                with b3.expander(
                    "Modifica",
                    expanded=False,
                ):
                    supplier_names = [
                        (
                            item.get("nome_commerciale")
                            or item.get("ragione_sociale")
                        )
                        for item in load_suppliers()
                    ]
                    supplier_by_name = {
                        (
                            item.get("nome_commerciale")
                            or item.get("ragione_sociale")
                        ): item
                        for item in load_suppliers()
                    }
                    category_names = [
                        item["nome"]
                        for item in load_expense_categories()
                    ]
                    category_by_name = {
                        item["nome"]: item
                        for item in load_expense_categories()
                    }

                    with st.form(
                        f"edit_recurring_rule_{rule['regola_id']}"
                    ):
                        supplier_name = st.selectbox(
                            "Fornitore",
                            supplier_names,
                            index=(
                                supplier_names.index(rule.get("fornitore"))
                                if rule.get("fornitore") in supplier_names
                                else 0
                            ),
                        )
                        category_name = st.selectbox(
                            "Categoria",
                            category_names,
                            index=(
                                category_names.index(rule.get("categoria"))
                                if rule.get("categoria") in category_names
                                else 0
                            ),
                        )
                        description = st.text_input(
                            "Descrizione",
                            value=rule.get("descrizione") or "",
                        )
                        a1, a2, a3 = st.columns(3)
                        taxable = a1.number_input(
                            "Imponibile",
                            min_value=0.0,
                            value=float(rule.get("imponibile") or 0),
                        )
                        vat = a2.number_input(
                            "IVA",
                            min_value=0.0,
                            value=float(rule.get("iva") or 0),
                        )
                        total = a3.number_input(
                            "Totale",
                            min_value=0.01,
                            value=float(rule.get("totale") or 0),
                        )
                        r1, r2, r3 = st.columns(3)
                        interval = r1.number_input(
                            "Intervallo mesi",
                            min_value=1,
                            max_value=60,
                            value=int(rule.get("intervallo_mesi") or 1),
                        )
                        start_date = r2.date_input(
                            "Data inizio",
                            value=date.fromisoformat(
                                str(rule.get("data_inizio"))[:10]
                            ),
                            format="DD/MM/YYYY",
                        )
                        end_date = r3.date_input(
                            "Data fine",
                            value=date.fromisoformat(
                                str(rule.get("data_fine"))[:10]
                            ),
                            format="DD/MM/YYYY",
                        )
                        due_day = st.number_input(
                            "Giorno scadenza",
                            min_value=1,
                            max_value=31,
                            value=int(rule.get("giorno_scadenza") or 1),
                        )
                        document_type = st.text_input(
                            "Tipo documento",
                            value=rule.get("tipo_documento") or "",
                        )
                        notes = st.text_area(
                            "Note",
                            value=rule.get("note") or "",
                        )
                        apply_label = st.radio(
                            "Applica la modifica",
                            [
                                "Solo dal mese indicato in avanti",
                                "A tutte le competenze, anche retroattive",
                            ],
                        )
                        from_month = st.date_input(
                            "Dal mese",
                            value=today_italy().replace(day=1),
                            format="DD/MM/YYYY",
                            disabled=(
                                apply_label
                                == "A tutte le competenze, anche retroattive"
                            ),
                        )
                        reason = st.text_area(
                            "Motivo della modifica"
                        )
                        submit_rule_edit = st.form_submit_button(
                            "Salva modifica regola",
                            use_container_width=True,
                        )

                    if submit_rule_edit:
                        try:
                            modifica_regola_spesa_ricorrente(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "regola_id": rule["regola_id"],
                                    "fornitore_id": supplier_by_name[
                                        supplier_name
                                    ]["id"],
                                    "categoria_spesa_id": category_by_name[
                                        category_name
                                    ]["id"],
                                    "descrizione": description.strip(),
                                    "imponibile": float(taxable),
                                    "iva": float(vat),
                                    "totale": float(total),
                                    "intervallo_mesi": int(interval),
                                    "data_inizio": start_date.isoformat(),
                                    "data_fine": end_date.isoformat(),
                                    "giorno_scadenza": int(due_day),
                                    "tipo_documento": (
                                        document_type.strip() or None
                                    ),
                                    "note": notes.strip() or None,
                                    "applica_a": (
                                        "tutte"
                                        if apply_label.startswith("A tutte")
                                        else "future"
                                    ),
                                    "dal_mese": (
                                        from_month.replace(day=1).isoformat()
                                    ),
                                    "motivo": reason.strip() or None,
                                    "utente_id": st.session_state.get(
                                        "auth_user_id"
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.success("Regola ricorrente modificata.")
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Regola non modificata: {exc}"
                            )

                with b4.expander(
                    "Elimina",
                    expanded=False,
                ):
                    st.warning(
                        "La regola non genererà più spese. Puoi "
                        "annullare solo le competenze future oppure "
                        "tutte, comprese quelle retroattive."
                    )
                    with st.form(
                        f"delete_recurring_rule_{rule['regola_id']}"
                    ):
                        delete_scope = st.radio(
                            "Competenze da eliminare",
                            [
                                "Dal mese indicato in avanti",
                                "Tutte, anche retroattive",
                            ],
                        )
                        delete_from = st.date_input(
                            "Dal mese",
                            value=today_italy().replace(day=1),
                            format="DD/MM/YYYY",
                            disabled=delete_scope.startswith("Tutte"),
                        )
                        delete_reason = st.text_area(
                            "Motivo obbligatorio"
                        )
                        confirm_delete = st.checkbox(
                            "Confermo l'eliminazione della regola"
                        )
                        submit_rule_delete = st.form_submit_button(
                            "Elimina regola e competenze selezionate",
                            use_container_width=True,
                        )

                    if submit_rule_delete:
                        try:
                            if not confirm_delete:
                                raise ValueError(
                                    "Devi confermare l'eliminazione."
                                )
                            elimina_regola_spesa_ricorrente(
                                db,
                                {
                                    "azienda_id": load_company()["id"],
                                    "regola_id": rule["regola_id"],
                                    "applica_a": (
                                        "tutte"
                                        if delete_scope.startswith("Tutte")
                                        else "future"
                                    ),
                                    "dal_mese": (
                                        delete_from.replace(day=1).isoformat()
                                    ),
                                    "motivo": delete_reason.strip(),
                                    "utente_id": st.session_state.get(
                                        "auth_user_id"
                                    ),
                                },
                            )
                            clear_data_cache()
                            st.success(
                                "Regola eliminata e competenze annullate."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Regola non eliminata: {exc}"
                            )


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
        "Spese ricorrenti",
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
    elif action == "Spese ricorrenti":
        recurring_expenses_page()
    elif action == "Spese":
        expenses_page()
    else:
        expense_deadlines_page()



# ============================================================
# ADMIN - CABINA DI CONTROLLO DIREZIONALE
# ============================================================

def _safe_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _valid_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if str(row.get("stato") or "").lower()
        not in {"annullato", "annullata"}
    ]


def _rows_between(
    rows: list[dict[str, Any]],
    field: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        row_date = _safe_date(row.get(field))
        if row_date and start_date <= row_date <= end_date:
            filtered.append(row)
    return filtered


def _month_label(value: date) -> str:
    months = [
        "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
        "Lug", "Ago", "Set", "Ott", "Nov", "Dic",
    ]
    return f"{months[value.month - 1]} {value.year}"


def build_admin_snapshot(
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Unico aggregatore direzionale.

    Tutte le sezioni Admin leggono questo snapshot, costruito dalle
    stesse viste operative usate dal gestionale. Nessun calcolo viene
    replicato nelle singole schede o nei grafici.
    """
    clients = load_clients()
    prospects = load_prospects()
    subscriptions = load_subscriptions()
    receipts = _valid_rows(load_receipts())
    expenses = _valid_rows(load_expenses())
    installments = load_installments()
    inventory = load_inventory_products()
    movements = _valid_rows(load_inventory_movements())
    bookings = load_bookings(
        start_date.isoformat(),
        end_date.isoformat(),
    )

    period_receipts = _rows_between(
        receipts,
        "data_incasso",
        start_date,
        end_date,
    )
    period_expenses = [
        row for row in expenses
        if (
            competence_date := _safe_date(
                row.get("competenza_mese")
                or row.get("data_spesa")
            )
        )
        and start_date <= competence_date <= end_date
    ]
    period_movements = _rows_between(
        movements,
        "data_movimento",
        start_date,
        end_date,
    )

    # CONTO ECONOMICO DIREZIONALE
    #
    # Gli abbonamenti vengono rilevati per il loro intero valore
    # contrattuale, indipendentemente dagli incassi già ricevuti.
    # Gli incassi di tipo "abbonamento" non vengono quindi sommati
    # nuovamente, evitando duplicazioni.
    period_subscriptions = [
        row for row in subscriptions
        if (
            subscription_date := _safe_date(
                row.get("data_inizio")
                or row.get("data_inizio_prevista")
                or row.get("created_at")
            )
        )
        and start_date <= subscription_date <= end_date
        and str(row.get("stato") or "").lower()
        not in {"annullato", "annullata"}
    ]

    subscriptions_contract_value = sum(
        float(row.get("prezzo_concordato") or 0)
        for row in period_subscriptions
    )

    non_subscription_receipts = [
        row for row in period_receipts
        if str(
            row.get("tipo_incasso")
            or "altro_ricavo"
        ) != "abbonamento"
    ]

    receipt_income_total = sum(
        float(row.get("importo") or 0)
        for row in non_subscription_receipts
    )

    expenses_total = sum(
        float(
            row.get("totale")
            or row.get("importo")
            or 0
        )
        for row in period_expenses
    )

    income_by_type: dict[str, float] = {
        "abbonamento": subscriptions_contract_value,
    }
    for row in non_subscription_receipts:
        kind = str(
            row.get("tipo_incasso")
            or "altro_ricavo"
        )
        income_by_type[kind] = (
            income_by_type.get(kind, 0.0)
            + float(row.get("importo") or 0)
        )

    expenses_by_category: dict[str, float] = {}
    for row in period_expenses:
        category = str(
            row.get("categoria")
            or row.get("categoria_spesa")
            or "Senza categoria"
        )
        expenses_by_category[category] = (
            expenses_by_category.get(category, 0.0)
            + float(
                row.get("totale")
                or row.get("importo")
                or 0
            )
        )

    monthly: dict[str, dict[str, float]] = {}

    for row in period_subscriptions:
        row_date = _safe_date(
            row.get("data_inizio")
            or row.get("data_inizio_prevista")
            or row.get("created_at")
        )
        if not row_date:
            continue
        key = row_date.strftime("%Y-%m")
        monthly.setdefault(
            key,
            {"ricavi": 0.0, "costi": 0.0},
        )
        monthly[key]["ricavi"] += float(
            row.get("prezzo_concordato") or 0
        )

    for row in non_subscription_receipts:
        row_date = _safe_date(row.get("data_incasso"))
        if not row_date:
            continue
        key = row_date.strftime("%Y-%m")
        monthly.setdefault(
            key,
            {"ricavi": 0.0, "costi": 0.0},
        )
        monthly[key]["ricavi"] += float(
            row.get("importo") or 0
        )

    for row in period_expenses:
        row_date = _safe_date(
            row.get("competenza_mese")
            or row.get("data_spesa")
        )
        if not row_date:
            continue
        key = row_date.strftime("%Y-%m")
        monthly.setdefault(
            key,
            {"ricavi": 0.0, "costi": 0.0},
        )
        monthly[key]["costi"] += float(
            row.get("totale")
            or row.get("importo")
            or 0
        )

    active_clients = [
        row for row in clients
        if (
            row.get("stato_cliente")
            or row.get("stato")
            or "attivo"
        ) == "attivo"
    ]
    active_prospects = [
        row for row in prospects
        if row.get("stato") not in {
            "Convertito",
            "Non interessato",
        }
    ]

    new_clients = []
    for row in clients:
        created = _safe_date(
            row.get("created_at")
            or row.get("data_creazione")
        )
        if created and start_date <= created <= end_date:
            new_clients.append(row)

    converted_prospects = [
        row for row in prospects
        if row.get("stato") == "Convertito"
        and (
            converted := _safe_date(
                row.get("converted_at")
            )
        )
        and start_date <= converted <= end_date
    ]

    overdue_installments = [
        row for row in installments
        if float(row.get("residuo_rata") or 0) > 0
        and "scadut" in str(
            row.get("stato") or ""
        ).lower()
    ]
    open_credit = sum(
        float(row.get("residuo") or 0)
        for row in subscriptions
        if str(row.get("stato") or "").lower()
        not in {"annullato", "terminato"}
    )
    overdue_credit = sum(
        float(row.get("residuo_rata") or 0)
        for row in overdue_installments
    )

    valid_bookings = [
        row for row in bookings
        if row.get("stato") != "annullata"
    ]
    present_bookings = [
        row for row in valid_bookings
        if row.get("stato") == "presente"
    ]
    absent_bookings = [
        row for row in valid_bookings
        if row.get("stato") == "assente"
    ]
    occupancy_rate = (
        len(present_bookings) / len(valid_bookings) * 100
        if valid_bookings
        else 0.0
    )

    bookings_by_day: dict[str, int] = {}
    bookings_by_operator: dict[str, int] = {}
    bookings_by_hour: dict[str, int] = {}
    for row in present_bookings:
        booking_date = _safe_date(
            row.get("data_prenotazione")
        )
        if booking_date:
            label = booking_date.strftime("%d/%m")
            bookings_by_day[label] = (
                bookings_by_day.get(label, 0) + 1
            )
        operator = str(
            row.get("operatore")
            or "Non assegnato"
        )
        bookings_by_operator[operator] = (
            bookings_by_operator.get(operator, 0) + 1
        )
        hour = str(
            row.get("ora_inizio") or ""
        )[:2]
        if hour:
            bookings_by_hour[f"{hour}:00"] = (
                bookings_by_hour.get(
                    f"{hour}:00",
                    0,
                )
                + 1
            )

    inventory_value = sum(
        float(row.get("giacenza") or 0)
        * float(row.get("costo_medio") or 0)
        for row in inventory
    )

    # Le giacenze finali di magazzino sono una componente positiva
    # separata del conto economico direzionale.
    income_total = (
        subscriptions_contract_value
        + receipt_income_total
        + inventory_value
    )
    operating_result = income_total - expenses_total

    # Per il trend mensile la giacenza finale viene attribuita al mese
    # di chiusura del periodo selezionato.
    inventory_month_key = end_date.strftime("%Y-%m")
    monthly.setdefault(
        inventory_month_key,
        {"ricavi": 0.0, "costi": 0.0},
    )
    monthly[inventory_month_key]["ricavi"] += inventory_value

    monthly_rows = []
    for key in sorted(monthly):
        year, month = map(int, key.split("-"))
        values = monthly[key]
        monthly_rows.append({
            "mese": _month_label(date(year, month, 1)),
            "ricavi": round(values["ricavi"], 2),
            "costi": round(values["costi"], 2),
            "risultato": round(
                values["ricavi"] - values["costi"],
                2,
            ),
        })
    low_stock = [
        row for row in inventory
        if row.get("attivo")
        and (
            float(row.get("giacenza") or 0) <= 0
            or (
                float(row.get("scorta_minima") or 0) > 0
                and float(row.get("giacenza") or 0)
                <= float(row.get("scorta_minima") or 0)
            )
        )
    ]

    purchases = [
        row for row in period_movements
        if row.get("tipo") == "acquisto"
    ]
    sales = [
        row for row in period_movements
        if row.get("tipo") == "vendita"
    ]
    purchase_value = sum(
        abs(float(row.get("quantita") or 0))
        * float(
            row.get("costo_unitario")
            or row.get("prezzo_unitario")
            or 0
        )
        for row in purchases
    )
    sales_value = sum(
        abs(float(row.get("quantita") or 0))
        * float(row.get("prezzo_unitario") or 0)
        for row in sales
    )

    product_sales: dict[str, dict[str, float]] = {}
    for row in sales:
        product = str(
            row.get("prodotto") or "Prodotto"
        )
        product_sales.setdefault(
            product,
            {"quantita": 0.0, "valore": 0.0},
        )
        product_sales[product]["quantita"] += abs(
            float(row.get("quantita") or 0)
        )
        product_sales[product]["valore"] += (
            abs(float(row.get("quantita") or 0))
            * float(row.get("prezzo_unitario") or 0)
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "clients": clients,
        "prospects": prospects,
        "subscriptions": subscriptions,
        "receipts": period_receipts,
        "expenses": period_expenses,
        "installments": installments,
        "inventory": inventory,
        "movements": period_movements,
        "bookings": valid_bookings,
        "income_total": income_total,
        "subscriptions_contract_value": subscriptions_contract_value,
        "inventory_income": inventory_value,
        "receipt_income_total": receipt_income_total,
        "expenses_total": expenses_total,
        "operating_result": operating_result,
        "income_by_type": income_by_type,
        "expenses_by_category": expenses_by_category,
        "monthly_rows": monthly_rows,
        "active_clients": active_clients,
        "active_prospects": active_prospects,
        "new_clients": new_clients,
        "converted_prospects": converted_prospects,
        "open_credit": open_credit,
        "overdue_credit": overdue_credit,
        "overdue_installments": overdue_installments,
        "present_bookings": present_bookings,
        "absent_bookings": absent_bookings,
        "occupancy_rate": occupancy_rate,
        "bookings_by_day": bookings_by_day,
        "bookings_by_operator": bookings_by_operator,
        "bookings_by_hour": bookings_by_hour,
        "inventory_value": inventory_value,
        "low_stock": low_stock,
        "purchases": purchases,
        "sales": sales,
        "purchase_value": purchase_value,
        "sales_value": sales_value,
        "product_sales": product_sales,
    }


def _admin_metric_row(
    values: list[tuple[str, Any]],
) -> None:
    columns = st.columns(len(values))
    for column, (label, value) in zip(
        columns,
        values,
    ):
        column.metric(label, value)


ADMIN_CURRENCY_COLUMNS = {
    "Importo",
    "Importo previsto",
    "Importo prossima rata",
    "Prezzo",
    "Pagato",
    "Residuo",
    "Ricavi",
    "Costi",
    "Risultato",
    "Valore",
    "Costo medio",
}

ADMIN_DATE_COLUMNS = {
    "Data",
    "Scadenza",
    "Prossima rata",
    "Primo contatto",
}

ADMIN_NUMERIC_COLUMNS = {
    "Numero",
    "Quantità",
    "Giacenza",
    "Scorta minima",
    "Clienti",
    "Prospect",
    "Presenze",
}


def _admin_currency(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    formatted = (
        f"{number:,.2f}"
        .replace(",", "§")
        .replace(".", ",")
        .replace("§", ".")
    )
    return f"€ {formatted}"


def _admin_date(value: Any) -> str:
    parsed = _safe_date(value)
    return parsed.strftime("%d/%m/%Y") if parsed else "—"


def _admin_cell_text(
    column: str,
    value: Any,
) -> str:
    if value in (None, ""):
        return "—"

    if column in ADMIN_CURRENCY_COLUMNS:
        return _admin_currency(value)

    if column in ADMIN_DATE_COLUMNS:
        return _admin_date(value)

    if column in ADMIN_NUMERIC_COLUMNS:
        try:
            number = float(value)
            if number.is_integer():
                return f"{int(number):,}".replace(",", ".")
            return (
                f"{number:,.2f}"
                .replace(",", "§")
                .replace(".", ",")
                .replace("§", ".")
            )
        except (TypeError, ValueError):
            pass

    return str(value)


def _admin_status_class(value: Any) -> str:
    text = str(value or "").lower()

    if any(
        token in text
        for token in (
            "scadut",
            "annull",
            "assente",
            "non interessato",
        )
    ):
        return "is-danger"

    if any(
        token in text
        for token in (
            "parziale",
            "da contattare",
            "in valutazione",
            "sotto scorta",
        )
    ):
        return "is-warning"

    if any(
        token in text
        for token in (
            "pagata",
            "presente",
            "attivo",
            "valido",
            "convertito",
            "regolare",
        )
    ):
        return "is-success"

    return "is-neutral"


def _admin_dataframe(
    rows: list[dict[str, Any]],
    *,
    empty_message: str,
    status_column: str | None = None,
    highlight_column: str | None = None,
) -> None:
    """
    Unico renderer delle tabelle Admin.

    Lo stile è applicato esclusivamente dentro .kreo-admin-table:
    nessuna regola globale e nessun conflitto con le altre pagine.
    """
    if not rows:
        st.info(empty_message)
        return

    columns = list(rows[0].keys())

    header_html = "".join(
        f"<div class='kreo-admin-th'>{escape(str(column))}</div>"
        for column in columns
    )

    body_rows: list[str] = []
    for row in rows:
        cells: list[str] = []

        for column in columns:
            value = row.get(column)
            text = escape(_admin_cell_text(column, value))

            classes = ["kreo-admin-td"]

            if column in ADMIN_CURRENCY_COLUMNS:
                classes.append("is-number")

            if column in ADMIN_DATE_COLUMNS:
                classes.append("is-date")

            if column == highlight_column:
                classes.append("is-highlight")

            if column == status_column:
                status_class = _admin_status_class(value)
                cell = (
                    f"<div class='{' '.join(classes)}'>"
                    f"<span class='kreo-status {status_class}'>"
                    f"<span class='kreo-status-dot'></span>"
                    f"{text}"
                    f"</span>"
                    f"</div>"
                )
            else:
                cell = (
                    f"<div class='{' '.join(classes)}'>"
                    f"{text}"
                    f"</div>"
                )

            cells.append(cell)

        body_rows.append(
            "<div class='kreo-admin-tr'>"
            + "".join(cells)
            + "</div>"
        )

    template = f"repeat({len(columns)}, minmax(130px, 1fr))"

    st.markdown(
        f"""
        <div class="kreo-admin-table-wrap">
            <div
                class="kreo-admin-table"
                style="--kreo-admin-columns:{template};"
            >
                <div class="kreo-admin-thead">
                    {header_html}
                </div>
                <div class="kreo-admin-tbody">
                    {''.join(body_rows)}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


ADMIN_CHART_COLORS = {
    "gold": "#D8B45D",
    "blue": "#7DA8FF",
    "red": "#FF8D82",
    "green": "#86D39A",
    "muted": "#7F8A96",
}


def _admin_chart_style(chart: alt.Chart) -> alt.Chart:
    return (
        chart.properties(
            height=300,
        )
        .configure_view(
            stroke="#BFA15A",
            strokeOpacity=0.45,
            cornerRadius=12,
            fill="#111417",
        )
        .configure(background="#111417")
        .configure_axis(
            domain=False,
            grid=True,
            gridColor="rgba(255,255,255,0.08)",
            tickColor="rgba(255,255,255,0.18)",
            labelColor="#EAE6DD",
            titleColor="#D8BC73",
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_legend(
            orient="bottom",
            titleColor="#D8BC73",
            labelColor="#EAE6DD",
            symbolStrokeWidth=6,
            padding=10,
        )
    )



def _admin_chart_tooltip(field: str, *, currency: bool = False, title: str | None = None) -> alt.Tooltip:
    if currency:
        return alt.Tooltip(field, title=title or field.split(":")[0], format=",.2f")
    return alt.Tooltip(field, title=title or field.split(":")[0])



def _admin_bar_chart(
    rows: list[dict[str, Any]],
    *,
    x: str,
    y: str,
    empty_message: str,
    currency: bool = False,
    color: str = "gold",
) -> None:
    if not rows:
        st.info(empty_message)
        return

    df = pd.DataFrame(rows)
    chart = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8,
        size=42,
        color=ADMIN_CHART_COLORS[color],
    ).encode(
        x=alt.X(f"{x}:N", sort="-y", axis=alt.Axis(labelAngle=-28)),
        y=alt.Y(f"{y}:Q", title=None),
        tooltip=[
            _admin_chart_tooltip(f"{x}:N", title=x),
            _admin_chart_tooltip(f"{y}:Q", currency=currency, title=y),
        ],
    )
    st.altair_chart(_admin_chart_style(chart), use_container_width=True)



def _admin_line_chart(
    rows: list[dict[str, Any]],
    *,
    x: str,
    y: str,
    empty_message: str,
    currency: bool = False,
    color: str = "gold",
) -> None:
    if not rows:
        st.info(empty_message)
        return

    df = pd.DataFrame(rows)
    line = alt.Chart(df).mark_line(
        point=alt.OverlayMarkDef(filled=True, size=72),
        strokeWidth=3,
        color=ADMIN_CHART_COLORS[color],
    ).encode(
        x=alt.X(f"{x}:N", axis=alt.Axis(labelAngle=-28)),
        y=alt.Y(f"{y}:Q", title=None),
        tooltip=[
            _admin_chart_tooltip(f"{x}:N", title=x),
            _admin_chart_tooltip(f"{y}:Q", currency=currency, title=y),
        ],
    )
    st.altair_chart(_admin_chart_style(line), use_container_width=True)



def _admin_multi_line_chart(
    rows: list[dict[str, Any]],
    *,
    x: str,
    series: list[tuple[str, str, str]],
    empty_message: str,
    currency: bool = False,
) -> None:
    if not rows:
        st.info(empty_message)
        return

    df = pd.DataFrame(rows)
    value_columns = [item[0] for item in series]
    label_map = {item[0]: item[1] for item in series}
    color_map = {item[1]: ADMIN_CHART_COLORS[item[2]] for item in series}

    melted = df.melt(
        id_vars=[x],
        value_vars=value_columns,
        var_name="serie_key",
        value_name="valore",
    )
    melted["Serie"] = melted["serie_key"].map(label_map)

    base = alt.Chart(melted).encode(
        x=alt.X(f"{x}:N", axis=alt.Axis(labelAngle=-28)),
        y=alt.Y("valore:Q", title=None),
        color=alt.Color(
            "Serie:N",
            scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values()),
            ),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            _admin_chart_tooltip(f"{x}:N", title=x),
            alt.Tooltip("Serie:N", title="Serie"),
            _admin_chart_tooltip("valore:Q", currency=currency, title="Valore"),
        ],
    )

    chart = base.mark_line(point=alt.OverlayMarkDef(filled=True, size=64), strokeWidth=3)
    st.altair_chart(_admin_chart_style(chart), use_container_width=True)


def admin_overview(
    snapshot: dict[str, Any],
) -> None:
    _admin_metric_row([
        (
            "Ricavi periodo",
            money(snapshot["income_total"]),
        ),
        (
            "Costi periodo",
            money(snapshot["expenses_total"]),
        ),
        (
            "Risultato operativo",
            money(snapshot["operating_result"]),
        ),
        (
            "Crediti da incassare",
            money(snapshot["open_credit"]),
        ),
    ])

    _admin_metric_row([
        (
            "Clienti attivi",
            len(snapshot["active_clients"]),
        ),
        (
            "Prospect attivi",
            len(snapshot["active_prospects"]),
        ),
        (
            "Presenze periodo",
            len(snapshot["present_bookings"]),
        ),
        (
            "Valore magazzino",
            money(snapshot["inventory_value"]),
        ),
    ])

    st.subheader("Andamento economico")
    monthly_rows = snapshot["monthly_rows"]
    if monthly_rows:
        _admin_multi_line_chart(
            monthly_rows,
            x="mese",
            series=[
                ("ricavi", "Ricavi", "blue"),
                ("costi", "Costi", "red"),
                ("risultato", "Risultato", "gold"),
            ],
            empty_message="Nessun movimento economico nel periodo.",
            currency=True,
        )
        monthly_table_rows = [
            {
                "Mese": row["mese"],
                "Ricavi": row["ricavi"],
                "Costi": row["costi"],
                "Risultato": row["risultato"],
            }
            for row in monthly_rows
        ]
        _admin_dataframe(
            monthly_table_rows,
            empty_message=(
                "Nessun movimento economico nel periodo."
            ),
            highlight_column="Risultato",
        )
    else:
        st.info("Nessun movimento economico nel periodo.")

    left, right = st.columns(2)
    with left:
        st.subheader("Situazioni da presidiare")
        alerts = pd.DataFrame([
            {
                "Indicatore": "Rate scadute",
                "Numero": len(
                    snapshot["overdue_installments"]
                ),
                "Valore": snapshot["overdue_credit"],
            },
            {
                "Indicatore": "Prodotti sotto scorta",
                "Numero": len(snapshot["low_stock"]),
                "Valore": None,
            },
            {
                "Indicatore": "Assenze",
                "Numero": len(
                    snapshot["absent_bookings"]
                ),
                "Valore": None,
            },
        ])
        _admin_dataframe(
            alerts.to_dict("records"),
            empty_message="Nessuna situazione da presidiare.",
        )

    with right:
        st.subheader("Acquisizione clienti")
        _admin_bar_chart(
            [
                {
                    "Indicatore": "Nuovi clienti",
                    "Valore": len(snapshot["new_clients"]),
                },
                {
                    "Indicatore": "Prospect convertiti",
                    "Valore": len(snapshot["converted_prospects"]),
                },
                {
                    "Indicatore": "Prospect aperti",
                    "Valore": len(snapshot["active_prospects"]),
                },
            ],
            x="Indicatore",
            y="Valore",
            empty_message="Nessun dato di acquisizione.",
            color="gold",
        )


def admin_economic(
    snapshot: dict[str, Any],
) -> None:
    st.subheader("Mini conto economico")

    subscriptions_income = snapshot[
        "subscriptions_contract_value"
    ]
    inventory_income = snapshot["inventory_income"]
    products_income = snapshot[
        "income_by_type"
    ].get("vendita_prodotto", 0.0)
    other_income = sum(
        value
        for key, value in snapshot[
            "income_by_type"
        ].items()
        if key not in {
            "abbonamento",
            "vendita_prodotto",
            "giacenze_magazzino",
        }
    )

    economic_rows = [
        {
            "Voce": "Ricavi abbonamenti",
            "Tipo": "Ricavo",
            "Importo": subscriptions_income,
        },
        {
            "Voce": "Giacenze finali di magazzino",
            "Tipo": "Ricavo",
            "Importo": inventory_income,
        },
        {
            "Voce": "Vendite integratori",
            "Tipo": "Ricavo",
            "Importo": products_income,
        },
        {
            "Voce": "Altri ricavi",
            "Tipo": "Ricavo",
            "Importo": other_income,
        },
        {
            "Voce": "Totale ricavi",
            "Tipo": "Totale",
            "Importo": snapshot["income_total"],
        },
        {
            "Voce": "Costi registrati",
            "Tipo": "Costo",
            "Importo": -snapshot["expenses_total"],
        },
        {
            "Voce": "Risultato operativo",
            "Tipo": "Risultato",
            "Importo": snapshot["operating_result"],
        },
    ]
    _admin_dataframe(
        economic_rows,
        empty_message="Nessun dato economico disponibile.",
        status_column="Tipo",
        highlight_column="Importo",
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Ricavi per tipologia")
        income_rows = [
            {
                "Tipologia": key.replace("_", " ").title(),
                "Importo": value,
            }
            for key, value in sorted(
                snapshot["income_by_type"].items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        if income_rows:
            _admin_bar_chart(
                income_rows,
                x="Tipologia",
                y="Importo",
                empty_message="Nessun ricavo nel periodo.",
                currency=True,
                color="gold",
            )
        else:
            st.info("Nessun ricavo nel periodo.")

    with right:
        st.subheader("Costi per categoria")
        cost_rows = [
            {
                "Categoria": key,
                "Importo": value,
            }
            for key, value in sorted(
                snapshot[
                    "expenses_by_category"
                ].items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        if cost_rows:
            _admin_bar_chart(
                cost_rows,
                x="Categoria",
                y="Importo",
                empty_message="Nessun costo nel periodo.",
                currency=True,
                color="red",
            )
        else:
            st.info("Nessun costo nel periodo.")

    st.subheader("Dettaglio costi")
    expense_rows = [
        {
            "Data": row.get("data_spesa"),
            "Categoria": (
                row.get("categoria")
                or row.get("categoria_spesa")
                or "Senza categoria"
            ),
            "Fornitore": (
                row.get("fornitore")
                or "—"
            ),
            "Descrizione": row.get("descrizione"),
            "Importo": float(
                row.get("totale")
                or row.get("importo")
                or 0
            ),
            "Pagato": float(
                row.get("pagato") or 0
            ),
            "Residuo": float(
                row.get("residuo") or 0
            ),
        }
        for row in snapshot["expenses"]
    ]
    _admin_dataframe(
        expense_rows,
        empty_message="Nessun costo registrato nel periodo.",
        highlight_column="Residuo",
    )


def admin_customers(
    snapshot: dict[str, Any],
) -> None:
    _admin_metric_row([
        (
            "Clienti attivi",
            len(snapshot["active_clients"]),
        ),
        (
            "Nuovi clienti",
            len(snapshot["new_clients"]),
        ),
        (
            "Prospect attivi",
            len(snapshot["active_prospects"]),
        ),
        (
            "Conversioni",
            len(snapshot["converted_prospects"]),
        ),
    ])

    left, right = st.columns(2)
    with left:
        st.subheader("Clienti per pacchetto")
        by_package: dict[str, int] = {}
        for row in snapshot["active_clients"]:
            package = str(
                row.get("pacchetto_nome")
                or row.get("pacchetto")
                or "Senza pacchetto"
            )
            by_package[package] = (
                by_package.get(package, 0) + 1
            )
        if by_package:
            _admin_bar_chart(
                [
                    {"Pacchetto": key, "Clienti": value}
                    for key, value in by_package.items()
                ],
                x="Pacchetto",
                y="Clienti",
                empty_message="Nessun cliente attivo.",
                color="gold",
            )
        else:
            st.info("Nessun cliente attivo.")

    with right:
        st.subheader("Prospect per stato")
        by_state: dict[str, int] = {}
        for row in snapshot["prospects"]:
            state = str(row.get("stato") or "Nuovo")
            by_state[state] = by_state.get(state, 0) + 1
        if by_state:
            _admin_bar_chart(
                [
                    {"Stato": key, "Prospect": value}
                    for key, value in by_state.items()
                ],
                x="Stato",
                y="Prospect",
                empty_message="Nessun prospect registrato.",
                color="blue",
            )
        else:
            st.info("Nessun prospect registrato.")

    st.subheader("Prospect da lavorare")
    prospect_rows = [
        {
            "Prospect": prospect_label(row),
            "Stato": row.get("stato"),
            "Fonte": row.get("fonte"),
            "Interesse": row.get("interesse"),
            "Telefono": (
                row.get("whatsapp")
                or row.get("telefono")
            ),
            "Operatore": row.get(
                "operatore_assegnato"
            ),
            "Primo contatto": row.get(
                "data_primo_contatto"
            ),
        }
        for row in snapshot["active_prospects"]
    ]
    _admin_dataframe(
        prospect_rows,
        empty_message="Nessun prospect attivo.",
        status_column="Stato",
    )


def admin_attendance(
    snapshot: dict[str, Any],
) -> None:
    _admin_metric_row([
        (
            "Prenotazioni",
            len(snapshot["bookings"]),
        ),
        (
            "Presenze",
            len(snapshot["present_bookings"]),
        ),
        (
            "Assenze",
            len(snapshot["absent_bookings"]),
        ),
        (
            "Tasso presenza",
            f"{snapshot['occupancy_rate']:.1f}%",
        ),
    ])

    left, right = st.columns(2)
    with left:
        st.subheader("Presenze per giorno")
        if snapshot["bookings_by_day"]:
            _admin_line_chart(
                [
                    {"Giorno": key, "Presenze": value}
                    for key, value in snapshot["bookings_by_day"].items()
                ],
                x="Giorno",
                y="Presenze",
                empty_message="Nessuna presenza nel periodo.",
                color="gold",
            )
        else:
            st.info("Nessuna presenza nel periodo.")

    with right:
        st.subheader("Presenze per operatore")
        if snapshot["bookings_by_operator"]:
            _admin_bar_chart(
                [
                    {"Operatore": key, "Presenze": value}
                    for key, value in snapshot["bookings_by_operator"].items()
                ],
                x="Operatore",
                y="Presenze",
                empty_message="Nessuna presenza nel periodo.",
                color="blue",
            )
        else:
            st.info("Nessuna presenza nel periodo.")

    st.subheader("Presenze per fascia oraria")
    if snapshot["bookings_by_hour"]:
        _admin_bar_chart(
            [
                {"Ora": key, "Presenze": value}
                for key, value in sorted(snapshot["bookings_by_hour"].items())
            ],
            x="Ora",
            y="Presenze",
            empty_message="Nessuna presenza nel periodo.",
            color="gold",
        )
    else:
        st.info("Nessuna presenza nel periodo.")


def admin_inventory(
    snapshot: dict[str, Any],
) -> None:
    _admin_metric_row([
        (
            "Valore inventario",
            money(snapshot["inventory_value"]),
        ),
        (
            "Prodotti sotto scorta",
            len(snapshot["low_stock"]),
        ),
        (
            "Acquisti periodo",
            money(snapshot["purchase_value"]),
        ),
        (
            "Vendite periodo",
            money(snapshot["sales_value"]),
        ),
    ])

    left, right = st.columns(2)
    with left:
        st.subheader("Prodotti più venduti")
        rows = [
            {
                "Prodotto": product,
                "Quantità": values["quantita"],
                "Valore": values["valore"],
            }
            for product, values in sorted(
                snapshot["product_sales"].items(),
                key=lambda item: item[1]["quantita"],
                reverse=True,
            )
        ]
        _admin_dataframe(
            rows[:10],
            empty_message=(
                "Nessuna vendita integratori "
                "nel periodo."
            ),
        )

    with right:
        st.subheader("Scorte da controllare")
        low_stock_rows = [
            {
                "Codice": row.get("codice"),
                "Prodotto": row.get("nome"),
                "Giacenza": float(
                    row.get("giacenza") or 0
                ),
                "Scorta minima": float(
                    row.get("scorta_minima") or 0
                ),
            }
            for row in snapshot["low_stock"]
        ]
        _admin_dataframe(
            low_stock_rows,
            empty_message="Nessuna scorta critica.",
            highlight_column="Giacenza",
        )

    st.subheader("Inventario valorizzato")
    inventory_rows = [
        {
            "Codice": row.get("codice"),
            "Prodotto": row.get("nome"),
            "Categoria": row.get("categoria"),
            "Giacenza": float(
                row.get("giacenza") or 0
            ),
            "Costo medio": float(
                row.get("costo_medio") or 0
            ),
            "Valore": (
                float(row.get("giacenza") or 0)
                * float(row.get("costo_medio") or 0)
            ),
        }
        for row in snapshot["inventory"]
        if row.get("attivo")
    ]
    _admin_dataframe(
        inventory_rows,
        empty_message="Nessun prodotto in inventario.",
        highlight_column="Valore",
    )


def admin_receivables(
    snapshot: dict[str, Any],
) -> None:
    _admin_metric_row([
        (
            "Crediti complessivi",
            money(snapshot["open_credit"]),
        ),
        (
            "Scaduto",
            money(snapshot["overdue_credit"]),
        ),
        (
            "Rate scadute",
            len(snapshot["overdue_installments"]),
        ),
        (
            "Clienti con residuo",
            sum(
                1
                for row in snapshot["subscriptions"]
                if float(row.get("residuo") or 0) > 0
            ),
        ),
    ])

    st.subheader("Rate scadute")
    overdue_rows = [
        {
            "Cliente": row.get("cliente"),
            "Scadenza": row.get("data_scadenza"),
            "Importo previsto": float(
                row.get("importo_previsto") or 0
            ),
            "Residuo": float(
                row.get("residuo_rata") or 0
            ),
            "Stato": row.get("stato"),
        }
        for row in snapshot["overdue_installments"]
    ]
    _admin_dataframe(
        overdue_rows,
        empty_message="Nessuna rata scaduta.",
        status_column="Stato",
        highlight_column="Residuo",
    )

    st.subheader("Residui per cliente")
    residual_rows = [
        {
            "Cliente": row.get("cliente"),
            "Pacchetto": row.get("pacchetto"),
            "Prezzo": float(
                row.get("prezzo_concordato") or 0
            ),
            "Pagato": float(row.get("pagato") or 0),
            "Residuo": float(row.get("residuo") or 0),
            "Prossima rata": row.get(
                "prossima_rata_data"
            ),
            "Importo prossima rata": float(
                row.get("prossima_rata_importo") or 0
            ),
        }
        for row in snapshot["subscriptions"]
        if float(row.get("residuo") or 0) > 0
    ]
    residual_rows.sort(
        key=lambda row: row["Residuo"],
        reverse=True,
    )
    _admin_dataframe(
        residual_rows,
        empty_message="Nessun credito aperto.",
        highlight_column="Residuo",
    )



def admin_users_access() -> None:
    require_permission("utenti.gestisci")
    st.subheader("Utenti e livelli di accesso")
    st.caption("Ruoli e permessi sono centralizzati per azienda.")

    company_id = load_company()["id"]
    roles = elenco_ruoli_accesso(db)
    users = elenco_utenti_azienda(db, company_id)
    role_labels = {row["nome"]: row["codice"] for row in roles}

    create_tab, users_tab = st.tabs([
        "Crea credenziali",
        "Utenti abilitati",
    ])
    with create_tab:
        st.caption(
            "L'utente viene creato direttamente: "
            "nessuna email viene inviata."
        )

        with st.form("create_user_credentials_form"):
            name = st.text_input("Nome e cognome")
            email = st.text_input(
                "Email / username",
                help=(
                    "Sarà usata come username per accedere "
                    "al gestionale."
                ),
            ).strip().lower()
            role_label = st.selectbox(
                "Ruolo",
                list(role_labels),
            )
            password = st.text_input(
                "Password temporanea",
                type="password",
                help="Minimo 8 caratteri.",
            )
            password_confirm = st.text_input(
                "Conferma password",
                type="password",
            )
            submitted = st.form_submit_button(
                "Crea utente e assegna accesso",
                use_container_width=True,
            )

        if submitted:
            try:
                if not name.strip():
                    raise ValueError(
                        "Inserisci nome e cognome."
                    )
                if not email:
                    raise ValueError(
                        "Inserisci l'email usata come username."
                    )
                if password != password_confirm:
                    raise ValueError(
                        "Le password non coincidono."
                    )

                auth_user_id = crea_utente_auth_con_password(
                    db,
                    email=email,
                    password=password,
                    nome_visualizzato=name,
                )

                try:
                    salva_accesso_utente(db, {
                        "azienda_id": company_id,
                        "auth_user_id": auth_user_id,
                        "email": email,
                        "nome_visualizzato": name.strip(),
                        "ruolo_codice": role_labels[role_label],
                        "attivo": True,
                        "modificato_da": st.session_state.get(
                            "auth_email"
                        ),
                    })
                except Exception:
                    # Evita utenti Auth orfani quando il salvataggio
                    # dell'associazione aziendale non riesce.
                    try:
                        db.auth.admin.delete_user(auth_user_id)
                    except Exception:
                        pass
                    raise

                st.success(
                    "Utente creato. Può accedere subito "
                    "con email e password assegnate."
                )
                st.rerun()

            except Exception as exc:
                message = str(exc)
                if (
                    "already registered" in message.lower()
                    or "already been registered" in message.lower()
                    or "user already exists" in message.lower()
                ):
                    st.error(
                        "Questa email esiste già in Supabase Auth. "
                        "Usa un'altra email oppure associa "
                        "l'account esistente."
                    )
                else:
                    st.error(
                        f"Utente non creato: {message}"
                    )

    with users_tab:
        if not users:
            st.info("Nessun utente abilitato.")
        for user in users:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1.4, 1])
                c1.write(f"**{user.get('nome_visualizzato') or user.get('email')}**")
                c1.caption(user.get("email"))
                current_role = user.get("ruolo_nome")
                role_options = list(role_labels)
                selected_index = role_options.index(current_role) if current_role in role_options else 0
                new_role_label = c2.selectbox(
                    "Ruolo",
                    role_options,
                    index=selected_index,
                    key=f"role_{user['id']}",
                    label_visibility="collapsed",
                )
                active = c3.toggle("Attivo", value=bool(user.get("attivo")), key=f"active_{user['id']}")
                if st.button("Aggiorna", key=f"save_access_{user['id']}"):
                    salva_accesso_utente(db, {
                        "id": user["id"],
                        "azienda_id": company_id,
                        "auth_user_id": user.get("auth_user_id"),
                        "email": user["email"],
                        "nome_visualizzato": user.get("nome_visualizzato"),
                        "ruolo_codice": role_labels[new_role_label],
                        "attivo": active,
                        "modificato_da": st.session_state.get("auth_email"),
                    })
                    st.success("Utente aggiornato.")
                    st.rerun()


def page_admin() -> None:
    header(
        "Admin",
        "Cabina di controllo direzionale KREO.",
    )

    today = today_italy()
    default_start = today.replace(day=1)

    filter_left, filter_right = st.columns(2)
    start_date = filter_left.date_input(
        "Dal",
        value=default_start,
        format="DD/MM/YYYY",
        key="admin_start_date",
    )
    end_date = filter_right.date_input(
        "Al",
        value=today,
        format="DD/MM/YYYY",
        key="admin_end_date",
    )

    if start_date > end_date:
        st.error(
            "La data iniziale non può essere "
            "successiva alla data finale."
        )
        return

    snapshot = build_admin_snapshot(
        start_date,
        end_date,
    )

    tabs = st.tabs([
        "Panoramica",
        "Economico",
        "Clienti e Prospect",
        "Presenze",
        "Magazzino",
        "Crediti e Rate",
        "Utenti e accessi",
    ])

    with tabs[0]:
        admin_overview(snapshot)
    with tabs[1]:
        admin_economic(snapshot)
    with tabs[2]:
        admin_customers(snapshot)
    with tabs[3]:
        admin_attendance(snapshot)
    with tabs[4]:
        admin_inventory(snapshot)
    with tabs[5]:
        admin_receivables(snapshot)
    with tabs[6]:
        admin_users_access()


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



def safe_export_filename(value: str) -> str:
    cleaned = "".join(
        character.lower()
        if character.isalnum()
        else "_"
        for character in value.strip()
    )
    return "_".join(
        part for part in cleaned.split("_") if part
    ) or "report"


def render_export_controls(
    *,
    report_key: str,
    title: str,
    columns: list[ExportColumn],
    rows: list[dict[str, Any]],
    filters: list[str] | None = None,
    totals: dict[str, Any] | None = None,
    orientation: str = "landscape",
) -> None:
    if not rows:
        st.caption("Nessun dato da esportare con i filtri attuali.")
        return

    company = load_company()
    generated_at = now_italy()
    filename = (
        f"{safe_export_filename(title)}_"
        f"{generated_at.strftime('%Y%m%d_%H%M')}"
    )

    excel_bytes = build_excel_bytes(
        title=title,
        company=company,
        columns=columns,
        rows=rows,
        filters=filters or [],
        totals=totals or {},
        generated_at=generated_at,
    )
    pdf_bytes = build_pdf_bytes(
        title=title,
        company=company,
        columns=columns,
        rows=rows,
        filters=filters or [],
        totals=totals or {},
        generated_at=generated_at,
        orientation=orientation,
    )
    csv_bytes = build_csv_bytes(
        columns=columns,
        rows=rows,
    )

    st.caption(
        "L'esportazione rispetta i filtri attualmente applicati."
    )
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "Esporta Excel",
        data=excel_bytes,
        file_name=f"{filename}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key=f"{report_key}_xlsx",
        use_container_width=True,
    )
    c2.download_button(
        "PDF / Stampa",
        data=pdf_bytes,
        file_name=f"{filename}.pdf",
        mime="application/pdf",
        key=f"{report_key}_pdf",
        use_container_width=True,
        help=(
            "Apri il PDF scaricato e usa il comando Stampa "
            "del browser o del lettore PDF."
        ),
    )
    c3.download_button(
        "Esporta CSV",
        data=csv_bytes,
        file_name=f"{filename}.csv",
        mime="text/csv",
        key=f"{report_key}_csv",
        use_container_width=True,
    )


def client_export_columns() -> list[ExportColumn]:
    return [
        ExportColumn("cliente", "Cliente", "text", 27),
        ExportColumn("telefono", "Telefono", "text", 15),
        ExportColumn("whatsapp", "WhatsApp", "text", 15),
        ExportColumn("pacchetto", "Pacchetto", "text", 25),
        ExportColumn("scadenza", "Scadenza", "date", 13),
        ExportColumn(
            "disponibilita_lezioni",
            "Disponibilità lezioni",
            "text",
            28,
        ),
        ExportColumn("prezzo", "Prezzo iniziale", "currency", 14),
        ExportColumn("pagato", "Pagato", "currency", 12),
        ExportColumn("residuo", "Residuo", "currency", 12),
        ExportColumn(
            "prossima_rata",
            "Prossima rata",
            "date",
            13,
        ),
        ExportColumn(
            "importo_prossima_rata",
            "Importo prossima rata",
            "currency",
            15,
        ),
        ExportColumn(
            "certificato",
            "Certificato",
            "text",
            16,
        ),
        ExportColumn(
            "stato_cliente",
            "Stato cliente",
            "text",
            13,
        ),
    ]


def client_export_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "cliente": (
                f"{row.get('cognome') or ''} "
                f"{row.get('nome') or ''}"
            ).strip(),
            "telefono": row.get("telefono"),
            "whatsapp": row.get("whatsapp"),
            "pacchetto": row.get("pacchetto_nome"),
            "scadenza": (
                None
                if row.get("senza_scadenza")
                else row.get("data_fine_prevista")
            ),
            "disponibilita_lezioni": (
                lesson_primary_text(row)
                + (
                    " · " + lesson_secondary_text(row)
                    if lesson_secondary_text(row)
                    else ""
                )
            ),
            "prezzo": float(
                row.get("prezzo_concordato") or 0
            ),
            "pagato": float(row.get("pagato") or 0),
            "residuo": float(row.get("residuo") or 0),
            "prossima_rata": row.get("prossima_rata_data"),
            "importo_prossima_rata": float(
                row.get("prossima_rata_importo") or 0
            ),
            "certificato": (
                row.get("certificato_stato") or "Mancante"
            ),
            "stato_cliente": (
                row.get("stato_cliente")
                or row.get("stato")
                or "attivo"
            ),
        }
        for row in rows
    ]


def inventory_export_columns(
    physical: bool = False,
) -> list[ExportColumn]:
    columns = [
        ExportColumn("codice", "Codice", "text", 13),
        ExportColumn("prodotto", "Prodotto", "text", 32),
        ExportColumn("categoria", "Categoria", "text", 15),
        ExportColumn("marca", "Marca", "text", 15),
        ExportColumn(
            "giacenza_iniziale",
            "Giacenza iniziale",
            "number",
            13,
        ),
        ExportColumn(
            "giacenza",
            "Giacenza attuale",
            "number",
            13,
        ),
    ]

    if physical:
        columns.extend([
            ExportColumn(
                "giacenza_contata",
                "Giacenza contata",
                "blank",
                14,
            ),
            ExportColumn(
                "differenza",
                "Differenza",
                "blank",
                12,
            ),
            ExportColumn(
                "note_conteggio",
                "Note conteggio",
                "blank",
                24,
            ),
        ])
        return columns

    columns.extend([
        ExportColumn(
            "costo_medio",
            "Costo medio",
            "currency",
            12,
        ),
        ExportColumn(
            "valore_giacenza",
            "Valore giacenza",
            "currency",
            14,
        ),
        ExportColumn(
            "prezzo_vendita",
            "Prezzo vendita",
            "currency",
            13,
        ),
        ExportColumn(
            "scorta_minima",
            "Scorta minima",
            "number",
            12,
        ),
        ExportColumn("stato", "Stato", "text", 13),
    ])
    return columns


def inventory_export_rows(
    rows: list[dict[str, Any]],
    *,
    physical: bool = False,
) -> list[dict[str, Any]]:
    exported = []

    for row in rows:
        stock = float(row.get("giacenza") or 0)
        minimum = float(row.get("scorta_minima") or 0)
        if not row.get("attivo"):
            state = "Inattivo"
        elif stock <= 0:
            state = "Esaurito"
        elif minimum > 0 and stock <= minimum:
            state = "Scorta bassa"
        else:
            state = "Disponibile"

        item = {
            "codice": row.get("codice"),
            "prodotto": row.get("nome"),
            "categoria": row.get("categoria"),
            "marca": row.get("marca"),
            "giacenza_iniziale": float(
                row.get("giacenza_iniziale") or 0
            ),
            "giacenza": stock,
        }

        if physical:
            item.update({
                "giacenza_contata": "",
                "differenza": "",
                "note_conteggio": "",
            })
        else:
            cost = float(row.get("costo_medio") or 0)
            item.update({
                "costo_medio": cost,
                "valore_giacenza": stock * cost,
                "prezzo_vendita": float(
                    row.get("prezzo_vendita") or 0
                ),
                "scorta_minima": minimum,
                "stato": state,
            })

        exported.append(item)

    return exported


def inventory_movement_columns() -> list[ExportColumn]:
    return [
        ExportColumn("data", "Data", "date", 12),
        ExportColumn("prodotto", "Prodotto", "text", 30),
        ExportColumn("tipo", "Movimento", "text", 18),
        ExportColumn("quantita", "Quantità", "number", 11),
        ExportColumn("cliente", "Cliente", "text", 22),
        ExportColumn("fornitore", "Fornitore", "text", 22),
        ExportColumn("documento", "Documento", "text", 16),
        ExportColumn("lotto", "Lotto", "text", 13),
        ExportColumn(
            "scadenza_lotto",
            "Scadenza lotto",
            "date",
            13,
        ),
        ExportColumn("causale", "Causale", "text", 30),
        ExportColumn("stato", "Stato", "text", 12),
    ]


def inventory_movement_export_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "data": row.get("data_movimento"),
            "prodotto": row.get("prodotto"),
            "tipo": row.get("tipo"),
            "quantita": float(row.get("quantita") or 0),
            "cliente": row.get("cliente"),
            "fornitore": row.get("fornitore"),
            "documento": row.get("documento"),
            "lotto": row.get("lotto"),
            "scadenza_lotto": row.get(
                "data_scadenza_lotto"
            ),
            "causale": row.get("causale"),
            "stato": row.get("stato"),
        }
        for row in rows
    ]


def page_reports() -> None:
    header(
        "Report",
        "Stampe ed esportazioni centralizzate per azienda.",
    )

    with st.expander("Invio automatico settimanale", expanded=False):
        st.write(
            "Ogni venerdì alle 19:00: report clienti e report "
            "integratori, entrambi in PDF e Excel."
        )
        st.caption(
            "Destinatario: rosariosoria2525@gmail.com"
        )
        if st.button(
            "Invia ora una prova",
            use_container_width=True,
            key="send_weekly_reports_test",
        ):
            try:
                email_config = dict(st.secrets["email"])
                result = send_weekly_reports_email(
                    db=db,
                    company=load_company(),
                    smtp_host=str(
                        email_config.get(
                            "smtp_host",
                            "smtp.gmail.com",
                        )
                    ),
                    smtp_port=int(
                        email_config.get("smtp_port", 587)
                    ),
                    username=str(email_config["username"]),
                    app_password=str(
                        email_config["app_password"]
                    ),
                    sender_name=str(
                        email_config.get(
                            "sender_name",
                            "KREO Studio Personal",
                        )
                    ),
                    recipient=str(
                        email_config.get(
                            "recipient",
                            "rosariosoria2525@gmail.com",
                        )
                    ),
                    force=True,
                    source="gestionale",
                )
                st.success(
                    "Email inviata correttamente con "
                    f"{result['attachment_count']} allegati."
                )
            except Exception as exc:
                st.error(f"Invio non riuscito: {exc}")

    report_type = st.selectbox(
        "Report",
        [
            "Elenco clienti",
            "Inventario valorizzato",
            "Inventario fisico",
            "Movimenti magazzino",
        ],
    )

    if report_type == "Elenco clienti":
        rows = load_clients()
        c1, c2 = st.columns([3, 1])
        search = c1.text_input(
            "Cerca cliente",
            key="report_client_search",
        )
        state_filter = c2.selectbox(
            "Stato",
            ["Tutti", "Attivi", "Inattivi"],
            key="report_client_state",
        )

        filtered = []
        for row in rows:
            state = (
                row.get("stato_cliente")
                or row.get("stato")
                or "attivo"
            )
            if state_filter == "Attivi" and state != "attivo":
                continue
            if (
                state_filter == "Inattivi"
                and state != "inattivo"
            ):
                continue
            searchable = " ".join(
                str(row.get(key) or "")
                for key in [
                    "nome",
                    "cognome",
                    "telefono",
                    "whatsapp",
                ]
            ).lower()
            if search and search.lower() not in searchable:
                continue
            filtered.append(row)

        export_rows = client_export_rows(filtered)
        st.dataframe(
            pd.DataFrame(export_rows),
            use_container_width=True,
            hide_index=True,
        )
        render_export_controls(
            report_key="central_clients",
            title="Elenco clienti",
            columns=client_export_columns(),
            rows=export_rows,
            filters=[
                f"Stato: {state_filter}",
                f"Ricerca: {search or 'nessuna'}",
            ],
            totals={
                "Numero clienti": len(export_rows),
                "Residuo complessivo": sum(
                    row["residuo"] for row in export_rows
                ),
            },
        )

    elif report_type in (
        "Inventario valorizzato",
        "Inventario fisico",
    ):
        rows = load_inventory_products()
        only_active = st.checkbox(
            "Solo prodotti attivi",
            value=True,
            key="report_inventory_active",
        )
        filtered = [
            row for row in rows
            if not only_active or row.get("attivo")
        ]
        physical = report_type == "Inventario fisico"
        export_rows = inventory_export_rows(
            filtered,
            physical=physical,
        )

        st.dataframe(
            pd.DataFrame(export_rows),
            use_container_width=True,
            hide_index=True,
        )
        render_export_controls(
            report_key=(
                "central_inventory_physical"
                if physical
                else "central_inventory"
            ),
            title=report_type,
            columns=inventory_export_columns(
                physical=physical
            ),
            rows=export_rows,
            filters=[
                (
                    "Solo prodotti attivi"
                    if only_active
                    else "Tutti i prodotti"
                )
            ],
            totals=(
                {
                    "Numero prodotti": len(export_rows),
                }
                if physical
                else {
                    "Numero prodotti": len(export_rows),
                    "Valore complessivo": sum(
                        row["valore_giacenza"]
                        for row in export_rows
                    ),
                }
            ),
        )

    else:
        rows = load_inventory_movements()
        export_rows = inventory_movement_export_rows(rows)
        st.dataframe(
            pd.DataFrame(export_rows),
            use_container_width=True,
            hide_index=True,
        )
        render_export_controls(
            report_key="central_inventory_movements",
            title="Movimenti magazzino",
            columns=inventory_movement_columns(),
            rows=export_rows,
            totals={"Numero movimenti": len(export_rows)},
        )


def placeholder_page(title: str) -> None:
    header(title, "Sezione prevista nella struttura.")
    st.info("Questa sezione entrerà nel blocco funzionale dedicato.")


PAGES = {
    "Reception": page_reception,
    "Pacchetti": page_packages,
    "Abbonamenti": page_subscriptions,
    "Clienti": page_customers,
    "Contabilità": page_accounting,
    "Magazzino": page_inventory,
    "Report": page_reports,
    "Admin": page_admin,
    "Azienda": company_page,
}


def main() -> None:
    if not PAGES:
        raise RuntimeError("Nessuna pagina registrata nel gestionale.")

    if not st.session_state.get("auth_user"):
        login_page()
        return

    if not load_companies():
        st.error("Utente autenticato ma non abilitato a nessuna azienda.")
        if st.button("Esci"):
            logout()
        return

    selected = sidebar()
    required_permission = PAGE_PERMISSIONS.get(selected)
    if required_permission:
        require_permission(required_permission)
    page = PAGES.get(selected)

    if page is None:
        allowed_pages = [name for name in PAGES if has_permission(PAGE_PERMISSIONS[name])]
        if not allowed_pages:
            st.error("Nessuna pagina autorizzata per questo ruolo.")
            return
        st.session_state.menu = allowed_pages[0]
        st.rerun()

    page()
    st.markdown(f'<div class="footer">{DEVELOPER_CREDIT}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
