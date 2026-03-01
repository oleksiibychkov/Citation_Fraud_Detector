"""Rich console output formatting for analysis results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cfd.analysis.pipeline import AnalysisResult
from cfd.i18n.translator import t

console = Console()

LEVEL_COLORS = {
    "normal": "green",
    "low": "yellow",
    "moderate": "orange3",
    "high": "red",
    "critical": "bold red",
}


def format_results_table(result: AnalysisResult) -> None:
    """Print analysis results as a formatted console table."""
    # Author info
    name = result.author_profile.full_name or result.author_profile.surname
    console.print(f"\n[bold]{t('report.author_info')}[/bold]: {name}")
    if result.author_profile.institution:
        console.print(f"  Institution: {result.author_profile.institution}")
    if result.author_profile.h_index is not None:
        console.print(
            f"  h-index: {result.author_profile.h_index}  |  "
            f"Publications: {result.author_profile.publication_count}  |  "
            f"Citations: {result.author_profile.citation_count}"
        )

    if result.status == "insufficient_data":
        console.print(f"\n[yellow]{t('info.insufficient_data')}[/yellow]")
        for w in result.warnings:
            console.print(f"  [dim]{w}[/dim]")
        return

    # Indicators table
    table = Table(title=f"\n{t('report.indicators')}")
    table.add_column("Indicator", style="cyan", min_width=8)
    table.add_column("Value", justify="right", min_width=10)
    table.add_column("Status", justify="center", min_width=10)

    for ind in result.indicators:
        if ind.indicator_type in result.triggered_indicators:
            status = "[red]TRIGGERED[/red]"
        elif ind.details.get("status") == "N/A":
            status = "[dim]N/A[/dim]"
        else:
            status = "[green]OK[/green]"
        table.add_row(ind.indicator_type, f"{ind.value:.4f}", status)

    console.print(table)

    # Fraud Score
    color = LEVEL_COLORS.get(result.confidence_level, "white")
    level_text = t(f"levels.{result.confidence_level}")

    console.print(
        Panel(
            f"[{color}]{result.fraud_score:.4f}[/{color}]  —  "
            f"[{color}]{level_text}[/{color}]",
            title=t("report.fraud_score"),
            border_style=color,
        )
    )

    # Warnings
    if result.warnings:
        for w in result.warnings:
            console.print(f"[yellow]  {t('report.warnings')}: {w}[/yellow]")

    # Disclaimer
    console.print(f"\n[dim]{t('report.disclaimer')}[/dim]\n")
