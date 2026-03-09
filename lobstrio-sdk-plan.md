# lobstrio-sdk — Python SDK Plan

## Overview

A standalone Python SDK for the Lobstr.io API. Will later replace the raw HTTP client in `lobstrio-cli`.

**Package name**: `lobstrio`
**Import**: `from lobstrio import LobstrClient`
**Repo**: `lobstrio/lobstrio-sdk`

---

## Design Principles

1. **Thin wrapper, not a framework** — mirror the API closely, don't over-abstract
2. **Typed everything** — dataclasses for all models, full type hints, IDE-friendly
3. **Sync + async** — sync by default, async variant available
4. **Pagination as iterators** — auto-paginate with lazy iterators, or fetch single pages
5. **Zero CLI dependency** — pure SDK, no typer/rich/display logic

---

## Project Structure

```
lobstrio-sdk/
  src/lobstrio/
    __init__.py           # Public API: LobstrClient, AsyncLobstrClient
    client.py             # Sync HTTP client
    async_client.py       # Async HTTP client
    _base.py              # Shared client logic (auth, error handling, base URL)
    models/
      __init__.py
      crawler.py          # Crawler, CrawlerParams
      squid.py            # Squid
      task.py             # Task, TaskStatus, UploadResult
      run.py              # Run, RunStats
      result.py           # Result
      user.py             # User, Balance
    exceptions.py         # AuthError, NotFoundError, RateLimitError, APIError
    pagination.py         # PageIterator, AsyncPageIterator
    _version.py           # Version string
  tests/
    conftest.py
    test_client.py
    test_async_client.py
    test_models.py
    test_pagination.py
    test_crawlers.py
    test_squids.py
    test_tasks.py
    test_runs.py
    test_results.py
  pyproject.toml
  README.md
  LICENSE                 # Apache 2.0
  CHANGELOG.md
```

---

## API Surface

### Client Initialization

```python
from lobstrio import LobstrClient

# Basic
client = LobstrClient(token="your-api-token")

# With options
client = LobstrClient(
    token="your-api-token",
    base_url="https://api.lobstr.io/v1/",  # default
    timeout=30.0,                           # default
)

# From environment variable (LOBSTR_TOKEN)
client = LobstrClient.from_env()

# Async
from lobstrio import AsyncLobstrClient
async_client = AsyncLobstrClient(token="...")
```

### User / Account

```python
user = client.me()                    # -> User
user.email                            # "user@example.com"
user.first_name
user.plan                             # [{"name": "Pro", "status": "active"}]

balance = client.balance()            # -> Balance
balance.available                     # 5000
balance.consumed                      # 1200
balance.used_slots                    # 2
balance.total_available_slots         # 5
```

### Crawlers

```python
# List all crawlers
crawlers = client.crawlers.list()           # -> list[Crawler]

# Get single crawler by ID
crawler = client.crawlers.get("4734d096...")  # -> Crawler

# Access fields
crawler.id
crawler.name                                  # "Google Maps Leads Scraper"
crawler.slug                                  # "google-maps-leads-scraper"
crawler.credits_per_row                       # 3 (resolved from dict if needed)
crawler.max_concurrency                       # 5
crawler.is_premium                            # False
crawler.is_available                          # True

# Get crawler parameters
params = client.crawlers.params("4734d096...")  # -> CrawlerParams
params.task_params                               # {"url": {"type": "string", "required": True, ...}}
params.squid_params                              # {"max_results": {"default": 100, ...}}
params.functions                                 # {"email_finder": {"credits_per_function": 5, ...}}
```

### Squids

```python
# List squids (paginated)
squids = client.squids.list()                        # -> list[Squid] (first page)
squids = client.squids.list(limit=10, page=2)        # -> list[Squid]

# Iterate all pages automatically
for squid in client.squids.iter():                   # -> Iterator[Squid]
    print(squid.name)

# Get single squid
squid = client.squids.get("abc123...")               # -> Squid

# Create squid
squid = client.squids.create(
    crawler="4734d096...",                            # crawler ID
    name="My Scraper",                                # optional
)

# Update squid
squid = client.squids.update("abc123...",
    concurrency=5,
    params={"max_results": 200},
    name="Renamed",
)

# Empty squid (remove all tasks)
result = client.squids.empty("abc123...")             # -> {"deleted_count": 10}

# Delete squid
client.squids.delete("abc123...")
```

### Tasks

```python
# List tasks for a squid
tasks = client.tasks.list(squid="abc123...")                    # -> list[Task]
tasks = client.tasks.list(squid="abc123...", limit=10, page=2)

# Iterate all pages
for task in client.tasks.iter(squid="abc123..."):
    print(task.params)

# Get single task
task = client.tasks.get("task_hash...")                         # -> Task

# Add tasks
result = client.tasks.add(
    squid="abc123...",
    tasks=[{"url": "https://example.com"}, {"url": "https://other.com"}],
)
# result.tasks -> list of created tasks
# result.duplicated_count -> 0

# Upload CSV
upload = client.tasks.upload(squid="abc123...", file="tasks.csv")
# upload.id -> "upload_id"

# Check upload status
status = client.tasks.upload_status("upload_id")               # -> UploadStatus
status.state                                                    # "completed"
status.meta.valid                                               # 100
status.meta.inserted                                            # 95
status.meta.duplicates                                          # 5

# Delete task
client.tasks.delete("task_hash...")
```

### Runs

```python
# Start a run
run = client.runs.start(squid="abc123...")                     # -> Run

# List runs for a squid
runs = client.runs.list(squid="abc123...")                     # -> list[Run]
runs = client.runs.list(squid="abc123...", limit=10, page=2)

# Get run details
run = client.runs.get("run_hash...")                           # -> Run
run.status                                                     # "finished"
run.total_results                                              # 500
run.duration                                                   # 120.5
run.credit_used                                                # 50

# Get run stats (real-time)
stats = client.runs.stats("run_hash...")                       # -> RunStats
stats.percent_done                                             # "75%"
stats.is_done                                                  # False
stats.eta                                                      # "2m 30s"

# List tasks in a run
tasks = client.runs.tasks("run_hash...")                       # -> list[Task]

# Abort a run
client.runs.abort("run_hash...")

# Get download URL
download = client.runs.download_url("run_hash...")             # -> str (S3 URL)

# Download to file
client.runs.download("run_hash...", dest="results.csv")

# Poll until done (convenience)
run = client.runs.wait(
    "run_hash...",
    poll_interval=3.0,                                         # default: 3s
    callback=lambda stats: print(stats.percent_done),          # optional progress callback
)
```

### Results

```python
# Fetch results
results = client.results.list(squid="abc123...")                # -> list[dict]
results = client.results.list(squid="abc123...", page=2, page_size=100)

# Iterate all pages
for result in client.results.iter(squid="abc123..."):
    print(result)
```

---

## Models

All models are `dataclass`es with `from_api()` classmethods that handle API quirks (e.g., `credits_per_row` being a dict or int).

```python
@dataclass
class Crawler:
    id: str
    name: str
    slug: str
    description: str | None
    credits_per_row: int | None
    credits_per_email: int | None
    max_concurrency: int
    account: bool
    has_email_verification: bool
    is_public: bool
    is_premium: bool
    is_available: bool
    has_issues: bool
    rank: int | None

    @classmethod
    def from_api(cls, data: dict) -> "Crawler":
        # Handle credits_per_row being dict or int
        cpr = data.get("credits_per_row")
        if isinstance(cpr, dict):
            cpr = cpr.get("current", cpr.get("legacy"))
        ...
```

Similar pattern for `Squid`, `Task`, `Run`, `RunStats`, `User`, `Balance`.

---

## Pagination

```python
class PageIterator(Iterator[T]):
    """Lazy iterator that auto-fetches next pages."""

    def __init__(self, fetch_page, model_cls, **params):
        self._fetch = fetch_page
        self._model = model_cls
        self._params = params
        self._page = 1
        self._buffer = []
        self._done = False
```

- `.list()` returns a single page (default first page)
- `.iter()` returns a `PageIterator` that fetches pages on demand
- Async variant: `AsyncPageIterator` with `async for`

---

## Error Handling

```python
from lobstrio.exceptions import AuthError, NotFoundError, RateLimitError, APIError

try:
    client.squids.get("bad_id")
except NotFoundError:
    print("Squid not found")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except AuthError:
    print("Invalid API token")
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

Exception hierarchy:
```
APIError (base)
  ├── AuthError (401)
  ├── NotFoundError (404)
  └── RateLimitError (429, includes retry_after)
```

---

## Implementation Phases

### Phase 1: Core (MVP)
- [ ] Project scaffolding (pyproject.toml, structure, CI)
- [ ] Exception classes
- [ ] Base HTTP client (sync only, auth, error handling)
- [ ] Models: User, Balance, Crawler, CrawlerParams
- [ ] `client.me()`, `client.balance()`
- [ ] `client.crawlers.list()`, `.get()`, `.params()`
- [ ] Tests for all above

### Phase 2: CRUD Operations
- [ ] Models: Squid, Task, Run, RunStats
- [ ] `client.squids.*` (list, get, create, update, empty, delete)
- [ ] `client.tasks.*` (list, get, add, delete, upload, upload_status)
- [ ] `client.runs.*` (start, list, get, stats, tasks, abort, download_url, download)
- [ ] `client.results.*` (list)
- [ ] Pagination iterators
- [ ] Tests for all above

### Phase 3: Convenience & Async
- [ ] `client.runs.wait()` — poll until complete with callback
- [ ] `AsyncLobstrClient` with same API surface
- [ ] `AsyncPageIterator`
- [ ] Tests for async

### Phase 4: Integration
- [ ] Replace raw HTTP client in `lobstrio-cli` with SDK
- [ ] Keep resolution logic (slug/name/hash) in CLI, not SDK
- [ ] Publish to PyPI as `lobstrio`

---

## Dependencies

- `httpx` — sync + async HTTP (already used in CLI)
- No other runtime dependencies

Dev dependencies:
- `pytest`, `pytest-asyncio`, `pytest-httpx`
- `ruff` — linting
- `mypy` — type checking

---

## Key Decisions

1. **Resolution stays in CLI** — the SDK works with raw IDs only. Slug/name/hash resolution is a CLI concern, not an SDK concern.
2. **Credits fields normalized** — `credits_per_row` and `credits_per_email` are always `int | None` in models, never dicts. The `from_api()` classmethod handles the dict→int conversion.
3. **No automatic retry on rate limit** — raise `RateLimitError` with `retry_after` and let the caller decide. The CLI can implement its own retry logic.
4. **Download streams to disk** — `client.runs.download()` streams directly to a file path, not to memory.
5. **Resource namespacing** — `client.crawlers.*`, `client.squids.*` etc. Groups related operations logically without deep nesting.
