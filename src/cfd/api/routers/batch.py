"""Batch analysis endpoint."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from cfd.api.auth import APIKeyInfo, require_role
from cfd.api.dependencies import get_pipeline, get_repos
from cfd.api.schemas import BatchResponse, BatchResultItem
from cfd.exceptions import CFDError

router = APIRouter(prefix="/batch", tags=["Batch"])

MAX_BATCH_SIZE = 50
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/analyze", response_model=BatchResponse)
async def batch_analyze(
    file: UploadFile,
    key_info: APIKeyInfo = Depends(require_role("analyst", "admin")),
    pipeline=Depends(get_pipeline),
    repos: dict = Depends(get_repos),
):
    """Batch analyze authors from uploaded CSV file."""
    from cfd.data.batch import load_batch_csv

    # Write uploaded file to temp (with size limit)
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail=f"File too large. Maximum {MAX_UPLOAD_BYTES} bytes.")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        validation = load_batch_csv(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    errors = list(validation.errors)
    entries = validation.entries[:MAX_BATCH_SIZE]

    if len(validation.entries) > MAX_BATCH_SIZE:
        errors.append(f"Batch truncated to {MAX_BATCH_SIZE} entries (submitted {len(validation.entries)})")

    loop = asyncio.get_running_loop()
    results: list[BatchResultItem] = []
    for entry in entries:
        try:
            result = await loop.run_in_executor(
                None,
                lambda e=entry: pipeline.analyze(e.surname, scopus_id=e.scopus_id, orcid=e.orcid),
            )
            results.append(BatchResultItem(
                surname=entry.surname,
                status=result.status,
                fraud_score=result.fraud_score,
                confidence_level=result.confidence_level,
            ))
        except CFDError as e:
            results.append(BatchResultItem(
                surname=entry.surname,
                status="error",
                error=str(e),
            ))
        except Exception:
            results.append(BatchResultItem(
                surname=entry.surname,
                status="error",
                error="Internal analysis error",
            ))

    processed = sum(1 for r in results if r.status != "error")

    repos["audit"].log(
        "batch_analyze",
        details={"total": len(entries), "processed": processed, "api_key": key_info.name},
        user_id=key_info.name, api_key_id=key_info.key_id,
    )

    return BatchResponse(total=len(entries), processed=processed, results=results, errors=errors)
