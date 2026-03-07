"""Dashboard authentication — ORCID OAuth or manual fallback."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

import streamlit as st

from cfd.i18n.translator import t

logger = logging.getLogger(__name__)

_ORCID_AUTH_URL = "https://orcid.org/oauth/authorize"
_ORCID_TOKEN_URL = "https://orcid.org/oauth/token"


def require_auth() -> dict | None:
    """Show login form if not authenticated. Return user dict or None."""
    if "auth_user" in st.session_state and st.session_state["auth_user"]:
        return st.session_state["auth_user"]

    from cfd.config.settings import Settings
    settings = Settings()

    oauth_configured = bool(
        settings.orcid_client_id and settings.orcid_client_secret and settings.orcid_redirect_uri
    )

    # Check for OAuth callback (code in URL query params)
    if oauth_configured:
        code = st.query_params.get("code")
        if code:
            with st.spinner(t("auth.verifying_orcid")):
                user = _handle_oauth_callback(code, settings)
            if user:
                st.session_state["auth_user"] = user
                st.query_params.clear()
                st.rerun()
            else:
                st.query_params.clear()

    # Show login page
    st.title(t("auth.welcome_title"))
    st.markdown(t("auth.welcome_message"))

    if oauth_configured:
        _show_oauth_login(settings)
    else:
        _show_manual_login()

    return None


def is_admin(user: dict) -> bool:
    """Check if the user has admin role."""
    return user.get("role") == "admin"


def logout():
    """Clear auth session."""
    st.session_state.pop("auth_user", None)


# ---------------------------------------------------------------------------
# ORCID OAuth flow
# ---------------------------------------------------------------------------

def _show_oauth_login(settings):
    """Show 'Log in with ORCID' button."""
    auth_url = (
        f"{_ORCID_AUTH_URL}"
        f"?client_id={settings.orcid_client_id}"
        f"&response_type=code"
        f"&scope=/authenticate"
        f"&redirect_uri={urllib.parse.quote(settings.orcid_redirect_uri, safe='')}"
    )
    st.link_button(t("auth.login_orcid_btn"), auth_url, type="primary")
    st.caption(t("auth.oauth_hint"))


def _handle_oauth_callback(code: str, settings) -> dict | None:
    """Exchange authorization code for token and register/login user."""
    # Exchange code for access token
    token_data = _exchange_code(code, settings)
    if not token_data:
        st.error(t("auth.oauth_failed"))
        return None

    orcid = token_data.get("orcid", "")
    name = token_data.get("name", "")

    if not orcid:
        st.error(t("auth.oauth_failed"))
        return None

    # Get surname from ORCID profile if not in token
    surname = ""
    if name:
        # Token returns "Given Family" format
        parts = name.strip().split()
        surname = parts[-1] if parts else name
    else:
        surname = _fetch_surname(orcid)

    if not surname:
        surname = orcid  # fallback

    return _find_or_register(surname, orcid)


def _exchange_code(code: str, settings) -> dict | None:
    """Exchange OAuth authorization code for access token."""
    data = urllib.parse.urlencode({
        "client_id": settings.orcid_client_id,
        "client_secret": settings.orcid_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.orcid_redirect_uri,
    }).encode("utf-8")

    req = urllib.request.Request(
        _ORCID_TOKEN_URL,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        logger.error("ORCID token exchange failed", exc_info=True)
        return None


def _fetch_surname(orcid: str) -> str:
    """Fetch surname from ORCID public API."""
    url = f"https://pub.orcid.org/v3.0/{orcid}/person"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        name_data = data.get("name")
        if name_data:
            family = (name_data.get("family-name") or {}).get("value", "")
            if family:
                return family
    except Exception:
        logger.warning("Failed to fetch ORCID profile for %s", orcid, exc_info=True)

    return ""


# ---------------------------------------------------------------------------
# Manual login fallback (when OAuth not configured)
# ---------------------------------------------------------------------------

def _show_manual_login():
    """Show manual surname + ORCID form."""
    st.info(t("auth.manual_mode"))

    with st.form("auth_form"):
        surname = st.text_input(t("auth.surname_label"))
        orcid = st.text_input(t("auth.orcid_label"), placeholder="0000-0000-0000-0000")
        submitted = st.form_submit_button(t("auth.submit_btn"))

    if not submitted:
        return

    surname = surname.strip()
    orcid = orcid.strip()

    if not surname:
        st.error(t("auth.surname_required"))
        return

    if not _is_valid_orcid(orcid):
        st.error(t("auth.orcid_invalid"))
        return

    # Verify surname against ORCID public API
    with st.spinner(t("auth.verifying_orcid")):
        verified = _verify_orcid_surname(surname, orcid)

    if not verified:
        st.error(t("auth.orcid_mismatch"))
        return

    user = _find_or_register(surname, orcid)
    if user:
        st.session_state["auth_user"] = user
        st.rerun()


def _is_valid_orcid(orcid: str) -> bool:
    """Basic ORCID format validation."""
    import re
    return bool(re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", orcid))


def _verify_orcid_surname(surname: str, orcid: str) -> bool:
    """Verify surname against ORCID public API."""
    url = f"https://pub.orcid.org/v3.0/{orcid}/person"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        # API unreachable — allow (don't block)
        return True

    name_data = data.get("name")
    if not name_data:
        return False

    family_name = (name_data.get("family-name") or {}).get("value", "")
    if not family_name:
        return True  # No public name — can't verify

    input_lower = surname.lower().strip()
    family_lower = family_name.lower().strip()

    return input_lower == family_lower or input_lower in family_lower or family_lower in input_lower


# ---------------------------------------------------------------------------
# Shared: DB registration
# ---------------------------------------------------------------------------

def _find_or_register(surname: str, orcid: str) -> dict | None:
    """Find existing user by ORCID or register a new one."""
    try:
        from cfd.config.settings import Settings
        from cfd.db.client import get_supabase_client

        settings = Settings()
        if not settings.supabase_url or not settings.supabase_key:
            st.error(t("auth.no_db"))
            return None

        client = get_supabase_client(settings)

        # Check if user exists
        result = client.table("cfd_users").select("*").eq("orcid", orcid).execute()

        if result.data:
            user = result.data[0]
            if user.get("surname") != surname:
                client.table("cfd_users").update({"surname": surname}).eq("orcid", orcid).execute()
                user["surname"] = surname
            return user

        # Register new user
        admin_orcids = [o.strip() for o in settings.admin_orcids.split(",") if o.strip()]
        role = "admin" if orcid in admin_orcids else "user"

        new_user = {"surname": surname, "orcid": orcid, "role": role}
        insert_result = client.table("cfd_users").insert(new_user).execute()

        if insert_result.data:
            st.success(t("auth.registered"))
            return insert_result.data[0]

        st.error(t("auth.register_failed"))
        return None

    except Exception as e:
        st.error(t("auth.error", error=str(e)))
        return None
