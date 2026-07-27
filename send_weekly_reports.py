from __future__ import annotations

import os
import sys

from supabase import create_client
from supabase.client import ClientOptions

from weekly_report_mail import send_weekly_reports_email


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variabile mancante: {name}")
    return value


def main() -> int:
    db = create_client(
        required("SUPABASE_URL"),
        required("SUPABASE_SECRET_KEY"),
        options=ClientOptions(
            schema=os.getenv("SUPABASE_SCHEMA", "gestionale_v2"),
            postgrest_client_timeout=30,
            storage_client_timeout=30,
        ),
    )

    companies = (
        db.table("aziende")
        .select("*")
        .eq("attiva", True)
        .order("nome_visualizzato")
        .limit(1)
        .execute()
        .data
        or []
    )
    if not companies:
        raise RuntimeError("Nessuna azienda attiva trovata.")

    result = send_weekly_reports_email(
        db=db,
        company=companies[0],
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        username=required("SMTP_USERNAME"),
        app_password=required("SMTP_APP_PASSWORD"),
        sender_name=os.getenv(
            "SMTP_SENDER_NAME", "KREO Studio Personal"
        ),
        recipient=os.getenv(
            "REPORT_RECIPIENT",
            "rosariosoria2525@gmail.com",
        ),
        force="--force" in sys.argv,
        source="github_actions",
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
