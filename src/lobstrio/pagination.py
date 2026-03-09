from __future__ import annotations

from typing import Any, Callable, Generic, Iterator, TypeVar

T = TypeVar("T")


class PageIterator(Generic[T], Iterator[T]):
    """Lazy iterator that auto-fetches next pages from paginated API endpoints."""

    def __init__(
        self,
        fetch_page: Callable[..., dict[str, Any]],
        model_cls: type[T],
        *,
        data_key: str = "data",
        **params: Any,
    ) -> None:
        self._fetch = fetch_page
        self._model = model_cls
        self._data_key = data_key
        self._params = params
        self._page = params.pop("page", 1)
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
        data = self._fetch(page=self._page, **self._params)

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

        # Detect last page
        if isinstance(data, dict):
            total_pages = data.get("total_pages")
            if total_pages is not None and self._page > total_pages:
                self._done = True
