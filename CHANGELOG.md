# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
