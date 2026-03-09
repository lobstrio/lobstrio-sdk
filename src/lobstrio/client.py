from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from lobstrio._base import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, _raise_for_status, _resolve_token
from lobstrio.models.crawler import Crawler, CrawlerParams
from lobstrio.models.run import Run, RunStats
from lobstrio.models.squid import Squid
from lobstrio.models.task import AddTasksResult, Task, UploadStatus
from lobstrio.models.user import Balance, User
from lobstrio.pagination import PageIterator


class _HTTPClient:
    """Low-level sync HTTP transport."""

    def __init__(self, token: str, base_url: str, timeout: float) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"authorization": f"Token {token}"},
            timeout=timeout,
        )

    @staticmethod
    def _parse_json(resp: httpx.Response) -> Any:
        """Parse JSON, returning {} for empty responses."""
        if not resp.content:
            return {}
        return resp.json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = self._client.get(path, params=params)
        _raise_for_status(resp)
        return self._parse_json(resp)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        resp = self._client.post(path, json=json, data=data, files=files, params=params)
        _raise_for_status(resp)
        return self._parse_json(resp)

    def delete(self, path: str) -> Any:
        resp = self._client.delete(path)
        _raise_for_status(resp)
        return self._parse_json(resp)

    def download(self, url: str, dest: str) -> None:
        """Download from a full URL (e.g. S3 signed URL) to a file path."""
        with httpx.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Resource classes
# ---------------------------------------------------------------------------


class CrawlersResource:
    """Operations on /crawlers endpoints."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self) -> list[Crawler]:
        """List all available crawlers."""
        data = self._http.get("/crawlers")
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Crawler.from_api(c) for c in items]

    def get(self, crawler_id: str) -> Crawler:
        """Get a single crawler by ID."""
        data = self._http.get(f"/crawlers/{crawler_id}")
        return Crawler.from_api(data)

    def params(self, crawler_id: str) -> CrawlerParams:
        """Get parameters for a crawler."""
        data = self._http.get(f"/crawlers/{crawler_id}/params")
        return CrawlerParams.from_api(data)


class SquidsResource:
    """Operations on /squids endpoints."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, *, limit: int = 50, page: int = 1, name: str | None = None) -> list[Squid]:
        """List squids (single page)."""
        params: dict[str, Any] = {"limit": limit, "page": page}
        if name is not None:
            params["name"] = name
        data = self._http.get("/squids", params=params)
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Squid.from_api(s) for s in items]

    def iter(self, *, limit: int = 50, **kwargs: Any) -> PageIterator[Squid]:
        """Iterate all squids across pages."""
        return PageIterator(
            lambda **p: self._http.get("/squids", params=p),
            Squid,
            limit=limit,
            **kwargs,
        )

    def get(self, squid_id: str) -> Squid:
        """Get a single squid by ID."""
        data = self._http.get(f"/squids/{squid_id}")
        return Squid.from_api(data)

    def create(self, crawler: str, *, name: str | None = None) -> Squid:
        """Create a new squid."""
        body: dict[str, Any] = {"crawler": crawler}
        if name is not None:
            body["name"] = name
        data = self._http.post("/squids", json=body)
        return Squid.from_api(data)

    def update(
        self,
        squid_id: str,
        *,
        concurrency: int | None = None,
        name: str | None = None,
        run_notify: str | None = None,
        export_unique_results: bool | None = None,
        params: dict[str, Any] | None = None,
    ) -> Squid:
        """Update squid settings."""
        body: dict[str, Any] = {}
        if concurrency is not None:
            body["concurrency"] = concurrency
        if name is not None:
            body["name"] = name
        if run_notify is not None:
            body["run_notify"] = run_notify
        if export_unique_results is not None:
            body["export_unique_results"] = export_unique_results
        if params is not None:
            body["params"] = params
        self._http.post(f"/squids/{squid_id}", json=body)
        return self.get(squid_id)

    def empty(self, squid_id: str, *, type: str = "url") -> dict[str, Any]:
        """Remove all tasks from a squid."""
        return self._http.post(f"/squids/{squid_id}/empty", json={"type": type})

    def delete(self, squid_id: str) -> dict[str, Any]:
        """Delete a squid."""
        return self._http.delete(f"/squids/{squid_id}")


class TasksResource:
    """Operations on /tasks endpoints."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, *, squid: str, limit: int = 50, page: int = 1) -> list[Task]:
        """List tasks for a squid (single page)."""
        data = self._http.get("/tasks", params={"squid": squid, "limit": limit, "page": page})
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Task.from_api(t) for t in items]

    def iter(self, *, squid: str, limit: int = 50, **kwargs: Any) -> PageIterator[Task]:
        """Iterate all tasks across pages."""
        return PageIterator(
            lambda **p: self._http.get("/tasks", params=p),
            Task,
            squid=squid,
            limit=limit,
            **kwargs,
        )

    def get(self, task_id: str) -> Task:
        """Get a single task by ID (full 32-char hash required)."""
        data = self._http.get(f"/tasks/{task_id}")
        return Task.from_api(data)

    def add(self, *, squid: str, tasks: list[dict[str, Any]]) -> AddTasksResult:
        """Add tasks to a squid."""
        data = self._http.post("/tasks", json={"squid": squid, "tasks": tasks})
        return AddTasksResult.from_api(data)

    def upload(self, *, squid: str, file: str | Path) -> dict[str, Any]:
        """Upload a CSV/TSV file of tasks."""
        path = Path(file)
        with open(path, "rb") as f:
            return self._http.post(
                "/tasks/upload",
                data={"squid": squid},
                files={"file": (path.name, f)},
            )

    def upload_status(self, upload_id: str) -> UploadStatus:
        """Check the status of a task upload."""
        data = self._http.get(f"/tasks/upload/{upload_id}")
        return UploadStatus.from_api(data)

    def delete(self, task_id: str) -> dict[str, Any]:
        """Delete a task (full 32-char hash required)."""
        return self._http.delete(f"/tasks/{task_id}")


class RunsResource:
    """Operations on /runs endpoints."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def start(self, *, squid: str) -> Run:
        """Start a new run."""
        data = self._http.post("/runs", json={"squid": squid})
        return Run.from_api(data)

    def list(self, *, squid: str, limit: int = 50, page: int = 1) -> list[Run]:
        """List runs for a squid (single page)."""
        data = self._http.get("/runs", params={"squid": squid, "limit": limit, "page": page})
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Run.from_api(r) for r in items]

    def iter(self, *, squid: str, limit: int = 50, **kwargs: Any) -> PageIterator[Run]:
        """Iterate all runs across pages."""
        return PageIterator(
            lambda **p: self._http.get("/runs", params=p),
            Run,
            squid=squid,
            limit=limit,
            **kwargs,
        )

    def get(self, run_id: str) -> Run:
        """Get run details (full 32-char hash required)."""
        data = self._http.get(f"/runs/{run_id}")
        return Run.from_api(data)

    def stats(self, run_id: str) -> RunStats:
        """Get real-time run statistics."""
        data = self._http.get(f"/runs/{run_id}/stats")
        return RunStats.from_api(data)

    def tasks(self, run_id: str, *, limit: int = 50, page: int = 1) -> list[Task]:
        """List tasks in a run."""
        data = self._http.get("/runtasks", params={"run": run_id, "limit": limit, "page": page})
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Task.from_api(t) for t in items]

    def abort(self, run_id: str) -> dict[str, Any]:
        """Abort a running execution."""
        return self._http.post(f"/runs/{run_id}/abort")

    def download_url(self, run_id: str) -> str:
        """Get the S3 download URL for run results."""
        data = self._http.get(f"/runs/{run_id}/download")
        return data["s3"]

    def download(self, run_id: str, dest: str) -> None:
        """Download run results to a file."""
        url = self.download_url(run_id)
        self._http.download(url, dest)

    def wait(
        self,
        run_id: str,
        *,
        poll_interval: float = 3.0,
        callback: Callable[[RunStats], Any] | None = None,
    ) -> Run:
        """Poll until a run completes, then return the final Run."""
        while True:
            st = self.stats(run_id)
            if callback is not None:
                callback(st)
            if st.is_done:
                break
            time.sleep(poll_interval)
        return self.get(run_id)


class ResultsResource:
    """Operations on /results endpoints."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, *, squid: str, page: int = 1, page_size: int = 100) -> list[dict[str, Any]]:
        """Fetch results (single page)."""
        data = self._http.get("/results", params={"squid": squid, "page": page, "page_size": page_size})
        items = data.get("data", data) if isinstance(data, dict) else data
        return list(items)

    def iter(self, *, squid: str, page_size: int = 100, **kwargs: Any) -> PageIterator[dict[str, Any]]:
        """Iterate all results across pages."""
        return PageIterator(
            lambda **p: self._http.get("/results", params=p),
            dict,
            squid=squid,
            page_size=page_size,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------


class LobstrClient:
    """Synchronous client for the Lobstr.io API."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        resolved = token or _resolve_token()
        if not resolved:
            raise ValueError(
                "No API token found. Pass token= explicitly, set LOBSTR_TOKEN env var, "
                "or run 'lobstr config set-token' to save one."
            )
        self._http = _HTTPClient(resolved, base_url, timeout)
        self.crawlers = CrawlersResource(self._http)
        self.squids = SquidsResource(self._http)
        self.tasks = TasksResource(self._http)
        self.runs = RunsResource(self._http)
        self.results = ResultsResource(self._http)

    def me(self) -> User:
        """Get current user profile."""
        data = self._http.get("/me")
        return User.from_api(data)

    def balance(self) -> Balance:
        """Get account balance."""
        data = self._http.get("/user/balance")
        return Balance.from_api(data)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> LobstrClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
