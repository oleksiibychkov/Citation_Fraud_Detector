"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CFD_")

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Scopus API (optional)
    scopus_api_key: str = ""

    # Analysis thresholds
    min_publications: int = 10
    min_citations: int = 20
    min_h_index: int = 3

    # Indicator thresholds
    mcr_threshold: float = 0.3
    scr_warn_threshold: float = 0.25
    scr_high_threshold: float = 0.40
    cb_threshold: float = 0.30
    ta_z_threshold: float = 3.0

    # Cache
    cache_ttl_days: int = 7

    # Rate limiting
    openalex_requests_per_second: int = 9
    scopus_requests_per_second: int = 5
    max_retries: int = 3

    # Localization
    default_language: str = "ua"

    # Algorithm version
    algorithm_version: str = "1.0.0"
