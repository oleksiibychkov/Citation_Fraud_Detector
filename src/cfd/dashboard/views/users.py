"""Users admin page — view registered users and their analysis history."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import t


def render():
    """Render the users admin page."""
    st.header(t("dashboard.users_header"))

    users = _load_users()
    if not users:
        st.info(t("dashboard.users_empty"))
        return

    logs = _load_analysis_log()
    # Group logs by user ORCID
    logs_by_user: dict[str, list[dict]] = {}
    for log in logs:
        orcid = log.get("user_orcid", "")
        logs_by_user.setdefault(orcid, []).append(log)

    st.caption(t("dashboard.users_total", count=len(users)))

    for user in users:
        orcid = user.get("orcid", "")
        surname = user.get("surname", "")
        role = user.get("role", "user")
        created = (user.get("created_at") or "")[:16].replace("T", " ")
        user_logs = logs_by_user.get(orcid, [])

        role_badge = "Admin" if role == "admin" else ""
        header = f"**{surname}** ({orcid}) {role_badge}"
        if created:
            header += f" — {t('dashboard.users_registered')}: {created}"

        with st.expander(header, expanded=False):
            if not user_logs:
                st.caption(t("dashboard.users_no_queries"))
            else:
                st.caption(t("dashboard.users_query_count", count=len(user_logs)))
                # Table of queries
                for log in user_logs:
                    author = log.get("author_name", "—")
                    scopus = log.get("scopus_id", "")
                    log_orcid = log.get("author_orcid", "")
                    score = log.get("fraud_score")
                    level = log.get("confidence_level", "")
                    ts = (log.get("created_at") or "")[:16].replace("T", " ")

                    id_info = f"Scopus: {scopus}" if scopus else f"ORCID: {log_orcid}" if log_orcid else ""
                    score_str = f"{score:.4f}" if score is not None else "—"
                    level_str = t(f"level_labels.{level}") if level else ""

                    st.markdown(
                        f"- **{author}** ({id_info}) — "
                        f"{t('dashboard.col_score')}: {score_str} {level_str} — {ts}"
                    )


def _load_users() -> list[dict]:
    """Load all registered users."""
    try:
        from cfd.config.settings import Settings
        from cfd.db.client import get_supabase_client

        settings = Settings()
        if not settings.supabase_url or not settings.supabase_key:
            return []

        client = get_supabase_client(settings)
        result = client.table("cfd_users").select("*").order("created_at", desc=True).execute()
        return result.data or []
    except Exception:
        return []


def _load_analysis_log() -> list[dict]:
    """Load all analysis log entries."""
    try:
        from cfd.config.settings import Settings
        from cfd.db.client import get_supabase_client

        settings = Settings()
        if not settings.supabase_url or not settings.supabase_key:
            return []

        client = get_supabase_client(settings)
        result = client.table("analysis_log").select("*").order("created_at", desc=True).execute()
        return result.data or []
    except Exception:
        return []
