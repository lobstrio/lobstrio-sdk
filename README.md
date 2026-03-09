# lobstrio

Python SDK for the [Lobstr.io](https://lobstr.io) API — web scraping automation platform.

- Sync + async clients with the same API surface
- Typed dataclass models for all responses
- Lazy auto-pagination
- Automatic token resolution from CLI config or environment

## Installation

```bash
pip install lobstrio
```

Requires Python 3.10+. The only runtime dependency is [httpx](https://www.python-httpx.org/).

## Authentication

The client resolves your API token in this order:

1. **Explicit** — `LobstrClient(token="your-token")`
2. **Environment variable** — `LOBSTR_TOKEN`
3. **CLI config file** — `~/.config/lobstr/config.toml` (same file used by `lobstr` CLI)

If you already have the CLI set up, the SDK works with no configuration:

```python
from lobstrio import LobstrClient

client = LobstrClient()  # token auto-resolved
user = client.me()
print(user.email)
```

## Quick Start

```python
from lobstrio import LobstrClient

with LobstrClient() as client:
    # Account info
    user = client.me()
    balance = client.balance()
    print(f"{user.email} — {balance.credits} credits")

    # List crawlers
    for crawler in client.crawlers.list():
        print(f"{crawler.name} ({crawler.id})")

    # Create a squid, add tasks, run it
    squid = client.squids.create("google-maps-scraper", name="My Scrape")
    client.squids.update(squid.id, params={"language": "English (United States)"})
    client.tasks.add(squid=squid.id, tasks=[{"url": "https://maps.google.com/..."}])
    run = client.runs.start(squid=squid.id)

    # Wait for completion with progress callback
    final = client.runs.wait(run.id, callback=lambda s: print(f"{s.percent_done}%"))

    # Download results
    client.runs.download(run.id, "results.csv")
```

## Resources

All API operations are organized under resource namespaces on the client.

### User

```python
user = client.me()           # User profile
balance = client.balance()   # Account balance (credits, subscription)
```

### Crawlers

Browse the available crawler templates.

```python
crawlers = client.crawlers.list()           # All crawlers
crawler = client.crawlers.get("crawler-id") # Single crawler
params = client.crawlers.params("crawler-id")  # Parameter schema
```

**Models:** `Crawler` (id, name, credits_per_row, description, logo), `CrawlerParams` (task_params, squid_params, functions)

### Squids

A squid is an instance of a crawler with your configuration.

```python
# List & iterate
squids = client.squids.list(limit=50, page=1)
for squid in client.squids.iter():     # auto-paginate all squids
    print(squid.name)

# CRUD
squid = client.squids.create("crawler-id", name="My Project")
squid = client.squids.get("squid-id")
squid = client.squids.update("squid-id", name="Renamed", concurrency=2,
                              params={"language": "English"})
client.squids.empty("squid-id")        # remove all tasks
client.squids.delete("squid-id")
```

**Model:** `Squid` (id, name, crawler, is_active, concurrency, params, created_at, ...)

### Tasks

Tasks are the input URLs/parameters fed into a squid.

```python
# List & iterate
tasks = client.tasks.list(squid="squid-id")
for task in client.tasks.iter(squid="squid-id"):
    print(task.id)

# Add tasks
result = client.tasks.add(
    squid="squid-id",
    tasks=[
        {"url": "https://maps.google.com/maps?cid=123"},
        {"url": "https://maps.google.com/maps?cid=456"},
    ],
)
print(f"Added {len(result.tasks)}, {result.duplicated_count} duplicates")

# Upload from CSV/TSV
resp = client.tasks.upload(squid="squid-id", file="tasks.csv")
status = client.tasks.upload_status(resp["id"])

# Get & delete
task = client.tasks.get("task-hash")
client.tasks.delete("task-hash")
```

**Models:** `Task` (id, is_active, params, status, created_at), `AddTasksResult`, `UploadStatus`, `UploadMeta`

### Runs

Start, monitor, and download scraping runs.

```python
# Start a run
run = client.runs.start(squid="squid-id")

# List runs
runs = client.runs.list(squid="squid-id")
for run in client.runs.iter(squid="squid-id"):
    print(run.id, run.status)

# Monitor
run = client.runs.get("run-id")
stats = client.runs.stats("run-id")
print(f"{stats.percent_done}% done, {stats.total_results} results")

# Wait for completion (blocking, with optional progress callback)
final = client.runs.wait("run-id", poll_interval=5.0,
                          callback=lambda s: print(f"{s.percent_done}%"))

# Download results
url = client.runs.download_url("run-id")   # signed S3 URL
client.runs.download("run-id", "output.csv")  # download to file

# Abort
client.runs.abort("run-id")

# Tasks within a run
tasks = client.runs.tasks("run-id")
```

**Models:** `Run` (id, squid, status, total_results, created_at, ...), `RunStats` (is_done, percent_done, total_results, ...)

### Results

Fetch scraped results for a squid.

```python
results = client.results.list(squid="squid-id", page_size=100)

# Auto-paginate all results
for row in client.results.iter(squid="squid-id"):
    print(row)  # dict
```

Results are returned as plain `dict` objects (the schema depends on the crawler).

### Accounts

Manage connected platform accounts (e.g. Google, LinkedIn).

```python
accounts = client.accounts.list()
account = client.accounts.get("account-id")
types = client.accounts.types()     # available account types

# Sync account with cookies
resp = client.accounts.sync(type="google", cookies={"SID": "...", "HSID": "..."})
status = client.accounts.sync_status(resp["id"])

# Update limits
client.accounts.update("account-id", type="google", params={"daily_limit": 100})

# Delete
client.accounts.delete("account-id")
```

**Models:** `Account` (id, name, type, is_active, ...), `AccountType` (id, name, display_name), `SyncStatus` (state, meta)

### Delivery

Configure how results are delivered after each run.

```python
# Email
client.delivery.email("squid-id", email="you@example.com")
client.delivery.test_email(email="you@example.com")

# Google Sheets
client.delivery.google_sheet("squid-id", url="https://docs.google.com/spreadsheets/d/...", append=True)
client.delivery.test_google_sheet(url="https://docs.google.com/spreadsheets/d/...")

# Webhook
client.delivery.webhook("squid-id", url="https://your-server.com/hook",
                         on_done=True, on_error=True)
client.delivery.test_webhook(url="https://your-server.com/hook")

# S3
client.delivery.s3("squid-id", bucket="my-bucket", target_path="scrapes/",
                    aws_access_key="...", aws_secret_key="...")
client.delivery.test_s3(bucket="my-bucket")

# SFTP
client.delivery.sftp("squid-id", host="ftp.example.com", username="user",
                      password="pass", directory="/uploads")
client.delivery.test_sftp(host="ftp.example.com", username="user",
                           password="pass", directory="/uploads")
```

**Models:** `EmailDelivery`, `GoogleSheetDelivery`, `S3Delivery`, `WebhookDelivery`, `SFTPDelivery`

## Async Client

The async client mirrors the sync API exactly, using `async/await`:

```python
from lobstrio import AsyncLobstrClient

async def main():
    async with AsyncLobstrClient() as client:
        user = await client.me()
        print(user.email)

        crawlers = await client.crawlers.list()
        for c in crawlers:
            print(c.name)

        squid = await client.squids.create("crawler-id", name="Async Scrape")
        await client.tasks.add(squid=squid.id, tasks=[{"url": "..."}])
        run = await client.runs.start(squid=squid.id)
        final = await client.runs.wait(run.id)
        await client.runs.download(run.id, "results.csv")
```

All resource methods (`client.crawlers.*`, `client.squids.*`, etc.) work identically — just add `await`.

## Pagination

Resources that return lists support two patterns:

### Single page (`.list()`)

Returns one page of results. Use `limit` and `page` to control:

```python
page1 = client.squids.list(limit=10, page=1)
page2 = client.squids.list(limit=10, page=2)
```

### Auto-pagination (`.iter()`)

Returns a lazy `PageIterator` that fetches pages on demand:

```python
for squid in client.squids.iter(limit=50):
    print(squid.name)  # automatically fetches next pages
```

The async client provides `AsyncPageIterator` for use with `async for`.

## Error Handling

All API errors raise typed exceptions with `status_code`, `message`, and `body`:

```python
from lobstrio import LobstrClient, AuthError, NotFoundError, RateLimitError, APIError

try:
    client.squids.get("nonexistent")
except NotFoundError as e:
    print(f"Not found: {e.message}")
except AuthError:
    print("Invalid or expired token")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except APIError as e:
    print(f"API error [{e.status_code}]: {e.message}")
```

| Exception | HTTP Status | When |
|---|---|---|
| `AuthError` | 401 | Invalid or missing token |
| `NotFoundError` | 404 | Resource doesn't exist |
| `RateLimitError` | 429 | Too many requests (has `retry_after`) |
| `APIError` | 4xx/5xx | All other API errors |

## Development

```bash
# Clone and install
git clone https://github.com/lobstrio/lobstrio-sdk.git
cd lobstrio-sdk
pip install -e ".[dev]"

# Run unit tests
pytest

# Run live tests (requires API token)
pytest tests/test_live.py -v

# Lint & type check
ruff check src/ tests/
mypy src/lobstrio/
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
