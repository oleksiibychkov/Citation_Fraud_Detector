"""CRIS system integration endpoints (Pure, Converis, VIVO) — §6.4."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cfd.api.auth import APIKeyInfo, require_role
from cfd.api.dependencies import get_repos

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cris", tags=["CRIS Integration"])


# ---------------------------------------------------------------------------
# Pydantic models for CRIS payloads
# ---------------------------------------------------------------------------


class CRISAuthorPayload(BaseModel):
    """Unified author payload extracted from any CRIS source."""

    surname: str
    given_name: str | None = None
    orcid: str | None = None
    scopus_id: str | None = None
    institution: str | None = None
    action: str = "add_to_watchlist"  # add_to_watchlist | queue_analysis


class PureWebhookBody(BaseModel):
    """Webhook payload from Pure (Elsevier)."""

    event: str = ""
    researcher: dict = Field(default_factory=dict)


class ConverisSyncBody(BaseModel):
    """Sync payload from Converis (Clarivate)."""

    action: str = ""
    person: dict = Field(default_factory=dict)


class VIVOQueryBody(BaseModel):
    """Query payload from VIVO (SPARQL-based)."""

    sparql: str = ""
    results: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _extract_pure_author(body: PureWebhookBody) -> CRISAuthorPayload | None:
    """Extract author info from a Pure webhook payload."""
    r = body.researcher
    if not r:
        return None
    return CRISAuthorPayload(
        surname=r.get("lastName", r.get("surname", "")),
        given_name=r.get("firstName", r.get("givenName")),
        orcid=r.get("orcid"),
        scopus_id=r.get("scopusId"),
        institution=r.get("institution"),
    )


def _extract_converis_author(body: ConverisSyncBody) -> CRISAuthorPayload | None:
    """Extract author info from a Converis sync payload."""
    p = body.person
    if not p:
        return None
    return CRISAuthorPayload(
        surname=p.get("familyName", p.get("surname", "")),
        given_name=p.get("givenName"),
        orcid=p.get("orcid"),
        scopus_id=p.get("scopusAuthorId"),
        institution=p.get("affiliation"),
    )


def _extract_vivo_author(body: VIVOQueryBody) -> CRISAuthorPayload | None:
    """Extract author info from VIVO SPARQL query results."""
    if not body.results:
        return None
    first = body.results[0]
    return CRISAuthorPayload(
        surname=first.get("familyName", first.get("lastName", "")),
        given_name=first.get("givenName"),
        orcid=first.get("orcid"),
        scopus_id=first.get("scopusId"),
        institution=first.get("institution"),
    )


def _process_cris_author(
    author: CRISAuthorPayload,
    repos: dict,
    source: str,
    key_info: APIKeyInfo,
) -> dict:
    """Process a CRIS-sourced author: add to watchlist or queue for analysis."""
    # Check if author exists in DB
    existing = None
    if author.scopus_id:
        existing = repos["author"].get_by_scopus_id(author.scopus_id)
    if existing is None and author.orcid:
        existing = repos["author"].get_by_orcid(author.orcid)

    result = {"source": source, "surname": author.surname, "action": author.action}

    if existing:
        author_id = existing.get("id")
        if author.action == "add_to_watchlist":
            repos["watchlist"].add(author_id, reason=f"CRIS integration ({source})")
            result["status"] = "added_to_watchlist"
            result["author_id"] = author_id
        else:
            result["status"] = "queued_for_analysis"
            result["author_id"] = author_id
    else:
        result["status"] = "author_not_found"

    # Audit log
    repos["audit"].log(
        f"cris_{source}", target_author_id=existing.get("id") if existing else None,
        details={"payload_surname": author.surname, "action": author.action},
        user_id=key_info.name, api_key_id=key_info.key_id,
    )

    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/pure/webhook")
async def pure_webhook(
    body: PureWebhookBody,
    key_info: APIKeyInfo = Depends(require_role("admin")),
    repos: dict = Depends(get_repos),
):
    """Receive webhook from Pure (Elsevier) when a researcher is added/updated."""
    author = _extract_pure_author(body)
    if author is None or not author.surname:
        return JSONResponse(status_code=202, content={"status": "accepted", "message": "No author data to process"})

    result = _process_cris_author(author, repos, "pure", key_info)
    return JSONResponse(status_code=202, content={"status": "accepted", **result})


@router.post("/converis/sync")
async def converis_sync(
    body: ConverisSyncBody,
    key_info: APIKeyInfo = Depends(require_role("admin")),
    repos: dict = Depends(get_repos),
):
    """REST integration with Converis (Clarivate)."""
    author = _extract_converis_author(body)
    if author is None or not author.surname:
        return JSONResponse(status_code=202, content={"status": "accepted", "message": "No author data to process"})

    result = _process_cris_author(author, repos, "converis", key_info)
    return JSONResponse(status_code=202, content={"status": "accepted", **result})


@router.post("/vivo/query")
async def vivo_query(
    body: VIVOQueryBody,
    key_info: APIKeyInfo = Depends(require_role("admin")),
    repos: dict = Depends(get_repos),
):
    """SPARQL integration with VIVO."""
    author = _extract_vivo_author(body)
    if author is None or not author.surname:
        return JSONResponse(status_code=202, content={"status": "accepted", "message": "No author data to process"})

    result = _process_cris_author(author, repos, "vivo", key_info)
    return JSONResponse(status_code=202, content={"status": "accepted", **result})
