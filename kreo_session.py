"""Session-local clients, cache boundaries and deferred widget-state cleanup.

No database/API role changes are performed here. Data clients still come from
the existing get_db() factory and never receive an end-user access token.
"""
from __future__ import annotations

from functools import wraps
import hashlib
import inspect
from typing import Any, Callable
from uuid import uuid4

import streamlit as st


AUTH_DEFAULTS = {
    "auth_user": None,
    "auth_user_id": None,
    "auth_email": None,
    "auth_accesses": [],
    "auth_permissions": [],
    "auth_role": None,
    "auth_name": None,
    "active_company_id": None,
}
_PREFIX = "_kreo_session_"
_NONCE = _PREFIX + "nonce"
_RESET = _PREFIX + "pending_reset"
_VERSIONS = _PREFIX + "cache_versions"


def clear_auth_identity() -> None:
    """Remove application authorization immediately; widget cleanup is deferred."""
    for key, default in AUTH_DEFAULTS.items():
        st.session_state[key] = list(default) if isinstance(default, list) else default


def queue_operational_reset(*, logout: bool = False) -> None:
    """Call before rerun: never delete or replace widget values in the current run."""
    if logout or st.session_state.get(_RESET) != "logout":
        st.session_state[_RESET] = "logout" if logout else "company"


def begin_session_run() -> None:
    """Run before any input widget is instantiated on each app rerun."""
    mode = st.session_state.pop(_RESET, None)
    if mode:
        # Clear Python operational/keyed state. Deleting keys alone cannot reset
        # Streamlit frontend widgets: main renders one complete transition run
        # without operational widgets before the new company is opened.
        for key in list(st.session_state):
            if key not in AUTH_DEFAULTS and not str(key).startswith(_PREFIX):
                del st.session_state[key]
        st.session_state[_NONCE] = uuid4().hex
        st.session_state[_VERSIONS] = {}
        if mode == "logout":
            clear_auth_identity()
            for key in list(st.session_state):
                if str(key).startswith(_PREFIX + "resource_"):
                    del st.session_state[key]
            st.session_state.pop(_PREFIX + "authorization_fingerprint", None)
            st.session_state.pop(_PREFIX + "transition_pending", None)
        else:
            st.session_state[_PREFIX + "transition_pending"] = True
    if _NONCE not in st.session_state:
        st.session_state[_NONCE] = uuid4().hex
    if _VERSIONS not in st.session_state:
        st.session_state[_VERSIONS] = {}
    # Payloads throughout the legacy app use both names. There is one identity.
    st.session_state["auth_user_id"] = st.session_state.get("auth_user")


def session_resource(name: str, factory: Callable[[], Any]) -> Any:
    """Create a resource once per browser session, without global cache_resource."""
    if name not in {"db", "auth"}:
        raise ValueError("Unknown KREO session resource")
    key = _PREFIX + "resource_" + name
    if key not in st.session_state:
        st.session_state[key] = factory()
    return st.session_state[key]


def cache_scope(function_identity: str) -> tuple:
    if _NONCE not in st.session_state:
        begin_session_run()
    versions = st.session_state.get(_VERSIONS, {})
    return (
        st.session_state[_NONCE],
        str(st.session_state.get("auth_user") or ""),
        str(st.session_state.get("auth_email") or "").strip().lower(),
        str(st.session_state.get("active_company_id") or ""),
        int(versions.get(function_identity, 0)),
    )


def session_cache_data(**options: Any) -> Callable:
    """Retain st.cache_data TTLs while hashing every authorization boundary.

    clear() without arguments bumps a version only in the current session.
    clear(*args, **kwargs) clears one entry for the current session/identity.
    Unreachable old entries expire with the existing function TTL.
    """
    def decorate(function: Callable) -> Callable:
        try:
            source = inspect.getsource(function)
        except (OSError, TypeError):
            source = repr(function.__code__.co_code) + repr(function.__code__.co_consts)
        identity = ":".join((
            function.__module__, function.__qualname__,
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        ))

        # Names must not begin with underscore: Streamlit must hash all arguments.
        def invoke(scope: tuple, function_identity: str, args: tuple, kwargs: dict):
            return function(*args, **kwargs)

        # Distinct registry keys also preserve each original function's TTL.
        # function_identity remains an explicit hashed argument as a second boundary.
        invoke.__qualname__ = "kreo_session_cache_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        cached_call = st.cache_data(**options)(invoke)

        @wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return cached_call(cache_scope(identity), identity, args, kwargs)

        def clear(*args: Any, **kwargs: Any) -> None:
            if args or kwargs:
                cached_call.clear(cache_scope(identity), identity, args, kwargs)
            else:
                versions = dict(st.session_state.get(_VERSIONS, {}))
                versions[identity] = int(versions.get(identity, 0)) + 1
                st.session_state[_VERSIONS] = versions

        wrapped.clear = clear
        return wrapped
    return decorate


def validate_auth_identity(auth_client: Any) -> None:
    """Check the session with Supabase Auth before application data are rendered.

    Network errors fail closed for this run; caller clears the app identity and
    asks for login again. Cached local identity is never accepted as proof.
    """
    result = auth_client.auth.get_user()
    user = getattr(result, "user", None)
    remote_id = str(getattr(user, "id", "") or "")
    remote_email = str(getattr(user, "email", "") or "").strip().lower()
    expected_id = str(st.session_state.get("auth_user") or "")
    expected_email = str(st.session_state.get("auth_email") or "").strip().lower()
    if not remote_id or not remote_email or remote_id != expected_id or remote_email != expected_email:
        raise RuntimeError("Sessione autenticata assente o identita non corrispondente")
    st.session_state["auth_user_id"] = remote_id
