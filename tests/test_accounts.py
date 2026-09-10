"""Tests for the accounts resource."""

ACCOUNT_DATA = {
    "id": "ac1",
    "username": "user@example.com",
    "type": "linkedin",
    "status": "valid",
}


def test_accounts_list(client, httpx_mock):
    httpx_mock.add_response(json={"data": [ACCOUNT_DATA], "total_pages": 1})
    items = client.accounts.list()
    assert len(items) == 1
    assert items[0].id == "ac1"


def test_accounts_iter_single_page(client, httpx_mock):
    httpx_mock.add_response(json={"data": [ACCOUNT_DATA], "total_pages": 1})
    items = list(client.accounts.iter())
    assert len(items) == 1
    assert items[0].username == "user@example.com"


def test_accounts_iter_walks_all_pages(client, httpx_mock):
    """iter() must keep paging past the first page (the 50-item default cap)."""
    page1 = [dict(ACCOUNT_DATA, id=f"a{i}") for i in range(50)]
    page2 = [dict(ACCOUNT_DATA, id=f"b{i}") for i in range(12)]
    httpx_mock.add_response(json={"data": page1, "total_pages": 2, "page": 1})
    httpx_mock.add_response(json={"data": page2, "total_pages": 2, "page": 2})

    items = list(client.accounts.iter())

    assert len(items) == 62
    assert len({a.id for a in items}) == 62
    assert items[-1].id == "b11"
