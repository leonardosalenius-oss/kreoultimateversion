"""
KREO TURNSTILE AGENT V4.3.2 - EDGE ATOMIC + FAILSAFE

Architettura:
- ST-FH320: associazioni badge cliente/staff;
- TShark: osserva gli eventi badge del controller del tornello;
- Supabase RPC: unica decisione KREO;
- TCP controller: apre SOLO se KREO=CONSENTITO;
- Supabase RPC: registra esito fisico e, solo dopo apertura confermata,
  marca la prenotazione cliente PRESENTE tramite la logica centrale KREO.

PerfectGym/Spy possono restare attivi durante questa fase di transizione,
ma NON partecipano alla decisione KREO.
"""

import os
import queue
import re
import shutil
import sqlite3
import socket
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import hid
import pyodbc
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
AZIENDA_ID = os.getenv("KREO_AZIENDA_ID", "")

MDB_PATH = os.getenv(
    "PERFECTGYM_MDB_PATH",
    r"C:\database\perfectgym.mdb",
)
TSHARK_PATH = os.getenv(
    "TSHARK_PATH",
    r"C:\Program Files\Wireshark\tshark.exe",
)
CAPTURE_INTERFACE_HINT = os.getenv(
    "TURNSTILE_CAPTURE_INTERFACE",
    "Ethernet",
)

TURNSTILE_IP = os.getenv("TURNSTILE_IP", "192.168.199.1")
RECEPTION_IP = os.getenv("RECEPTION_IP", "192.168.199.100")
TURNSTILE_PORT = int(os.getenv("TURNSTILE_PORT", "10001"))
POLL_SECONDS = float(os.getenv("BADGE_AGENT_POLL_SECONDS", "0.5"))
DEBOUNCE_SECONDS = float(os.getenv("TURNSTILE_DEBOUNCE_SECONDS", "2.0"))
EDGE_SYNC_SECONDS = float(os.getenv("KREO_EDGE_SYNC_SECONDS", "2.0"))
EDGE_MAX_CACHE_AGE = float(os.getenv("KREO_EDGE_MAX_CACHE_AGE", "6.0"))
PAIRING_TIMEOUT_SECONDS = int(os.getenv("KREO_PAIRING_TIMEOUT_SECONDS", "60"))
EDGE_DB_PATH = os.getenv("KREO_EDGE_DB_PATH", str(Path(__file__).with_name("kreo_edge_queue.sqlite3")))

VID = 0xFFFF
PID = 0x0035
REPORT_SIZE = 256

FRAME_1 = bytes.fromhex(
    "AA 00 0A 20 00 01 06 00 11 22 33 44 55 3C BB"
)
FRAME_2 = bytes.fromhex(
    "AA 00 03 25 26 00 00 BB"
)

# Comando di apertura catturato e già verificato fisicamente.
OPEN_MESSAGE = (
    b"\x02"
    + b"06|000255000|010|1|0001"
    + b"\x03"
)

EVENT_RE = re.compile(
    rb"\x02" + re.escape(b"2M|A|H|1|S|") + rb"([^\x03]+)\x03"
)

stop_event = threading.Event()
hid_lock = threading.Lock()
event_queue = queue.Queue()
last_seen = {}
edge_cache = {}
edge_cache_lock = threading.RLock()
edge_cache_updated_monotonic = 0.0
edge_cache_generated_at = None
welcome_queue = queue.Queue()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY or not AZIENDA_ID:
        raise RuntimeError(
            "Configura SUPABASE_URL, SUPABASE_KEY e "
            "KREO_AZIENDA_ID nel file .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def make_report(frame):
    report = bytearray(REPORT_SIZE)
    report[0] = 0x01
    report[6:8] = len(frame).to_bytes(2, "little")
    report[8:8 + len(frame)] = frame
    return bytes(report)


def uid_from_response(data):
    raw = bytes(data or b"")
    if len(raw) < 8:
        return None
    frame_len = int.from_bytes(raw[6:8], "little")
    frame = raw[8:8 + frame_len]

    if len(frame) >= 11 and frame[0] == 0xAA and frame[-1] == 0xBB:
        uid = frame[5:9]
        if len(uid) == 4:
            return uid.hex().upper()

    if len(frame) >= 8 and frame[0] == 0xAA and frame[-1] == 0xBB:
        uid = frame[4:8]
        if len(uid) == 4:
            return uid.hex().upper()
    return None


def read_badge_once():
    with hid_lock:
        device = hid.device()
        try:
            device.open(VID, PID)
            device.send_feature_report(make_report(FRAME_1))
            time.sleep(0.12)
            response_1 = device.get_feature_report(0x02, REPORT_SIZE)
            uid_1 = uid_from_response(response_1)

            time.sleep(0.08)

            device.send_feature_report(make_report(FRAME_2))
            time.sleep(0.12)
            response_2 = device.get_feature_report(0x02, REPORT_SIZE)
            uid_2 = uid_from_response(response_2)
            return uid_2 or uid_1
        finally:
            try:
                device.close()
            except Exception:
                pass


def next_queue_row(client, table):
    rows = (
        client.schema("gestionale_v2")
        .table(table)
        .select("*")
        .eq("stato", "in_attesa")
        .order("richiesto_il")
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def update_queue(client, table, row_id, values):
    values["updated_at"] = now_iso()
    (
        client.schema("gestionale_v2")
        .table(table)
        .update(values)
        .eq("id", row_id)
        .execute()
    )


def process_badge_request(client, table, row):
    row_id = row["id"]
    update_queue(
        client,
        table,
        row_id,
        {
            "stato": "in_lettura",
            "preso_in_carico_il": now_iso(),
        },
    )

    label = (
        "STAFF"
        if table == "richieste_lettura_badge_staff"
        else "CLIENTE"
    )
    print(
        f"{datetime.now():%H:%M:%S} | "
        f"Lettura {label} {row_id} | attendo ST-FH320..."
    )

    deadline = time.time() + 18
    uid = None
    while time.time() < deadline and not stop_event.is_set():
        try:
            uid = read_badge_once()
            if uid:
                break
        except Exception as exc:
            print("WARN lettore ST-FH320:", repr(exc))
        time.sleep(0.35)

    if uid:
        update_queue(
            client,
            table,
            row_id,
            {
                "stato": "letto",
                "rfid_uid": uid,
                "letto_il": now_iso(),
            },
        )
        print(f"{datetime.now():%H:%M:%S} | RFID {label}: {uid}")
    else:
        update_queue(
            client,
            table,
            row_id,
            {
                "stato": "scaduto",
                "errore": "Nessun badge rilevato entro il tempo previsto",
            },
        )


def expire_old_manual_open_requests(client):
    now = now_iso()
    rows = (
        client.schema("gestionale_v2")
        .table("richieste_apertura_tornello")
        .select("id,scade_il")
        .eq("azienda_id", AZIENDA_ID)
        .eq("stato", "in_attesa")
        .lt("scade_il", now)
        .execute()
        .data
        or []
    )
    for row in rows:
        (
            client.schema("gestionale_v2")
            .table("richieste_apertura_tornello")
            .update(
                {
                    "stato": "scaduto",
                    "completato_il": now_iso(),
                    "errore": (
                        "Richiesta scaduta prima della presa in carico"
                    ),
                    "updated_at": now_iso(),
                }
            )
            .eq("id", row["id"])
            .execute()
        )


def next_manual_open_request(client):
    expire_old_manual_open_requests(client)
    rows = (
        client.schema("gestionale_v2")
        .table("richieste_apertura_tornello")
        .select("*")
        .eq("azienda_id", AZIENDA_ID)
        .eq("stato", "in_attesa")
        .gt("scade_il", now_iso())
        .order("richiesto_il")
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def process_manual_open_request(client, row):
    row_id = row["id"]
    (
        client.schema("gestionale_v2")
        .table("richieste_apertura_tornello")
        .update(
            {
                "stato": "in_esecuzione",
                "preso_in_carico_il": now_iso(),
                "updated_at": now_iso(),
            }
        )
        .eq("id", row_id)
        .eq("stato", "in_attesa")
        .execute()
    )

    print(
        f"{datetime.now():%H:%M:%S} | "
        "APERTURA MANUALE richiesta | "
        + str(row.get("motivazione") or "")
    )

    success, response, error = open_turnstile()

    values = {
        "stato": "aperto" if success else "errore",
        "completato_il": now_iso(),
        "risposta_controller": response or None,
        "errore": error or (
            None if success else "Controller non ha restituito OK"
        ),
        "updated_at": now_iso(),
    }
    (
        client.schema("gestionale_v2")
        .table("richieste_apertura_tornello")
        .update(values)
        .eq("id", row_id)
        .execute()
    )

    if success:
        print(
            f"{datetime.now():%H:%M:%S} | "
            "APERTURA MANUALE: OK - controller conferma"
        )
    else:
        print(
            f"{datetime.now():%H:%M:%S} | "
            "APERTURA MANUALE: ERRORE | "
            + str(error or response or "nessun OK")
        )


def manual_open_queue_loop():
    client = get_supabase()
    while not stop_event.is_set():
        try:
            row = next_manual_open_request(client)
            if row:
                process_manual_open_request(client, row)
            else:
                time.sleep(POLL_SECONDS)
        except Exception as exc:
            print("ERRORE coda apertura manuale:", repr(exc))
            time.sleep(2)


def badge_queue_loop():
    client = get_supabase()
    tables = (
        "richieste_lettura_badge",
        "richieste_lettura_badge_staff",
    )
    while not stop_event.is_set():
        try:
            handled = False
            for table in tables:
                row = next_queue_row(client, table)
                if row:
                    process_badge_request(client, table, row)
                    handled = True
                    break
            if not handled:
                time.sleep(POLL_SECONDS)
        except Exception as exc:
            print("ERRORE coda badge:", repr(exc))
            time.sleep(2)


def resolve_tshark():
    candidates = [
        Path(TSHARK_PATH),
        Path(r"C:\Program Files\Wireshark\tshark.exe"),
        Path(r"C:\Program Files (x86)\Wireshark\tshark.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which("tshark")
    if found:
        return found
    raise FileNotFoundError(
        "tshark.exe non trovato. Configura TSHARK_PATH nel file .env."
    )


def resolve_interface(tshark):
    result = subprocess.run(
        [tshark, "-D"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    hint = CAPTURE_INTERFACE_HINT.lower()

    for line in lines:
        if hint in line.lower():
            number = line.split(".", 1)[0].strip()
            if number.isdigit():
                print("Interfaccia TShark:", line)
                return number

    print("Interfacce disponibili:")
    for line in lines:
        print(" ", line)
    raise RuntimeError(
        f"Interfaccia contenente '{CAPTURE_INTERFACE_HINT}' non trovata."
    )


def hex_field_to_bytes(value):
    clean = re.sub(r"[^0-9A-Fa-f]", "", value or "")
    if not clean or len(clean) % 2:
        return b""
    try:
        return bytes.fromhex(clean)
    except ValueError:
        return b""


class PerfectGymLegacy:
    def __init__(self):
        self.conn = None
        self.last_id = None

    def connect(self):
        if not Path(MDB_PATH).exists():
            return False
        self.conn = pyodbc.connect(
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            rf"DBQ={MDB_PATH};READONLY=TRUE;",
            autocommit=True,
        )
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT MAX(IDStorico) FROM Storico_accessi")
            row = cur.fetchone()
            self.last_id = int(row[0]) if row and row[0] is not None else 0
        finally:
            cur.close()

        print(
            "PerfectGym legacy correlation: attiva | "
            f"ultimo IDStorico={self.last_id}"
        )
        return True

    def newest_idsocio_after_event(self, wait_seconds=0.65):
        if not self.conn:
            return None
        time.sleep(wait_seconds)
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT TOP 10 IDStorico, IDSocio
                FROM Storico_accessi
                WHERE IDStorico > ?
                ORDER BY IDStorico ASC
                """,
                self.last_id or 0,
            )
            rows = cur.fetchall()
            if not rows:
                return None
            self.last_id = max(int(row[0]) for row in rows)
            idsocio = rows[-1][1]
            return str(idsocio).strip() if idsocio is not None else None
        except Exception as exc:
            print("WARN correlazione PerfectGym:", repr(exc))
            return None
        finally:
            cur.close()



def expire_pending_pairings(client):
    try:
        result = client.schema("gestionale_v2").rpc(
            "scadi_richieste_abbinamento_tornello",
            {
                "p_azienda_id": AZIENDA_ID,
                "p_timeout_secondi": PAIRING_TIMEOUT_SECONDS,
            },
        ).execute().data
        if result:
            print(
                f"{datetime.now():%H:%M:%S} | "
                f"PAIRING FAILSAFE: {result} richiesta/e scaduta/e"
            )
    except Exception as exc:
        print("WARN scadenza pairing:", repr(exc))


def fail_pairing(client, pairing, message):
    try:
        client.schema("gestionale_v2").rpc(
            "fallisci_richiesta_abbinamento_tornello",
            {
                "payload": {
                    "richiesta_id": pairing["id"],
                    "azienda_id": AZIENDA_ID,
                    "errore": str(message)[:1000],
                }
            },
        ).execute()
    except Exception as exc:
        print("WARN chiusura pairing in errore:", repr(exc))


def mapped_badge_owner(code):
    code = str(code or "").strip().upper()
    if not code:
        return None

    with edge_cache_lock:
        row = dict(edge_cache.get(code) or {})

    if not row:
        return None

    return {
        "mapped": True,
        "ambiguous": bool(row.get("_collisione_badge")),
        "identity": row.get("identita"),
        "tipo_badge": row.get("tipo_badge"),
        "badge_cliente_id": row.get("badge_cliente_id"),
        "badge_staff_id": row.get("badge_staff_id"),
    }


def pairing_targets_same_badge(pairing, owner):
    if not owner or owner.get("ambiguous"):
        return False

    if pairing.get("tipo_badge") == "cliente":
        return (
            str(pairing.get("badge_id") or "")
            == str(owner.get("badge_cliente_id") or "")
        )

    if pairing.get("tipo_badge") == "staff":
        return (
            str(pairing.get("badge_id") or "")
            == str(owner.get("badge_staff_id") or "")
        )

    return False


def get_pending_pairing(client):
    expire_pending_pairings(client)
    rows = (
        client.schema("gestionale_v2")
        .table("richieste_abbinamento_tornello")
        .select("*")
        .eq("azienda_id", AZIENDA_ID)
        .eq("stato", "in_attesa")
        .order("richiesto_il")
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def complete_pairing(client, pairing, code):
    try:
        result = client.schema("gestionale_v2").rpc(
            "completa_abbinamento_tornello",
            {
                "payload": {
                    "richiesta_id": pairing["id"],
                    "codice_tornello": code,
                }
            },
        ).execute().data or {}
    except Exception as exc:
        fail_pairing(client, pairing, repr(exc))
        print(
            f"{datetime.now():%H:%M:%S} | "
            f"PAIRING ERRORE -> accesso normale | {repr(exc)}"
        )
        return False, {"stato": "errore", "errore": repr(exc)}

    print(
        f"{datetime.now():%H:%M:%S} | "
        f"PAIRING {pairing['tipo_badge']} -> {code} | {result}"
    )
    return bool(result.get("abbinato")), result


def code_is_already_mapped(client, code):
    for table in ("badge_staff", "badge_clienti"):
        rows = (
            client.schema("gestionale_v2")
            .table(table)
            .select("id")
            .eq("azienda_id", AZIENDA_ID)
            .eq("attivo", True)
            .eq("codice_tornello", code)
            .limit(1)
            .execute()
            .data
        )
        if rows:
            return True
    return False




def render_welcome_template(template, row):
    text = str(template or "")
    return (
        text
        .replace("{nome}", str(row.get("nome") or "").strip())
        .replace(
            "{cognome}",
            str(row.get("cognome") or "").strip(),
        )
    ).strip()


def speak_windows_tts(text, volume=100, rate=0):
    if not text:
        return

    # TTS locale Windows: usa il dispositivo audio predefinito del
    # PC Reception. Parte in un worker separato: non rallenta il tornello.
    safe_text = text.replace("'", "''")
    volume = max(0, min(100, int(volume or 100)))
    rate = max(-10, min(10, int(rate or 0)))

    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Volume = {volume}; "
        f"$s.Rate = {rate}; "
        "$voices = $s.GetInstalledVoices() | "
        "Where-Object { $_.Enabled -and "
        "$_.VoiceInfo.Culture.Name -like 'it-*' }; "
        "if ($voices.Count -gt 0) { "
        "$s.SelectVoice($voices[0].VoiceInfo.Name) }; "
        f"$s.Speak('{safe_text}');"
    )

    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            ps,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def welcome_worker():
    while not stop_event.is_set():
        try:
            item = welcome_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        try:
            speak_windows_tts(
                item.get("text"),
                item.get("volume", 100),
                item.get("rate", 0),
            )
        except Exception as exc:
            print("WARN TTS:", repr(exc))
        finally:
            welcome_queue.task_done()


def edge_snapshot(client):
    rows = client.schema("gestionale_v2").rpc(
        "snapshot_tornello_edge",
        {"p_azienda_id": AZIENDA_ID},
    ).execute().data or []

    by_code = {}
    generated_at = None

    for row in rows:
        code = str(row.get("codice_tornello") or "").strip().upper()
        if not code:
            continue
        by_code.setdefault(code, []).append(row)
        generated_at = row.get("generato_il") or generated_at

    snapshot = {}

    for code, matches in by_code.items():
        owners = {}
        for row in matches:
            owner_key = (
                str(row.get("tipo_badge") or ""),
                str(
                    row.get("badge_cliente_id")
                    or row.get("badge_staff_id")
                    or row.get("cliente_id")
                    or ""
                ),
            )
            owners.setdefault(owner_key, row)

        if len(owners) == 1:
            snapshot[code] = next(iter(owners.values()))
            continue

        names = sorted({
            str(row.get("identita") or "Soggetto sconosciuto")
            for row in owners.values()
        })

        snapshot[code] = {
            "codice_tornello": code,
            "tipo_badge": "ambiguo",
            "badge_cliente_id": None,
            "badge_staff_id": None,
            "cliente_id": None,
            "nome": None,
            "cognome": None,
            "identita": " / ".join(names),
            "decisione_kreo": "negato",
            "motivo": (
                "BADGE AMBIGUO: codice "
                + code
                + " associato a "
                + ", ".join(names)
            ),
            "prenotazione_id": None,
            "benvenuto_attivo": False,
            "benvenuto_app_attivo": False,
            "benvenuto_audio_attivo": False,
            "generato_il": generated_at,
            "_collisione_badge": True,
        }

    return snapshot, generated_at


def edge_sync_loop():
    global edge_cache
    global edge_cache_updated_monotonic
    global edge_cache_generated_at

    client = get_supabase()

    while not stop_event.is_set():
        started = time.monotonic()
        try:
            snapshot, generated_at = edge_snapshot(client)
            with edge_cache_lock:
                edge_cache = snapshot
                edge_cache_updated_monotonic = time.monotonic()
                edge_cache_generated_at = generated_at
            collision_count = sum(
                1
                for row in snapshot.values()
                if row.get("_collisione_badge")
            )
            print(
                f"{datetime.now():%H:%M:%S} | "
                f"EDGE SYNC: {len(snapshot)} codici in cache"
                + (
                    f" | COLLISIONI: {collision_count}"
                    if collision_count
                    else ""
                )
            )
        except Exception as exc:
            print("WARN EDGE SYNC:", repr(exc))

        elapsed = time.monotonic() - started
        stop_event.wait(max(0.10, EDGE_SYNC_SECONDS - elapsed))


def local_edge_decision(code):
    code = str(code or "").strip().upper()

    with edge_cache_lock:
        row = dict(edge_cache.get(code) or {})
        updated = edge_cache_updated_monotonic
        generated_at = edge_cache_generated_at

    if not row:
        return None, "cache_miss"

    age = time.monotonic() - updated if updated else float("inf")

    if age > EDGE_MAX_CACHE_AGE:
        return None, f"cache_stale_{age:.2f}s"

    row["cache_age_seconds"] = age
    row["cache_generata_il"] = row.get("generato_il") or generated_at
    return row, "edge"


def init_edge_queue():
    with sqlite3.connect(EDGE_DB_PATH) as conn:
        conn.execute(
            """
            create table if not exists pending_edge_events (
              id integer primary key autoincrement,
              payload text not null,
              created_at text not null,
              attempts integer not null default 0
            )
            """
        )
        conn.commit()


def _prepare_edge_payload(payload, detected_at=None):
    prepared = dict(payload)
    prepared.setdefault("edge_event_uid", str(uuid.uuid4()))
    prepared.setdefault("rilevato_il", detected_at or now_iso())
    return prepared


def enqueue_edge_event(payload, detected_at=None):
    import json
    prepared = _prepare_edge_payload(payload, detected_at)
    with sqlite3.connect(EDGE_DB_PATH) as conn:
        conn.execute(
            """
            insert into pending_edge_events(payload, created_at)
            values (?, ?)
            """,
            (
                json.dumps(prepared),
                prepared["rilevato_il"],
            ),
        )
        conn.commit()


def _persist_edge_payload(row_id, payload):
    import json
    with sqlite3.connect(EDGE_DB_PATH) as conn:
        conn.execute(
            """
            update pending_edge_events
            set payload = ?
            where id = ?
            """,
            (json.dumps(payload), row_id),
        )
        conn.commit()


def next_edge_event():
    import json
    with sqlite3.connect(EDGE_DB_PATH) as conn:
        row = conn.execute(
            """
            select id, payload, created_at, attempts
            from pending_edge_events
            order by id
            limit 1
            """
        ).fetchone()

    if not row:
        return None

    row_id, payload_text, created_at, attempts = row
    payload = json.loads(payload_text)

    changed = False
    if not payload.get("edge_event_uid"):
        payload["edge_event_uid"] = str(uuid.uuid4())
        changed = True
    if not payload.get("rilevato_il"):
        payload["rilevato_il"] = created_at or now_iso()
        changed = True

    if changed:
        _persist_edge_payload(row_id, payload)

    return {
        "id": row_id,
        "payload": payload,
        "created_at": created_at,
        "attempts": attempts,
    }


def delete_edge_event(row_id):
    with sqlite3.connect(EDGE_DB_PATH) as conn:
        conn.execute(
            "delete from pending_edge_events where id = ?",
            (row_id,),
        )
        conn.commit()


def bump_edge_event(row_id):
    with sqlite3.connect(EDGE_DB_PATH) as conn:
        conn.execute(
            """
            update pending_edge_events
            set attempts = attempts + 1
            where id = ?
            """,
            (row_id,),
        )
        conn.commit()


def sync_edge_event(client, payload):
    result = client.schema("gestionale_v2").rpc(
        "sincronizza_evento_tornello_edge",
        {
            "payload": {
                "azienda_id": AZIENDA_ID,
                "edge_event_uid": payload.get("edge_event_uid"),
                "rilevato_il": payload.get("rilevato_il"),
                "codice_tornello": payload["codice_tornello"],
                "tipo_badge": payload.get("tipo_badge"),
                "badge_cliente_id": payload.get("badge_cliente_id"),
                "badge_staff_id": payload.get("badge_staff_id"),
                "cliente_id": payload.get("cliente_id"),
                "identita": payload.get("identita"),
                "decisione_kreo": payload["decisione_kreo"],
                "motivo": payload.get("motivo"),
                "prenotazione_id": payload.get("prenotazione_id"),
                "cache_generata_il": payload.get("cache_generata_il"),
                "latenza_decisione_ms": payload.get(
                    "latenza_decisione_ms"
                ),
                "apertura_tentata": payload.get("apertura_tentata"),
                "apertura_successo": payload.get("apertura_successo"),
                "risposta_controller": payload.get(
                    "risposta_controller"
                ),
                "errore_apertura": payload.get("errore_apertura"),
                "benvenuto_app_attivo": payload.get(
                    "benvenuto_app_attivo"
                ),
                "benvenuto_testo_app_rendered": payload.get(
                    "benvenuto_testo_app_rendered"
                ),
            }
        },
    ).execute().data or {}

    post = result.get("post_apertura") or {}
    if payload.get("apertura_tentata"):
        print(
            f"{datetime.now():%H:%M:%S} | "
            "POST ACCESSO: "
            f"evento={result.get('evento_id')} | "
            f"presenza={post.get('presenza_registrata')} | "
            f"tipo={post.get('tipo_consumo')} | "
            f"consumo={post.get('consumo_lezioni')} | "
            f"saldo={post.get('saldo_lezioni_dopo')} | "
            f"quota={post.get('utilizzi_settimana')}/"
            f"{post.get('quota_settimanale')} | "
            f"residue={post.get('residue_settimana')} | "
            f"errore={post.get('errore_presenza')}"
        )

    return result


def edge_post_sync_loop():
    client = get_supabase()

    while not stop_event.is_set():
        row = next_edge_event()
        if not row:
            stop_event.wait(0.20)
            continue

        try:
            sync_edge_event(client, row["payload"])
            delete_edge_event(row["id"])
        except Exception as exc:
            bump_edge_event(row["id"])
            retry_number = row["attempts"] + 1
            wait_seconds = min(
                60.0,
                max(2.0, 2.0 ** min(retry_number, 5)),
            )
            print(
                "WARN EDGE POST-SYNC:",
                repr(exc),
                "| retry:",
                retry_number,
                f"| nuovo tentativo tra {wait_seconds:.0f}s",
            )
            stop_event.wait(wait_seconds)


def evaluate_event(client, code, idsocio=None):
    payload = {
        "azienda_id": AZIENDA_ID,
        "codice_tornello": code,
        "modalita": "attivo",
    }
    if idsocio:
        payload["perfectgym_idsocio"] = idsocio

    return client.schema("gestionale_v2").rpc(
        "valuta_evento_tornello_kreo",
        {"payload": payload},
    ).execute().data or {}


def open_turnstile():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3.0)
    try:
        sock.connect((TURNSTILE_IP, TURNSTILE_PORT))
        sock.sendall(OPEN_MESSAGE)
        try:
            response = sock.recv(4096)
        except socket.timeout:
            response = b""

        success = b"OK" in response
        response_text = (
            response.decode("ascii", errors="replace")
            if response
            else ""
        )
        return success, response_text, None
    except Exception as exc:
        return False, "", repr(exc)
    finally:
        try:
            sock.close()
        except Exception:
            pass


def register_open_result(
    client,
    event_id,
    success,
    response_text,
    error_text,
):
    return client.schema("gestionale_v2").rpc(
        "registra_esito_apertura_tornello",
        {
            "payload": {
                "azienda_id": AZIENDA_ID,
                "evento_id": event_id,
                "successo": success,
                "risposta_controller": response_text or None,
                "errore_apertura": error_text or None,
            }
        },
    ).execute().data or {}


def event_worker():
    client = get_supabase()
    legacy = PerfectGymLegacy()
    try:
        legacy.connect()
    except Exception as exc:
        print(
            "PerfectGym legacy correlation non disponibile:",
            repr(exc),
        )

    while not stop_event.is_set():
        try:
            code = event_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        detected_at = time.monotonic()
        detected_iso = now_iso()

        try:
            pairing = get_pending_pairing(client)
            if pairing:
                owner = mapped_badge_owner(code)

                if owner and not pairing_targets_same_badge(
                    pairing,
                    owner,
                ):
                    fail_pairing(
                        client,
                        pairing,
                        (
                            "Badge già assegnato a "
                            + str(
                                owner.get("identity")
                                or "altro soggetto"
                            )
                        ),
                    )
                    print(
                        f"{datetime.now():%H:%M:%S} | "
                        f"PAIRING IGNORATO: {code} già assegnato a "
                        f"{owner.get('identity') or 'altro soggetto'} | "
                        "proseguo come ACCESSO"
                    )
                    # Nessun continue: lo stesso badge viene valutato
                    # immediatamente come normale accesso.
                else:
                    paired, pairing_result = complete_pairing(
                        client,
                        pairing,
                        code,
                    )

                    if paired:
                        print(
                            f"{datetime.now():%H:%M:%S} | "
                            "Pairing completato: ripassa il badge "
                            "per il test accesso."
                        )
                        continue

                    print(
                        f"{datetime.now():%H:%M:%S} | "
                        "PAIRING NON COMPLETATO: "
                        f"{pairing_result.get('errore') or pairing_result} | "
                        "proseguo come ACCESSO"
                    )
                    # Anche qui niente continue: accesso normale.

            decision, source = local_edge_decision(code)

            if decision is None:
                idsocio = None
                if not code_is_already_mapped(client, code) and legacy.conn:
                    idsocio = legacy.newest_idsocio_after_event()

                cloud = evaluate_event(client, code, idsocio)
                status = cloud.get("decisione_kreo", "?")
                identity = cloud.get("identita") or "NON MAPPATO"
                reason = cloud.get("motivo") or f"Fallback cloud: {source}"
                event_id = cloud.get("evento_id")

                print(
                    f"{datetime.now():%H:%M:%S} | "
                    f"TORNELLO {code} | CLOUD FALLBACK | "
                    f"KREO={status.upper()} | {identity} | {reason}"
                )

                if status != "consentito":
                    continue

                success, response, error = open_turnstile()
                elapsed_ms = (time.monotonic() - detected_at) * 1000.0

                print(
                    f"{datetime.now():%H:%M:%S} | "
                    f"APERTURA CLOUD: "
                    f"{'OK' if success else 'ERRORE'} | "
                    f"{elapsed_ms:.0f} ms"
                )

                if event_id:
                    register_open_result(
                        client,
                        event_id,
                        success,
                        response,
                        error,
                    )
                continue

            status = decision.get("decisione_kreo", "?")
            identity = decision.get("identita") or "NON MAPPATO"
            reason = decision.get("motivo") or ""
            cache_age = float(decision.get("cache_age_seconds") or 0)

            decision_ms = (time.monotonic() - detected_at) * 1000.0

            print(
                f"{datetime.now():%H:%M:%S} | "
                f"TORNELLO {code} | EDGE | "
                f"KREO={status.upper()} | {identity} | "
                f"cache={cache_age:.2f}s | {reason}"
            )

            payload = {
                "codice_tornello": code,
                "tipo_badge": decision.get("tipo_badge"),
                "badge_cliente_id": decision.get("badge_cliente_id"),
                "badge_staff_id": decision.get("badge_staff_id"),
                "cliente_id": decision.get("cliente_id"),
                "identita": identity,
                "decisione_kreo": status,
                "motivo": reason,
                "prenotazione_id": decision.get("prenotazione_id"),
                "cache_generata_il": decision.get("cache_generata_il"),
                "latenza_decisione_ms": round(decision_ms, 2),
                "apertura_tentata": False,
                "apertura_successo": False,
                "risposta_controller": None,
                "errore_apertura": None,
                "benvenuto_app_attivo": bool(
                    decision.get("benvenuto_attivo")
                    and decision.get("benvenuto_app_attivo")
                    and decision.get("tipo_badge") == "cliente"
                ),
                "benvenuto_testo_app_rendered": render_welcome_template(
                    decision.get("benvenuto_testo_app"),
                    decision,
                ),
            }

            if status != "consentito":
                enqueue_edge_event(payload, detected_iso)
                if decision.get("_collisione_badge"):
                    print(
                        f"{datetime.now():%H:%M:%S} | "
                        f"BADGE AMBIGUO {code} | {reason}"
                    )
                print(
                    f"{datetime.now():%H:%M:%S} | "
                    f"EDGE DECISIONE: NEGATA in {decision_ms:.0f} ms"
                )
                continue

            success, response, error = open_turnstile()
            elapsed_ms = (time.monotonic() - detected_at) * 1000.0

            payload.update(
                {
                    "apertura_tentata": True,
                    "apertura_successo": success,
                    "risposta_controller": response or None,
                    "errore_apertura": error or None,
                }
            )

            if (
                success
                and decision.get("tipo_badge") == "cliente"
                and decision.get("benvenuto_attivo")
                and decision.get("benvenuto_audio_attivo")
            ):
                welcome_queue.put(
                    {
                        "text": render_welcome_template(
                            decision.get("benvenuto_testo_audio"),
                            decision,
                        ),
                        "volume": decision.get(
                            "benvenuto_volume",
                            100,
                        ),
                        "rate": decision.get(
                            "benvenuto_velocita_voce",
                            0,
                        ),
                    }
                )

            enqueue_edge_event(payload, detected_iso)

            print(
                f"{datetime.now():%H:%M:%S} | "
                f"APERTURA EDGE: {'OK' if success else 'ERRORE'} | "
                f"badge→apertura {elapsed_ms:.0f} ms"
            )

        except Exception as exc:
            print("ERRORE evento tornello:", repr(exc))
        finally:
            event_queue.task_done()


def tshark_capture_loop():
    tshark = resolve_tshark()
    interface = resolve_interface(tshark)

    display_filter = (
        f"tcp.port == {TURNSTILE_PORT}"
        f" && ip.src == {TURNSTILE_IP}"
        f" && ip.dst == {RECEPTION_IP}"
        " && tcp.len > 0"
    )

    cmd = [
        tshark,
        "-l",
        "-n",
        "-i",
        interface,
        "-Y",
        display_filter,
        "-T",
        "fields",
        "-e",
        "tcp.payload",
    ]

    print("Capture tornello: ATTIVA")
    print("Decisione KREO: ATTIVA")
    print("Apertura tornello da KREO: ATTIVA")
    print("Apertura manuale da gestionale: ATTIVA")
    print("Filtro:", display_filter)
    print()

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    try:
        while not stop_event.is_set():
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    err = proc.stderr.read().strip()
                    raise RuntimeError(
                        "TShark terminato: " + (err or "errore sconosciuto")
                    )
                time.sleep(0.1)
                continue

            raw = hex_field_to_bytes(line.strip())
            if not raw:
                continue

            for match in EVENT_RE.finditer(raw):
                code = match.group(1).decode(
                    "ascii",
                    errors="ignore",
                ).strip().upper()

                if not code:
                    continue

                now = time.monotonic()
                previous = last_seen.get(code, 0)
                if now - previous < DEBOUNCE_SECONDS:
                    continue
                last_seen[code] = now

                print(
                    f"{datetime.now():%H:%M:%S} | "
                    f"Badge tornello rilevato: {code}"
                )
                event_queue.put(code)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def main():
    print("=" * 72)
    print("KREO TURNSTILE AGENT V4.3.2 - EDGE ATOMIC + FAILSAFE")
    print("=" * 72)
    print("ST-FH320: cliente + staff")
    print("Decisione accessi: KREO EDGE LOCALE")
    print(f"Sync cache: ogni {EDGE_SYNC_SECONDS:.1f}s")
    print(f"Cache max age: {EDGE_MAX_CACHE_AGE:.1f}s")
    print(f"Pairing timeout: {PAIRING_TIMEOUT_SECONDS}s")
    print("Pairing fail-safe: ATTIVO")
    print("Sync Edge atomico/idempotente: ATTIVO")
    print("STAFF: accesso senza limitazioni")
    print("Apertura fisica: KREO -> controller Ethernet")
    print("Presenza cliente: registrata SOLO dopo apertura confermata")
    print("=" * 72)
    print()

    get_supabase()
    init_edge_queue()

    threads = [
        threading.Thread(
            target=badge_queue_loop,
            name="badge-queue",
            daemon=True,
        ),
        threading.Thread(
            target=manual_open_queue_loop,
            name="manual-open-queue",
            daemon=True,
        ),
        threading.Thread(
            target=edge_sync_loop,
            name="edge-sync",
            daemon=True,
        ),
        threading.Thread(
            target=edge_post_sync_loop,
            name="edge-post-sync",
            daemon=True,
        ),
        threading.Thread(
            target=welcome_worker,
            name="welcome-tts",
            daemon=True,
        ),
        threading.Thread(
            target=event_worker,
            name="event-worker",
            daemon=True,
        ),
        threading.Thread(
            target=tshark_capture_loop,
            name="tshark-capture",
            daemon=True,
        ),
    ]

    for thread in threads:
        thread.start()

    try:
        while all(thread.is_alive() for thread in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArresto richiesto...")
    finally:
        stop_event.set()

    print("Agent terminato.")


if __name__ == "__main__":
    main()
