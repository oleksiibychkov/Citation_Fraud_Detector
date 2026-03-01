"""Report generation CLI command."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from cfd.cli.formatters import console


@click.command()
@click.option("--author", required=True, help="Author surname")
@click.option("--scopus-id", default=None, help="Scopus Author ID")
@click.option("--orcid", default=None, help="ORCID identifier")
@click.option(
    "--format", "fmt",
    type=click.Choice(["json", "csv", "pdf", "html"]),
    default="json",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), required=True, help="Output file path")
@click.option("--lang", type=click.Choice(["ua", "en"]), default=None, help="Report language")
@click.option("--source", type=click.Choice(["openalex", "scopus", "auto"]), default="auto")
@click.pass_context
def report(ctx, author, scopus_id, orcid, fmt, output, lang, source):
    """Generate a full author dossier report in the specified format."""
    from cfd.cli.main import _build_pipeline, _build_strategy

    settings = ctx.obj["settings"]
    report_lang = lang or settings.default_language

    if not scopus_id and not orcid:
        console.print("[red]Scopus ID or ORCID is required[/red]")
        sys.exit(1)

    # Run analysis
    strategy = _build_strategy(source, settings)
    pipeline = _build_pipeline(strategy, settings)

    try:
        result = pipeline.analyze(author, scopus_id=scopus_id, orcid=orcid)
    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")
        sys.exit(1)

    output_path = Path(output)

    # Generate figures for HTML/PDF formats
    figures = None
    if fmt in ("html", "pdf"):
        figures = _generate_figures(result, settings)

    # Export in requested format
    if fmt == "json":
        from cfd.export.json_export import export_to_json
        export_to_json(result, output_path, settings)

    elif fmt == "csv":
        from cfd.export.csv_export import export_to_csv
        export_to_csv(result, output_path, settings)

    elif fmt == "html":
        from cfd.export.html_export import export_to_html
        export_to_html(result, output_path, settings, figures=figures, lang=report_lang)

    elif fmt == "pdf":
        from cfd.export.pdf_export import export_to_pdf
        export_to_pdf(result, output_path, settings, figures=figures, lang=report_lang)

    console.print(f"[green]Report saved: {output}[/green]")


def _generate_figures(result, settings) -> dict | None:
    """Generate visualization figures for the report."""
    try:
        from cfd.visualization.temporal import build_spike_chart

        figures = {}
        figures["spike_chart"] = build_spike_chart(
            # We need author_data but only have result — use what's available
            type("MockAuthorData", (), {"publications": [], "citations": []})(),
            result,
        )
        return figures
    except ImportError:
        return None
    except Exception:
        return None
