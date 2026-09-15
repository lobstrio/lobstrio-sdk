from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Account:
    """A third-party platform account (e.g. LinkedIn, Twitter)."""

    id: str
    username: str
    type: str
    status_code_info: str | None
    status_code_description: str | None
    baseurl: str | None
    created_at: str | None
    updated_at: str | None
    last_synchronization_time: str | None
    squids: list[dict[str, Any]]
    params: dict[str, Any]
    # Added for account-attach auto-pick (see squids.attach_accounts()): `status`
    # is the API's raw status code as a string (e.g. "200" = healthy) — the exact
    # condition the run worker uses to decide whether an attached account is
    # usable. `resets_in`/`lock_time` surface whether the account is mid-run on
    # another squid (`params.lock_time` server-side) so a client can avoid
    # picking a busy account. All three are additive; nothing above changed.
    status: str | None = None
    resets_in: int | None = None
    lock_time: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Account:
        return cls(
            id=data["id"],
            username=data.get("username", ""),
            type=data.get("type", ""),
            status_code_info=data.get("status_code_info"),
            status_code_description=data.get("status_code_description"),
            baseurl=data.get("baseurl"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_synchronization_time=data.get("last_synchronization_time"),
            squids=data.get("squids", []),
            params=data.get("params", {}),
            status=data.get("status"),
            resets_in=data.get("resets_in"),
            lock_time=data.get("lock_time"),
        )


@dataclass
class AccountType:
    """An available account type."""

    name: str
    domain: str
    baseurl: str
    cookies: list[dict[str, Any]]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AccountType:
        return cls(
            name=data.get("name", ""),
            domain=data.get("domain", ""),
            baseurl=data.get("baseurl", ""),
            cookies=data.get("cookies", []),
        )


@dataclass
class SyncStatus:
    """Status of an account synchronization."""

    id: str
    status_code: str | None
    status_text: str | None
    account_hash: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SyncStatus:
        return cls(
            id=data.get("id", ""),
            status_code=data.get("status_code"),
            status_text=data.get("status_text"),
            account_hash=data.get("account_hash"),
        )
