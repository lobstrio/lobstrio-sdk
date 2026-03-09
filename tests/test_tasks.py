TASK_DATA = {
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


def test_tasks_list(client, httpx_mock):
    httpx_mock.add_response(json={"data": [TASK_DATA], "total_pages": 1})
    tasks = client.tasks.list(squid="sq1")
    assert len(tasks) == 1
    assert tasks[0].id == "t1"


def test_tasks_get(client, httpx_mock):
    httpx_mock.add_response(json=TASK_DATA)
    t = client.tasks.get("t1" * 16)
    assert t.status is not None
    assert t.status.total_results == 10


def test_tasks_add(client, httpx_mock):
    httpx_mock.add_response(json={"tasks": [TASK_DATA], "duplicated_count": 0})
    result = client.tasks.add(squid="sq1", tasks=[{"url": "https://example.com"}])
    assert len(result.tasks) == 1
    assert result.duplicated_count == 0


def test_tasks_upload_status(client, httpx_mock):
    httpx_mock.add_response(
        json={"state": "completed", "meta": {"valid": 100, "inserted": 95, "duplicates": 5, "invalid": 0}}
    )
    status = client.tasks.upload_status("upload1")
    assert status.state == "completed"
    assert status.meta.inserted == 95


def test_tasks_delete(client, httpx_mock):
    httpx_mock.add_response(json={"deleted": True})
    result = client.tasks.delete("t1" * 16)
    assert result["deleted"] is True


def test_tasks_iter(client, httpx_mock):
    httpx_mock.add_response(json={"data": [TASK_DATA], "total_pages": 1})
    items = list(client.tasks.iter(squid="sq1"))
    assert len(items) == 1
