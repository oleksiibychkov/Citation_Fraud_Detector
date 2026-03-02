# Citation Fraud Detector (CFD)

A multi-level system for detecting anomalous citation patterns in scientometric databases.

## Overview

CFD analyzes authors' citation networks to identify potential citation manipulation through 20 complementary indicators, graph analysis, and mathematical theorems. The system combines data from OpenAlex and Scopus APIs with network analysis techniques to produce fraud confidence scores.

## Key Features

- **20 citation fraud indicators** spanning self-citation, mutual citation, temporal, graph-based, and contextual signals
- **Dual data source support**: OpenAlex (free) and Scopus (API key required)
- **Graph analysis**: NetworkX and optional igraph engines for centrality, community detection, and clique analysis
- **3 mathematical theorems**: Perron-Frobenius, Ramsey-based clique, Benford's law
- **REST API** with authentication, rate limiting, and role-based access control
- **CLI** for single author and batch analysis
- **Visualization**: Plotly network graphs, timelines, heatmaps
- **Export**: JSON, CSV, PDF, HTML reports
- **Watchlist system** with periodic re-analysis and snapshot comparison
- **i18n**: Ukrainian and English interfaces

## Quick Start

```bash
pip install -e ".[dev]"
cfd analyze --author "Smith" --orcid "0000-0002-1234-5678" --source openalex
```

## Confidence Levels

| Level | Score Range | Interpretation |
|-------|-------------|----------------|
| Normal | 0.0 - 0.2 | No anomalies detected |
| Low | 0.2 - 0.4 | Minor irregularities |
| Moderate | 0.4 - 0.6 | Notable patterns requiring review |
| High | 0.6 - 0.8 | Significant manipulation indicators |
| Critical | 0.8 - 1.0 | Strong evidence of citation fraud |
