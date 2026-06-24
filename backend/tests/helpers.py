"""Shared test doubles for mocking outbound httpx.AsyncClient calls (Google OAuth/Calendar/Gmail)."""


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}

    def json(self):
        return self._json


class FakeAsyncClient:
    """Returns queued responses in call order, regardless of which method/URL is used."""

    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, *args, **kwargs):
        return self._responses.pop(0)

    async def post(self, *args, **kwargs):
        return self._responses.pop(0)


def fake_async_client_factory(responses):
    """Returns a callable that mimics `httpx.AsyncClient` and always yields the same queue."""
    def _factory(*args, **kwargs):
        return FakeAsyncClient(responses)
    return _factory
