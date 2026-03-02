"""Watchlist CLI commands."""

from __future__ import annotations

import json
import logging

import click
from rich.table import Table

from cfd.cli.formatters import console

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def watchlist(ctx):
    """Watch-list management / Управління списком спостереження."""
    pass


@watchlist.command()
@click.option("--scopus-id", default=None, help="Scopus Author ID")
@click.option("--orcid", default=None, help="ORCID identifier")
@click.option("--reason", default=None, help="Reason for adding to watchlist")
@click.pass_context
def add(ctx, scopus_id, orcid, reason):
    """Add an author to the watch-list."""
    settings = ctx.obj["settings"]

    if not scopus_id and not orcid:
        console.print("[red]Scopus ID or ORCID is required[/red]")
        return

    try:
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.authors import AuthorRepository
        from cfd.db.repositories.watchlist import WatchlistRepository

        client = get_supabase_client(settings)
        author_repo = AuthorRepository(client)
        watchlist_repo = WatchlistRepository(client)

        # Find author
        author = author_repo.get_by_scopus_id(scopus_id) if scopus_id else author_repo.get_by_orcid(orcid)

        if not author:
            console.print("[red]Author not found in database. Run 'cfd analyze' first.[/red]")
            return

        author_id = author.get("id")
        watchlist_repo.add(author_id, reason=reason)
        console.print(f"[green]Author added to watchlist (ID: {author_id})[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@watchlist.command()
@click.option("--scopus-id", default=None, help="Scopus Author ID")
@click.option("--orcid", default=None, help="ORCID identifier")
@click.pass_context
def remove(ctx, scopus_id, orcid):
    """Remove an author from the watch-list."""
    settings = ctx.obj["settings"]

    if not scopus_id and not orcid:
        console.print("[red]Scopus ID or ORCID is required[/red]")
        return

    try:
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.authors import AuthorRepository
        from cfd.db.repositories.watchlist import WatchlistRepository

        client = get_supabase_client(settings)
        author_repo = AuthorRepository(client)
        watchlist_repo = WatchlistRepository(client)

        author = author_repo.get_by_scopus_id(scopus_id) if scopus_id else author_repo.get_by_orcid(orcid)

        if not author:
            console.print("[red]Author not found[/red]")
            return

        watchlist_repo.remove(author["id"])
        console.print("[green]Author removed from watchlist[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@watchlist.command(name="list")
@click.pass_context
def list_watchlist(ctx):
    """List all active watch-list entries."""
    settings = ctx.obj["settings"]

    try:
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.watchlist import WatchlistRepository

        client = get_supabase_client(settings)
        watchlist_repo = WatchlistRepository(client)

        entries = watchlist_repo.get_active()

        if not entries:
            console.print("[dim]Watchlist is empty[/dim]")
            return

        table = Table(title="Active Watchlist")
        table.add_column("Author ID", style="cyan")
        table.add_column("Reason")
        table.add_column("Added")
        table.add_column("Notes")

        for entry in entries:
            table.add_row(
                str(entry.get("author_id", "")),
                entry.get("reason", "—"),
                str(entry.get("created_at", ""))[:10],
                entry.get("notes", "—"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@watchlist.command()
@click.option("--all", "reanalyze_all", is_flag=True, help="Re-analyze all active watchlist authors")
@click.pass_context
def reanalyze(ctx, reanalyze_all):
    """Re-analyze watchlist authors (used by cron / §4.4)."""
    settings = ctx.obj["settings"]

    if not reanalyze_all:
        console.print("[red]Use --all to re-analyze all active watchlist authors[/red]")
        return

    try:
        from cfd.cli.main import _build_strategy
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.authors import AuthorRepository
        from cfd.db.repositories.citations import CitationRepository
        from cfd.db.repositories.fraud_scores import FraudScoreRepository
        from cfd.db.repositories.indicators import IndicatorRepository
        from cfd.db.repositories.publications import PublicationRepository
        from cfd.db.repositories.snapshots import SnapshotRepository
        from cfd.db.repositories.watchlist import WatchlistRepository

        client = get_supabase_client(settings)
        watchlist_repo = WatchlistRepository(client)
        author_repo = AuthorRepository(client)
        pub_repo = PublicationRepository(client)
        cit_repo = CitationRepository(client)
        ind_repo = IndicatorRepository(client)
        score_repo = FraudScoreRepository(client)
        snapshot_repo = SnapshotRepository(client)

        entries = watchlist_repo.get_active()
        if not entries:
            console.print("[dim]No active watchlist entries[/dim]")
            return

        console.print(f"Re-analyzing {len(entries)} watchlist authors...")
        strategy = _build_strategy("auto", settings)

        from cfd.analysis.pipeline import AnalysisPipeline
        from cfd.notifications.dispatcher import dispatch_score_change

        for entry in entries:
            author_id = entry.get("author_id")
            author = author_repo.get_by_id(author_id) if author_id else None
            if not author:
                console.print(f"  [dim]Author {author_id}: not found in DB — skipping[/dim]")
                continue

            surname = author.get("surname", "unknown")
            scopus_id = author.get("scopus_id")
            orcid = author.get("orcid")

            # Get previous score for comparison
            prev_scores = score_repo.get_latest_by_author(author_id)
            old_score = prev_scores.get("score", 0.0) if prev_scores else 0.0

            # Sensitivity overrides
            overrides = entry.get("sensitivity_overrides")

            try:
                pipeline = AnalysisPipeline(
                    strategy=strategy,
                    settings=settings,
                    author_repo=author_repo,
                    pub_repo=pub_repo,
                    cit_repo=cit_repo,
                    ind_repo=ind_repo,
                    score_repo=score_repo,
                )
                result = pipeline.analyze(
                    surname, scopus_id=scopus_id, orcid=orcid,
                    sensitivity_overrides=overrides,
                )

                # Save snapshot
                snapshot_repo.save({
                    "author_id": author_id,
                    "fraud_score": result.fraud_score,
                    "confidence_level": result.confidence_level,
                    "indicator_values": {i.indicator_type: i.value for i in result.indicators},
                    "algorithm_version": settings.algorithm_version,
                })

                # Notify if score changed significantly
                dispatch_score_change(
                    settings=settings,
                    author_name=author.get("full_name", surname),
                    author_id=author_id,
                    old_score=old_score,
                    new_score=result.fraud_score,
                )

                console.print(
                    f"  [green]{surname}[/green]: {result.fraud_score:.4f} "
                    f"(was {old_score:.4f}, status={result.status})"
                )
            except Exception as e:
                console.print(f"  [red]{surname}: {e}[/red]")
                logger.warning("Reanalyze failed for author %d", author_id, exc_info=True)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@watchlist.command(name="set-sensitivity")
@click.option("--author-id", required=True, type=int, help="Author database ID")
@click.option("--overrides", required=True, help="JSON string of overrides, e.g. '{\"scr_warn_threshold\":0.30}'")
@click.pass_context
def set_sensitivity(ctx, author_id, overrides):
    """Set per-author sensitivity overrides (§4.4)."""
    settings = ctx.obj["settings"]

    try:
        overrides_dict = json.loads(overrides)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        return

    if not isinstance(overrides_dict, dict):
        console.print("[red]Overrides must be a JSON object (dict), not a list or scalar[/red]")
        return

    from cfd.api.schemas import _ALLOWED_SENSITIVITY_KEYS

    bad_keys = set(overrides_dict) - _ALLOWED_SENSITIVITY_KEYS
    if bad_keys:
        console.print(f"[red]Invalid sensitivity keys: {sorted(bad_keys)}[/red]")
        return

    try:
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.watchlist import WatchlistRepository

        client = get_supabase_client(settings)
        watchlist_repo = WatchlistRepository(client)
        result = watchlist_repo.set_sensitivity_overrides(author_id, overrides_dict)

        if result:
            console.print(f"[green]Sensitivity overrides set for author {author_id}[/green]")
        else:
            console.print("[yellow]No watchlist entry found for this author[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
