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


def test_squids_update_accounts_field(client, httpx_mock):
    """`accounts` is sent verbatim when passed to update() directly — this is
    the raw, full-replace API field, not the safe merge helper."""
    import json as _json

    httpx_mock.add_response(json={"accounts": ["ac1"]})  # POST (update)
    httpx_mock.add_response(json={**SQUID_DATA, "accounts": [{"id": "ac1", "status": "ok"}]})  # GET
    s = client.squids.update("sq1", accounts=["ac1"])
    body = _json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"accounts": ["ac1"]}
    assert s.accounts == [{"id": "ac1", "status": "ok"}]


def test_squids_update_omits_accounts_by_default(client, httpx_mock):
    """`accounts=None` (the default) must never appear in the body — sending
    an empty/absent `accounts` key would detach everything on the API side."""
    import json as _json

    httpx_mock.add_response(json={"name": "My Scraper"})
    httpx_mock.add_response(json=SQUID_DATA)
    client.squids.update("sq1", name="My Scraper")
    body = _json.loads(httpx_mock.get_requests()[0].content)
    assert "accounts" not in body


def test_attach_accounts_merges_with_existing_by_default(client, httpx_mock):
    """The API's `accounts` field is full-replace. attach_accounts() must read
    the current list first and send the union, not just the new hash."""
    import json as _json

    existing = {**SQUID_DATA, "accounts": [{"id": "ac_old", "status": "ok"}]}
    httpx_mock.add_response(json=existing)  # GET (read current)
    httpx_mock.add_response(json={"accounts": ["ac_old", "ac_new"]})  # POST (update)
    httpx_mock.add_response(json={**SQUID_DATA, "accounts": [
        {"id": "ac_old", "status": "ok"}, {"id": "ac_new", "status": "ok"},
    ]})  # GET (re-fetch)

    s = client.squids.attach_accounts("sq1", ["ac_new"])

    body = _json.loads(httpx_mock.get_requests()[1].content)
    assert body == {"accounts": ["ac_old", "ac_new"]}
    assert {a["id"] for a in s.accounts} == {"ac_old", "ac_new"}


def test_attach_accounts_accepts_a_non_list_sequence(client, httpx_mock):
    """`accounts` takes any `Sequence[str]` (e.g. a tuple), not just a list —
    the signature widened when the merge stopped mutating the parameter in
    place."""
    import json as _json

    httpx_mock.add_response(json={**SQUID_DATA, "accounts": []})  # GET (read current)
    httpx_mock.add_response(json={"accounts": ["ac_new"]})  # POST (update)
    httpx_mock.add_response(json={**SQUID_DATA, "accounts": [{"id": "ac_new", "status": "ok"}]})  # GET

    client.squids.attach_accounts("sq1", ("ac_new",))

    body = _json.loads(httpx_mock.get_requests()[1].content)
    assert body == {"accounts": ["ac_new"]}


def test_attach_accounts_dedupes_already_attached(client, httpx_mock):
    import json as _json

    existing = {**SQUID_DATA, "accounts": [{"id": "ac1", "status": "ok"}]}
    httpx_mock.add_response(json=existing)  # GET (read current)
    httpx_mock.add_response(json={"accounts": ["ac1"]})  # POST (update)
    httpx_mock.add_response(json=existing)  # GET (re-fetch)

    client.squids.attach_accounts("sq1", ["ac1"])

    body = _json.loads(httpx_mock.get_requests()[1].content)
    assert body == {"accounts": ["ac1"]}


def test_attach_accounts_replace_true_skips_the_read(client, httpx_mock):
    """`replace=True` sends exactly the given list — no GET first, and it can
    detach (e.g. `accounts=[]`)."""
    import json as _json

    httpx_mock.add_response(json={"accounts": []})  # POST (update)
    httpx_mock.add_response(json={**SQUID_DATA, "accounts": []})  # GET (re-fetch)

    client.squids.attach_accounts("sq1", [], replace=True)

    assert len(httpx_mock.get_requests()) == 2  # no extra GET before the POST
    body = _json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"accounts": []}


def test_attach_accounts_drops_malformed_existing_entry_without_losing_the_rest(client, httpx_mock):
    """A squid's current `accounts` is untyped API JSON. An entry with no
    string "id" must be skipped, not crash the merge and not be silently
    treated as if nothing were attached — that would let a malformed entry
    turn a merge into an accidental full-replace-to-empty."""
    import json as _json

    existing = {**SQUID_DATA, "accounts": [
        {"id": "ac_good", "status": "ok"},
        {"status": "ok"},  # missing "id" — must be dropped, not crash
        {"id": 123, "status": "ok"},  # non-string "id" — must be dropped too
    ]}
    httpx_mock.add_response(json=existing)  # GET (read current)
    httpx_mock.add_response(json={"accounts": ["ac_good", "ac_new"]})  # POST (update)
    httpx_mock.add_response(json={**SQUID_DATA, "accounts": [
        {"id": "ac_good", "status": "ok"}, {"id": "ac_new", "status": "ok"},
    ]})  # GET (re-fetch)

    client.squids.attach_accounts("sq1", ["ac_new"])

    body = _json.loads(httpx_mock.get_requests()[1].content)
    assert body == {"accounts": ["ac_good", "ac_new"]}


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
