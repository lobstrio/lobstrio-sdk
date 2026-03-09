from lobstrio.models.crawler import Crawler, CrawlerParams, _resolve_credits
from lobstrio.models.run import Run, RunStats
from lobstrio.models.squid import Squid
from lobstrio.models.task import AddTasksResult, Task, TaskStatus, UploadMeta, UploadStatus
from lobstrio.models.user import Balance, User


class TestResolveCredits:
    def test_int(self):
        assert _resolve_credits(3) == 3

    def test_float(self):
        assert _resolve_credits(3.5) == 3

    def test_dict_current(self):
        assert _resolve_credits({"current": 5, "legacy": 2}) == 5

    def test_dict_legacy_only(self):
        assert _resolve_credits({"legacy": 2}) == 2

    def test_none(self):
        assert _resolve_credits(None) is None

    def test_empty_dict(self):
        assert _resolve_credits({}) is None


class TestCrawler:
    def test_from_api(self):
        data = {
            "id": "abc123",
            "name": "Test Crawler",
            "slug": "test-crawler",
            "description": "A test",
            "credits_per_row": {"current": 3, "legacy": 1},
            "credits_per_email": 5,
            "max_concurrency": 10,
            "account": True,
            "has_email_verification": True,
            "is_public": True,
            "is_premium": False,
            "is_available": True,
            "has_issues": False,
            "rank": 1,
        }
        c = Crawler.from_api(data)
        assert c.id == "abc123"
        assert c.name == "Test Crawler"
        assert c.credits_per_row == 3
        assert c.credits_per_email == 5
        assert c.account is True
        assert c.rank == 1

    def test_minimal_data(self):
        c = Crawler.from_api({"id": "x"})
        assert c.id == "x"
        assert c.credits_per_row is None
        assert c.max_concurrency == 1


class TestCrawlerParams:
    def test_from_api_with_functions(self):
        data = {
            "task": {"url": {"type": "string", "required": True}},
            "squid": {
                "max_results": {"default": 100},
                "functions": {"email_finder": {"credits_per_function": 5}},
            },
        }
        p = CrawlerParams.from_api(data)
        assert "url" in p.task_params
        assert "max_results" in p.squid_params
        assert "functions" not in p.squid_params
        assert "email_finder" in p.functions


class TestUser:
    def test_from_api(self):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "is_staff": False,
            "plan": [{"name": "Pro", "status": "active"}],
        }
        u = User.from_api(data)
        assert u.email == "john@example.com"
        assert u.plan[0]["name"] == "Pro"


class TestBalance:
    def test_from_api(self):
        data = {"available": 5000, "consumed": 1200, "used_slots": 2, "total_available_slots": 5}
        b = Balance.from_api(data)
        assert b.available == 5000
        assert b.used_slots == 2


class TestSquid:
    def test_from_api(self):
        data = {
            "id": "sq1",
            "name": "My Scraper",
            "crawler": "cr1",
            "crawler_name": "Test",
            "is_active": True,
            "is_ready": True,
            "concurrency": 3,
            "to_complete": 10,
            "last_run_status": "success",
            "last_run_at": "2026-01-01T00:00:00Z",
            "total_runs": 5,
            "export_unique_results": False,
            "params": {"max_results": 100},
        }
        s = Squid.from_api(data)
        assert s.id == "sq1"
        assert s.concurrency == 3
        assert s.params["max_results"] == 100


class TestTask:
    def test_from_api_with_status(self):
        data = {
            "id": "t1",
            "is_active": True,
            "params": {"url": "https://example.com"},
            "status": {
                "status": "done",
                "total_results": 10,
                "total_pages": 2,
                "done_reason": "done",
                "has_errors": False,
            },
            "created_at": "2026-01-01T00:00:00Z",
        }
        t = Task.from_api(data)
        assert t.id == "t1"
        assert t.status is not None
        assert t.status.total_results == 10

    def test_from_api_hash_value_fallback(self):
        t = Task.from_api({"hash_value": "h1", "params": {}})
        assert t.id == "h1"

    def test_from_api_no_status(self):
        t = Task.from_api({"id": "t2", "params": {}})
        assert t.status is None


class TestAddTasksResult:
    def test_from_api(self):
        data = {
            "tasks": [{"id": "t1", "params": {"url": "https://example.com"}}],
            "duplicated_count": 1,
        }
        r = AddTasksResult.from_api(data)
        assert len(r.tasks) == 1
        assert r.duplicated_count == 1


class TestUploadStatus:
    def test_from_api(self):
        data = {"state": "completed", "meta": {"valid": 100, "inserted": 95, "duplicates": 5, "invalid": 0}}
        s = UploadStatus.from_api(data)
        assert s.state == "completed"
        assert s.meta.inserted == 95


class TestRun:
    def test_from_api(self):
        data = {
            "id": "r1",
            "status": "finished",
            "total_results": 500,
            "total_unique_results": 450,
            "duration": 120.5,
            "credit_used": 50.0,
            "origin": "user",
            "done_reason": "tasks_done",
            "done_reason_desc": "All tasks completed",
            "export_done": True,
            "started_at": "2026-01-01T00:00:00Z",
            "ended_at": "2026-01-01T00:02:00Z",
        }
        r = Run.from_api(data)
        assert r.total_results == 500
        assert r.duration == 120.5


class TestRunStats:
    def test_from_api(self):
        data = {
            "percent_done": "75%",
            "total_tasks": 20,
            "total_tasks_done": 15,
            "total_tasks_left": 5,
            "total_results": 150,
            "duration": 60.0,
            "eta": "2 minutes",
            "current_task": "t5",
            "is_done": False,
        }
        s = RunStats.from_api(data)
        assert s.percent_done == "75%"
        assert s.is_done is False
        assert s.total_tasks_left == 5
