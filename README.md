# Citation Fraud Detector (CFD)

Багаторівнева система детекції аномальних патернів цитування у наукометричних базах даних.

A multi-level system for detecting anomalous citation patterns in scientometric databases.

## Встановлення / Installation

```bash
# Clone the repository
git clone <repo-url>
cd "Citation Fraud Detector"

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your Supabase credentials
```

## Використання / Usage

### Аналіз окремого автора / Single Author Analysis

```bash
# By ORCID (OpenAlex source)
cfd analyze --author "Ivanenko" --orcid "0000-0002-1234-5678" --source openalex

# By Scopus ID
cfd analyze --author "Ivanenko" --scopus-id "57200000001" --source scopus

# Auto source selection with JSON export
cfd analyze --author "Ivanenko" --orcid "0000-0002-1234-5678" --output report.json

# English interface
cfd --lang en analyze --author "Smith" --orcid "0000-0002-1234-5678"
```

### Batch-аналіз / Batch Analysis

```bash
cfd batch --batch authors.csv --source openalex --output-dir ./reports
```

CSV format:
```csv
surname,scopus_id,orcid
Ivanenko,57200000001,0000-0002-1234-5678
Petrenko,,0000-0003-9876-5432
```

## REST API

Start the API server:

```bash
pip install -e ".[api]"
cfd-api
```

Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/v1/authors/{id}/report` | Full analysis report |
| `GET /api/v1/authors/{id}/score` | Fraud score |
| `POST /api/v1/batch` | Batch CSV analysis |
| `GET /api/v1/watchlist` | Watchlist entries |
| `GET /api/docs` | Interactive Swagger docs |

Authentication via `X-API-Key` header. See [API docs](docs/api.md) for details.

## Архітектура / Architecture

```
CLI/API → Core Engine (20 indicators + 3 theorems) → Data Layer (OpenAlex/Scopus)
                ↓                                            ↓
          Graph Analysis                              HTTP Cache
       (NetworkX/igraph/Neo4j)                      (Supabase)
                ↓
          Database (Supabase/PostgreSQL, 16 tables)
```

## Індикатори / Indicators

20 indicators across 5 categories:

| Category | Indicators |
|----------|------------|
| Core Citation | SCR, MCR, CB, TA, HTA |
| Reference & Geographic | RLA, GIC |
| Graph-Based | EIGEN, BETWEENNESS, PAGERANK, COMMUNITY, CLIQUE |
| Temporal & Velocity | CV, SBD |
| Contextual & Advanced | CTX, ANA, PB, SSD, CC, CPC |

See [full indicator documentation](docs/indicators.md) for formulas and thresholds.

## Рівні впевненості / Confidence Levels

| Level | Score Range | Color |
|-------|-------------|-------|
| Normal | 0.0–0.2 | Green |
| Low | 0.2–0.4 | Yellow |
| Moderate | 0.4–0.6 | Orange |
| High | 0.6–0.8 | Red |
| Critical | 0.8–1.0 | Dark Red |

## Deployment

```bash
# Docker
docker build -t cfd-api .
docker run -p 8000:8000 --env-file .env cfd-api

# Docker Compose (API + Neo4j)
docker-compose up -d
```

See [deployment guide](docs/deployment.md) for Render.com, backup scripts, and CI/CD.

## Розробка / Development

```bash
# Run tests (668+ tests, ≥80% coverage)
pytest --cov=cfd

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Build docs
pip install -e ".[docs]"
mkdocs serve
```

## Документація / Documentation

Full documentation available via MkDocs:

```bash
pip install -e ".[docs]"
mkdocs serve
# Open http://localhost:8000
```

Pages: [Installation](docs/installation.md) | [Usage](docs/usage.md) | [API](docs/api.md) | [Indicators](docs/indicators.md) | [Architecture](docs/architecture.md) | [Deployment](docs/deployment.md) | [Contributing](docs/contributing.md)

## Ліцензія / License

MIT
