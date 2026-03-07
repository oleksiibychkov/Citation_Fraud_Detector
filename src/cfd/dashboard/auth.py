"""Dashboard authentication — registration & login via ORCID."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import t


def require_auth() -> dict | None:
    """Show login/register form if not authenticated. Return user dict or None."""
    if "auth_user" in st.session_state and st.session_state["auth_user"]:
        return st.session_state["auth_user"]

    st.title(t("auth.welcome_title"))
    st.markdown(t("auth.welcome_message"))

    with st.form("auth_form"):
        surname = st.text_input(t("auth.surname_label"))
        orcid = st.text_input(t("auth.orcid_label"), placeholder="0000-0000-0000-0000")
        submitted = st.form_submit_button(t("auth.submit_btn"))

    if not submitted:
        return None

    # Validate inputs
    surname = surname.strip()
    orcid = orcid.strip()

    if not surname:
        st.error(t("auth.surname_required"))
        return None

    if not _is_valid_orcid(orcid):
        st.error(t("auth.orcid_invalid"))
        return None

    # Try to find or register user
    user = _find_or_register(surname, orcid)
    if user:
        st.session_state["auth_user"] = user
        st.rerun()

    return None


def is_admin(user: dict) -> bool:
    """Check if the user has admin role."""
    return user.get("role") == "admin"


def logout():
    """Clear auth session."""
    st.session_state.pop("auth_user", None)


def _is_valid_orcid(orcid: str) -> bool:
    """Basic ORCID format validation (0000-0000-0000-000X)."""
    import re
    return bool(re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", orcid))


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
            # Update surname if changed
            if user.get("surname") != surname:
                client.table("cfd_users").update({"surname": surname}).eq("orcid", orcid).execute()
                user["surname"] = surname
            return user

        # Register new user
        admin_orcids = [o.strip() for o in settings.admin_orcids.split(",") if o.strip()]
        role = "admin" if orcid in admin_orcids else "user"

        new_user = {
            "surname": surname,
            "orcid": orcid,
            "role": role,
        }
        insert_result = client.table("cfd_users").insert(new_user).execute()

        if insert_result.data:
            st.success(t("auth.registered"))
            return insert_result.data[0]

        st.error(t("auth.register_failed"))
        return None

    except Exception as e:
        st.error(t("auth.error", error=str(e)))
        return None
