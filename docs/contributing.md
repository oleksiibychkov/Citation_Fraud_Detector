# Contributing

## Development Setup

```bash
git clone <repo-url>
cd "Citation Fraud Detector"
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,api]"
cp .env.example .env
```

## Code Style

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Lint
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format
ruff format src/ tests/
```

Configuration is in `pyproject.toml`:

- Target: Python 3.11+
- Line length: 120
- Rules: E, F, W, I, N, UP, B, SIM

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=cfd --cov-report=term-missing

# Coverage must be >= 80%
pytest --cov=cfd --cov-fail-under=80

# Run specific test file
pytest tests/test_graph/test_scoring.py -v

# Run by keyword
pytest -k "test_scr" -v
```

## Project Structure

- `src/cfd/` — Source code
- `tests/` — Test suite (mirrors src structure)
- `locales/` — i18n translation files (en.json, ua.json)
- `docs/` — MkDocs documentation

## Adding a New Indicator

1. Implement the computation function in `src/cfd/graph/metrics.py` (or a new module)
2. Add normalization logic in `src/cfd/graph/scoring.py` (`_normalize_indicator`)
3. Add default weight in `DEFAULT_WEIGHTS`
4. Write tests in `tests/test_graph/`
5. Update algorithm version
6. Document in `docs/indicators.md`

## Adding a New Repository

1. Create the repository class in `src/cfd/db/repositories/`
2. Add tests in `tests/test_db/`
3. If needed, add the table schema to Supabase

## Pull Request Checklist

- [ ] All tests pass (`pytest`)
- [ ] Lint passes (`ruff check src/ tests/`)
- [ ] Coverage >= 80%
- [ ] New code has tests
- [ ] Changelog updated
