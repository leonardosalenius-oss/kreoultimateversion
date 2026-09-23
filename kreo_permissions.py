"""Owner flags and server-side gates for the trusted Streamlit backend.

This does not turn the service key into an end-user database credential. Machine
Agents retain their existing service clients; only interactive app clients are
wrapped. Every mapped write checks a fresh signed-user context from PostgreSQL.
Unknown endpoints fail closed. Construct once per script run, never globally.
"""
from __future__ import annotations
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable


class PermissionDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Rule:
    primary: str = ""
    alternatives: tuple[str, ...] = ()
    owner: bool = False
    all_of: tuple[str, ...] = ()


def allowed(context: dict, rule: Rule) -> bool:
    if context.get("proprietario") is True:
        return True
    if rule.owner:
        return False
    if any(code not in (context.get("permessi") or []) or code in (context.get("negati") or [])
           for code in rule.all_of):
        return False
    if not rule.primary:
        return True  # Company context already authenticated by the RPC.
    if rule.primary in (context.get("negati") or []):
        return False
    return bool(set((rule.primary,) + rule.alternatives) & set(context.get("permessi") or []))


C_READ = Rule("clienti.visualizza", ("report.visualizza", "admin.visualizza"))
C_WRITE = Rule("clienti.modifica")
A_WRITE = Rule("abbonamenti.gestisci")
CASH_READ = Rule("contabilita.visualizza", ("report.visualizza", "admin.visualizza"))
CASH_WRITE = Rule("contabilita.modifica")
CASH_CANCEL = Rule("contabilita.annulla")
STOCK_READ = Rule("magazzino.visualizza", ("report.visualizza", "admin.visualizza"))
STOCK_WRITE = Rule("magazzino.modifica")
RECEPTION = Rule("reception.visualizza")
BEP_WRITE = Rule("contabilita.modifica", all_of=("admin.visualizza",))
OWNER = Rule(owner=True)
MEMBER = Rule()
TABLE_RULES: dict[str, tuple[Rule, Rule]] = {}


def _tables(names: str, read: Rule, write: Rule) -> None:
    for name in names.split():
        TABLE_RULES[name] = (read, write)


_tables("aziende", MEMBER, Rule("azienda.modifica"))
_tables("vista_accesso_utente", MEMBER, OWNER)
_tables("ruoli_accesso vista_utenti_accessi", OWNER, OWNER)
_tables("clienti prospect accessi_clienti vista_clienti_operativa vista_certificati_clienti "
        "vista_rilevazioni_fisiche_cliente", C_READ, C_WRITE)
_tables("tipi_documento", C_READ, OWNER)
_tables("vista_abbonamenti_operativa vista_movimenti_lezioni_operativa vista_disponibilita_lezioni "
        "vista_quota_settimanale_tempo utilizzi_settimanali_tempo prenotazioni recuperi_settimanali", C_READ, A_WRITE)
_tables("pacchetti", Rule("pacchetti.gestisci", ("abbonamenti.gestisci", "reception.visualizza", "admin.visualizza", "report.visualizza")), Rule("pacchetti.gestisci"))
_tables("vista_incassi_operativa vista_rate_operativa vista_pagamenti_spesa_operativa vista_spese_operativa "
        "vista_regole_spese_ricorrenti vista_scadenze_spesa_operativa fornitori categorie_spesa", CASH_READ, CASH_WRITE)
_tables("vista_prodotti_magazzino vista_movimenti_magazzino vista_ordini_cliente_operativa", STOCK_READ, STOCK_WRITE)
_tables("operatori_agenda vista_prenotazioni_operativa vista_indisponibilita_operatori "
        "vista_slot_app_cliente_operativa vista_alert_prenotazioni_cliente vista_badge_operativa "
        "vista_accessi_operativa eventi_tornello_kreo vista_dispositivi_accesso badge_staff",
        Rule("reception.visualizza", ("admin.visualizza", "report.visualizza")), RECEPTION)
_tables("invii_report", Rule("report.visualizza"), Rule("report.visualizza"))
_tables("configurazione_bep configurazione_bep_pacchetti costi_fissi_bep", Rule("admin.visualizza"), BEP_WRITE)
RPC_RULES: dict[str, tuple[Rule, bool]] = {}


def _rpcs(names: str, rule: Rule, write: bool = True) -> None:
    for name in names.split():
        RPC_RULES[name] = (rule, write)


_rpcs("modifica_anagrafica_cliente salva_documento_cliente modifica_documento_cliente annulla_documento_cliente "
      "associa_badge_cliente associa_badge_rfid_reale cambia_stato_badge salva_rilevazione_fisica_cliente "
      "elimina_rilevazione_fisica_cliente", C_WRITE)
_rpcs("crea_cliente_completo", C_WRITE)
_rpcs("crea_abbonamento_cliente aggiorna_abbonamento_cliente aggiorna_rate_abbonamento "
      "rimodula_rate_residue rinnova_abbonamento_cliente cambia_stato_abbonamento "
      "registra_movimento_lezioni registra_recupero_settimanale", A_WRITE)
_rpcs("get_abbonamento_dettaglio get_cliente_dettaglio elenco_recuperi_abbonamento", C_READ, False)
_rpcs("calcola_lezioni_contrattuali_rpc", Rule("abbonamenti.gestisci", ("reception.visualizza",)), False)
_rpcs("salva_pacchetto", Rule("pacchetti.gestisci"))
_rpcs("registra_incasso_completo registra_pagamento_spesa crea_categoria_spesa crea_fornitore modifica_fornitore "
      "crea_spesa_completa modifica_spesa crea_regola_spesa_ricorrente modifica_regola_spesa_ricorrente "
      "cambia_stato_regola_spesa_ricorrente genera_spese_ricorrenti genera_ricevuta_incasso collega_pdf_ricevuta", CASH_WRITE)
_rpcs("annulla_incasso annulla_pagamento_spesa annulla_spesa elimina_regola_spesa_ricorrente", CASH_CANCEL)
_rpcs("get_ricevuta_dettaglio", CASH_READ, False)
_rpcs("registra_acquisto_magazzino registra_vendita_magazzino registra_rettifica_magazzino "
      "annulla_movimento_magazzino salva_prodotto_magazzino aggiorna_stato_ordine_cliente", STOCK_WRITE)
_rpcs("crea_prenotazione modifica_prenotazione cambia_stato_prenotazione segna_alert_prenotazione_letto "
      "gestisci_accesso_manuale crea_richiesta_apertura_tornello crea_richiesta_abbinamento_tornello "
      "crea_richiesta_lettura_badge crea_richiesta_lettura_badge_staff", RECEPTION)
_rpcs("get_cliente_staff_tecnico get_configurazione_tornello elenco_collisioni_badge elenco_richieste_apertura_tornello "
      "stato_richiesta_abbinamento_tornello stato_richiesta_apertura_tornello stato_richiesta_lettura_badge "
      "stato_richiesta_lettura_badge_staff verifica_collisione_badge", RECEPTION, False)
_rpcs("salva_indisponibilita_operatore elimina_indisponibilita_operatore crea_operatore_agenda "
      "rigenera_slot_operatori salva_slot_app_cliente cambia_stato_slot_app_cliente", Rule("agenda.indisponibilita"))
_rpcs("imposta_blocco_prenotazioni_cliente", Rule("clienti.blocca_prenotazioni"))
_rpcs("salva_azienda salva_asset_azienda imposta_regole_accesso_tornello imposta_benvenuto_tornello "
      "imposta_audio_dinieghi_tornello crea_dispositivo_accesso rigenera_token_dispositivo "
      "associa_badge_staff_rfid cambia_stato_badge_staff", Rule("azienda.modifica"))
_rpcs("salva_configurazione_bep salva_configurazione_bep_pacchetto salva_costo_fisso_bep elimina_costo_fisso_bep", BEP_WRITE)
_rpcs("elimina_cliente_definitivamente salva_accesso_utente bootstrap_super_admin kreo_salva_flag_utenti", OWNER)
_rpcs("kreo_leggi_flag_utenti", OWNER, False)
_rpcs("registra_audit_accesso", MEMBER)
JWT_RPCS = {"salva_accesso_utente", "kreo_leggi_flag_utenti", "kreo_salva_flag_utenti"}
GLOBAL_TABLES = {"ruoli_accesso"}


def user_rpc(auth_client: Any, client_factory: Callable, name: str, params: dict) -> Any:
    """The fresh client receives the user JWT; the shared service client never does."""
    session = auth_client.auth.get_session()
    token = getattr(session, "access_token", None)
    if not token:
        raise PermissionDenied("Sessione scaduta: accedi nuovamente.")
    client = client_factory()
    client.postgrest.auth(token)
    return client.rpc(name, params).execute()


class ProtectedDB:
    def __init__(self, data_client: Any, auth_client: Any, client_factory: Callable,
                 expected_user_id: str, company_id: str):
        self._data = data_client
        self._auth = auth_client
        self._factory = client_factory
        self.user_id = str(expected_user_id)
        self.company_id = str(company_id)
        self._context: dict | None = None
        self._created_auth_ids: set[str] = set()
        self.auth = SimpleNamespace(admin=_Admin(self))
        self.storage = _Storage(self)

    def context(self, *, fresh: bool = False) -> dict:
        if fresh or self._context is None:
            result = user_rpc(self._auth, self._factory, "kreo_contesto_permessi", {"p_azienda_id": self.company_id})
            data = result.data
            if not isinstance(data, dict) or str(data.get("auth_user_id")) != self.user_id or str(data.get("azienda_id")) != self.company_id:
                raise PermissionDenied("Identità o azienda della sessione non corrispondente.")
            self._context = data
        return self._context

    def require(self, rule: Rule, *, write: bool = False) -> dict:
        ctx = self.context(fresh=write)
        if not allowed(ctx, rule):
            raise PermissionDenied("Operazione non autorizzata per questo utente.")
        return ctx

    def table(self, name: str) -> Any:
        if name not in TABLE_RULES:
            raise PermissionDenied(f"Tabella non abilitata nel controllo accessi: {name}")
        return _Query(self, self._data.table(name), name)

    def rpc(self, name: str, params: dict | None = None) -> Any:
        if name not in RPC_RULES:
            raise PermissionDenied(f"Funzione non abilitata nel controllo accessi: {name}")
        return _RPC(self, name, params or {})

    def check_company(self, values: Any) -> None:
        if isinstance(values, list):
            for value in values:
                self.check_company(value)
        elif isinstance(values, dict):
            for key, value in values.items():
                if key in {"azienda_id", "p_azienda_id"} and str(value) != self.company_id:
                    raise PermissionDenied("Operazione riferita a un'altra azienda.")
                if isinstance(value, (dict, list)):
                    self.check_company(value)


def protect_db(data_client: Any, auth_client: Any, client_factory: Callable,
               expected_user_id: str, company_id: str) -> ProtectedDB:
    return ProtectedDB(data_client, auth_client, client_factory, expected_user_id, company_id)


class _Query:
    def __init__(self, db: ProtectedDB, query: Any, name: str):
        self._db, self._query, self._name = db, query, name
        self._write = False
        self._insert = False

    def __getattr__(self, method: str) -> Callable:
        if method.startswith("_") or method not in {
            "select", "insert", "upsert", "update", "delete", "eq", "neq", "gt", "gte", "lt", "lte",
            "like", "ilike", "in_", "is_", "or_", "not_", "contains", "contained_by", "order", "limit",
            "range", "single", "maybe_single", "filter", "match"}:
            raise AttributeError(method)
        def apply(*args, **kwargs):
            if method in {"insert", "upsert", "update", "delete"}:
                self._write = True
                self._insert = method in {"insert", "upsert"}
                if args:
                    self._db.check_company(args[0])
                if self._insert and self._name not in GLOBAL_TABLES and self._name != "aziende":
                    rows = args[0] if isinstance(args[0], list) else [args[0]]
                    if any(str(row.get("azienda_id")) != self._db.company_id for row in rows):
                        raise PermissionDenied("Azienda obbligatoria nei nuovi record.")
            if method == "eq" and args and args[0] == "azienda_id":
                self._db.check_company({"azienda_id": args[1]})
            self._query = getattr(self._query, method)(*args, **kwargs)
            return self
        return apply

    def execute(self, *args, **kwargs):
        rule = TABLE_RULES[self._name][int(self._write)]
        self._db.require(rule, write=self._write)
        if not self._insert and self._name not in GLOBAL_TABLES:
            column = "id" if self._name == "aziende" else "azienda_id"
            self._query = self._query.eq(column, self._db.company_id)
        if self._name == "vista_accesso_utente":
            self._query = self._query.eq("auth_user_id", self._db.user_id)
        return self._query.execute(*args, **kwargs)


class _RPC:
    def __init__(self, db: ProtectedDB, name: str, params: dict):
        self._db, self._name, self._params = db, name, params

    def execute(self, *args, **kwargs):
        rule, write = RPC_RULES[self._name]
        self._db.require(rule, write=write)
        self._db.check_company(self._params)
        # New customer is an atomic composite operation: check all included writes.
        if self._name == "crea_cliente_completo":
            payload = self._params.get("payload") or {}
            if payload.get("abbonamento"):
                self._db.require(A_WRITE)
            if payload.get("incasso_iniziale"):
                self._db.require(CASH_WRITE)
        if self._name in {"crea_abbonamento_cliente", "rinnova_abbonamento_cliente"}:
            if (self._params.get("payload") or {}).get("pagamento_iniziale"):
                self._db.require(CASH_WRITE)
        if self._name == "registra_vendita_magazzino":
            self._db.require(CASH_WRITE)
        if self._name in JWT_RPCS:
            result = user_rpc(self._db._auth, self._db._factory, self._name, self._params)
            self._db._context = None
            return result
        return self._db._data.rpc(self._name, self._params).execute(*args, **kwargs)


class _Admin:
    def __init__(self, db: ProtectedDB):
        self._db = db

    def create_user(self, attributes: dict):
        ctx = self._db.require(C_WRITE, write=True)
        result = self._db._data.auth.admin.create_user(attributes)
        user = getattr(result, "user", None)
        if user and getattr(user, "id", None):
            self._db._created_auth_ids.add(str(user.id))
        return result

    def _check_target(self, auth_user_id: str):
        ctx = self._db.context(fresh=True)
        if ctx.get("proprietario"):
            return
        self._db.require(C_WRITE)
        target = str(auth_user_id)
        # Never let a client-password reset become a staff-password reset.
        staff = self._db._data.table("utenti_aziende").select("id").eq("auth_user_id", target).limit(1).execute().data or []
        if staff:
            raise PermissionDenied("Le credenziali dello staff sono riservate al proprietario.")
        if target in self._db._created_auth_ids:
            return
        rows = self._db._data.table("accessi_clienti").select("id").eq("azienda_id", self._db.company_id).eq("auth_user_id", target).limit(1).execute().data or []
        if not rows:
            raise PermissionDenied("Account non collegato a un cliente di questa azienda.")

    def update_user_by_id(self, auth_user_id: str, attributes: dict):
        self._check_target(auth_user_id)
        if set(attributes) != {"password"}:
            raise PermissionDenied("Questa operazione consente solo la modifica password.")
        return self._db._data.auth.admin.update_user_by_id(auth_user_id, attributes)

    def delete_user(self, auth_user_id: str):
        self._check_target(auth_user_id)
        # Deletion is only for rollback of a just-created account in this run.
        if str(auth_user_id) not in self._db._created_auth_ids:
            raise PermissionDenied("Eliminazione account consentita solo come annullamento della creazione.")
        return self._db._data.auth.admin.delete_user(auth_user_id)


class _Storage:
    def __init__(self, db: ProtectedDB):
        self._db = db

    def from_(self, bucket: str):
        rules = {
            "documenti-clienti": (C_READ, C_WRITE),
            "immagini-prodotti": (STOCK_READ, STOCK_WRITE),
            "asset-aziende": (MEMBER, Rule("azienda.modifica")),
            "ricevute-pdf": (CASH_READ, CASH_WRITE),
            "documenti-spese": (CASH_READ, CASH_WRITE),
        }
        if bucket not in rules:
            raise PermissionDenied(f"Archivio non abilitato: {bucket}")
        return _Bucket(self._db, self._db._data.storage.from_(bucket), rules[bucket])


class _Bucket:
    def __init__(self, db: ProtectedDB, bucket: Any, rules: tuple[Rule, Rule]):
        self._db, self._bucket, self._rules = db, bucket, rules

    def __getattr__(self, method: str):
        if method not in {"upload", "remove", "create_signed_url", "get_public_url", "download"}:
            raise AttributeError(method)
        def call(*args, **kwargs):
            write = method in {"upload", "remove"}
            self._db.require(self._rules[int(write)], write=write)
            values = args[0] if args else kwargs.get("path")
            paths = values if isinstance(values, list) else [values]
            if not paths or any(not isinstance(p, str) or not p.startswith(self._db.company_id + "/")
                                or ".." in p.split("/") for p in paths):
                raise PermissionDenied("File non appartenente all'azienda attiva.")
            return getattr(self._bucket, method)(*args, **kwargs)
        return call


def render_user_permission_flags(st: Any, db: ProtectedDB, company_id: str, on_saved: Callable) -> None:
    """Owner-only UI; RPC also rejects other identities independently of widgets."""
    db.require(OWNER)
    data = db.rpc("kreo_leggi_flag_utenti", {"p_azienda_id": company_id}).execute().data
    st.subheader("Permessi individuali")
    st.caption("Eredita mantiene il ruolo assegnato. Consenti e Nega valgono per questo utente. Le modifiche sono registrate nello storico.")
    choices = ["Eredita dal ruolo", "Consenti", "Nega"]
    for user in data.get("utenti", []):
        if user.get("proprietario"):
            st.caption(f"{user.get('nome_visualizzato')}: proprietario, accesso completo protetto.")
            continue
        key = f"flags_{company_id}_{user['id']}_{data['revisione']}"
        with st.expander(user.get("nome_visualizzato") or user.get("email") or "Utente"):
            st.caption(f"Ruolo: {user.get('ruolo_nome')} · {user.get('email')}")
            with st.form(key):
                selected = {}
                for permission in data.get("catalogo", []):
                    code = permission["codice"]
                    current = (user.get("override") or {}).get(code)
                    index = 0 if current is None else (1 if current is True else 2)
                    label = f"{permission['area']} — {permission['descrizione']}"
                    choice = st.selectbox(label, choices, index=index, key=f"{key}_{code}")
                    if choice != choices[0]:
                        selected[code] = choice == choices[1]
                submitted = st.form_submit_button("Salva permessi", use_container_width=True)
            if submitted:
                try:
                    db.rpc("kreo_salva_flag_utenti", {"payload": {
                        "azienda_id": company_id, "utente_azienda_id": user["id"],
                        "revisione": data["revisione"], "override": selected,
                    }}).execute()
                except Exception as exc:
                    st.error(f"Permessi non salvati: {exc}")
                else:
                    on_saved()
                    st.success("Permessi aggiornati.")
                    st.rerun()
