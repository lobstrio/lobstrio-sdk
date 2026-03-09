def test_crawlers_list(client, httpx_mock):
    httpx_mock.add_response(
        json={
            "data": [
                {
                    "id": "c1",
                    "name": "Google Maps",
                    "slug": "google-maps",
                    "credits_per_row": {"current": 3, "legacy": 1},
                    "max_concurrency": 5,
                    "is_available": True,
                    "is_premium": False,
                },
                {
                    "id": "c2",
                    "name": "Twitter Search",
                    "slug": "twitter-search",
                    "credits_per_row": 2,
                    "max_concurrency": 3,
                    "is_available": True,
                    "is_premium": True,
                },
            ]
        }
    )
    crawlers = client.crawlers.list()
    assert len(crawlers) == 2
    assert crawlers[0].name == "Google Maps"
    assert crawlers[0].credits_per_row == 3
    assert crawlers[1].credits_per_row == 2
    assert crawlers[1].is_premium is True


def test_crawlers_list_bare_array(client, httpx_mock):
    httpx_mock.add_response(json=[{"id": "c1", "name": "Test"}])
    crawlers = client.crawlers.list()
    assert len(crawlers) == 1


def test_crawlers_get(client, httpx_mock):
    httpx_mock.add_response(
        json={
            "id": "c1",
            "name": "Google Maps",
            "slug": "google-maps",
            "description": "Scrape Google Maps",
            "credits_per_row": 3,
            "max_concurrency": 5,
            "rank": 1,
        }
    )
    c = client.crawlers.get("c1")
    assert c.id == "c1"
    assert c.description == "Scrape Google Maps"


def test_crawlers_params(client, httpx_mock):
    httpx_mock.add_response(
        json={
            "task": {"url": {"type": "string", "required": True}},
            "squid": {
                "max_results": {"default": 100},
                "functions": {"email_finder": {"credits_per_function": 5}},
            },
        }
    )
    p = client.crawlers.params("c1")
    assert "url" in p.task_params
    assert "email_finder" in p.functions
    assert "functions" not in p.squid_params
