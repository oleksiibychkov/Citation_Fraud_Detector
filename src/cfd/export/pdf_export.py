"""PDF report generation using ReportLab."""

from __future__ import annotations

import io
import logging
from datetime import UTC, datetime
from pathlib import Path

from cfd.analysis.pipeline import AnalysisResult
from cfd.config.settings import Settings

logger = logging.getLogger(__name__)


def export_to_pdf(
    result: AnalysisResult,
    output_path: Path,
    settings: Settings | None = None,
    figures: dict | None = None,
    lang: str = "ua",
) -> None:
    """Export analysis result as a PDF report.

    Args:
        result: Analysis result to export.
        output_path: Path to write PDF file.
        settings: Application settings.
        figures: Dict of name -> plotly.graph_objects.Figure (rendered as static images).
        lang: Language for localization (ua/en).
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as err:
        raise ImportError(
            "reportlab is required for PDF export. Install with: pip install citation-fraud-detector[pdf]"
        ) from err

    s = settings or Settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Register Unicode font if available
    _register_unicode_font()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    # Apply Unicode font to styles if registered
    _apply_unicode_font(styles)
    title_style = ParagraphStyle("CustomTitle", parent=styles["Title"], fontSize=18, spaceAfter=12)
    heading_style = ParagraphStyle("CustomHeading", parent=styles["Heading2"], fontSize=14, spaceAfter=8)
    normal_style = styles["Normal"]
    disclaimer_style = ParagraphStyle("Disclaimer", parent=normal_style, fontSize=9, textColor=colors.grey)

    translations = _get_pdf_translations(lang)
    elements = []

    # Title
    author_name = result.author_profile.full_name or result.author_profile.surname
    elements.append(Paragraph(f"{translations['report_title']} — {author_name}", title_style))
    elements.append(Paragraph(
        f"Algorithm v{s.algorithm_version} | {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        normal_style,
    ))
    elements.append(Spacer(1, 10 * mm))

    # Author Info
    elements.append(Paragraph(translations["author_info"], heading_style))
    author_data = [
        [translations["name"], author_name],
        ["Scopus ID", result.author_profile.scopus_id or "—"],
        ["ORCID", result.author_profile.orcid or "—"],
        [translations["institution"], result.author_profile.institution or "—"],
        [translations["discipline"], result.author_profile.discipline or "—"],
        ["h-index", str(result.author_profile.h_index) if result.author_profile.h_index is not None else "—"],
        [translations["publications"],
         str(result.author_profile.publication_count)
         if result.author_profile.publication_count is not None else "—"],
        [translations["citations"],
         str(result.author_profile.citation_count)
         if result.author_profile.citation_count is not None else "—"],
    ]
    author_table = Table(author_data, colWidths=[50 * mm, 100 * mm])
    author_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(author_table)
    elements.append(Spacer(1, 8 * mm))

    # Fraud Score
    elements.append(Paragraph(translations["fraud_score"], heading_style))
    level_color = _level_to_color(result.confidence_level)
    score_data = [[
        f"Score: {result.fraud_score:.4f}",
        f"{translations['level']}: {result.confidence_level.upper()}",
    ]]
    score_table = Table(score_data, colWidths=[75 * mm, 75 * mm])
    score_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 14),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, -1), level_color),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 8 * mm))

    # Indicators
    elements.append(Paragraph(translations["indicators"], heading_style))
    ind_data = [[translations["type"], translations["value"], translations["status"]]]
    for ind in result.indicators:
        triggered = ind.indicator_type in result.triggered_indicators
        status = "TRIGGERED" if triggered else ("N/A" if ind.details.get("status") == "N/A" else "OK")
        ind_data.append([ind.indicator_type, f"{ind.value:.4f}", status])

    ind_table = Table(ind_data, colWidths=[50 * mm, 40 * mm, 60 * mm])
    ind_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.93, 0.94, 0.95)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    # Color triggered rows
    for i, ind in enumerate(result.indicators, 1):
        if ind.indicator_type in result.triggered_indicators:
            ind_table.setStyle(TableStyle([
                ("TEXTCOLOR", (2, i), (2, i), colors.red),
            ]))
    elements.append(ind_table)
    elements.append(Spacer(1, 8 * mm))

    # Figures (static images)
    if figures:
        elements.append(Paragraph(translations["visualizations"], heading_style))
        for name, fig in figures.items():
            try:
                img_bytes = fig.to_image(format="png", width=700, height=400)
                img_buffer = io.BytesIO(img_bytes)
                elements.append(Image(img_buffer, width=160 * mm, height=90 * mm))
                elements.append(Spacer(1, 5 * mm))
            except Exception:
                logger.warning("Failed to render figure '%s' for PDF", name, exc_info=True)
                elements.append(Paragraph(f"[Figure '{name}' could not be rendered]", normal_style))

    # Warnings
    if result.warnings:
        elements.append(Paragraph(translations["warnings"], heading_style))
        for w in result.warnings:
            elements.append(Paragraph(f"⚠ {w}", normal_style))
        elements.append(Spacer(1, 5 * mm))

    # Disclaimer
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(translations["disclaimer"], disclaimer_style))

    doc.build(elements)


def export_antiranking_pdf(
    results: list[AnalysisResult],
    output_path: Path,
    settings: Settings | None = None,
    lang: str = "ua",
) -> None:
    """Export anti-ranking PDF: authors sorted by Fraud Score."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as err:
        raise ImportError(
            "reportlab is required for PDF export. Install with: pip install citation-fraud-detector[pdf]"
        ) from err

    s = settings or Settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _register_unicode_font()

    doc = SimpleDocTemplate(str(output_path), pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    _apply_unicode_font(styles)
    elements = []

    translations = _get_pdf_translations(lang)
    elements.append(Paragraph(translations["antiranking_title"], styles["Title"]))
    elements.append(Paragraph(
        f"Algorithm v{s.algorithm_version} | {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 10 * mm))

    sorted_results = sorted(results, key=lambda r: r.fraud_score, reverse=True)

    data = [["#", translations["name"], "Scopus ID", "Score", translations["level"], translations["triggered"]]]
    for i, r in enumerate(sorted_results, 1):
        data.append([
            str(i),
            r.author_profile.full_name or r.author_profile.surname,
            r.author_profile.scopus_id or "—",
            f"{r.fraud_score:.4f}",
            r.confidence_level.upper(),
            ", ".join(r.triggered_indicators) or "—",
        ])

    col_widths = [10 * mm, 50 * mm, 35 * mm, 25 * mm, 25 * mm, 80 * mm]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.24, 0.31)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
    ]))

    # Color score cells by level
    for i, r in enumerate(sorted_results, 1):
        color = _level_to_color(r.confidence_level)
        table.setStyle(TableStyle([
            ("TEXTCOLOR", (3, i), (4, i), color),
        ]))

    elements.append(table)
    doc.build(elements)


def _register_unicode_font():
    """Register a Unicode font for non-Latin characters."""
    try:
        import shutil

        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        font_path = shutil.which("DejaVuSans.ttf")
        if not font_path:
            # Common locations
            for candidate in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]:
                if Path(candidate).exists():
                    font_path = candidate
                    break

        if font_path:
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
    except Exception:
        logger.debug("Could not register Unicode font, using defaults", exc_info=True)


def _apply_unicode_font(styles):
    """Apply registered Unicode font to all paragraph styles."""
    try:
        from reportlab.pdfbase import pdfmetrics

        if "DejaVuSans" in pdfmetrics.getRegisteredFontNames():
            for style in styles.byName.values():
                style.fontName = "DejaVuSans"
    except Exception:
        pass


def _level_to_color(level: str):
    """Convert confidence level to ReportLab color."""
    from reportlab.lib import colors

    mapping = {
        "normal": colors.Color(0.18, 0.8, 0.44),
        "low": colors.Color(0.95, 0.77, 0.06),
        "moderate": colors.Color(0.9, 0.49, 0.13),
        "high": colors.Color(0.91, 0.3, 0.24),
        "critical": colors.Color(0.75, 0.22, 0.17),
    }
    return mapping.get(level, colors.grey)


def _get_pdf_translations(lang: str) -> dict:
    """Get PDF-specific translations."""
    if lang == "ua":
        return {
            "report_title": "Звіт CFD",
            "antiranking_title": "Антирейтинг авторів",
            "author_info": "Інформація про автора",
            "name": "Ім'я",
            "institution": "Установа",
            "discipline": "Дисципліна",
            "publications": "Публікації",
            "citations": "Цитування",
            "fraud_score": "Оцінка підозрілості",
            "level": "Рівень",
            "indicators": "Індикатори",
            "type": "Тип",
            "value": "Значення",
            "status": "Статус",
            "triggered": "Спрацьовано",
            "visualizations": "Візуалізації",
            "warnings": "Попередження",
            "disclaimer": "Це оцінка підозрілості, а не вирок. Остаточне рішення приймає людина.",
        }
    return {
        "report_title": "CFD Report",
        "antiranking_title": "Author Anti-Ranking",
        "author_info": "Author Information",
        "name": "Name",
        "institution": "Institution",
        "discipline": "Discipline",
        "publications": "Publications",
        "citations": "Citations",
        "fraud_score": "Fraud Score",
        "level": "Level",
        "indicators": "Indicators",
        "type": "Type",
        "value": "Value",
        "status": "Status",
        "triggered": "Triggered",
        "visualizations": "Visualizations",
        "warnings": "Warnings",
        "disclaimer": "This is a suspicion score, not a verdict. Final decision rests with a human.",
    }
