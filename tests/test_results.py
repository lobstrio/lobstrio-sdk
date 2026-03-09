def test_results_list(client, httpx_mock):
    httpx_mock.add_response(
        json={
            "data": [
                {"id": "res1", "email": "test@example.com", "name": "John"},
                {"id": "res2", "email": "jane@example.com", "name": "Jane"},
            ],
            "total_pages": 1,
        }
    )
    results = client.results.list(squid="sq1")
    assert len(results) == 2
    assert results[0]["email"] == "test@example.com"


def test_results_iter(client, httpx_mock):
    httpx_mock.add_response(
        json={
            "data": [{"id": "res1", "name": "Test"}],
            "total_pages": 1,
        }
    )
    items = list(client.results.iter(squid="sq1"))
    assert len(items) == 1
