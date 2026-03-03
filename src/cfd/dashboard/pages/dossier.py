"""Author Dossier page — full analysis with all 4 visualizations."""

from __future__ import annotations

import streamlit as st

from cfd.visualization.colors import LEVEL_COLORS

VALID_LEVELS = {"normal", "low", "moderate", "high", "critical"}

# Indicator descriptions: short name, full name, what it measures
INDICATOR_INFO: dict[str, tuple[str, str]] = {
    "SCR": (
        "Self-Citation Ratio",
        "Share of self-citations in total citations. "
        "High values indicate the author excessively cites their own works.",
    ),
    "MCR": (
        "Mutual Citation Ratio",
        "Detects reciprocal citation agreements between authors — "
        "'I cite you, you cite me' patterns.",
    ),
    "CB": (
        "Citation Bottleneck",
        "Concentration of incoming citations from a single source. "
        "High values mean most citations come from one author/group.",
    ),
    "TA": (
        "Temporal Anomaly",
        "Detects unnatural spikes in citation count that don't correlate "
        "with publication activity (Z-score analysis).",
    ),
    "HTA": (
        "h-Index Temporal Analysis",
        "Analyzes h-index growth rate over time. Flags abnormally fast growth "
        "not explained by publication output.",
    ),
    "RLA": (
        "Reference List Anomaly",
        "Evaluates diversity of reference lists. High values indicate narrow "
        "citing patterns — repeatedly referencing the same sources.",
    ),
    "GIC": (
        "Geographic/Institutional Clustering",
        "Measures concentration of citing authors by institution/geography. "
        "High values mean citations come from a very narrow circle.",
    ),
    "EIGEN": (
        "Eigenvector Centrality",
        "Network influence measure — are the author's works connected to "
        "other highly-cited works, or isolated in a small cluster?",
    ),
    "BETWEENNESS": (
        "Betweenness Centrality",
        "How often the author's works serve as bridges in the citation network. "
        "Anomalous values may indicate artificial network positioning.",
    ),
    "PAGERANK": (
        "PageRank Centrality",
        "Google-style importance score in the citation network. "
        "Abnormal PageRank may indicate citation manipulation.",
    ),
    "COMMUNITY": (
        "Community Detection",
        "Louvain algorithm detects dense citation clusters. "
        "Flags suspicious communities with high internal but low external citation density.",
    ),
    "CLIQUE": (
        "Citation Clique Detection",
        "Detects tightly connected groups where everyone cites everyone — "
        "a classic sign of organized citation manipulation.",
    ),
    "CV": (
        "Citation Velocity",
        "Measures how fast papers accumulate citations relative to their age, "
        "discipline, and journal. Abnormally fast accumulation is suspicious.",
    ),
    "SBD": (
        "Sleeping Beauty Detector",
        "Identifies papers that were 'dormant' for years then suddenly got many citations — "
        "possible sign of coordinated citation campaigns.",
    ),
    "ANA": (
        "Authorship Network Anomaly",
        "Detects guest/gift authorship patterns: many one-time coauthors, "
        "unusual author position patterns, low repeat collaboration.",
    ),
    "CC": (
        "Citation Cannibalism",
        "Excessive self-referencing within paper reference lists — "
        "author repeatedly cites their own works in each new paper.",
    ),
    "SSD": (
        "Salami Slicing Detector",
        "Detects paper splitting — publishing highly similar papers in quick succession "
        "to inflate publication count.",
    ),
    "PB": (
        "Peer Benchmark",
        "Compares author's metrics (h-index, citations, publications) with similar peers. "
        "Large deviations may indicate artificial inflation.",
    ),
    "CPC": (
        "Cross-Platform Consistency",
        "Compares metrics between OpenAlex and Scopus. "
        "Large divergence (>20%) may indicate data manipulation or profile issues.",
    ),
    "JSCR": (
        "Journal Self-Citation Rate",
        "Share of references pointing to the same journal. "
        "High values may indicate journal-level citation manipulation.",
    ),
    "COERCE": (
        "Coercive Citation Detection",
        "Detects signs of journals forcing authors to cite the journal's own papers — "
        "high concentration, recency bias, and rising trend.",
    ),
    "CTX": (
        "Contextual Anomaly Analysis",
        "Meta-indicator that aggregates multiple signals and checks for legitimate "
        "explanations (review articles, trending topics). Final verification step.",
    ),
}

LEVEL_CONCLUSIONS = {
    "normal": (
        "No signs of citation manipulation detected. "
        "The author's citation profile is consistent with normal academic activity. "
        "All indicators are within expected ranges for the discipline and career stage."
    ),
    "low": (
        "Minor deviations from typical citation patterns were detected. "
        "These may be natural variations or early warning signs. "
        "No immediate concern, but periodic monitoring is recommended."
    ),
    "moderate": (
        "Several indicators show deviations from expected citation patterns. "
        "This does not constitute proof of manipulation, but warrants closer examination. "
        "Recommended: review the triggered indicators and compare with discipline norms."
    ),
    "high": (
        "Significant anomalies detected across multiple citation indicators. "
        "The pattern is consistent with possible citation manipulation practices. "
        "Recommended: detailed manual review by an expert committee, "
        "cross-reference with Scopus data, and examination of the specific triggered indicators."
    ),
    "critical": (
        "Strong evidence of systematic citation anomalies detected. "
        "Multiple independent indicators converge on manipulation patterns: "
        "citation rings, excessive self-citation, temporal spikes, and/or coercive practices. "
        "Recommended: immediate expert review, institutional investigation, "
        "and comparison with verified Scopus/Web of Science data."
    ),
}


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

    # Data source disclaimer
    api_used = getattr(result.author_profile, "source_api", source) or source
    if api_used == "openalex":
        st.info(
            "Data source: **OpenAlex** (free). "
            "OpenAlex may have incomplete coverage compared to Scopus — "
            "h-index, publication count, and citation count may be lower than in Scopus. "
            "For more accurate data, configure a Scopus API key (`CFD_SCOPUS_API_KEY`)."
        )

    # Section 1: Author Info
    st.subheader("Author Profile")
    profile = result.author_profile
    info_cols = st.columns(4)
    info_cols[0].metric("Name", profile.full_name or author_name)
    info_cols[1].metric("h-index", profile.h_index if profile.h_index is not None else "\u2014")
    info_cols[2].metric("Publications", profile.publication_count if profile.publication_count is not None else "\u2014")
    info_cols[3].metric("Citations", profile.citation_count if profile.citation_count is not None else "\u2014")

    # Section 2: Fraud Score
    st.subheader("Fraud Score")
    level = result.confidence_level or "normal"
    if level not in VALID_LEVELS:
        level = "normal"
    color = LEVEL_COLORS.get(level, "#999999")
    st.markdown(
        f"<h2 style='color:{color}'>{result.fraud_score:.4f} \u2014 {level.upper()}</h2>",
        unsafe_allow_html=True,
    )

    # Section 3: Indicators with descriptions
    st.subheader("Indicators")
    triggered = set(result.triggered_indicators)
    triggered_details = []
    normal_details = []

    for ind in result.indicators:
        name = ind.indicator_type
        value = ind.value
        is_triggered = name in triggered
        info = INDICATOR_INFO.get(name)
        full_name = info[0] if info else name
        description = info[1] if info else ""

        if is_triggered:
            triggered_details.append((name, full_name, value, description))
        else:
            normal_details.append((name, full_name, value, description))

    # Show triggered (suspicious) indicators first
    if triggered_details:
        st.markdown("#### \u26a0\ufe0f Triggered indicators (above threshold)")
        for code, full_name, value, description in triggered_details:
            with st.expander(f"\u26a0\ufe0f **{code}** ({full_name}): {value:.4f}", expanded=True):
                st.markdown(description)

    # Then normal indicators (collapsed)
    if normal_details:
        st.markdown("#### \u2705 Normal indicators (within threshold)")
        for code, full_name, value, description in normal_details:
            with st.expander(f"\u2705 **{code}** ({full_name}): {value:.4f}"):
                st.markdown(description)

    # Section 4: Warnings
    if result.warnings:
        st.subheader("Warnings")
        for w in result.warnings:
            st.warning(w)

    # Section 5: Visualizations
    st.subheader("Visualizations")
    _render_visualizations(author_data, result)

    # Section 6: Conclusion
    _render_conclusion(result, level, color)


def _render_conclusion(result, level, color):
    """Render a detailed conclusion about the analysis."""
    st.subheader("Conclusion")

    triggered = result.triggered_indicators
    total = len(result.indicators)
    triggered_count = len(triggered)
    score = result.fraud_score

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total indicators analyzed", total)
    col2.metric("Indicators triggered", triggered_count)
    col3.metric("Fraud score", f"{score:.4f}")

    # Verdict
    level_label = {
        "normal": "NORMAL",
        "low": "LOW RISK",
        "moderate": "MODERATE RISK",
        "high": "HIGH RISK",
        "critical": "CRITICAL RISK",
    }
    verdict = level_label.get(level, level.upper())

    st.markdown(
        f"### Verdict: <span style='color:{color}'>{verdict}</span>",
        unsafe_allow_html=True,
    )

    # Detailed conclusion text
    conclusion = LEVEL_CONCLUSIONS.get(level, "")
    st.markdown(conclusion)

    # List triggered indicators in the conclusion
    if triggered:
        st.markdown("**Triggered indicators:**")
        for code in triggered:
            info = INDICATOR_INFO.get(code)
            full_name = info[0] if info else code
            # Find the value
            value = 0.0
            for ind in result.indicators:
                if ind.indicator_type == code:
                    value = ind.value
                    break
            st.markdown(f"- **{code}** ({full_name}): {value:.4f}")

    # Disclaimer
    st.markdown("---")
    st.caption(
        "This analysis is algorithmic and does not constitute a final judgment. "
        "Citation patterns can have legitimate explanations (narrow research field, "
        "review articles, trending topics). Results should be interpreted by qualified experts "
        "and verified against multiple data sources."
    )


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
