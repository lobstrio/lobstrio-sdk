from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailDelivery:
    email: str
    notifications: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> EmailDelivery:
        return cls(
            email=data.get("email", ""),
            notifications=data.get("notifications", True),
        )


@dataclass
class GoogleSheetDelivery:
    url: str
    append: bool
    is_active: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> GoogleSheetDelivery:
        fields = data.get("google_sheet_fields", data)
        return cls(
            url=fields.get("url", ""),
            append=fields.get("append", False),
            is_active=fields.get("is_active", fields.get("active", True)),
        )


@dataclass
class S3Delivery:
    bucket: str
    target_path: str
    is_active: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> S3Delivery:
        fields = data.get("s3_fields", data)
        return cls(
            bucket=fields.get("bucket", ""),
            target_path=fields.get("target_path", ""),
            is_active=fields.get("is_active", fields.get("active", True)),
        )


@dataclass
class WebhookEvents:
    run_running: bool = False
    run_paused: bool = False
    run_done: bool = True
    run_error: bool = True

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> WebhookEvents:
        return cls(
            run_running=data.get("run.running", False),
            run_paused=data.get("run.paused", False),
            run_done=data.get("run.done", True),
            run_error=data.get("run.error", True),
        )

    def to_api(self) -> dict[str, bool]:
        return {
            "run.running": self.run_running,
            "run.paused": self.run_paused,
            "run.done": self.run_done,
            "run.error": self.run_error,
        }


@dataclass
class WebhookDelivery:
    url: str
    is_active: bool
    retry: bool
    events: WebhookEvents = field(default_factory=WebhookEvents)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> WebhookDelivery:
        fields = data.get("webhook_fields", data)
        events_data = fields.get("events", {})
        return cls(
            url=fields.get("url", ""),
            is_active=fields.get("is_active", fields.get("active", True)),
            retry=fields.get("retry", True),
            events=WebhookEvents.from_api(events_data),
        )


@dataclass
class SFTPDelivery:
    host: str
    port: int
    username: str
    directory: str
    is_active: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SFTPDelivery:
        fields = data.get("ftp_fields", data)
        return cls(
            host=fields.get("host", ""),
            port=fields.get("port", 22),
            username=fields.get("username", ""),
            directory=fields.get("directory", ""),
            is_active=fields.get("is_active", fields.get("active", True)),
        )
