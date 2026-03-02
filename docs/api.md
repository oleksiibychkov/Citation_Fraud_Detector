# API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

All endpoints under `/api/v1/` require API key authentication via the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/authors/1/report
```

## Roles

| Role | Permissions |
|------|-------------|
| reader | Read-only access to reports, scores, indicators |
| analyst | Reader permissions + batch analysis, watchlist management |
| admin | All permissions + audit log access |

## Endpoints

### Health

#### `GET /health`

No authentication required.

```json
{"status": "ok", "version": "0.7.0"}
```

#### `GET /health/ready`

Returns database connectivity status.

```json
{"status": "ok", "database": "connected"}
```

### Authors

#### `GET /api/v1/authors/{author_id}/report`

Full analysis report for an author.

**Response** (200):
```json
{
  "author_id": 1,
  "full_name": "Oleksandr Ivanenko",
  "fraud_score": 0.35,
  "confidence_level": "low",
  "indicators": [...],
  "theorem_results": [...]
}
```

#### `GET /api/v1/authors/{author_id}/score`

Fraud score summary.

**Response** (200):
```json
{
  "author_id": 1,
  "score": 0.35,
  "confidence_level": "low",
  "algorithm_version": "5.0.0"
}
```

#### `GET /api/v1/authors/{author_id}/indicators`

All computed indicator values.

**Response** (200):
```json
{
  "author_id": 1,
  "indicators": [
    {"type": "SCR", "value": 0.15, "details": {...}},
    {"type": "MCR", "value": 0.08, "details": {...}}
  ]
}
```

#### `GET /api/v1/authors/{author_id}/graph`

Citation graph data for visualization.

**Response** (200):
```json
{
  "nodes": [{"id": "A1", "label": "Ivanenko"}],
  "edges": [{"source": "A1", "target": "A2", "weight": 3}]
}
```

### Batch Analysis

#### `POST /api/v1/batch`

Upload CSV for batch analysis. Requires `analyst` role.

**Request**: `multipart/form-data` with `file` field (CSV, max 50 entries).

**Response** (202):
```json
{
  "status": "accepted",
  "total": 5,
  "results": [...]
}
```

### Watchlist

#### `POST /api/v1/watchlist`

Add author to monitoring watchlist. Requires `analyst` role.

**Request**:
```json
{"author_db_id": 1, "reason": "High SCR detected"}
```

#### `GET /api/v1/watchlist`

List active watchlist entries.

#### `GET /api/v1/watchlist/{author_id}/history`

Snapshot history for a watched author.

### Audit

#### `GET /api/v1/audit`

Paginated audit log. Requires `admin` role.

**Query params**: `limit` (default 50), `offset` (default 0).

### Algorithm Version

#### `GET /api/v1/version`

Current algorithm version and indicator weights.

#### `GET /api/v1/version/history`

List of all algorithm versions.

## Error Responses

| Status | Meaning |
|--------|---------|
| 401 | Missing or invalid API key |
| 403 | Insufficient role permissions |
| 404 | Author not found |
| 422 | Validation error |
| 429 | Rate limit exceeded |
| 503 | Database unavailable |
