import pytest

from lobstrio import LobstrClient


@pytest.fixture
def client(httpx_mock):
    """Create a LobstrClient pointed at a mock server."""
    return LobstrClient(token="test-token", base_url="https://api.lobstr.io/v1/")
