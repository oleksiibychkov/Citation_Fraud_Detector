"""CSV batch import with validation and deduplication."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path

from cfd.data.validators import validate_orcid, validate_scopus_id
from cfd.exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class BatchEntry:
    """A single entry from a batch CSV file."""

    surname: str
    scopus_id: str | None = None
    orcid: str | None = None


@dataclass
class BatchValidationResult:
    """Result of batch CSV validation."""

    entries: list[BatchEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicates_removed: int = 0


def load_batch_csv(file_path: Path) -> BatchValidationResult:
    """Load and validate a batch CSV file. Deduplicates by ID."""
    result = BatchValidationResult()
    seen_ids: set[str] = set()

    if not file_path.exists():
        result.errors.append(f"File not found: {file_path}")
        return result

    try:
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate required columns
            fieldnames = set(reader.fieldnames or [])
            if "surname" not in fieldnames:
                result.errors.append("Missing required column: 'surname'")
                return result

            has_scopus = "scopus_id" in fieldnames
            has_orcid = "orcid" in fieldnames
            if not has_scopus and not has_orcid:
                result.errors.append("CSV must have at least one of: 'scopus_id', 'orcid'")
                return result

            for row_num, row in enumerate(reader, start=2):
                surname = (row.get("surname") or "").strip()
                if not surname:
                    result.errors.append(f"Row {row_num}: empty surname")
                    continue

                scopus_id = (row.get("scopus_id") or "").strip() or None
                orcid = (row.get("orcid") or "").strip() or None

                # Validate formats
                if scopus_id:
                    try:
                        scopus_id = validate_scopus_id(scopus_id)
                    except ValidationError as e:
                        result.errors.append(f"Row {row_num}: {e}")
                        continue

                if orcid:
                    try:
                        orcid = validate_orcid(orcid)
                    except ValidationError as e:
                        result.errors.append(f"Row {row_num}: {e}")
                        continue

                if not scopus_id and not orcid:
                    result.errors.append(f"Row {row_num}: no Scopus ID or ORCID provided for '{surname}'")
                    continue

                # Dedup by ID
                dedup_key = scopus_id or orcid or ""
                if dedup_key in seen_ids:
                    result.duplicates_removed += 1
                    result.warnings.append(f"Row {row_num}: duplicate ID '{dedup_key}' for '{surname}', skipped")
                    continue
                seen_ids.add(dedup_key)

                result.entries.append(BatchEntry(surname=surname, scopus_id=scopus_id, orcid=orcid))

    except UnicodeDecodeError:
        result.errors.append("CSV file encoding error. Please use UTF-8.")
    except csv.Error as e:
        result.errors.append(f"CSV parsing error: {e}")

    return result
