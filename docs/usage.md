# Usage

## CLI Commands

### Single Author Analysis

```bash
# By ORCID (OpenAlex)
cfd analyze --author "Ivanenko" --orcid "0000-0002-1234-5678" --source openalex

# By Scopus ID
cfd analyze --author "Ivanenko" --scopus-id "57200000001" --source scopus

# Auto source selection with JSON export
cfd analyze --author "Ivanenko" --orcid "0000-0002-1234-5678" --output report.json

# English interface
cfd --lang en analyze --author "Smith" --orcid "0000-0002-1234-5678"
```

### Batch Analysis

```bash
cfd batch --batch authors.csv --source openalex --output-dir ./reports
```

CSV format:

```csv
surname,scopus_id,orcid
Ivanenko,57200000001,0000-0002-1234-5678
Petrenko,,0000-0003-9876-5432
```

### Watchlist

```bash
# Add author to watchlist
cfd watchlist add --author "Ivanenko" --scopus-id "57200000001"

# List active watchlist entries
cfd watchlist list

# Re-analyze all watchlist authors
cfd watchlist reanalyze
```

### Export Formats

The `--output` flag determines the export format based on file extension:

```bash
cfd analyze --author "Smith" --orcid "..." --output report.json   # JSON
cfd analyze --author "Smith" --orcid "..." --output report.csv    # CSV
cfd analyze --author "Smith" --orcid "..." --output report.pdf    # PDF
cfd analyze --author "Smith" --orcid "..." --output report.html   # HTML
```

## REST API

Start the API server:

```bash
cfd-api
# or
uvicorn cfd.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

### Authentication

All API endpoints require an `X-API-Key` header. Keys are configured via `CFD_API_KEYS` environment variable:

```
CFD_API_KEYS=mykey1:admin,mykey2:analyst,mykey3:reader
```

### Endpoints

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/health` | - | Health check |
| GET | `/api/v1/authors/{id}/report` | reader+ | Full analysis report |
| GET | `/api/v1/authors/{id}/score` | reader+ | Fraud score only |
| GET | `/api/v1/authors/{id}/indicators` | reader+ | All indicator values |
| GET | `/api/v1/authors/{id}/graph` | reader+ | Citation graph data |
| POST | `/api/v1/batch` | analyst+ | Batch CSV analysis |
| POST | `/api/v1/watchlist` | analyst+ | Add to watchlist |
| GET | `/api/v1/watchlist` | reader+ | List watchlist |
| GET | `/api/v1/watchlist/{id}/history` | reader+ | Snapshot history |
| GET | `/api/v1/audit` | admin | Audit log |
| GET | `/api/v1/version` | reader+ | Algorithm version |

Interactive API docs available at `/api/docs` (Swagger) and `/api/redoc`.
