"""Input validation for ORCID, Scopus ID, and surname matching."""

import re

from cfd.exceptions import ValidationError

ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
SCOPUS_ID_PATTERN = re.compile(r"^\d{5,15}$")


def validate_orcid(orcid: str) -> str:
    """Validate and normalize ORCID format. Returns cleaned ORCID."""
    orcid = orcid.strip()
    if orcid.startswith("https://orcid.org/"):
        orcid = orcid[len("https://orcid.org/"):]
    if orcid.startswith("http://orcid.org/"):
        orcid = orcid[len("http://orcid.org/"):]
    if not ORCID_PATTERN.match(orcid):
        raise ValidationError(f"Invalid ORCID format: {orcid}. Expected: 0000-0000-0000-000X")
    return orcid


def validate_scopus_id(scopus_id: str) -> str:
    """Validate Scopus Author ID format. Returns cleaned ID."""
    scopus_id = scopus_id.strip()
    if not SCOPUS_ID_PATTERN.match(scopus_id):
        raise ValidationError(f"Invalid Scopus Author ID format: {scopus_id}. Expected: 5-15 digits")
    return scopus_id


def check_surname_match(input_surname: str, api_name: str) -> tuple[bool, str]:
    """Check if input surname matches the name returned by API.

    Returns (matches, warning_message). Case-insensitive comparison.
    """
    if not api_name:
        return False, "API returned empty name"

    input_lower = input_surname.lower().strip()
    api_lower = api_name.lower().strip()

    # Direct substring match
    if input_lower in api_lower:
        return True, ""

    # Check individual name parts
    api_parts = api_lower.replace(",", " ").replace(".", " ").split()
    for part in api_parts:
        if input_lower == part:
            return True, ""

    return False, f"Surname mismatch: input='{input_surname}', API='{api_name}'"
