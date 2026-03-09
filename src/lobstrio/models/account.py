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
