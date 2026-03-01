"""CFD CLI entry point using Click."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from cfd.cli.formatters import console, format_results_table
from cfd.config.settings import Settings
from cfd.data.validators import validate_orcid, validate_scopus_id
from cfd.exceptions import AuthorNotFoundError, CFDError, IdentityMismatchError, ValidationError
from cfd.export.json_export import export_to_json
from cfd.i18n.translator import set_language, t


def _build_strategy(source: str, settings: Settings):
    """Build the appropriate data source strategy."""
    from cfd.data.http_client import CachedHttpClient, RateLimiter

    # Try to get supabase client for caching
    supabase_client = None
    if settings.supabase_url and settings.supabase_key:
        try:
            from cfd.db.client import get_supabase_client

            supabase_client = get_supabase_client(settings)
        except Exception:
            pass

    if source == "scopus":
        from cfd.data.scopus import ScopusStrategy

        rate_limiter = RateLimiter(settings.scopus_requests_per_second)
        http_client = CachedHttpClient(supabase_client, rate_limiter, settings.cache_ttl_days)
        return ScopusStrategy(http_client, settings.scopus_api_key)

    if source == "openalex":
        from cfd.data.openalex import OpenAlexStrategy

        rate_limiter = RateLimiter(settings.openalex_requests_per_second)
        http_client = CachedHttpClient(supabase_client, rate_limiter, settings.cache_ttl_days)
        return OpenAlexStrategy(http_client)

    # Auto: try OpenAlex first, fallback to Scopus
    from cfd.data.fallback import FallbackStrategy
    from cfd.data.openalex import OpenAlexStrategy

    rate_limiter_oa = RateLimiter(settings.openalex_requests_per_second)
    http_oa = CachedHttpClient(supabase_client, rate_limiter_oa, settings.cache_ttl_days)
    primary = OpenAlexStrategy(http_oa)

    if settings.scopus_api_key:
        from cfd.data.scopus import ScopusStrategy

        rate_limiter_sc = RateLimiter(settings.scopus_requests_per_second)
        http_sc = CachedHttpClient(supabase_client, rate_limiter_sc, settings.cache_ttl_days)
        secondary = ScopusStrategy(http_sc, settings.scopus_api_key)
        return FallbackStrategy(primary, secondary)

    return primary


def _build_pipeline(strategy, settings: Settings):
    """Build analysis pipeline with optional DB repositories."""
    from cfd.analysis.pipeline import AnalysisPipeline

    author_repo = None
    pub_repo = None
    cit_repo = None
    ind_repo = None
    score_repo = None

    if settings.supabase_url and settings.supabase_key:
        try:
            from cfd.db.client import get_supabase_client
            from cfd.db.repositories.authors import AuthorRepository
            from cfd.db.repositories.citations import CitationRepository
            from cfd.db.repositories.fraud_scores import FraudScoreRepository
            from cfd.db.repositories.indicators import IndicatorRepository
            from cfd.db.repositories.publications import PublicationRepository

            client = get_supabase_client(settings)
            author_repo = AuthorRepository(client)
            pub_repo = PublicationRepository(client)
            cit_repo = CitationRepository(client)
            ind_repo = IndicatorRepository(client)
            score_repo = FraudScoreRepository(client)
        except Exception:
            logging.getLogger(__name__).warning("DB not available, running without persistence")

    return AnalysisPipeline(
        strategy=strategy,
        settings=settings,
        author_repo=author_repo,
        pub_repo=pub_repo,
        cit_repo=cit_repo,
        ind_repo=ind_repo,
        score_repo=score_repo,
    )


@click.group()
@click.option("--lang", type=click.Choice(["ua", "en"]), default="ua", help="Interface language / Мова інтерфейсу")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, lang, verbose):
    """Citation Fraud Detector — аналіз патернів цитатних маніпуляцій."""
    set_language(lang)
    ctx.ensure_object(dict)
    ctx.obj["settings"] = Settings()

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)


@cli.command()
@click.option("--author", required=True, help="Author surname / Прізвище автора")
@click.option("--scopus-id", default=None, help="Scopus Author ID")
@click.option("--orcid", default=None, help="ORCID identifier")
@click.option(
    "--source",
    type=click.Choice(["openalex", "scopus", "auto"]),
    default="auto",
    help="Data source",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output JSON file path")
@click.pass_context
def analyze(ctx, author, scopus_id, orcid, source, output):
    """Analyze a single author for citation manipulation indicators."""
    settings = ctx.obj["settings"]

    # Validate inputs
    if not scopus_id and not orcid:
        console.print(f"[red]{t('error.id_required')}[/red]")
        sys.exit(1)

    try:
        if scopus_id:
            scopus_id = validate_scopus_id(scopus_id)
        if orcid:
            orcid = validate_orcid(orcid)
    except ValidationError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    # Build strategy and pipeline
    strategy = _build_strategy(source, settings)
    pipeline = _build_pipeline(strategy, settings)

    # Run analysis
    console.print(t("info.analyzing", author=author))

    try:
        result = pipeline.analyze(author, scopus_id=scopus_id, orcid=orcid)
    except AuthorNotFoundError:
        console.print(f"[red]{t('error.author_not_found', author=author)}[/red]")
        sys.exit(1)
    except IdentityMismatchError:
        console.print(f"[red]{t('error.identity_mismatch')}[/red]")
        sys.exit(1)
    except CFDError as e:
        console.print(f"[red]{t('error.api_error', message=str(e))}[/red]")
        sys.exit(1)

    # Display results
    format_results_table(result)

    # Export if requested
    if output:
        export_to_json(result, Path(output), settings)
        console.print(t("info.exported", path=output))


@cli.command()
@click.option("--batch", "batch_file", required=True, type=click.Path(exists=True), help="CSV file with authors")
@click.option(
    "--source",
    type=click.Choice(["openalex", "scopus", "auto"]),
    default="auto",
)
@click.option("--output-dir", type=click.Path(), default="./reports", help="Output directory for reports")
@click.pass_context
def batch(ctx, batch_file, source, output_dir):
    """Batch analysis of multiple authors from CSV."""
    from cfd.data.batch import load_batch_csv

    settings = ctx.obj["settings"]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load and validate CSV
    validation = load_batch_csv(Path(batch_file))

    if validation.errors:
        console.print("[red]CSV validation errors:[/red]")
        for err in validation.errors:
            console.print(f"  [red]{err}[/red]")
        if not validation.entries:
            sys.exit(1)

    if validation.warnings:
        for warn in validation.warnings:
            console.print(f"[yellow]{warn}[/yellow]")

    if validation.duplicates_removed > 0:
        console.print(f"[yellow]Duplicates removed: {validation.duplicates_removed}[/yellow]")

    entries = validation.entries
    console.print(t("info.batch_start", count=len(entries)))

    # Build strategy and pipeline
    strategy = _build_strategy(source, settings)
    pipeline = _build_pipeline(strategy, settings)

    # Process each author
    for i, entry in enumerate(entries, 1):
        console.print(t("info.batch_progress", current=i, total=len(entries), author=entry.surname))

        try:
            result = pipeline.analyze(entry.surname, scopus_id=entry.scopus_id, orcid=entry.orcid)
            format_results_table(result)

            # Export individual report
            report_file = output_path / f"{entry.surname}_{entry.scopus_id or entry.orcid}.json"
            export_to_json(result, report_file, settings)

        except CFDError as e:
            console.print(t("info.batch_skipped", author=entry.surname, reason=str(e)))
            continue

    console.print(t("info.batch_complete", output_dir=str(output_path)))
