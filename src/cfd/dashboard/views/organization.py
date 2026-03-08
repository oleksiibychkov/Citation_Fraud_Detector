"""Organization module — collect affiliated authors, report publications, run analysis."""

from __future__ import annotations

import io
from datetime import date

import streamlit as st

from cfd.i18n.translator import t


def render():
    """Render the organization analysis page."""
    st.header(t("org.header"))
    st.caption(t("org.caption"))

    # Step 1: Institution search
    col1, col2 = st.columns([3, 1])
    with col1:
        org_name = st.text_input(
            t("org.name_label"),
            value=st.session_state.get("org_name", ""),
            placeholder="Taras Shevchenko National University of Kyiv",
        )
    with col2:
        ror_id = st.text_input(
            t("org.ror_label"),
            value=st.session_state.get("org_ror", ""),
            placeholder="https://ror.org/...",
        )

    # Period selection
    col_from, col_to, col_max = st.columns(3)
    with col_from:
        period_from = st.date_input(
            t("org.period_from"),
            value=date(date.today().year - 1, 1, 1),
            key="org_period_from",
        )
    with col_to:
        period_to = st.date_input(
            t("org.period_to"),
            value=date.today(),
            key="org_period_to",
        )
    with col_max:
        max_authors = st.number_input(
            t("org.max_authors"),
            min_value=10,
            max_value=2000,
            value=200,
            step=50,
            key="org_max_authors",
        )

    # Collect button
    collect_clicked = st.button(t("org.collect_btn"), type="primary")

    if collect_clicked:
        if not org_name and not ror_id:
            st.error(t("org.input_required"))
            return

        _collect_organization(org_name, ror_id, period_from, period_to, max_authors)

    # Display results if available
    org_data = st.session_state.get("org_data")
    if org_data is None:
        return

    _render_institution_profile(org_data)
    _render_authors_table(org_data)
    _render_export(org_data)
    _render_analysis_section(org_data)


def _collect_organization(org_name, ror_id, period_from, period_to, max_authors):
    """Collect organization data from OpenAlex."""
    try:
        from cfd.config.settings import Settings
        from cfd.data.http_client import CachedHttpClient, RateLimiter
        from cfd.data.organization_openalex import OrganizationCollector

        settings = Settings()
        http_client = CachedHttpClient(
            rate_limiter=RateLimiter(settings.openalex_requests_per_second),
            max_retries=settings.max_retries,
        )

        collector = OrganizationCollector(http_client)

        progress_bar = st.progress(0, text=t("org.collecting_institution"))

        def on_progress(current, total, name):
            pct = current / total if total > 0 else 0
            progress_bar.progress(pct, text=t("org.collecting_author", current=current + 1, total=total, name=name))

        org_data = collector.collect_organization(
            org_name,
            ror=ror_id.strip() or None,
            date_from=period_from,
            date_to=period_to,
            max_authors=max_authors,
            fetch_works=True,
            progress_callback=on_progress,
        )

        progress_bar.progress(1.0, text=t("org.collection_done"))

        st.session_state["org_data"] = org_data
        st.session_state["org_name"] = org_name
        st.session_state["org_ror"] = ror_id
        st.success(t("org.collection_success", count=len(org_data.authors)))

    except Exception as e:
        st.error(f"{t('error.api_error', message=str(e))}")


def _render_institution_profile(org_data):
    """Render institution profile section."""
    st.subheader(t("org.profile_header"))
    inst = org_data.institution

    cols = st.columns(4)
    cols[0].metric(t("org.inst_name"), inst.display_name)
    cols[1].metric(t("org.inst_country"), inst.country_code or "\u2014")
    cols[2].metric(t("org.inst_type"), inst.type or "\u2014")
    cols[3].metric(t("org.inst_authors"), inst.authors_count)

    cols2 = st.columns(4)
    cols2[0].metric(t("org.inst_works"), inst.works_count)
    cols2[1].metric(t("org.inst_citations"), inst.cited_by_count)
    period_str = ""
    if org_data.period_from and org_data.period_to:
        period_str = f"{org_data.period_from.isoformat()} \u2014 {org_data.period_to.isoformat()}"
    cols2[2].metric(t("org.period_label"), period_str)
    cols2[3].metric(t("org.total_scopus"), org_data.total_scopus_indexed)


def _render_authors_table(org_data):
    """Render authors table with sorting."""
    st.subheader(t("org.authors_header"))

    if not org_data.authors:
        st.info(t("org.no_authors"))
        return

    # Sort options
    sort_options = {
        "scopus_indexed_in_period": t("org.sort_scopus"),
        "works_in_period": t("org.sort_works_period"),
        "h_index": t("org.sort_h_index"),
        "cited_by_count": t("org.sort_citations"),
        "works_count": t("org.sort_works_total"),
    }

    col_sort, col_dir = st.columns([3, 1])
    with col_sort:
        sort_key = st.selectbox(
            t("org.sort_by"),
            list(sort_options.keys()),
            format_func=lambda k: sort_options[k],
            key="org_sort_key",
        )
    with col_dir:
        ascending = st.checkbox(t("org.ascending"), value=False, key="org_ascending")

    # Sort authors
    sorted_authors = sorted(
        org_data.authors,
        key=lambda a: getattr(a, sort_key) or 0,
        reverse=not ascending,
    )

    # Filter: show only authors with works in period
    show_all = st.checkbox(t("org.show_all_authors"), value=False, key="org_show_all")
    if not show_all:
        sorted_authors = [a for a in sorted_authors if a.works_in_period > 0]

    st.caption(t("org.showing_count", shown=len(sorted_authors), total=len(org_data.authors)))

    # Build table data
    table_data = []
    for i, author in enumerate(sorted_authors):
        table_data.append({
            "#": i + 1,
            t("org.col_name"): author.display_name,
            t("org.col_orcid"): author.orcid or "\u2014",
            t("org.col_h_index"): author.h_index if author.h_index is not None else "\u2014",
            t("org.col_works_total"): author.works_count,
            t("org.col_works_period"): author.works_in_period,
            t("org.col_scopus_period"): author.scopus_indexed_in_period,
            t("org.col_citations"): author.cited_by_count,
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)


def _render_export(org_data):
    """Render CSV export button."""
    st.subheader(t("org.export_header"))

    if st.button(t("org.export_csv_btn")):
        csv = _build_csv(org_data)
        st.download_button(
            label=t("org.download_csv"),
            data=csv,
            file_name=f"org_report_{org_data.institution.display_name.replace(' ', '_')}.csv",
            mime="text/csv",
            key="org_download_csv",
        )


def _build_csv(org_data) -> str:
    """Build CSV report from organization data."""
    lines = []
    # Header
    lines.append(",".join([
        "Name",
        "ORCID",
        "Scopus ID",
        "h-index",
        "Total Works",
        f"Works ({org_data.period_from} to {org_data.period_to})",
        f"Scopus Indexed ({org_data.period_from} to {org_data.period_to})",
        "Total Citations",
    ]))

    for author in org_data.authors:
        name = f'"{author.display_name}"' if "," in author.display_name else author.display_name
        lines.append(",".join([
            name,
            author.orcid or "",
            author.scopus_id or "",
            str(author.h_index or 0),
            str(author.works_count),
            str(author.works_in_period),
            str(author.scopus_indexed_in_period),
            str(author.cited_by_count),
        ]))

    # Summary
    lines.append("")
    lines.append(f"Institution:,{org_data.institution.display_name}")
    lines.append(f"Period:,{org_data.period_from} to {org_data.period_to}")
    lines.append(f"Total Authors:,{len(org_data.authors)}")
    lines.append(f"Total Works in Period:,{org_data.total_works_in_period}")
    lines.append(f"Scopus Indexed:,{org_data.total_scopus_indexed}")

    return "\n".join(lines)


def _render_analysis_section(org_data):
    """Render batch analysis section."""
    st.markdown("---")
    st.subheader(t("org.analysis_header"))
    st.caption(t("org.analysis_caption"))

    # Select authors for analysis
    authors_with_works = [a for a in org_data.authors if a.works_count > 0]
    if not authors_with_works:
        st.info(t("org.no_authors_for_analysis"))
        return

    analysis_mode = st.radio(
        t("org.analysis_mode"),
        ["all", "select"],
        format_func=lambda k: t(f"org.mode_{k}"),
        key="org_analysis_mode",
        horizontal=True,
    )

    selected_authors = authors_with_works
    if analysis_mode == "select":
        author_names = [f"{a.display_name} (h={a.h_index or 0})" for a in authors_with_works]
        selected_indices = st.multiselect(
            t("org.select_authors"),
            range(len(author_names)),
            format_func=lambda i: author_names[i],
            key="org_selected_authors",
        )
        selected_authors = [authors_with_works[i] for i in selected_indices]

    if not selected_authors:
        return

    st.info(t("org.will_analyze", count=len(selected_authors)))

    if st.button(t("org.run_analysis_btn"), type="primary", key="org_run_analysis"):
        _run_batch_analysis(selected_authors)


def _run_batch_analysis(authors):
    """Run CFD analysis for selected authors."""
    try:
        from cfd.cli.main import _build_pipeline, _build_strategy
        from cfd.config.settings import Settings

        settings = Settings()
        overrides = st.session_state.get("threshold_overrides", {})
        if overrides:
            try:
                settings = settings.model_copy(update=overrides)
            except Exception:
                pass

        strategy = _build_strategy("openalex", settings)
        pipeline = _build_pipeline(strategy, settings)

        results = []
        progress = st.progress(0, text=t("org.analyzing"))

        for i, author in enumerate(authors):
            progress.progress(
                (i + 1) / len(authors),
                text=t("org.analyzing_author", current=i + 1, total=len(authors), name=author.display_name),
            )

            try:
                # Use ORCID if available, otherwise OpenAlex ID as surname search
                surname = author.display_name.split()[-1] if author.display_name else "Unknown"
                result = pipeline.analyze(
                    surname,
                    orcid=author.orcid,
                    scopus_id=author.scopus_id,
                )
                results.append({
                    "author": author,
                    "result": result,
                    "error": None,
                })
            except Exception as e:
                results.append({
                    "author": author,
                    "result": None,
                    "error": str(e),
                })

        progress.progress(1.0, text=t("org.analysis_complete"))

        st.session_state["org_analysis_results"] = results
        _render_analysis_results(results)

    except Exception as e:
        st.error(f"{t('error.api_error', message=str(e))}")


def _render_analysis_results(results):
    """Render batch analysis results."""
    from cfd.visualization.colors import LEVEL_COLORS

    st.subheader(t("org.results_header"))

    # Summary
    completed = [r for r in results if r["result"] is not None]
    failed = [r for r in results if r["error"] is not None]

    col1, col2, col3 = st.columns(3)
    col1.metric(t("org.results_total"), len(results))
    col2.metric(t("org.results_completed"), len(completed))
    col3.metric(t("org.results_failed"), len(failed))

    if not completed:
        return

    # Sort by score descending
    completed.sort(key=lambda r: r["result"].fraud_score, reverse=True)

    # Results table
    table_data = []
    for i, r in enumerate(completed):
        author = r["author"]
        result = r["result"]
        level = result.confidence_level or "normal"
        level_label = t(f"level_labels.{level}")
        color = LEVEL_COLORS.get(level, "#999999")

        table_data.append({
            "#": i + 1,
            t("org.col_name"): author.display_name,
            t("org.col_score"): f"{result.fraud_score:.4f}",
            t("org.col_level"): level_label,
            t("org.col_triggered"): len(result.triggered_indicators),
            t("org.col_h_index"): author.h_index if author.h_index is not None else "\u2014",
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)

    # Expandable details per author
    for r in completed:
        author = r["author"]
        result = r["result"]
        level = result.confidence_level or "normal"
        color = LEVEL_COLORS.get(level, "#999999")
        score_str = f"{result.fraud_score:.4f}"

        with st.expander(f"**{author.display_name}** — {score_str} ({t(f'level_labels.{level}')})"):
            if result.triggered_indicators:
                st.markdown(f"**{t('org.triggered_list')}:** {', '.join(result.triggered_indicators)}")
            if result.warnings:
                for w in result.warnings:
                    st.caption(f"\u26a0\ufe0f {w}")

    # Show errors
    if failed:
        with st.expander(t("org.errors_header"), expanded=False):
            for r in failed:
                st.caption(f"\u274c **{r['author'].display_name}**: {r['error']}")
