"""Snapshot comparison CLI command."""

from __future__ import annotations

import sys

import click
from rich.table import Table

from cfd.cli.formatters import console


@click.command()
@click.option("--author-id", required=True, type=int, help="Author database ID")
@click.option("--snapshots", type=int, default=2, help="Number of recent snapshots to compare")
@click.pass_context
def compare(ctx, author_id, snapshots):
    """Compare recent snapshots for a watchlisted author."""
    settings = ctx.obj["settings"]

    try:
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.snapshots import SnapshotRepository

        client = get_supabase_client(settings)
        snap_repo = SnapshotRepository(client)

        entries = snap_repo.get_by_author_id(author_id, limit=snapshots)

        if not entries:
            console.print("[dim]No snapshots found for this author[/dim]")
            return

        if len(entries) < 2:
            console.print("[yellow]Only one snapshot available — no comparison possible[/yellow]")
            _show_single_snapshot(entries[0])
            return

        # Compare latest vs previous
        latest = entries[0]
        previous = entries[1]

        table = Table(title=f"Snapshot Comparison — Author {author_id}")
        table.add_column("Metric", style="cyan")
        table.add_column(f"Previous ({_format_date(previous)})")
        table.add_column(f"Latest ({_format_date(latest)})")
        table.add_column("Delta")

        # Compare key metrics
        metrics = [
            ("fraud_score", "Fraud Score"),
            ("h_index", "h-index"),
            ("citation_count", "Citations"),
            ("publication_count", "Publications"),
        ]

        for key, label in metrics:
            prev_val = previous.get(key, previous.get("metrics", {}).get(key))
            curr_val = latest.get(key, latest.get("metrics", {}).get(key))

            if prev_val is not None and curr_val is not None:
                try:
                    delta = float(curr_val) - float(prev_val)
                    delta_str = f"{delta:+.4f}" if isinstance(curr_val, float) else f"{delta:+.0f}"
                    color = ("red" if delta > 0 else "green" if delta < 0 else "dim") if key == "fraud_score" else "dim"
                    table.add_row(label, str(prev_val), str(curr_val), f"[{color}]{delta_str}[/{color}]")
                except (TypeError, ValueError):
                    table.add_row(label, str(prev_val), str(curr_val), "—")
            else:
                table.add_row(label, str(prev_val or "—"), str(curr_val or "—"), "—")

        # Algorithm version check
        prev_algo = previous.get("algorithm_version", "?")
        curr_algo = latest.get("algorithm_version", "?")
        if prev_algo != curr_algo:
            table.add_row(
                "Algorithm Version",
                str(prev_algo),
                str(curr_algo),
                "[yellow]VERSION CHANGED[/yellow]",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def _show_single_snapshot(snapshot: dict) -> None:
    """Display a single snapshot."""
    table = Table(title="Latest Snapshot")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    for key in ("fraud_score", "h_index", "citation_count", "publication_count", "algorithm_version"):
        val = snapshot.get(key, snapshot.get("metrics", {}).get(key, "—"))
        table.add_row(key, str(val))

    console.print(table)


def _format_date(snapshot: dict) -> str:
    """Format snapshot date for display."""
    d = snapshot.get("snapshot_date") or snapshot.get("created_at", "?")
    return str(d)[:10]
