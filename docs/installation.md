# Installation

## Requirements

- Python 3.11+
- Supabase account (for database persistence)
- Optional: Neo4j 5.x (for persistent graph storage)
- Optional: Scopus API key (for Scopus data source)

## Basic Installation

```bash
git clone <repo-url>
cd "Citation Fraud Detector"

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -e ".[dev]"
```

## Optional Dependencies

```bash
# REST API server
pip install -e ".[api]"

# Neo4j graph database
pip install -e ".[neo4j]"

# igraph for large graphs (>50K nodes)
pip install -e ".[igraph]"

# Visualization (Plotly)
pip install -e ".[viz]"

# PDF report export
pip install -e ".[pdf]"

# HTML report export
pip install -e ".[html]"

# Streamlit dashboard
pip install -e ".[dashboard]"

# Neural similarity (sentence-transformers)
pip install -e ".[neural]"

# All optional dependencies
pip install -e ".[all]"
```

## Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required: Supabase
CFD_SUPABASE_URL=https://your-project.supabase.co
CFD_SUPABASE_KEY=your-anon-key

# Optional: Scopus
CFD_SCOPUS_API_KEY=your-scopus-key

# Optional: Neo4j
CFD_NEO4J_URI=bolt://localhost:7687
CFD_NEO4J_USER=neo4j
CFD_NEO4J_PASSWORD=your-password

# Optional: API
CFD_API_HOST=0.0.0.0
CFD_API_PORT=8000
CFD_API_KEYS=key1:admin,key2:analyst,key3:reader
```

## Verify Installation

```bash
python -c "from cfd import __version__; print(__version__)"
pytest --cov=cfd
```
