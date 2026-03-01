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

    # Neo4j (optional, AuraDB Free)
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Indicator thresholds
    mcr_threshold: float = 0.3
    scr_warn_threshold: float = 0.25
    scr_high_threshold: float = 0.40
    cb_threshold: float = 0.30
    ta_z_threshold: float = 3.0

    # Extended indicator thresholds (Stage 2)
    rla_threshold: float = 0.4
    gic_threshold: float = 0.6
    eigenvector_threshold: float = 0.5
    betweenness_threshold: float = 0.3
    pagerank_threshold: float = 0.1

    # Community detection
    community_density_ratio_threshold: float = 2.0
    min_community_size: int = 3

    # Clique detection
    min_clique_size: int = 3

    # Theorem 2 (Cantelli inequality)
    cantelli_z_threshold: float = 3.0

    # G_mutual threshold
    mutual_mcr_threshold: float = 0.3

    # Citation Velocity (Stage 3)
    cv_threshold: float = 5.0
    cv_window_months: int = 24

    # Sleeping Beauty Detector (Stage 3)
    sbd_beauty_threshold: float = 100.0
    sbd_suspicious_threshold: float = 0.3

    # Contextual analysis (Stage 3)
    ctx_independent_threshold: int = 3

    # Scalability
    igraph_node_threshold: int = 50_000

    # Cache
    cache_ttl_days: int = 7

    # Rate limiting
    openalex_requests_per_second: int = 9
    scopus_requests_per_second: int = 5
    max_retries: int = 3

    # Localization
    default_language: str = "ua"

    # Algorithm version
    algorithm_version: str = "4.0.0"
