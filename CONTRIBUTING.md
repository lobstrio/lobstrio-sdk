# Contributing to lobstrio-sdk

Thanks for your interest in contributing! This guide covers how to get started.

## Setup

```bash
git clone https://github.com/lobstrio/lobstrio-sdk.git
cd lobstrio-sdk
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Development Workflow

1. Create a branch from `main`
2. Make your changes
3. Run checks (see below)
4. Open a pull request

## Running Checks

```bash
# Unit tests
pytest

# Live integration tests (requires API token)
pytest tests/test_live.py -v

# Linting
ruff check src/ tests/

# Formatting
ruff format src/ tests/

# Type checking
mypy src/lobstrio/
```

All checks must pass before a PR can be merged.

## Code Style

- **Formatter/linter:** [Ruff](https://docs.astral.sh/ruff/) with `line-length = 120`
- **Type hints:** Required on all public APIs. The project uses `mypy --strict`.
- **Models:** Use `@dataclass` with a `from_api(cls, data)` classmethod for API response parsing.
- **Sync/async parity:** Every method on the sync client must have an equivalent on `AsyncLobstrClient`. Keep them in sync.

## Project Structure

```
src/lobstrio/
  __init__.py          # Public exports
  _base.py             # Token resolution, error handling
  _version.py          # Version string
  client.py            # Sync client + resource classes
  async_client.py      # Async client (mirrors client.py)
  exceptions.py        # APIError, AuthError, NotFoundError, RateLimitError
  pagination.py        # PageIterator, AsyncPageIterator
  models/
    account.py         # Account, AccountType, SyncStatus
    crawler.py         # Crawler, CrawlerParams
    delivery.py        # EmailDelivery, GoogleSheetDelivery, S3Delivery, ...
    run.py             # Run, RunStats
    squid.py           # Squid
    task.py            # Task, TaskStatus, AddTasksResult, UploadStatus
    user.py            # User, Balance
tests/
  conftest.py          # Shared fixtures (pytest-httpx mock client)
  test_live.py         # Live integration tests against real API
  test_*.py            # Unit tests per module
```

## Adding a New API Resource

1. **Model** — Add a dataclass in `src/lobstrio/models/` with `from_api()`.
2. **Sync resource** — Add a resource class in `client.py`, wire it in `LobstrClient.__init__`.
3. **Async resource** — Mirror the sync class in `async_client.py`.
4. **Exports** — Add to `__init__.py` and `__all__`.
5. **Tests** — Add unit tests (with `pytest-httpx` mocks) and live tests.
6. **README** — Document the new resource.

## Versioning

This project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

| Change type | Bump | Example |
|---|---|---|
| Bug fix, internal refactor | `PATCH` | 0.1.0 → 0.1.1 |
| New resource, new method, new model field | `MINOR` | 0.1.1 → 0.2.0 |
| Breaking change (renamed method, removed param, changed return type) | `MAJOR` | 0.2.0 → 1.0.0 |

### How to bump the version

1. Update the version string in `src/lobstrio/_version.py`:
   ```python
   __version__ = "0.2.0"
   ```
2. Add an entry to `CHANGELOG.md` under a new `## [0.2.0]` heading.
3. Commit with message: `release: v0.2.0`
4. Tag: `git tag v0.2.0`

### Pre-1.0 stability

While the version is `0.x.y`, minor releases may include breaking changes. After `1.0.0`, the public API (all names exported in `__init__.py`) is considered stable and breaking changes require a major bump.

### What counts as the public API

- All classes and functions listed in `__all__` in `src/lobstrio/__init__.py`
- Method signatures on `LobstrClient`, `AsyncLobstrClient`, and their resource classes
- Dataclass fields on model classes

Internal modules prefixed with `_` (e.g. `_base.py`, `_version.py`) are not part of the public API.

## Reporting Issues

Open an issue on GitHub with:
- What you expected
- What happened instead
- Steps to reproduce
- Python version and `lobstrio` version (`python -c "import lobstrio; print(lobstrio.__version__)"`)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
