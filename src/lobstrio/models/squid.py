from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Squid:
    """A scraping project container."""

    id: str
    name: str
    crawler: str
    crawler_name: str
    is_active: bool
    is_ready: bool
    concurrency: int
    to_complete: int | None
    last_run_status: str | None
    last_run_at: str | None
    total_runs: int
    export_unique_results: bool
    params: dict[str, Any]
    # The accounts linked to this squid, as the API returns them:
    # ``[{"id": <account hash>, "status": <status_code_info>}, ...]``, or ``[]``
    # when none are attached (the API forces this field to ``[]`` rather than
    # omitting it whenever the crawler needs an account — see
    # ``squids.attach_accounts()``). Empty for account-less crawlers too.
    accounts: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Squid:
        return cls(
            raw=data,
            id=data["id"],
            name=data.get("name", ""),
            crawler=data.get("crawler", ""),
            crawler_name=data.get("crawler_name", ""),
            is_active=data.get("is_active", False),
            is_ready=data.get("is_ready", False),
            concurrency=data.get("concurrency", 1),
            to_complete=data.get("to_complete"),
            last_run_status=data.get("last_run_status"),
            last_run_at=data.get("last_run_at"),
            total_runs=data.get("total_runs", 0),
            export_unique_results=data.get("export_unique_results", False),
            params=data.get("params", {}),
            accounts=data.get("accounts") or [],
        )
