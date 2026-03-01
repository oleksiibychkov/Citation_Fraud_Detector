"""Custom exception hierarchy for CFD."""


class CFDError(Exception):
    """Base exception for CFD."""


class AuthorNotFoundError(CFDError):
    """Author not found in API."""


class InsufficientDataError(CFDError):
    """Author does not meet minimum requirements for analysis."""


class APIError(CFDError):
    """API request failed."""


class RateLimitError(APIError):
    """API rate limit exceeded."""


class IdentityMismatchError(CFDError):
    """ORCID and Scopus ID point to different people."""


class ValidationError(CFDError):
    """Input validation failed."""


class Neo4jConnectionError(CFDError):
    """Neo4j connection failed."""


class GraphEngineError(CFDError):
    """Graph engine computation failed."""
