"""Pannello importabile da app.py. Il chiamante verifica il permesso tornello."""

RULE_LABELS = {
    "cliente_attivo": ("Cliente inattivo", "Rivolgiti alla reception per riattivare il tuo profilo."),
    "abbonamento_valido": ("Abbonamento non valido", "Il tuo abbonamento non è valido. Rivolgiti alla reception."),
    "limite_lezioni": ("Limite lezioni raggiunto", "Hai raggiunto il limite di lezioni previsto dal tuo abbonamento."),
    "rate_abbonamento": ("Rate scadute", "È necessario regolarizzare il pagamento in reception."),
    "certificato_medico": ("Certificato mancante o scaduto", "Aggiorna il certificato medico in reception."),
    "prenotazione": ("Prenotazione assente", "Non risulta una prenotazione valida. Rivolgiti alla reception."),
}


def render_denial_audio_settings(st, db, company_id, config, on_saved, user_id=None):
    st.subheader("Messaggi vocali per accesso negato")
    if "diniego_audio_regole" not in config:
        st.info("La configurazione dei messaggi di accesso negato non è ancora disponibile.")
        return
    st.caption("Ogni messaggio segue il controllo che ha negato l'accesso. "
               "Spegnere la voce lascia attiva la regola. Puoi usare {nome} e {cognome}.")
    if not config.get("regole_accesso_attive", True):
        st.info("I controlli sono disattivati: i messaggi di accesso negato restano silenziosi.")
    prefix = f"denial_{company_id}"
    rules = config.get("diniego_audio_regole") or {}
    with st.form(prefix + "_form"):
        enabled = st.checkbox("Attiva voce per accessi negati",
                              value=bool(config.get("diniego_audio_attivo", False)),
                              key=prefix + "_enabled")
        desired = {}
        for code, (label, default) in RULE_LABELS.items():
            current = rules.get(code) or {}
            active = st.checkbox(label, value=bool(current.get("attivo", False)),
                                 key=prefix + "_" + code + "_enabled")
            text = st.text_input("Messaggio: " + label,
                                 value=str(current.get("testo", default)), max_chars=300,
                                 key=prefix + "_" + code + "_text")
            desired[code] = {"attivo": active, "testo": text.strip()}
        volume = st.slider("Volume messaggi di accesso negato", 0, 100,
                           int(config.get("diniego_audio_volume", 100)),
                           key=prefix + "_volume")
        rate = st.slider("Velocità messaggi di accesso negato", -10, 10,
                         int(config.get("diniego_audio_velocita_voce", 0)),
                         key=prefix + "_rate")
        submitted = st.form_submit_button("Salva messaggi di accesso negato")
    if submitted:
        if any(v["attivo"] and not v["testo"] for v in desired.values()):
            st.error("Inserisci il testo per ciascun messaggio attivo.")
            return
        try:
            response = db.rpc("imposta_audio_dinieghi_tornello", {"payload": {
                "azienda_id": str(company_id),
                "diniego_audio_attivo": enabled,
                "diniego_audio_regole": desired,
                "diniego_audio_volume": volume,
                "diniego_audio_velocita_voce": rate,
                "versione_attesa": int(config.get("diniego_audio_versione", 0)),
                "utente_id": user_id,
            }}).execute()
            if response.data is None:
                raise RuntimeError("Configurazione non salvata.")
            on_saved()
            st.success("Messaggi di accesso negato salvati.")
            st.rerun()
        except Exception as exc:
            st.error(f"Impossibile salvare i messaggi: {exc}")
