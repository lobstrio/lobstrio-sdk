from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TaskStatus:
    """Status info embedded in a task."""

    status: str
    total_results: int
    total_pages: int
    done_reason: str | None
    has_errors: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TaskStatus:
        return cls(
            status=data.get("status", ""),
            total_results=data.get("total_results", 0),
            total_pages=data.get("total_pages", 0),
            done_reason=data.get("done_reason"),
            has_errors=data.get("has_errors", False),
        )


@dataclass
class Task:
    """A scraping task within a squid."""

    id: str
    is_active: bool
    params: dict[str, Any]
    status: TaskStatus | None
    created_at: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Task:
        status_data = data.get("status")
        return cls(
            id=data.get("id", data.get("hash_value", "")),
            is_active=data.get("is_active", True),
            params=data.get("params", {}),
            status=TaskStatus.from_api(status_data) if isinstance(status_data, dict) else None,
            created_at=data.get("created_at"),
        )


@dataclass
class AddTasksResult:
    """Result of adding tasks to a squid."""

    tasks: list[Task]
    duplicated_count: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AddTasksResult:
        return cls(
            tasks=[Task.from_api(t) for t in data.get("tasks", [])],
            duplicated_count=data.get("duplicated_count", 0),
        )


@dataclass
class UploadMeta:
    """Metadata from a task upload."""

    valid: int
    inserted: int
    duplicates: int
    invalid: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> UploadMeta:
        return cls(
            valid=data.get("valid", 0),
            inserted=data.get("inserted", 0),
            duplicates=data.get("duplicates", 0),
            invalid=data.get("invalid", 0),
        )


@dataclass
class UploadStatus:
    """Status of a CSV task upload."""

    state: str
    meta: UploadMeta

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> UploadStatus:
        return cls(
            state=data.get("state", ""),
            meta=UploadMeta.from_api(data.get("meta", {})),
        )
