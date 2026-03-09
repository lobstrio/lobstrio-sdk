import pytest

from lobstrio import LobstrClient
from lobstrio.exceptions import APIError, AuthError, NotFoundError, RateLimitError


def test_client_from_env_missing(monkeypatch):
    monkeypatch.delenv("LOBSTR_TOKEN", raising=False)
    with pytest.raises(ValueError, match="LOBSTR_TOKEN"):
        LobstrClient.from_env()


def test_client_from_env(monkeypatch, httpx_mock):
    monkeypatch.setenv("LOBSTR_TOKEN", "env-token")
    client = LobstrClient.from_env()
    assert client is not None
    client.close()


def test_client_context_manager(httpx_mock):
    with LobstrClient(token="t") as client:
        assert client is not None


def test_auth_error(client, httpx_mock):
    httpx_mock.add_response(status_code=401, json={"error": "Invalid token"})
    with pytest.raises(AuthError) as exc_info:
        client.me()
    assert exc_info.value.status_code == 401


def test_not_found_error(client, httpx_mock):
    httpx_mock.add_response(status_code=404, json={"error": "Not found"})
    with pytest.raises(NotFoundError):
        client.crawlers.get("bad_id")


def test_rate_limit_error(client, httpx_mock):
    httpx_mock.add_response(status_code=429, json={"error": "Too many requests"}, headers={"retry-after": "30"})
    with pytest.raises(RateLimitError) as exc_info:
        client.me()
    assert exc_info.value.retry_after == "30"


def test_generic_api_error(client, httpx_mock):
    httpx_mock.add_response(status_code=500, json={"error": "Internal error"})
    with pytest.raises(APIError) as exc_info:
        client.me()
    assert exc_info.value.status_code == 500


def test_error_shape_errors_dict(client, httpx_mock):
    httpx_mock.add_response(
        status_code=400,
        json={"errors": {"message": "Invalid param", "type": "validation_error", "code": 400}},
    )
    with pytest.raises(APIError) as exc_info:
        client.me()
    assert "Invalid param" in exc_info.value.message


def test_me(client, httpx_mock):
    httpx_mock.add_response(
        json={
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "is_staff": False,
            "plan": [{"name": "Pro", "status": "active"}],
        }
    )
    user = client.me()
    assert user.email == "alice@example.com"
    assert user.first_name == "Alice"


def test_balance(client, httpx_mock):
    httpx_mock.add_response(json={"available": 5000, "consumed": 1200, "used_slots": 2, "total_available_slots": 5})
    balance = client.balance()
    assert balance.available == 5000
    assert balance.used_slots == 2
