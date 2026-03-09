import pytest

from lobstrio import AsyncLobstrClient
from lobstrio.exceptions import AuthError


@pytest.fixture
async def async_client(httpx_mock):
    client = AsyncLobstrClient(token="test-token", base_url="https://api.lobstr.io/v1/")
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_async_me(async_client, httpx_mock):
    httpx_mock.add_response(
        json={
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "is_staff": False,
            "plan": [],
        }
    )
    user = await async_client.me()
    assert user.email == "alice@example.com"


@pytest.mark.asyncio
async def test_async_balance(async_client, httpx_mock):
    httpx_mock.add_response(json={"available": 5000, "consumed": 0, "used_slots": 0, "total_available_slots": 5})
    balance = await async_client.balance()
    assert balance.available == 5000


@pytest.mark.asyncio
async def test_async_auth_error(async_client, httpx_mock):
    httpx_mock.add_response(status_code=401, json={"error": "Invalid token"})
    with pytest.raises(AuthError):
        await async_client.me()


@pytest.mark.asyncio
async def test_async_crawlers_list(async_client, httpx_mock):
    httpx_mock.add_response(json={"data": [{"id": "c1", "name": "Test", "slug": "test"}]})
    crawlers = await async_client.crawlers.list()
    assert len(crawlers) == 1


@pytest.mark.asyncio
async def test_async_squids_list(async_client, httpx_mock):
    httpx_mock.add_response(
        json={
            "data": [
                {
                    "id": "sq1",
                    "name": "Test",
                    "crawler": "c1",
                    "crawler_name": "Test",
                    "is_active": True,
                    "is_ready": True,
                    "concurrency": 1,
                    "total_runs": 0,
                    "params": {},
                }
            ],
            "total_pages": 1,
        }
    )
    squids = await async_client.squids.list()
    assert len(squids) == 1


@pytest.mark.asyncio
async def test_async_squids_create(async_client, httpx_mock):
    httpx_mock.add_response(
        json={"id": "sq1", "name": "New", "crawler": "c1", "crawler_name": "Test", "is_active": True, "params": {}}
    )
    squid = await async_client.squids.create("c1", name="New")
    assert squid.id == "sq1"


@pytest.mark.asyncio
async def test_async_tasks_add(async_client, httpx_mock):
    httpx_mock.add_response(
        json={"tasks": [{"id": "t1", "params": {"url": "https://example.com"}}], "duplicated_count": 0}
    )
    result = await async_client.tasks.add(squid="sq1", tasks=[{"url": "https://example.com"}])
    assert len(result.tasks) == 1


@pytest.mark.asyncio
async def test_async_runs_start(async_client, httpx_mock):
    httpx_mock.add_response(json={"id": "r1", "status": "running", "total_results": 0, "duration": 0, "credit_used": 0})
    run = await async_client.runs.start(squid="sq1")
    assert run.id == "r1"


@pytest.mark.asyncio
async def test_async_runs_wait(async_client, httpx_mock):
    httpx_mock.add_response(
        json={
            "percent_done": "100%",
            "total_tasks": 1,
            "total_tasks_done": 1,
            "total_tasks_left": 0,
            "total_results": 10,
            "duration": 5.0,
            "eta": "",
            "is_done": True,
        }
    )
    httpx_mock.add_response(json={"id": "r1", "status": "finished", "total_results": 10, "duration": 5.0, "credit_used": 1.0})
    run = await async_client.runs.wait("r1", poll_interval=0.01)
    assert run.status == "finished"


@pytest.mark.asyncio
async def test_async_results_list(async_client, httpx_mock):
    httpx_mock.add_response(json={"data": [{"id": "res1", "name": "Test"}], "total_pages": 1})
    results = await async_client.results.list(squid="sq1")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_async_context_manager(httpx_mock):
    httpx_mock.add_response(json={"first_name": "Test", "email": "t@t.com", "plan": []})
    async with AsyncLobstrClient(token="t") as client:
        user = await client.me()
        assert user.email == "t@t.com"
