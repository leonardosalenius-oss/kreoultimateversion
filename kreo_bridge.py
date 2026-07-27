from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

BRIDGE_VERSION = "0.20.1"
CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            "File config.json non trovato. Copia config.example.json "
            "e inserisci URL, codice dispositivo e token."
        )

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    required = [
        "supabase_url",
        "supabase_anon_key",
        "device_code",
        "device_token",
    ]
    missing = [
        key for key in required
        if not str(config.get(key) or "").strip()
    ]
    if missing:
        raise RuntimeError(
            "Configurazione incompleta: " + ", ".join(missing)
        )
    return config


def process_badge(
    config: dict[str, Any],
    badge_code: str,
) -> dict[str, Any]:
    url = (
        config["supabase_url"].rstrip("/")
        + "/rest/v1/rpc/processa_accesso_badge"
    )
    api_key = str(config["supabase_anon_key"]).strip()

    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "Accept-Profile": config.get(
            "schema",
            "gestionale_v2",
        ),
        "Content-Profile": config.get(
            "schema",
            "gestionale_v2",
        ),
    }

    # Le nuove chiavi publishable Supabase (sb_publishable_...)
    # non sono JWT e non devono essere inviate come Bearer token.
    # La vecchia chiave anon JWT, invece, può essere usata anche
    # nell'header Authorization.
    if api_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "p_codice_dispositivo": config["device_code"],
        "p_token": config["device_token"],
        "p_codice_badge": badge_code,
        "p_versione_bridge": BRIDGE_VERSION,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def activate_turnstile(config: dict[str, Any]) -> None:
    command = config.get("open_command")
    if not command:
        print("[SIMULAZIONE] Comando apertura tornello non configurato.")
        return

    subprocess.run(
        command,
        shell=True,
        check=True,
        timeout=5,
    )


def signal_result(
    config: dict[str, Any],
    result: dict[str, Any],
) -> None:
    allowed = bool(result.get("consentito"))
    client = result.get("cliente") or ""
    message = result.get("messaggio") or ""

    if allowed:
        print(f"ACCESSO CONSENTITO {client} — {message}")
        activate_turnstile(config)
        print("\a", end="", flush=True)
    else:
        print(f"ACCESSO NEGATO {client} — {message}")
        print("\a\a", end="", flush=True)


def main() -> int:
    try:
        config = load_config()
    except Exception as exc:
        print(f"ERRORE CONFIGURAZIONE: {exc}")
        input("Premi Invio per chiudere...")
        return 1

    print("=" * 58)
    print(f"KREO Bridge {BRIDGE_VERSION}")
    print("Lettore attivo. Passa il badge e premi Invio.")
    print("Scrivi EXIT per chiudere.")
    print("=" * 58)

    last_badge = None
    last_read_at = 0.0
    debounce_seconds = float(
        config.get("debounce_seconds", 2.0)
    )

    while True:
        try:
            badge_code = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nChiusura Bridge.")
            return 0

        if not badge_code:
            continue
        if badge_code.upper() == "EXIT":
            return 0

        now = time.monotonic()
        if (
            badge_code == last_badge
            and now - last_read_at < debounce_seconds
        ):
            print("Lettura duplicata ignorata.")
            continue

        last_badge = badge_code
        last_read_at = now

        try:
            result = process_badge(config, badge_code)
            signal_result(config, result)
        except requests.HTTPError as exc:
            response_text = ""
            if exc.response is not None:
                response_text = exc.response.text.strip()
            detail = (
                f" · {response_text}"
                if response_text
                else ""
            )
            print(f"ERRORE CONNESSIONE: {exc}{detail}")
        except requests.RequestException as exc:
            print(f"ERRORE CONNESSIONE: {exc}")
        except Exception as exc:
            print(f"ERRORE BRIDGE: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
