"""Visualization CLI command."""

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
    "--type", "viz_type",
    type=click.Choice(["network", "timeline", "heatmap", "spike"]),
    default="network",
    help="Visualization type",
)
@click.option("--output", "-o", type=click.Path(), required=True, help="Output HTML file")
@click.option("--source", type=click.Choice(["openalex", "scopus", "auto"]), default="auto")
@click.pass_context
def visualize(ctx, author, scopus_id, orcid, viz_type, output, source):
    """Generate interactive visualization as standalone HTML."""
    from cfd.cli.main import _build_pipeline, _build_strategy

    settings = ctx.obj["settings"]

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

    # Rebuild author_data for visualization
    try:
        author_data = strategy.collect(author, scopus_id=scopus_id, orcid=orcid)
    except Exception:
        console.print("[yellow]Could not re-collect data for visualization, using limited data[/yellow]")
        from cfd.data.models import AuthorData
        author_data = AuthorData(profile=result.author_profile, publications=[], citations=[])

    # Build the figure
    try:
        fig = _build_figure(viz_type, author_data, result, settings)
    except ImportError:
        console.print(
            "[red]plotly is required. Install with: pip install citation-fraud-detector[viz][/red]"
        )
        sys.exit(1)

    # Write HTML
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))
    console.print(f"[green]Visualization saved: {output}[/green]")


def _build_figure(viz_type, author_data, result, settings):
    """Build the requested Plotly figure."""
    if viz_type == "network":
        from cfd.visualization.network import build_network_figure
        return build_network_figure(author_data, result)

    if viz_type == "timeline":
        from cfd.visualization.temporal import build_ht_nt_figure
        return build_ht_nt_figure(author_data)

    if viz_type == "heatmap":
        from cfd.visualization.heatmap import build_mutual_heatmap
        return build_mutual_heatmap(author_data, mcr_threshold=settings.mutual_mcr_threshold)

    if viz_type == "spike":
        from cfd.visualization.temporal import build_spike_chart
        return build_spike_chart(author_data, result)

    raise ValueError(f"Unknown visualization type: {viz_type}")
