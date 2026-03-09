from dataclasses import dataclass

from lobstrio.pagination import PageIterator


@dataclass
class FakeItem:
    id: str
    name: str

    @classmethod
    def from_api(cls, data):
        return cls(id=data["id"], name=data["name"])


def test_single_page():
    calls = []

    def fetch(**params):
        calls.append(params)
        return {"data": [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}], "total_pages": 1}

    it = PageIterator(fetch, FakeItem, limit=10)
    items = list(it)
    assert len(items) == 2
    assert items[0].id == "1"
    assert len(calls) == 1


def test_multi_page():
    def fetch(**params):
        page = params["page"]
        if page == 1:
            return {"data": [{"id": "1", "name": "a"}], "total_pages": 2}
        elif page == 2:
            return {"data": [{"id": "2", "name": "b"}], "total_pages": 2}
        return {"data": []}

    it = PageIterator(fetch, FakeItem, limit=1)
    items = list(it)
    assert len(items) == 2
    assert items[1].name == "b"


def test_empty_response():
    def fetch(**params):
        return {"data": [], "total_pages": 0}

    it = PageIterator(fetch, FakeItem)
    items = list(it)
    assert items == []


def test_dict_model_no_from_api():
    """When model_cls is dict (for results), items pass through as-is."""

    def fetch(**params):
        return {"data": [{"email": "test@example.com"}], "total_pages": 1}

    it = PageIterator(fetch, dict)
    items = list(it)
    assert len(items) == 1
    assert items[0]["email"] == "test@example.com"
