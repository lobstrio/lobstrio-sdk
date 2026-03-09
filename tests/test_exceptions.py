from lobstrio.exceptions import APIError, AuthError, NotFoundError, RateLimitError


def test_exception_hierarchy():
    assert issubclass(AuthError, APIError)
    assert issubclass(NotFoundError, APIError)
    assert issubclass(RateLimitError, APIError)


def test_api_error_attrs():
    err = APIError(400, "bad request", {"error": "bad"})
    assert err.status_code == 400
    assert err.message == "bad request"
    assert err.body == {"error": "bad"}
    assert "[400]" in str(err)


def test_rate_limit_retry_after():
    err = RateLimitError(429, "slow down", retry_after="30")
    assert err.retry_after == "30"
