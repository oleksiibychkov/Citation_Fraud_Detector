"""HTML report generation with embedded Plotly visualizations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from cfd.analysis.pipeline import AnalysisResult
from cfd.config.settings import Settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def export_to_html(
    result: AnalysisResult,
    output_path: Path,
    settings: Settings | None = None,
    figures: dict | None = None,
    lang: str = "ua",
) -> None:
    """Export analysis result as an HTML report with embedded Plotly charts.

    Args:
        result: Analysis result to export.
        output_path: Path to write HTML file.
        settings: Application settings.
        figures: Dict of name -> plotly.graph_objects.Figure to embed.
        lang: Language for localization (ua/en).
    """
    try:
        import jinja2
    except ImportError as err:
        raise ImportError(
            "jinja2 is required for HTML export. Install with: pip install citation-fraud-detector[html]"
        ) from err

    s = settings or Settings()

    # Convert figures to HTML divs
    fig_html = {}
    if figures:
        try:
            import plotly.io as pio
            for name, fig in figures.items():
                fig_html[name] = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
        except ImportError:
            logger.warning("plotly not available, skipping figure embedding")

    # Build template context
    translations = _get_translations(lang)

    indicators = []
    for ind in result.indicators:
        indicators.append({
            "type": ind.indicator_type,
            "value": round(ind.value, 4),
            "triggered": ind.indicator_type in result.triggered_indicators,
            "na": ind.details.get("status") == "N/A",
        })

    theorem_results = []
    for tr in result.theorem_results:
        theorem_results.append({
            "theorem_number": tr.theorem_number,
            "passed": tr.passed,
            "details": str(tr.details),
        })

    context = {
        "lang": lang,
        "report_title": translations.get("report_title", "CFD Report"),
        "algorithm_version": f"Algorithm v{s.algorithm_version}",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "author": result.author_profile,
        "fraud_score": round(result.fraud_score, 4),
        "confidence_level": result.confidence_level,
        "indicators": indicators,
        "theorem_results": theorem_results,
        "figures": fig_html,
        "warnings": result.warnings,
        **translations,
    }

    # Render template
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")
    html_content = template.render(**context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def _get_translations(lang: str) -> dict:
    """Get translation strings for the template."""
    if lang == "ua":
        return {
            "t_author_info": "Інформація про автора",
            "t_name": "Ім'я",
            "t_institution": "Установа",
            "t_discipline": "Дисципліна",
            "t_publications": "Публікації",
            "t_citations": "Цитування",
            "t_fraud_score": "Оцінка підозрілості",
            "t_level": "Рівень",
            "t_indicators": "Індикатори",
            "t_type": "Тип",
            "t_value": "Значення",
            "t_status": "Статус",
            "t_theorems": "Результати теорем",
            "t_visualizations": "Візуалізації",
            "t_warnings": "Попередження",
            "t_disclaimer": "Це оцінка підозрілості, а не вирок. Остаточне рішення приймає людина.",
        }
    return {
        "t_author_info": "Author Information",
        "t_name": "Name",
        "t_institution": "Institution",
        "t_discipline": "Discipline",
        "t_publications": "Publications",
        "t_citations": "Citations",
        "t_fraud_score": "Fraud Score",
        "t_level": "Level",
        "t_indicators": "Indicators",
        "t_type": "Type",
        "t_value": "Value",
        "t_status": "Status",
        "t_theorems": "Theorem Results",
        "t_visualizations": "Visualizations",
        "t_warnings": "Warnings",
        "t_disclaimer": "This is a suspicion score, not a verdict. Final decision rests with a human.",
    }
