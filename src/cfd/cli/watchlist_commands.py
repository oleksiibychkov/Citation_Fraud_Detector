"""Watchlist CLI commands."""

from __future__ import annotations

import click
from rich.table import Table

from cfd.cli.formatters import console


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
