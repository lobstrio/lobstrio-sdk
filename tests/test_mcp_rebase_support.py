"""Coverage for the additions that let lobstr-mcp build on the SDK:
raw payloads on models, crawlers pagination, a results envelope + run/task
filters, and a User-Agent / transport hook on the client."""
import httpx

from lobstrio import LobstrClient
from lobstrio.models.crawler import Crawler, CrawlerParams
from lobstrio.models.run import RunStats

# --- raw payloads --------------------------------------------------------

def test_crawler_raw_keeps_fields_the_dataclass_renames_or_resolves():
    payload = {
        "id": "gm", "name": "Google Maps", "slug": "google-maps",
        "credits_per_row": {"current": 1, "legacy": 100},
        "result": ["name", "phone"], "input": [{"name": "url"}],
    }
    c = Crawler.from_api(payload)
    assert c.raw == payload                      # exact API payload retained
    assert c.raw["credits_per_row"] == {"current": 1, "legacy": 100}  # raw dict, not the resolved float
    assert c.raw["result"] == ["name", "phone"]  # API key, not result_fields
    assert c.credits_per_row == 1.0              # dataclass still resolves


def test_crawler_params_keeps_functions_and_does_not_mutate_input():
    payload = {"task": {"url": "string"},
               "squid": {"max_results": "int", "functions": {"emails": {"default": True}}}}
    cp = CrawlerParams.from_api(payload)
    assert cp.functions == {"emails": {"default": True}}
    assert cp.squid_params == {"max_results": "int"}          # split out
    assert payload["squid"] == {"max_results": "int", "functions": {"emails": {"default": True}}}  # NOT mutated
    assert cp.raw["squid"]["functions"] == {"emails": {"default": True}}  # raw keeps the original shape


def test_runstats_raw_exposes_fields_the_model_drops():
    payload = {"id": "run1", "status": "running", "percent_done": "50%",
               "is_done": False, "started_at": "2026-09-01T00:00:00Z", "ended_at": None}
    s = RunStats.from_api(payload)
    assert s.raw["started_at"] == "2026-09-01T00:00:00Z"   # not a dataclass field, but in raw
    assert s.raw["status"] == "running"
    assert s.percent_done == "50%"


# --- crawlers pagination -------------------------------------------------

def test_crawlers_iter_paginates(client, httpx_mock):
    httpx_mock.add_response(json={"data": [{"id": "a", "name": "A", "slug": "a"}], "total_pages": 2})
    httpx_mock.add_response(json={"data": [{"id": "b", "name": "B", "slug": "b"}], "total_pages": 2})
    got = [c.id for c in client.crawlers.iter()]
    assert got == ["a", "b"]


# --- results envelope + run/task filters --------------------------------

def test_results_page_returns_envelope_and_supports_run_filter(client, httpx_mock):
    httpx_mock.add_response(json={
        "total_results": 87, "page": 1, "total_pages": 9,
        "next": "https://api.lobstr.io/v1/results?run=r1&page=2",
        "data": [{"name": "Deansgate Dental"}],
    })
    env = client.results.page(run="r1")
    assert env["total_results"] == 87
    assert env["total_pages"] == 9
    assert env["next"].endswith("page=2")
    assert env["data"][0]["name"] == "Deansgate Dental"
    req = httpx_mock.get_requests()[0]
    assert "run=r1" in str(req.url)          # filtered by run, not squid


# --- User-Agent + transport hook ----------------------------------------

def test_user_agent_header_is_sent(httpx_mock):
    httpx_mock.add_response(json={"available": 5, "consumed": 1})
    c = LobstrClient(token="t", base_url="https://api.lobstr.io/v1/", user_agent="lobstr-mcp/9.9")
    c.balance()
    assert httpx_mock.get_requests()[0].headers["user-agent"] == "lobstr-mcp/9.9"


def test_transport_hook_is_used():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"available": 42, "consumed": 0})
    c = LobstrClient(token="t", base_url="https://api.lobstr.io/v1/",
                     transport=httpx.MockTransport(handler))
    assert c.balance().available == 42
