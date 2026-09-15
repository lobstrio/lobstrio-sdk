# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-09-15

### Added

- `squids.update(...)` gains `accounts` (sync + async): a list of account
  hashes to link, matching `POST /squids/{id}`. **The API field is
  full-replace** — sending `accounts` deletes every existing link first, so
  a naive call detaches whatever was already attached. `accounts=None` (the
  default, like every other `update()` field) leaves accounts untouched.
- `squids.attach_accounts(squid_id, accounts, *, replace=False)` (sync +
  async): the safe entry point for linking an account without dropping the
  others. By default it reads the squid's current `accounts` first and sends
  the union (de-duplicated); `replace=True` sends exactly the given list,
  including `[]` to detach everything. Added alongside `update(accounts=...)`
  rather than instead of it: `update()` stays a thin, literal mirror of the
  API body for callers that already track the full desired list (or want to
  detach deliberately), while `attach_accounts()` is what a client reaches
  for by default, so the read-merge-write dance for "add one account" isn't
  duplicated in every downstream caller (CLI, MCP). The read and the write
  are two separate requests, not an atomic compare-and-set — the API offers
  no such primitive — so a concurrent attach on the same squid between them
  can still race and drop one addition.
- `Squid.accounts`: the squid's linked accounts as the API returns them
  (`[{"id": <account hash>, "status": <status_code_info>}, ...]`), previously
  reachable only via `.raw["accounts"]`.
- `Account.status`, `Account.resets_in`, `Account.lock_time`: the fields a
  client needs to auto-pick a healthy, unlocked account —
  `status == "200"` is the exact condition the run worker itself checks
  before accepting an attached account (`matrix/worker/consumer.py`);
  `resets_in`/`lock_time` show whether the account is currently locked by a
  run on another squid. Previously dropped by `Account.from_api`.
- `Crawler.account_type`: the account type slug a crawler needs (e.g.
  `linkedin-sync`, `sales-nav-sync`), or `None` if it needs no account.
  Added alongside the existing `Crawler.account: bool`, which is unchanged,
  so nothing that already checks `if crawler.account:` breaks. Two LinkedIn
  crawlers can need two different account types; matching on this slug
  (not on the crawler's name) is what makes auto-pick safe — see
  `attach_accounts()` above.

## [0.6.0] - 2026-09-10

### Added

- `accounts.iter()` (sync + async) — iterate every connected account across
  pages, matching the `iter()` already available on crawlers, squids, tasks,
  runs, and results. `accounts.list()` returns only a single page (50 by
  default), so resolving an account by username silently missed anything past
  the first page.

## [0.5.0] - 2026-09-09

### Added

- `squids.estimate(squid_id)` (sync + async) — authoritative pre-run cost/result
  estimate via `POST /squid/estimate`. Returns the API's real numbers (per-service
  credit/result breakdown, `total_credits`, `estimated_time`, projected
  `max_results`, `tasks` preview). The squid must exist with at least one task.

- `squids.update(...)` gains the remaining documented `POST /squids/{id}` fields
  (sync + async): `is_active`, `to_complete`, `no_line_breaks`, `cron_expression`,
  `timezone`. Only the fields you pass are sent.

## [0.4.1] - 2026-09-08

### Added

- Default `User-Agent: lobstrio-sdk/<version>` on every request. The API uses it
  to attribute requests — e.g. it now records a squid's creation source (`sdk`)
  from this header. A caller that passes `user_agent=` still has it sent verbatim
  (a downstream client such as an MCP server owns its own identity). Previously no
  `User-Agent` was sent unless the caller passed one.

## [0.4.0] - 2026-09-07

### Added

- `max_pages` on `PageIterator` / `AsyncPageIterator` (and thus every `iter()`
  method via `**kwargs`) — cap the number of pages walked as a safety limit
  against a runaway `total_pages`. Defaults to `None` (walk every page), so
  existing `iter()` behaviour is unchanged.

- `py.typed` marker — the package now advertises its inline type hints (PEP 561),
  so downstream type-checkers no longer skip `lobstrio`.

### Fixed

- `iter()` now terminates on a bare-list response (an endpoint returning a plain
  JSON array instead of a `{data, total_pages, ...}` envelope): it is treated as
  a single page rather than being re-fetched forever.

## [0.3.0] - 2026-09-07

### Added

- `runs.call()` — start a run and wait for it to finish in one call
  (`squid=`, `poll_interval=`, `timeout=`, `callback=`), returning the finished
  `Run` (sync + async); mirrors `start()`/`call()` semantics
- `runs.wait()` gains a `timeout` (seconds); raises the new `RunTimeout`
  (a `TimeoutError` subclass, exported from the package) if the run doesn't
  finish in time. `timeout=None` keeps the wait-forever default. A timeout does
  not abort the run — it keeps running server-side and can be re-attached with
  `wait()` / `get()`
- `raw` attribute on `Crawler`, `CrawlerParams`, `Run`, `RunStats`, `Squid`, and
  `Balance` — the untouched API payload, for callers that need a field the
  dataclass drops or renames
- `crawlers.iter()` — paginated iteration over the full crawler catalog (sync + async)
- `results.page()` — one page of results with the full pagination envelope
  (`total_results`, `page`, `total_pages`, `next`, `data`), filterable by
  `squid` / `run` / `task` (sync + async)
- `results.list()` / `results.iter()` now accept `run` and `task` filters, not just `squid`
- `user_agent=` and `transport=` parameters on `LobstrClient` and `AsyncLobstrClient`

### Fixed

- `CrawlerParams.from_api()` no longer mutates its input payload

## [0.2.1] - 2026-03-17

### Added

- Pagination support for `accounts.list()` (`limit`, `page` parameters)
- `crawlers.attributes()` method for result column metadata

### Fixed

- All ruff lint errors and mypy strict-mode errors

## [0.2.0] - 2026-03-13

### Changed

- Renamed PyPI package from `lobstrio` to `lobstrio-sdk` (import name `lobstrio` unchanged)
- Updated install instructions in README and CONTRIBUTING

### Added

- Crawler detail fields: `default_worker_stats`, `email_worker_stats`, `input_params`, `result_fields`

## [0.1.0] - 2026-03-09

### Added

- Initial release of the Lobstr.io Python SDK
- Sync client (`LobstrClient`) and async client (`AsyncLobstrClient`)
- Automatic token resolution from `LOBSTR_TOKEN` env var or `~/.config/lobstr/config.toml`
- Resource namespaces:
  - `crawlers` — list, get, params
  - `squids` — list, iter, get, create, update, empty, delete
  - `tasks` — list, iter, get, add, upload (CSV/TSV), upload_status, delete
  - `runs` — start, list, iter, get, stats, tasks, abort, download_url, download, wait
  - `results` — list, iter
  - `accounts` — list, get, types, sync, sync_status, update, delete
  - `delivery` — email, google_sheet, s3, webhook, sftp (configure + test)
- Typed dataclass models for all API responses
- Lazy auto-pagination with `PageIterator` and `AsyncPageIterator`
- Typed exception hierarchy: `APIError`, `AuthError`, `NotFoundError`, `RateLimitError`
- Context manager support (`with LobstrClient() as client:`)
- 75 unit tests and 21 live integration tests
