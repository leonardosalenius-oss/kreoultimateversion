from __future__ import annotations

import streamlit as st
from supabase import Client, create_client
from supabase.client import ClientOptions


def get_db() -> Client:
    required = ["SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_SCHEMA"]
    missing = [key for key in required if key not in st.secrets]

    if missing:
        raise RuntimeError("Secrets mancanti: " + ", ".join(missing))

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SECRET_KEY"],
        options=ClientOptions(
            schema=st.secrets["SUPABASE_SCHEMA"],
            postgrest_client_timeout=20,
            storage_client_timeout=20,
        ),
    )
