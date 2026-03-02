"""Health check and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from cfd import __version__

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def ready(request: Request):
    """Readiness check — verifies DB connectivity."""
    supabase = getattr(request.app.state, "supabase", None)
    if supabase is None:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})
    try:
        supabase.table("authors").select("id").limit(1).execute()
        return {"status": "ok", "database": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "error"})
