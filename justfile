_default:
    @just --list

# Format code and sort imports
fmt:
    uv run ruff check --select I --fix src/ tests/
    uv run ruff format src/ tests/

# Run linter
lint:
    uv run ruff check src/ tests/

# Format + lint
check: fmt lint

# Run tests
test *args:
    uv run pytest tests/ -v {{ args }}

# Run full test matrix via tox
tox *args:
    uv run tox run {{ args }}
