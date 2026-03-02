"""Algorithm version information endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from cfd.api.auth import require_role
from cfd.api.dependencies import get_repos, get_settings
from cfd.api.schemas import VersionInfo
from cfd.config.settings import Settings

router = APIRouter(prefix="/version", tags=["Version"])


@router.get("/current", response_model=VersionInfo)
async def get_current_version(
    key_info=Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
    settings: Settings = Depends(get_settings),
):
    """Get current algorithm version info."""
    version_data = repos["algorithm"].get_by_version(settings.algorithm_version)
    if version_data:
        return VersionInfo(
            version=version_data.get("version", settings.algorithm_version),
            release_date=str(version_data.get("release_date", "")),
            indicator_count=version_data.get("indicator_count"),
            weights=version_data.get("weights"),
            thresholds=version_data.get("thresholds"),
            changelog=version_data.get("changelog"),
        )
    return VersionInfo(version=settings.algorithm_version)


@router.get("/history", response_model=list[VersionInfo])
async def get_version_history(
    key_info=Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
):
    """Get all algorithm versions."""
    versions = repos["algorithm"].get_all()
    return [
        VersionInfo(
            version=v.get("version", ""),
            release_date=str(v.get("release_date", "")),
            indicator_count=v.get("indicator_count"),
            weights=v.get("weights"),
            thresholds=v.get("thresholds"),
            changelog=v.get("changelog"),
        )
        for v in versions
    ]
