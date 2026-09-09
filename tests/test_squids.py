SQUID_DATA = {
    "id": "sq1",
    "name": "My Scraper",
    "crawler": "cr1",
    "crawler_name": "Test",
    "is_active": True,
    "is_ready": True,
    "concurrency": 3,
    "to_complete": 10,
    "last_run_status": "success",
    "total_runs": 5,
    "export_unique_results": False,
    "params": {"max_results": 100},
}


def test_squids_list(client, httpx_mock):
    httpx_mock.add_response(json={"data": [SQUID_DATA], "total_pages": 1})
    squids = client.squids.list()
    assert len(squids) == 1
    assert squids[0].id == "sq1"


def test_squids_get(client, httpx_mock):
    httpx_mock.add_response(json=SQUID_DATA)
    s = client.squids.get("sq1")
    assert s.name == "My Scraper"
    assert s.concurrency == 3


def test_squids_create(client, httpx_mock):
    httpx_mock.add_response(json=SQUID_DATA)
    s = client.squids.create("cr1", name="My Scraper")
    assert s.id == "sq1"


def test_squids_update(client, httpx_mock):
    updated = {**SQUID_DATA, "concurrency": 5}
    # First response is for the POST (update), second for GET (re-fetch)
    httpx_mock.add_response(json={"name": "My Scraper"})
    httpx_mock.add_response(json=updated)
    s = client.squids.update("sq1", concurrency=5)
    assert s.concurrency == 5


def test_squids_empty(client, httpx_mock):
    httpx_mock.add_response(json={"deleted_count": 10})
    result = client.squids.empty("sq1")
    assert result["deleted_count"] == 10


def test_squids_delete(client, httpx_mock):
    httpx_mock.add_response(json={"id": "sq1", "deleted": True})
    result = client.squids.delete("sq1")
    assert result["deleted"] is True


def test_squids_iter(client, httpx_mock):
    httpx_mock.add_response(json={"data": [SQUID_DATA], "total_pages": 1})
    items = list(client.squids.iter())
    assert len(items) == 1
    assert items[0].id == "sq1"


ESTIMATE_DATA = {
    "services": [{"name": "Google Maps data", "results": 300, "credits": 300}],
    "total_credits": 300,
    "estimated_time": "5 mins - 12 mins",
    "recommended_upgrade_plan": None,
    "max_results": 800,
    "tasks": {"count": 8, "preview": []},
}


def test_squids_estimate(client, httpx_mock):
    import json as _json

    httpx_mock.add_response(json=ESTIMATE_DATA)
    est = client.squids.estimate("sq1")
    assert est["total_credits"] == 300
    assert est["tasks"]["count"] == 8
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path.endswith("/squid/estimate")
    assert _json.loads(req.content) == {"squid": "sq1"}


def test_squids_update_new_fields(client, httpx_mock):
    import json as _json

    httpx_mock.add_response(json={"name": "My Scraper"})  # POST (update)
    httpx_mock.add_response(json=SQUID_DATA)  # GET (re-fetch)
    client.squids.update(
        "sq1",
        is_active=False,
        to_complete=50,
        no_line_breaks=True,
        cron_expression="0 9 * * 1",
        timezone="Europe/Paris",
    )
    body = _json.loads(httpx_mock.get_requests()[0].content)
    assert body == {
        "is_active": False,
        "to_complete": 50,
        "no_line_breaks": True,
        "cron_expression": "0 9 * * 1",
        "timezone": "Europe/Paris",
    }
