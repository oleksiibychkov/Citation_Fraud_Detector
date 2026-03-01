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

## Індикатори / Indicators

| Indicator | Description | Threshold |
|-----------|-------------|-----------|
| SCR | Self-Citation Ratio | >0.25 warn, >0.40 high |
| MCR | Mutual Citation Ratio | >0.30 |
| CB | Citation Bottleneck | >0.30 |
| TA | Temporal Anomaly (Z-score) | >3σ |
| HTA | h-Index Temporal Analysis | anomalous dh/dt |

## Рівні впевненості / Confidence Levels

| Level | Score Range | Color |
|-------|-------------|-------|
| Normal | 0.0–0.2 | Green |
| Low | 0.2–0.4 | Yellow |
| Moderate | 0.4–0.6 | Orange |
| High | 0.6–0.8 | Red |
| Critical | 0.8–1.0 | Dark Red |

## Розробка / Development

```bash
# Run tests
pytest --cov=cfd

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Ліцензія / License

MIT
