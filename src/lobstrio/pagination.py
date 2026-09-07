from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class PageIterator(Generic[T], Iterator[T]):
    """Lazy iterator that auto-fetches next pages from paginated API endpoints."""

    def __init__(
        self,
        fetch_page: Callable[..., dict[str, Any]],
        model_cls: type[T],
        *,
        data_key: str = "data",
        max_pages: int | None = None,
        **params: Any,
    ) -> None:
        self._fetch = fetch_page
        self._model = model_cls
        self._data_key = data_key
        self._params = params
        self._page = params.pop("page", 1)
        # Cap the number of pages fetched. None (the default) walks every page;
        # set it as a safety limit against a runaway total_pages.
        self._max_pages = max_pages
        self._pages_fetched = 0
        self._buffer: list[T] = []
        self._done = False

    def __iter__(self) -> PageIterator[T]:
        return self

    def __next__(self) -> T:
        if self._buffer:
            return self._buffer.pop(0)
        if self._done:
            raise StopIteration
        self._load_next_page()
        if not self._buffer:
            raise StopIteration
        return self._buffer.pop(0)

    def _load_next_page(self) -> None:
        if self._max_pages is not None and self._pages_fetched >= self._max_pages:
            self._done = True
            return

        data = self._fetch(page=self._page, **self._params)
        self._pages_fetched += 1

        items = data.get(self._data_key, data) if isinstance(data, dict) else data
        if not items:
            self._done = True
            return

        from_api = getattr(self._model, "from_api", None)
        if from_api:
            self._buffer = [from_api(item) for item in items]
        else:
            self._buffer = list(items)

        self._page += 1

        # A bare-list response carries no pagination envelope, so treat it as the
        # only page — otherwise a loose endpoint that keeps returning the same
        # list would iterate forever.
        if not isinstance(data, dict):
            self._done = True
            return

        # Detect last page
        total_pages = data.get("total_pages")
        if total_pages is not None and self._page > total_pages:
            self._done = True
