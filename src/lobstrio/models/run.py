from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Run:
    """A single execution of a squid's tasks."""

    id: str
    status: str
    total_results: int
    total_unique_results: int
    duration: float
    credit_used: float
    origin: str
    done_reason: str | None
    done_reason_desc: str | None
    export_done: bool
    started_at: str | None
    ended_at: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Run:
        return cls(
            id=data["id"],
            status=data.get("status", ""),
            total_results=data.get("total_results", 0),
            total_unique_results=data.get("total_unique_results", 0),
            duration=data.get("duration", 0.0),
            credit_used=data.get("credit_used", 0.0),
            origin=data.get("origin", ""),
            done_reason=data.get("done_reason"),
            done_reason_desc=data.get("done_reason_desc"),
            export_done=data.get("export_done", False),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
        )


@dataclass
class RunStats:
    """Real-time statistics for a running execution."""

    percent_done: str
    total_tasks: int
    total_tasks_done: int
    total_tasks_left: int
    total_results: int
    duration: float
    eta: str
    current_task: str | None
    is_done: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RunStats:
        return cls(
            percent_done=data.get("percent_done", "0%"),
            total_tasks=data.get("total_tasks", 0),
            total_tasks_done=data.get("total_tasks_done", 0),
            total_tasks_left=data.get("total_tasks_left", 0),
            total_results=data.get("total_results", 0),
            duration=data.get("duration", 0.0),
            eta=data.get("eta", ""),
            current_task=data.get("current_task"),
            is_done=data.get("is_done", False),
        )
