"""
Live integration tests against the real Lobstr.io API.

Run with: pytest tests/test_live.py -v -s
Requires a valid token in ~/.config/lobstr/config.toml or LOBSTR_TOKEN env var.
"""

import os
import tempfile

import pytest

from lobstrio import (
    Account,
    AccountType,
    AsyncLobstrClient,
    Crawler,
    CrawlerParams,
    LobstrClient,
    Run,
    RunStats,
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

# Google Maps crawler ID (first crawler, well-known)
MAPS_CRAWLER_ID = "4734d096159ef05210e0e1677e8be823"
MAPS_URL_1 = "https://www.google.com/maps/place/Eiffel+Tower/@48.8583701,2.2944813"
MAPS_URL_2 = "https://www.google.com/maps/place/Louvre+Museum/@48.8606111,2.3354553"


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
        crawler = client.crawlers.get(MAPS_CRAWLER_ID)
        assert crawler.id == MAPS_CRAWLER_ID
        assert "Google Maps" in crawler.name
        print(f"  Got crawler: {crawler.name}")
        print(f"    max_concurrency={crawler.max_concurrency}, premium={crawler.is_premium}")

    def test_params(self, client):
        params = client.crawlers.params(MAPS_CRAWLER_ID)
        assert isinstance(params, CrawlerParams)
        assert "url" in params.task_params
        print(f"  Params for Google Maps:")
        print(f"    task_params: {list(params.task_params.keys())}")
        print(f"    squid_params: {list(params.squid_params.keys())}")
        if params.functions:
            print(f"    functions: {list(params.functions.keys())}")


# ---- Squids CRUD ----


class TestSquidsCRUD:
    """Full squid lifecycle: create -> get -> update -> list -> empty -> delete."""

    def test_full_lifecycle(self, client):
        # Create
        squid = client.squids.create(MAPS_CRAWLER_ID, name="SDK Live Test")
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
    """Task add, list, get, iter, delete."""

    def test_task_lifecycle(self, client):
        squid = client.squids.create(MAPS_CRAWLER_ID, name="SDK Task Test")
        squid_id = squid.id
        print(f"  Created squid: {squid_id}")

        try:
            # Add tasks
            result = client.tasks.add(
                squid=squid_id,
                tasks=[{"url": MAPS_URL_1}, {"url": MAPS_URL_2}],
            )
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


class TestTaskUpload:
    """CSV upload and upload status check."""

    def test_upload_csv(self, client):
        squid = client.squids.create(MAPS_CRAWLER_ID, name="SDK Upload Test")
        squid_id = squid.id
        print(f"  Created squid: {squid_id}")

        try:
            # Create a CSV file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
                f.write("url\n")
                f.write(f"{MAPS_URL_1}\n")
                f.write(f"{MAPS_URL_2}\n")
                csv_path = f.name

            try:
                # Upload
                upload_result = client.tasks.upload(squid=squid_id, file=csv_path)
                assert "id" in upload_result
                upload_id = upload_result["id"]
                print(f"  Upload started: id={upload_id}")

                # Check upload status
                import time
                for _ in range(10):
                    status = client.tasks.upload_status(upload_id)
                    print(f"  Upload status: state={status.state}, "
                          f"valid={status.meta.valid}, inserted={status.meta.inserted}, "
                          f"duplicates={status.meta.duplicates}, invalid={status.meta.invalid}")
                    if status.state in ("completed", "done", "finished"):
                        break
                    time.sleep(1)

                assert status.meta.valid >= 0
                print(f"  Upload completed: {status.meta.inserted} inserted")

                # Verify tasks were created
                tasks = client.tasks.list(squid=squid_id)
                print(f"  Tasks after upload: {len(tasks)}")

            finally:
                os.unlink(csv_path)

        finally:
            client.squids.delete(squid_id)
            print(f"  Cleaned up squid {squid_id}")


# ---- Runs (full lifecycle) ----


class TestRunsFullLifecycle:
    """Start a run, poll stats, abort, download."""

    def test_start_stats_abort(self, client):
        """Start a run, check stats, then abort it before it consumes too many credits."""
        squid = client.squids.create(MAPS_CRAWLER_ID, name="SDK Run Test")
        squid_id = squid.id
        print(f"  Created squid: {squid_id}")

        try:
            # Configure squid params (Google Maps requires language)
            client.squids.update(
                squid_id,
                params={"language": "English (United States)", "max_results": 1},
            )
            print("  Configured squid params")

            # Add a task
            client.tasks.add(squid=squid_id, tasks=[{"url": MAPS_URL_1}])
            print("  Added 1 task")

            # Start run
            run = client.runs.start(squid=squid_id)
            assert isinstance(run, Run)
            assert run.id
            run_id = run.id
            print(f"  Started run: {run_id}, status={run.status}")

            # Get run details
            run_detail = client.runs.get(run_id)
            assert run_detail.id == run_id
            print(f"  Run detail: status={run_detail.status}, origin={run_detail.origin}")

            # Check stats
            stats = client.runs.stats(run_id)
            assert isinstance(stats, RunStats)
            print(f"  Stats: {stats.percent_done} done, "
                  f"tasks={stats.total_tasks_done}/{stats.total_tasks}, "
                  f"is_done={stats.is_done}")

            # List runs for this squid
            runs = client.runs.list(squid=squid_id)
            assert any(r.id == run_id for r in runs)
            print(f"  Listed {len(runs)} runs, found ours")

            # Run tasks
            run_tasks = client.runs.tasks(run_id)
            print(f"  Run tasks: {len(run_tasks)}")

            # Abort the run
            abort_result = client.runs.abort(run_id)
            print(f"  Abort result: {abort_result}")

            # Verify aborted
            import time
            time.sleep(1)
            aborted_run = client.runs.get(run_id)
            print(f"  Run after abort: status={aborted_run.status}, "
                  f"done_reason={aborted_run.done_reason}")

        finally:
            client.squids.delete(squid_id)
            print(f"  Cleaned up squid {squid_id}")

    def test_download_url_and_download(self, client):
        """Test download on an existing completed run."""
        squids = client.squids.list()

        for squid in squids:
            if squid.total_runs > 0:
                runs = client.runs.list(squid=squid.id)
                # Find a completed run with results
                for run in runs:
                    if run.status == "done" and run.total_results > 0:
                        # Download URL
                        url = client.runs.download_url(run.id)
                        assert url
                        assert "http" in url
                        print(f"  Download URL for run {run.id}: {url[:80]}...")

                        # Download to temp file
                        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                            dest = f.name

                        try:
                            client.runs.download(run.id, dest=dest)
                            size = os.path.getsize(dest)
                            assert size > 0
                            print(f"  Downloaded {size} bytes to {dest}")

                            # Read first few lines
                            with open(dest) as f:
                                lines = f.readlines()[:3]
                            print(f"  First lines: {[l.strip()[:80] for l in lines]}")
                        finally:
                            os.unlink(dest)

                        return

        pytest.skip("No completed runs with results found for download test")

    def test_wait_on_completed_run(self, client):
        """Test runs.wait() on an already-completed run (instant return)."""
        squids = client.squids.list()

        for squid in squids:
            if squid.total_runs > 0:
                runs = client.runs.list(squid=squid.id)
                for run in runs:
                    if run.status == "done":
                        callbacks = []
                        result = client.runs.wait(
                            run.id,
                            poll_interval=0.1,
                            callback=lambda s: callbacks.append(s),
                        )
                        assert isinstance(result, Run)
                        assert result.status == "done"
                        assert len(callbacks) == 1
                        assert callbacks[0].is_done is True
                        print(f"  wait() returned immediately for completed run {run.id}")
                        print(f"  Callback received: {callbacks[0].percent_done}")
                        return

        pytest.skip("No completed runs found for wait test")


# ---- Runs (read-only on existing data) ----


class TestRunsReadOnly:
    """List runs for existing squids (non-destructive)."""

    def test_list_runs(self, client):
        squids = client.squids.list()
        if not squids:
            pytest.skip("No squids available")

        for squid in squids:
            if squid.total_runs > 0:
                runs = client.runs.list(squid=squid.id)
                assert len(runs) > 0
                assert all(isinstance(r, Run) for r in runs)
                print(f"  Squid '{squid.name}': {len(runs)} runs")

                run = client.runs.get(runs[0].id)
                print(f"    Run {run.id}: status={run.status}, results={run.total_results}, "
                      f"duration={run.duration}s, credits={run.credit_used}")

                stats = client.runs.stats(runs[0].id)
                print(f"    Stats: {stats.percent_done} done, is_done={stats.is_done}")

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


# ---- Accounts ----


class TestAccounts:
    def test_list(self, client):
        accounts = client.accounts.list()
        assert isinstance(accounts, list)
        print(f"  Found {len(accounts)} accounts")
        for a in accounts:
            assert isinstance(a, Account)
            print(f"    - {a.username} (type={a.type}, status={a.status_code_info})")

    def test_types(self, client):
        types = client.accounts.types()
        assert len(types) > 0
        assert all(isinstance(t, AccountType) for t in types)
        print(f"  Found {len(types)} account types:")
        for t in types[:5]:
            print(f"    - {t.name} ({t.domain})")

    def test_get(self, client):
        accounts = client.accounts.list()
        if not accounts:
            pytest.skip("No accounts available")
        account = client.accounts.get(accounts[0].id)
        assert account.id == accounts[0].id
        print(f"  Got account: {account.username} (type={account.type})")
        print(f"    squids: {len(account.squids)}")


# ---- Delivery ----


class TestDelivery:
    """Test delivery configuration (non-destructive — configures then reads back)."""

    def test_email_delivery(self, client):
        squid = client.squids.create(MAPS_CRAWLER_ID, name="SDK Delivery Test")
        squid_id = squid.id
        try:
            result = client.delivery.email(squid_id, email="test@example.com", notifications=True)
            assert result.email == "test@example.com"
            assert result.notifications is True
            print(f"  Email delivery configured: {result.email}, notifications={result.notifications}")
        finally:
            client.squids.delete(squid_id)

    def test_webhook_delivery(self, client):
        squid = client.squids.create(MAPS_CRAWLER_ID, name="SDK Webhook Test")
        squid_id = squid.id
        try:
            result = client.delivery.webhook(
                squid_id,
                url="https://httpbin.org/post",
                on_done=True,
                on_error=True,
                on_running=False,
            )
            assert result.url == "https://httpbin.org/post"
            print(f"  Webhook delivery configured: url={result.url}, active={result.is_active}")
        finally:
            client.squids.delete(squid_id)


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
