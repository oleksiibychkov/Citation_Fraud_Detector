# Changelog

## v0.7.0 — Hardening, Coverage & Documentation

- **Test coverage raised to ≥80%** (from 67%), 668+ tests
- **DB repository tests**: 64 new tests covering all 16 Supabase repositories
- **Data layer tests**: 36 new tests for OpenAlex, Scopus strategies and HTTP client
- **Neo4j query tests**: 9 new tests with mocked driver/session
- **API cache tests**: 10 new tests for cache get/set/invalidate/cleanup
- **igraph engine tests**: 20 new tests (skipped when igraph not installed)
- **MkDocs documentation site**: 8 pages (index, installation, usage, API, indicators, architecture, deployment, contributing)
- **Docker hardening**: `.dockerignore` for optimized build context
- **Backup scripts**: `scripts/backup_postgres.sh`, `scripts/backup_neo4j.sh`
- **CI**: `--cov-fail-under=80` coverage threshold, `[dev,api,igraph]` install
- **Updated README** with API, architecture, deployment, and documentation sections

## v0.6.0 — REST API, Deployment & Finalization

- **FastAPI REST API** with `create_app()` factory pattern, OpenAPI docs at `/api/docs`
- **API key authentication** via `X-API-Key` header with SHA-256 hash lookup in DB, env fallback
- **Role-based access control**: reader, analyst, admin roles with `require_role()` dependency
- **Rate limiting** via slowapi, keyed by API key
- **Author endpoints**: GET report, score, indicators, graph (read cached results from DB)
- **Batch analysis**: POST CSV upload, max 50 entries, synchronous processing
- **Watchlist management**: add, list, history endpoints
- **Audit log**: admin-only paginated endpoint
- **Algorithm version**: current + history endpoints
- **CRIS integration stubs**: Pure webhook, Converis sync, VIVO query (202 Accepted)
- **I18n middleware**: Accept-Language header sets per-request language
- **Exception handlers**: AuthorNotFound→404, Validation→422, Authorization→403, RateLimit→429, DBUnavailable→503
- **Deployment**: Dockerfile (multi-stage), docker-compose (API + Neo4j), CI/CD workflows
- **549 tests** (488 existing + 61 new API tests)

## v0.5.0 — Advanced Indicators & Calibration

- **5 new indicators**: Authorship Network Anomaly (ANA), Peer Benchmark (PB), Salami Slicing Detector (SSD), Citation Cannibalism (CC), Cross-Platform Consistency (CPC)
- **Weight calibration system**: scipy SLSQP optimizer with synthetic fixtures, evaluation metrics
- **20 total indicators** with balanced weights (sum = 1.0)
- **Algorithm version 5.0.0**
- **4 new contextual signals**: SSD, CC, ANA, CPC
- 488 tests

## v0.4.0 — Dashboard, Visualization & Anti-Ranking

- **Streamlit dashboard** with 4 tabs: Overview, Author Dossier, Snapshot Compare, Anti-Ranking
- **5 Plotly visualizations**: citation network, timeline, heatmap, spike, baseline
- **Anti-ranking system**: top suspicious authors, sortable, filterable
- **Snapshot comparison**: side-by-side temporal comparison with delta indicators
- **PDF/HTML export** via ReportLab and Jinja2
- 415 tests

## v0.3.0 — Graph Analysis & Theorems

- **NetworkX graph analysis**: PageRank, eigenvector centrality, betweenness, community detection, clique analysis
- **3 mathematical theorems**: Perron-Frobenius, Ramsey-based clique, Benford's law
- **Citation velocity** and **Sleeping Beauty** indicators
- **Contextual analysis** with discipline baselines
- **Neo4j optional integration** for persistent graph storage
- 302 tests

## v0.2.0 — Database & Persistence

- **Supabase integration** with 8 repository classes
- **Watchlist system** with periodic re-analysis and snapshots
- **Audit logging** for all operations
- **Algorithm versioning** with DB-backed version history
- **Batch CSV analysis** with validation
- 185 tests

## v0.1.0 — Core Engine

- **OpenAlex data strategy** with HTTP client and caching
- **Self-citation ratio (SCR)** and **Mutual Citation Rate (MCR)** indicators
- **Citation burst (CB)** and **Temporal Anomaly (TA)** detection
- **H-index Temporal Anomaly (HTA)** indicator
- **Reference List Anomaly (RLA)** and **Geographic/Institutional Concentration (GIC)**
- **Fraud scoring** with configurable weights and thresholds
- **CLI** with `cfd analyze`, `cfd batch`, `cfd watchlist` commands
- **i18n** support (Ukrainian, English)
- 95 tests
