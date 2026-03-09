from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _resolve_credits(value: Any) -> int | None:
    """Normalize credits fields that can be int, dict, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        v = value.get("current", value.get("legacy"))
        return int(v) if v is not None else None
    return None


@dataclass
class Crawler:
    """A scraping crawler (template)."""

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
    def from_api(cls, data: dict[str, Any]) -> Crawler:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            description=data.get("description"),
            credits_per_row=_resolve_credits(data.get("credits_per_row")),
            credits_per_email=_resolve_credits(data.get("credits_per_email")),
            max_concurrency=data.get("max_concurrency", 1),
            account=bool(data.get("account")),
            has_email_verification=data.get("has_email_verification", False),
            is_public=data.get("is_public", True),
            is_premium=data.get("is_premium", False),
            is_available=data.get("is_available", True),
            has_issues=data.get("has_issues", False),
            rank=data.get("rank"),
        )


@dataclass
class CrawlerParams:
    """Parameters accepted by a crawler."""

    task_params: dict[str, Any]
    squid_params: dict[str, Any]
    functions: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CrawlerParams:
        task = data.get("task", {})
        squid = data.get("squid", {})
        # Functions may be nested inside squid params or at top level
        functions = squid.pop("functions", {}) if isinstance(squid, dict) else {}
        return cls(
            task_params=task,
            squid_params=squid,
            functions=functions,
        )
