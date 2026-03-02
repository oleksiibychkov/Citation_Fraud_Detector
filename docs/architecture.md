# Architecture

## System Overview

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   CLI/API   │────>│  Core Engine  │────>│  Data Layer │
│  (Click/    │     │  (Indicators, │     │  (OpenAlex, │
│   FastAPI)  │     │   Scoring,    │     │   Scopus)   │
└──────┬──────┘     │   Theorems)   │     └──────┬──────┘
       │            └──────┬───────┘            │
       │                   │                     │
       v                   v                     v
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    Export     │    │    Graph     │    │   HTTP Cache  │
│ (JSON,CSV,   │    │  (NetworkX,  │    │  (Supabase    │
│  PDF,HTML)   │    │   igraph,    │    │   api_cache)  │
└──────────────┘    │   Neo4j)     │    └──────────────┘
                    └──────────────┘
                           │
                           v
                    ┌──────────────┐
                    │   Database    │
                    │  (Supabase/   │
                    │  PostgreSQL)  │
                    └──────────────┘
```

## Package Structure

```
src/cfd/
├── __init__.py              # Version
├── exceptions.py            # Custom exception hierarchy
├── config/
│   └── settings.py          # Pydantic Settings (env vars)
├── data/
│   ├── models.py            # Core data models (AuthorProfile, Publication, Citation)
│   ├── strategy.py          # DataStrategy abstract base
│   ├── openalex.py          # OpenAlex API strategy
│   ├── scopus.py            # Scopus API strategy
│   └── http_client.py       # Cached HTTP client with rate limiting
├── db/
│   ├── client.py            # Supabase client singleton
│   ├── cache.py             # API response cache
│   └── repositories/        # 16 repository classes (one per table)
├── graph/
│   ├── engine.py            # GraphEngine ABC + NetworkXEngine + select_engine()
│   ├── igraph_engine.py     # IGraphEngine (optional, for >50K nodes)
│   ├── builder.py           # Build NetworkX graph from citations
│   ├── metrics.py           # Core indicators (SCR, MCR, CB, TA, HTA, CV, SBD, CTX, ANA, PB, SSD, CC, CPC)
│   ├── indicators.py        # RLA, GIC indicators
│   ├── centrality.py        # EIGEN, BETWEENNESS, PAGERANK
│   ├── community.py         # COMMUNITY indicator
│   ├── cliques.py           # CLIQUE indicator
│   ├── mutual.py            # MCR computation
│   ├── scoring.py           # Weighted score aggregation
│   └── theorems.py          # 3 mathematical theorems
├── neo4j/
│   ├── client.py            # Neo4j driver management
│   ├── engine.py            # Neo4jGraphEngine
│   ├── etl.py               # Load data into Neo4j
│   └── queries.py           # Cypher queries (GDS algorithms)
├── cli/
│   └── main.py              # Click CLI (analyze, batch, watchlist)
├── api/
│   ├── app.py               # FastAPI factory
│   ├── dependencies.py      # Auth, DB dependency injection
│   ├── schemas.py           # Pydantic response models
│   ├── middleware.py         # I18n middleware
│   ├── rate_limit.py        # SlowAPI rate limiter
│   └── routers/             # Endpoint routers
├── export/
│   ├── json_export.py
│   ├── csv_export.py
│   ├── pdf_export.py
│   └── html_export.py
├── visualization/
│   ├── network.py           # Plotly citation network
│   ├── temporal.py          # Timeline charts
│   ├── heatmap.py           # Indicator heatmap
│   └── colors.py            # Color constants
└── i18n/
    └── translator.py        # Locale-based translation
```

## Data Flow

1. **Input**: Author identifier (ORCID, Scopus ID, or name) via CLI or API
2. **Data Fetch**: OpenAlex/Scopus strategy fetches author profile, publications, and citations
3. **Graph Construction**: NetworkX DiGraph built from citation relationships
4. **Indicator Computation**: 20 indicators computed from data + graph
5. **Theorem Verification**: 3 mathematical theorems applied
6. **Score Aggregation**: Weighted average with normalization
7. **Persistence**: Results stored in Supabase (16 tables)
8. **Output**: Report via CLI (Rich), API (JSON), or export (PDF/HTML/CSV)

## Database Schema

The system uses Supabase (PostgreSQL) with 16 tables:

- `authors` — Author profiles and metadata
- `publications` — Publication records
- `citations` — Citation relationships
- `indicators` — Computed indicator values
- `fraud_scores` — Aggregated fraud scores
- `theorem_results` — Mathematical theorem results
- `watchlist` — Monitoring watchlist
- `snapshots` — Temporal snapshots for comparison
- `algorithm_versions` — Version history
- `audit_log` — Operation audit trail
- `discipline_baselines` — Field-level baseline statistics
- `cliques` — Detected citation cliques
- `communities` — Community detection results
- `author_connections` — Co-citation/co-authorship links
- `report_evidence` — Evidence items for reports
- `api_cache` — HTTP response cache
- `peer_groups` — Peer group compositions

## Engine Selection

The system auto-selects the best graph engine:

- **NetworkX** (default): Pure Python, suitable for graphs < 50K nodes
- **igraph** (optional): C-based, recommended for graphs > 50K nodes
- **Neo4j** (optional): Persistent graph database with GDS algorithms
