from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class User:
    """Lobstr.io user profile."""

    first_name: str
    last_name: str
    email: str
    is_staff: bool
    plan: list[dict[str, Any]]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> User:
        return cls(
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            is_staff=data.get("is_staff", False),
            plan=data.get("plan", []),
        )


@dataclass
class Balance:
    """Account credit balance."""

    available: int
    consumed: int
    used_slots: int
    total_available_slots: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Balance:
        return cls(
            available=data.get("available", 0),
            consumed=data.get("consumed", 0),
            used_slots=data.get("used_slots", 0),
            total_available_slots=data.get("total_available_slots", 0),
        )
