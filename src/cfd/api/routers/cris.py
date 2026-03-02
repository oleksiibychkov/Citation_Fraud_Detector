"""CRIS system integration stubs (Pure, Converis, VIVO)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from cfd.api.auth import require_role

router = APIRouter(prefix="/cris", tags=["CRIS Integration"])


@router.post("/pure/webhook")
async def pure_webhook(
    body: dict,
    key_info=Depends(require_role("admin")),
):
    """Stub: Receive webhook from Pure (Elsevier) when a researcher is added."""
    return JSONResponse(status_code=202, content={"status": "accepted", "message": "Pure webhook received (stub)"})


@router.post("/converis/sync")
async def converis_sync(
    body: dict,
    key_info=Depends(require_role("admin")),
):
    """Stub: REST integration with Converis (Clarivate)."""
    return JSONResponse(status_code=202, content={"status": "accepted", "message": "Converis sync received (stub)"})


@router.post("/vivo/query")
async def vivo_query(
    body: dict,
    key_info=Depends(require_role("admin")),
):
    """Stub: SPARQL integration with VIVO."""
    return JSONResponse(status_code=202, content={"status": "accepted", "message": "VIVO query received (stub)"})
