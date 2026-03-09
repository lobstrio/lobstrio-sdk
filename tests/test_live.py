"""
Live integration tests against the real Lobstr.io API.

Run with: pytest tests/test_live.py -v -s
Requires a valid token in ~/.config/lobstr/config.toml or LOBSTR_TOKEN env var.
"""

import pytest

from lobstrio import (
    AsyncLobstrClient,
    Crawler,
    CrawlerParams,
    LobstrClient,
    Run,
    Squid,
    Task,
)

# Skip all tests if no token available
try:
    _client = LobstrClient()
    _client.close()
    HAS_TOKEN = True
except ValueError:
    HAS_TOKEN = False

pytestmark = pytest.mark.skipif(not HAS_TOKEN, reason="No API token available")


@pytest.fixture(scope="module")
def client():
    c = LobstrClient()
    yield c
    c.close()


# ---- User / Balance ----


class TestUser:
    def test_me(self, client):
        user = client.me()
        assert user.email
        assert isinstance(user.first_name, str)
        assert isinstance(user.plan, list)
        print(f"  User: {user.first_name} {user.last_name} <{user.email}>")
        print(f"  Plan: {user.plan}")

    def test_balance(self, client):
        balance = client.balance()
        assert balance.available >= 0
        assert balance.total_available_slots >= 0
        print(f"  Balance: {balance.available} available, {balance.consumed} consumed")
        print(f"  Slots: {balance.used_slots}/{balance.total_available_slots}")


# ---- Crawlers ----


class TestCrawlers:
    def test_list(self, client):
        crawlers = client.crawlers.list()
        assert len(crawlers) > 0
        assert all(isinstance(c, Crawler) for c in crawlers)
        print(f"  Found {len(crawlers)} crawlers")
        for c in crawlers[:5]:
            print(f"    - {c.name} ({c.slug}) [credits/row: {c.credits_per_row}]")

    def test_get(self, client):
        crawlers = client.crawlers.list()
        crawler = client.crawlers.get(crawlers[0].id)
        assert crawler.id == crawlers[0].id
        assert crawler.name == crawlers[0].name
        print(f"  Got crawler: {crawler.name}")
        print(f"    max_concurrency={crawler.max_concurrency}, premium={crawler.is_premium}")

    def test_params(self, client):
        crawlers = client.crawlers.list()
        params = client.crawlers.params(crawlers[0].id)
        assert isinstance(params, CrawlerParams)
        print(f"  Params for: {crawlers[0].name}")
        print(f"    task_params: {list(params.task_params.keys())}")
        print(f"    squid_params: {list(params.squid_params.keys())}")
        if params.functions:
            print(f"    functions: {list(params.functions.keys())}")


# ---- Squids CRUD ----


class TestSquidsCRUD:
    """Full squid lifecycle: create -> get -> update -> list -> empty -> delete."""

    def test_full_lifecycle(self, client):
        # Pick a crawler
        crawlers = client.crawlers.list()
        crawler = crawlers[0]
        print(f"  Using crawler: {crawler.name} ({crawler.id})")

        # Create
        squid = client.squids.create(crawler.id, name="SDK Live Test")
        assert isinstance(squid, Squid)
        assert squid.name == "SDK Live Test"
        squid_id = squid.id
        print(f"  Created squid: {squid.name} ({squid_id})")

        try:
            # Get
            fetched = client.squids.get(squid_id)
            assert fetched.id == squid_id
            assert fetched.name == "SDK Live Test"
            print(f"  Fetched squid: {fetched.name}")

            # Update
            updated = client.squids.update(squid_id, name="SDK Live Test Updated")
            assert updated.name == "SDK Live Test Updated"
            print(f"  Updated name to: {updated.name}")

            # List — should find our squid
            squids = client.squids.list()
            assert any(s.id == squid_id for s in squids)
            print(f"  Listed {len(squids)} squids, found ours")

            # Iter
            found = False
            for s in client.squids.iter():
                if s.id == squid_id:
                    found = True
                    break
            assert found
            print("  Iter: found squid via iterator")

            # Empty (no tasks to remove, but should succeed)
            result = client.squids.empty(squid_id)
            print(f"  Empty result: {result}")

        finally:
            # Delete
            client.squids.delete(squid_id)
            print(f"  Deleted squid {squid_id}")


# ---- Tasks ----


class TestTasks:
    """Create squid, add tasks, list them, delete."""

    def test_task_lifecycle(self, client):
        crawlers = client.crawlers.list()
        crawler = crawlers[0]

        # Get params to find the right task key
        params = client.crawlers.params(crawler.id)
        task_keys = list(params.task_params.keys())
        print(f"  Crawler: {crawler.name}, task params: {task_keys}")

        squid = client.squids.create(crawler.id, name="SDK Task Test")
        squid_id = squid.id
        print(f"  Created squid: {squid_id}")

        try:
            # Add tasks — use a valid Google Maps URL for the first crawler
            key = task_keys[0] if task_keys else "url"
            if key == "url":
                tasks_input = [
                    {key: "https://www.google.com/maps/place/Eiffel+Tower/@48.8583701,2.2944813"},
                    {key: "https://www.google.com/maps/place/Louvre+Museum/@48.8606111,2.3354553"},
                ]
            else:
                tasks_input = [{key: "test value 1"}, {key: "test value 2"}]
            result = client.tasks.add(squid=squid_id, tasks=tasks_input)
            assert len(result.tasks) >= 1
            print(f"  Added {len(result.tasks)} tasks, {result.duplicated_count} duplicates")

            # List tasks
            tasks = client.tasks.list(squid=squid_id)
            assert len(tasks) >= 1
            assert all(isinstance(t, Task) for t in tasks)
            print(f"  Listed {len(tasks)} tasks")

            # Get single task
            task = client.tasks.get(tasks[0].id)
            assert task.id == tasks[0].id
            print(f"  Got task: {task.id}, params={task.params}")

            # Iter tasks
            iter_tasks = list(client.tasks.iter(squid=squid_id))
            assert len(iter_tasks) >= 1
            print(f"  Iterated {len(iter_tasks)} tasks")

            # Delete one task
            client.tasks.delete(tasks[0].id)
            print(f"  Deleted task {tasks[0].id}")

        finally:
            client.squids.delete(squid_id)
            print(f"  Cleaned up squid {squid_id}")


# ---- Runs ----


class TestRuns:
    """List runs for existing squids (non-destructive)."""

    def test_list_runs(self, client):
        squids = client.squids.list()
        if not squids:
            pytest.skip("No squids available")

        # Find a squid that has runs
        for squid in squids:
            if squid.total_runs > 0:
                runs = client.runs.list(squid=squid.id)
                assert len(runs) > 0
                assert all(isinstance(r, Run) for r in runs)
                print(f"  Squid '{squid.name}': {len(runs)} runs")

                # Get first run details
                run = client.runs.get(runs[0].id)
                print(f"    Run {run.id}: status={run.status}, results={run.total_results}, "
                      f"duration={run.duration}s, credits={run.credit_used}")

                # Stats
                stats = client.runs.stats(runs[0].id)
                print(f"    Stats: {stats.percent_done} done, is_done={stats.is_done}")

                # Run tasks
                run_tasks = client.runs.tasks(runs[0].id)
                print(f"    Run tasks: {len(run_tasks)}")
                return

        pytest.skip("No squids with runs found")


# ---- Results ----


class TestResults:
    def test_list_results(self, client):
        squids = client.squids.list()
        if not squids:
            pytest.skip("No squids available")

        for squid in squids:
            if squid.total_runs > 0:
                results = client.results.list(squid=squid.id, page_size=5)
                print(f"  Squid '{squid.name}': {len(results)} results (page 1, size 5)")
                if results:
                    print(f"    Sample keys: {list(results[0].keys())[:10]}")
                return

        pytest.skip("No squids with results found")


# ---- Async ----


class TestAsync:
    @pytest.mark.asyncio
    async def test_async_me(self):
        async with AsyncLobstrClient() as client:
            user = await client.me()
            assert user.email
            print(f"  Async user: {user.email}")

    @pytest.mark.asyncio
    async def test_async_crawlers(self):
        async with AsyncLobstrClient() as client:
            crawlers = await client.crawlers.list()
            assert len(crawlers) > 0
            print(f"  Async: {len(crawlers)} crawlers")

    @pytest.mark.asyncio
    async def test_async_balance(self):
        async with AsyncLobstrClient() as client:
            balance = await client.balance()
            assert balance.available >= 0
            print(f"  Async balance: {balance.available}")
