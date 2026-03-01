"""Tests for ORCID, Scopus ID, and surname matching validators."""

import pytest

from cfd.data.validators import check_surname_match, validate_orcid, validate_scopus_id
from cfd.exceptions import ValidationError


class TestValidateOrcid:
    def test_valid_orcid(self):
        assert validate_orcid("0000-0002-1234-5678") == "0000-0002-1234-5678"

    def test_valid_orcid_with_x(self):
        assert validate_orcid("0000-0002-1234-567X") == "0000-0002-1234-567X"

    def test_strips_whitespace(self):
        assert validate_orcid("  0000-0002-1234-5678  ") == "0000-0002-1234-5678"

    def test_strips_https_prefix(self):
        assert validate_orcid("https://orcid.org/0000-0002-1234-5678") == "0000-0002-1234-5678"

    def test_strips_http_prefix(self):
        assert validate_orcid("http://orcid.org/0000-0002-1234-5678") == "0000-0002-1234-5678"

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="Invalid ORCID format"):
            validate_orcid("1234-5678")

    def test_letters_in_digits_raises(self):
        with pytest.raises(ValidationError):
            validate_orcid("000A-0002-1234-5678")

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_orcid("")


class TestValidateScopusId:
    def test_valid_5_digits(self):
        assert validate_scopus_id("12345") == "12345"

    def test_valid_11_digits(self):
        assert validate_scopus_id("57200000001") == "57200000001"

    def test_valid_15_digits(self):
        assert validate_scopus_id("123456789012345") == "123456789012345"

    def test_strips_whitespace(self):
        assert validate_scopus_id("  57200000001  ") == "57200000001"

    def test_too_short_raises(self):
        with pytest.raises(ValidationError, match="Invalid Scopus Author ID"):
            validate_scopus_id("1234")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_scopus_id("1234567890123456")

    def test_letters_raises(self):
        with pytest.raises(ValidationError):
            validate_scopus_id("5720000abc")

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_scopus_id("")


class TestCheckSurnameMatch:
    def test_exact_match(self):
        matches, warning = check_surname_match("Ivanenko", "Oleksandr Ivanenko")
        assert matches is True
        assert warning == ""

    def test_case_insensitive(self):
        matches, _ = check_surname_match("ivanenko", "OLEKSANDR IVANENKO")
        assert matches is True

    def test_substring_match(self):
        matches, _ = check_surname_match("Ivan", "Ivanenko")
        assert matches is True

    def test_comma_separated_name(self):
        matches, _ = check_surname_match("Ivanenko", "Ivanenko, O.")
        assert matches is True

    def test_no_match(self):
        matches, warning = check_surname_match("Petrenko", "Oleksandr Ivanenko")
        assert matches is False
        assert "Surname mismatch" in warning

    def test_empty_api_name_passes(self):
        matches, _ = check_surname_match("Ivanenko", "")
        assert matches is True

    def test_whitespace_handling(self):
        matches, _ = check_surname_match("  Ivanenko  ", "  Oleksandr Ivanenko  ")
        assert matches is True
