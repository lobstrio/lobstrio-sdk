# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
