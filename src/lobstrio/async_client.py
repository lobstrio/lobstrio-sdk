from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import httpx

from lobstrio._base import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, _raise_for_status, _resolve_token
from lobstrio.models.account import Account, AccountType, SyncStatus
from lobstrio.models.crawler import Crawler, CrawlerParams
from lobstrio.models.delivery import (
    EmailDelivery,
    GoogleSheetDelivery,
    S3Delivery,
    SFTPDelivery,
    WebhookDelivery,
)
from lobstrio.models.run import Run, RunStats
from lobstrio.models.squid import Squid
from lobstrio.models.task import AddTasksResult, Task, UploadStatus
from lobstrio.models.user import Balance, User


class _AsyncHTTPClient:
    """Low-level async HTTP transport."""

    def __init__(self, token: str, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"authorization": f"Token {token}"},
            timeout=timeout,
        )

    @staticmethod
    def _parse_json(resp: httpx.Response) -> Any:
        if not resp.content:
            return {}
        return resp.json()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = await self._client.get(path, params=params)
        _raise_for_status(resp)
        return self._parse_json(resp)

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        resp = await self._client.post(path, json=json, data=data, files=files, params=params)
        _raise_for_status(resp)
        return self._parse_json(resp)

    async def delete(self, path: str) -> Any:
        resp = await self._client.delete(path)
        _raise_for_status(resp)
        return self._parse_json(resp)

    async def download(self, url: str, dest: str) -> None:
        """Download from a full URL to a file path."""
        async with httpx.AsyncClient() as dl:
            async with dl.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

    async def close(self) -> None:
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Async page iterator
# ---------------------------------------------------------------------------


class AsyncPageIterator(AsyncIterator[Any]):
    """Lazy async iterator that auto-fetches next pages."""

    def __init__(
        self,
        fetch_page: Callable[..., Any],
        model_cls: type[Any],
        *,
        data_key: str = "data",
        **params: Any,
    ) -> None:
        self._fetch = fetch_page
        self._model = model_cls
        self._data_key = data_key
        self._params = params
        self._page = params.pop("page", 1)
        self._buffer: list[Any] = []
        self._done = False

    def __aiter__(self) -> AsyncPageIterator:
        return self

    async def __anext__(self) -> Any:
        if self._buffer:
            return self._buffer.pop(0)
        if self._done:
            raise StopAsyncIteration
        await self._load_next_page()
        if not self._buffer:
            raise StopAsyncIteration
        return self._buffer.pop(0)

    async def _load_next_page(self) -> None:
        data = await self._fetch(page=self._page, **self._params)

        items = data.get(self._data_key, data) if isinstance(data, dict) else data
        if not items:
            self._done = True
            return

        from_api = getattr(self._model, "from_api", None)
        if from_api:
            self._buffer = [from_api(item) for item in items]
        else:
            self._buffer = list(items)

        self._page += 1

        if isinstance(data, dict):
            total_pages = data.get("total_pages")
            if total_pages is not None and self._page > total_pages:
                self._done = True


# ---------------------------------------------------------------------------
# Async resource classes
# ---------------------------------------------------------------------------


class AsyncCrawlersResource:
    def __init__(self, http: _AsyncHTTPClient) -> None:
        self._http = http

    async def list(self) -> list[Crawler]:
        data = await self._http.get("/crawlers")
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Crawler.from_api(c) for c in items]

    async def get(self, crawler_id: str) -> Crawler:
        data = await self._http.get(f"/crawlers/{crawler_id}")
        return Crawler.from_api(data)

    async def params(self, crawler_id: str) -> CrawlerParams:
        data = await self._http.get(f"/crawlers/{crawler_id}/params")
        return CrawlerParams.from_api(data)


class AsyncSquidsResource:
    def __init__(self, http: _AsyncHTTPClient) -> None:
        self._http = http

    async def list(self, *, limit: int = 50, page: int = 1, name: str | None = None) -> list[Squid]:
        params: dict[str, Any] = {"limit": limit, "page": page}
        if name is not None:
            params["name"] = name
        data = await self._http.get("/squids", params=params)
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Squid.from_api(s) for s in items]

    def iter(self, *, limit: int = 50, **kwargs: Any) -> AsyncPageIterator:
        return AsyncPageIterator(
            lambda **p: self._http.get("/squids", params=p),
            Squid,
            limit=limit,
            **kwargs,
        )

    async def get(self, squid_id: str) -> Squid:
        data = await self._http.get(f"/squids/{squid_id}")
        return Squid.from_api(data)

    async def create(self, crawler: str, *, name: str | None = None) -> Squid:
        body: dict[str, Any] = {"crawler": crawler}
        if name is not None:
            body["name"] = name
        data = await self._http.post("/squids", json=body)
        return Squid.from_api(data)

    async def update(
        self,
        squid_id: str,
        *,
        concurrency: int | None = None,
        name: str | None = None,
        run_notify: str | None = None,
        export_unique_results: bool | None = None,
        params: dict[str, Any] | None = None,
    ) -> Squid:
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
        await self._http.post(f"/squids/{squid_id}", json=body)
        return await self.get(squid_id)

    async def empty(self, squid_id: str, *, type: str = "url") -> dict[str, Any]:
        return await self._http.post(f"/squids/{squid_id}/empty", json={"type": type})

    async def delete(self, squid_id: str) -> dict[str, Any]:
        return await self._http.delete(f"/squids/{squid_id}")


class AsyncTasksResource:
    def __init__(self, http: _AsyncHTTPClient) -> None:
        self._http = http

    async def list(self, *, squid: str, limit: int = 50, page: int = 1) -> list[Task]:
        data = await self._http.get("/tasks", params={"squid": squid, "limit": limit, "page": page})
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Task.from_api(t) for t in items]

    def iter(self, *, squid: str, limit: int = 50, **kwargs: Any) -> AsyncPageIterator:
        return AsyncPageIterator(
            lambda **p: self._http.get("/tasks", params=p),
            Task,
            squid=squid,
            limit=limit,
            **kwargs,
        )

    async def get(self, task_id: str) -> Task:
        data = await self._http.get(f"/tasks/{task_id}")
        return Task.from_api(data)

    async def add(self, *, squid: str, tasks: list[dict[str, Any]]) -> AddTasksResult:
        data = await self._http.post("/tasks", json={"squid": squid, "tasks": tasks})
        return AddTasksResult.from_api(data)

    async def upload(self, *, squid: str, file: str | Path) -> dict[str, Any]:
        path = Path(file)
        with open(path, "rb") as f:
            return await self._http.post(
                "/tasks/upload",
                data={"squid": squid},
                files={"file": (path.name, f)},
            )

    async def upload_status(self, upload_id: str) -> UploadStatus:
        data = await self._http.get(f"/tasks/upload/{upload_id}")
        return UploadStatus.from_api(data)

    async def delete(self, task_id: str) -> dict[str, Any]:
        return await self._http.delete(f"/tasks/{task_id}")


class AsyncRunsResource:
    def __init__(self, http: _AsyncHTTPClient) -> None:
        self._http = http

    async def start(self, *, squid: str) -> Run:
        data = await self._http.post("/runs", json={"squid": squid})
        return Run.from_api(data)

    async def list(self, *, squid: str, limit: int = 50, page: int = 1) -> list[Run]:
        data = await self._http.get("/runs", params={"squid": squid, "limit": limit, "page": page})
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Run.from_api(r) for r in items]

    def iter(self, *, squid: str, limit: int = 50, **kwargs: Any) -> AsyncPageIterator:
        return AsyncPageIterator(
            lambda **p: self._http.get("/runs", params=p),
            Run,
            squid=squid,
            limit=limit,
            **kwargs,
        )

    async def get(self, run_id: str) -> Run:
        data = await self._http.get(f"/runs/{run_id}")
        return Run.from_api(data)

    async def stats(self, run_id: str) -> RunStats:
        data = await self._http.get(f"/runs/{run_id}/stats")
        return RunStats.from_api(data)

    async def tasks(self, run_id: str, *, limit: int = 50, page: int = 1) -> list[Task]:
        data = await self._http.get("/runtasks", params={"run": run_id, "limit": limit, "page": page})
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Task.from_api(t) for t in items]

    async def abort(self, run_id: str) -> dict[str, Any]:
        return await self._http.post(f"/runs/{run_id}/abort")

    async def download_url(self, run_id: str) -> str:
        data = await self._http.get(f"/runs/{run_id}/download")
        return data["s3"]

    async def download(self, run_id: str, dest: str) -> None:
        url = await self.download_url(run_id)
        await self._http.download(url, dest)

    async def wait(
        self,
        run_id: str,
        *,
        poll_interval: float = 3.0,
        callback: Callable[[RunStats], Any] | None = None,
    ) -> Run:
        """Poll until a run completes, then return the final Run."""
        while True:
            st = await self.stats(run_id)
            if callback is not None:
                callback(st)
            if st.is_done:
                break
            await asyncio.sleep(poll_interval)
        return await self.get(run_id)


class AsyncResultsResource:
    def __init__(self, http: _AsyncHTTPClient) -> None:
        self._http = http

    async def list(self, *, squid: str, page: int = 1, page_size: int = 100) -> list[dict[str, Any]]:
        data = await self._http.get("/results", params={"squid": squid, "page": page, "page_size": page_size})
        items = data.get("data", data) if isinstance(data, dict) else data
        return list(items)

    def iter(self, *, squid: str, page_size: int = 100, **kwargs: Any) -> AsyncPageIterator:
        return AsyncPageIterator(
            lambda **p: self._http.get("/results", params=p),
            dict,
            squid=squid,
            page_size=page_size,
            **kwargs,
        )


class AsyncAccountsResource:
    def __init__(self, http: _AsyncHTTPClient) -> None:
        self._http = http

    async def list(self) -> list[Account]:
        data = await self._http.get("/accounts")
        items = data.get("data", data) if isinstance(data, dict) else data
        return [Account.from_api(a) for a in items]

    async def get(self, account_id: str) -> Account:
        data = await self._http.get(f"/accounts/{account_id}")
        if isinstance(data, dict) and "data" in data:
            items = data["data"]
            if isinstance(items, list) and items:
                return Account.from_api(items[0])
        return Account.from_api(data)

    async def types(self) -> list[AccountType]:
        data = await self._http.get("/account_types")
        items = data.get("data", data) if isinstance(data, dict) else data
        return [AccountType.from_api(t) for t in items]

    async def sync(
        self,
        type: str,
        cookies: dict[str, str],
        *,
        account: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"type": type, "cookies": cookies}
        if account is not None:
            body["account"] = account
        return await self._http.post("/accounts/cookies", json=body)

    async def sync_status(self, sync_id: str) -> SyncStatus:
        data = await self._http.get(f"/synchronize/{sync_id}")
        return SyncStatus.from_api(data)

    async def update(self, account_id: str, *, type: str, params: dict[str, Any]) -> dict[str, Any]:
        return await self._http.post("/accounts", json={
            "account": account_id,
            "type": type,
            "params": params,
        })

    async def delete(self, account_id: str) -> dict[str, Any]:
        return await self._http.delete(f"/accounts/{account_id}")


class AsyncDeliveryResource:
    def __init__(self, http: _AsyncHTTPClient) -> None:
        self._http = http

    async def email(self, squid: str, *, email: str, notifications: bool = True) -> EmailDelivery:
        data = await self._http.post(
            "/delivery", json={"email": email, "notifications": notifications}, params={"squid": squid},
        )
        return EmailDelivery.from_api(data)

    async def google_sheet(self, squid: str, *, url: str, append: bool = False, is_active: bool = True) -> GoogleSheetDelivery:
        data = await self._http.post(
            "/delivery", json={"google_sheet_fields": {"url": url, "append": append, "is_active": is_active}}, params={"squid": squid},
        )
        return GoogleSheetDelivery.from_api(data)

    async def s3(
        self, squid: str, *, bucket: str, target_path: str,
        aws_access_key: str | None = None, aws_secret_key: str | None = None, is_active: bool = True,
    ) -> S3Delivery:
        fields: dict[str, Any] = {"bucket": bucket, "target_path": target_path, "is_active": is_active}
        if aws_access_key is not None:
            fields["aws_access_key"] = aws_access_key
        if aws_secret_key is not None:
            fields["aws_secret_key"] = aws_secret_key
        data = await self._http.post("/delivery", json={"s3_fields": fields}, params={"squid": squid})
        return S3Delivery.from_api(data)

    async def webhook(
        self, squid: str, *, url: str, is_active: bool = True, retry: bool = True,
        on_running: bool = False, on_paused: bool = False, on_done: bool = True, on_error: bool = True,
    ) -> WebhookDelivery:
        data = await self._http.post(
            "/delivery",
            json={"webhook_fields": {
                "url": url, "is_active": is_active, "retry": retry,
                "events": {"run.running": on_running, "run.paused": on_paused, "run.done": on_done, "run.error": on_error},
            }},
            params={"squid": squid},
        )
        return WebhookDelivery.from_api(data)

    async def sftp(
        self, squid: str, *, host: str, port: int = 22, username: str, password: str, directory: str, is_active: bool = True,
    ) -> SFTPDelivery:
        data = await self._http.post(
            "/delivery",
            json={"ftp_fields": {"host": host, "port": port, "username": username, "password": password, "directory": directory, "is_active": is_active}},
            params={"squid": squid},
        )
        return SFTPDelivery.from_api(data)

    async def test_email(self, *, email: str) -> dict[str, Any]:
        return await self._http.post("/delivery/test-email", json={"email": email})

    async def test_google_sheet(self, *, url: str) -> dict[str, Any]:
        return await self._http.post("/delivery/test-googlesheet", json={"url": url})

    async def test_s3(self, *, bucket: str, aws_access_key: str | None = None, aws_secret_key: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"bucket": bucket}
        if aws_access_key is not None:
            body["aws_access_key"] = aws_access_key
        if aws_secret_key is not None:
            body["aws_secret_key"] = aws_secret_key
        return await self._http.post("/delivery/test-s3", json=body)

    async def test_webhook(self, *, url: str) -> dict[str, Any]:
        return await self._http.post("/delivery/test-webhook", json={"url": url})

    async def test_sftp(self, *, host: str, port: int = 22, username: str, password: str, directory: str) -> dict[str, Any]:
        return await self._http.post("/delivery/test-sftp", json={
            "host": host, "port": port, "username": username, "password": password, "directory": directory,
        })


# ---------------------------------------------------------------------------
# Main async client
# ---------------------------------------------------------------------------


class AsyncLobstrClient:
    """Asynchronous client for the Lobstr.io API."""

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
        self._http = _AsyncHTTPClient(resolved, base_url, timeout)
        self.crawlers = AsyncCrawlersResource(self._http)
        self.squids = AsyncSquidsResource(self._http)
        self.tasks = AsyncTasksResource(self._http)
        self.runs = AsyncRunsResource(self._http)
        self.results = AsyncResultsResource(self._http)
        self.accounts = AsyncAccountsResource(self._http)
        self.delivery = AsyncDeliveryResource(self._http)

    async def me(self) -> User:
        data = await self._http.get("/me")
        return User.from_api(data)

    async def balance(self) -> Balance:
        data = await self._http.get("/user/balance")
        return Balance.from_api(data)

    async def close(self) -> None:
        await self._http.close()

    async def __aenter__(self) -> AsyncLobstrClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
