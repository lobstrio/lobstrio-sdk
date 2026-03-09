RUN_DATA = {
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

STATS_DATA = {
    "percent_done": "100%",
    "total_tasks": 20,
    "total_tasks_done": 20,
    "total_tasks_left": 0,
    "total_results": 500,
    "duration": 120.5,
    "eta": "",
    "current_task": None,
    "is_done": True,
}


def test_runs_start(client, httpx_mock):
    httpx_mock.add_response(json=RUN_DATA)
    run = client.runs.start(squid="sq1")
    assert run.id == "r1"
    assert run.status == "finished"


def test_runs_list(client, httpx_mock):
    httpx_mock.add_response(json={"data": [RUN_DATA], "total_pages": 1})
    runs = client.runs.list(squid="sq1")
    assert len(runs) == 1


def test_runs_get(client, httpx_mock):
    httpx_mock.add_response(json=RUN_DATA)
    run = client.runs.get("r1" * 16)
    assert run.total_results == 500


def test_runs_stats(client, httpx_mock):
    httpx_mock.add_response(json=STATS_DATA)
    stats = client.runs.stats("r1" * 16)
    assert stats.is_done is True
    assert stats.percent_done == "100%"


def test_runs_tasks(client, httpx_mock):
    httpx_mock.add_response(
        json={
            "data": [{"id": "t1", "params": {"url": "https://example.com"}}],
            "total_pages": 1,
        }
    )
    tasks = client.runs.tasks("r1" * 16)
    assert len(tasks) == 1


def test_runs_abort(client, httpx_mock):
    httpx_mock.add_response(json={"status": "aborted"})
    result = client.runs.abort("r1" * 16)
    assert result["status"] == "aborted"


def test_runs_download_url(client, httpx_mock):
    httpx_mock.add_response(json={"s3": "https://s3.example.com/results.csv"})
    url = client.runs.download_url("r1" * 16)
    assert url == "https://s3.example.com/results.csv"


def test_runs_wait(client, httpx_mock):
    # Stats returns is_done=True immediately
    httpx_mock.add_response(json=STATS_DATA)
    httpx_mock.add_response(json=RUN_DATA)
    callbacks = []
    run = client.runs.wait("r1" * 16, poll_interval=0.01, callback=lambda s: callbacks.append(s))
    assert run.id == "r1"
    assert len(callbacks) == 1
    assert callbacks[0].is_done is True


def test_runs_iter(client, httpx_mock):
    httpx_mock.add_response(json={"data": [RUN_DATA], "total_pages": 1})
    items = list(client.runs.iter(squid="sq1"))
    assert len(items) == 1
