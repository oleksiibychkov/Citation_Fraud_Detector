"""Author Dossier page — full analysis with all 4 visualizations."""

from __future__ import annotations

import streamlit as st

from cfd.visualization.colors import LEVEL_COLORS

VALID_LEVELS = {"normal", "low", "moderate", "high", "critical"}


def render():
    """Render the author dossier page."""
    st.header("Author Dossier")

    # Input form
    col1, col2, col3 = st.columns(3)
    with col1:
        author_name = st.text_input("Author surname")
    with col2:
        scopus_id = st.text_input("Scopus ID")
    with col3:
        orcid = st.text_input("ORCID")

    # Only show Scopus option when API key is configured
    from cfd.config.settings import Settings as _Settings

    _s = _Settings()
    sources = ["openalex", "auto"]
    if _s.scopus_api_key:
        sources.append("scopus")
    source = st.selectbox("Data source", sources)

    if not st.button("Analyze"):
        return

    if not author_name:
        st.error("Author surname is required.")
        return

    if not scopus_id and not orcid:
        st.error("Scopus ID or ORCID is required.")
        return

    # Run analysis
    with st.spinner("Analyzing..."):
        result, author_data = _run_analysis(author_name, scopus_id, orcid, source)

    if result is None:
        st.error("Analysis failed. Check your inputs and try again.")
        return

    # Section 1: Author Info
    st.subheader("Author Profile")
    profile = result.author_profile
    info_cols = st.columns(4)
    info_cols[0].metric("Name", profile.full_name or author_name)
    info_cols[1].metric("h-index", profile.h_index if profile.h_index is not None else "—")
    info_cols[2].metric("Publications", profile.publication_count if profile.publication_count is not None else "—")
    info_cols[3].metric("Citations", profile.citation_count if profile.citation_count is not None else "—")

    # Section 2: Fraud Score
    st.subheader("Fraud Score")
    level = result.confidence_level or "normal"
    if level not in VALID_LEVELS:
        level = "normal"
    color = LEVEL_COLORS.get(level, "#999999")
    st.markdown(
        f"<h2 style='color:{color}'>{result.fraud_score:.4f} — {level.upper()}</h2>",
        unsafe_allow_html=True,
    )

    # Section 3: Indicators
    st.subheader("Indicators")
    for ind in result.indicators:
        name = ind.indicator_type
        value = ind.value
        triggered = name in result.triggered_indicators
        icon = "\u26a0\ufe0f" if triggered else "\u2705"
        st.write(f"{icon} **{name}**: {value:.4f}")

    # Section 4: Visualizations
    st.subheader("Visualizations")
    _render_visualizations(author_data, result)


def _run_analysis(author_name, scopus_id, orcid, source):
    """Run the analysis pipeline."""
    try:
        from cfd.cli.main import _build_pipeline, _build_strategy
        from cfd.config.settings import Settings

        settings = Settings()
        strategy = _build_strategy(source, settings)
        pipeline = _build_pipeline(strategy, settings)

        result = pipeline.analyze(author_name, scopus_id=scopus_id or None, orcid=orcid or None)

        # Try to collect author_data for visualizations
        try:
            author_data = strategy.collect(author_name, scopus_id=scopus_id or None, orcid=orcid or None)
        except Exception:
            from cfd.data.models import AuthorData

            author_data = AuthorData(profile=result.author_profile, publications=[], citations=[])

        return result, author_data
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None


def _render_visualizations(author_data, result):
    """Render all 4 visualization types."""
    tab1, tab2, tab3, tab4 = st.tabs(["Citation Network", "Timeline h(t)/N(t)", "Mutual Heatmap", "Spike Chart"])

    try:
        from cfd.visualization.heatmap import build_mutual_heatmap
        from cfd.visualization.network import build_network_figure
        from cfd.visualization.temporal import build_ht_nt_figure, build_spike_chart

        with tab1:
            fig = build_network_figure(author_data, result)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig = build_ht_nt_figure(author_data)
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            fig = build_mutual_heatmap(author_data)
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            fig = build_spike_chart(author_data, result)
            st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("Plotly is required for visualizations. Install with: pip install citation-fraud-detector[viz]")
    except Exception as e:
        st.warning(f"Could not render visualizations: {e}")

    from cfd.dashboard.disclaimer import render_disclaimer

    render_disclaimer()
