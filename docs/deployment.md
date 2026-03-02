# Deployment

## Docker

### Build and Run

```bash
docker build -t cfd-api .
docker run -p 8000:8000 --env-file .env cfd-api
```

### Docker Compose

The included `docker-compose.yml` runs the API with Neo4j:

```bash
docker-compose up -d
```

Services:

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | CFD REST API |
| neo4j | 7474, 7687 | Neo4j Browser + Bolt |

### Environment Variables

```env
# Required
CFD_SUPABASE_URL=https://your-project.supabase.co
CFD_SUPABASE_KEY=your-anon-key

# Optional — API
CFD_API_HOST=0.0.0.0
CFD_API_PORT=8000
CFD_API_KEYS=key1:admin,key2:analyst
CFD_API_CORS_ORIGINS=http://localhost:3000

# Optional — Neo4j
CFD_NEO4J_URI=bolt://neo4j:7687
CFD_NEO4J_USER=neo4j
CFD_NEO4J_PASSWORD=changeme

# Optional — Scopus
CFD_SCOPUS_API_KEY=your-scopus-key
```

## Render.com

1. Create a new **Web Service** from the repository
2. Set **Build Command**: `pip install .[api]`
3. Set **Start Command**: `uvicorn cfd.api.app:create_app --factory --host 0.0.0.0 --port $PORT`
4. Add environment variables in the Render dashboard
5. Deploy

## Backup Scripts

### PostgreSQL (Supabase)

```bash
scripts/backup_postgres.sh
```

Creates a timestamped pg_dump of the Supabase database.

### Neo4j

```bash
scripts/backup_neo4j.sh
```

Creates a timestamped neo4j-admin dump.

## CI/CD

The project includes GitHub Actions workflows:

- **ci.yml**: Lint + test on every push/PR to main
- **deploy.yml**: Build Docker image on tag push, run smoke test
- **watchlist_cron.yml**: Weekly re-analysis of watchlist authors (Monday 06:00 UTC)

## Monitoring

- `/health` — Basic health check (no auth required)
- `/health/ready` — Database connectivity check
- API responses include `X-Request-ID` for tracing
- Audit log tracks all operations with timestamps
