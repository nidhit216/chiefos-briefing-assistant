import asyncio
import time

import pytest
from fastapi import HTTPException

from app.services.cancellation import run_cancellable


class FakeRequest:
    """Stands in for fastapi.Request — returns is_disconnected() values from a queue."""

    def __init__(self, disconnect_sequence):
        self._sequence = list(disconnect_sequence)
        self.calls = 0

    async def is_disconnected(self) -> bool:
        self.calls += 1
        if not self._sequence:
            raise AssertionError("is_disconnected() called more times than expected")
        return self._sequence.pop(0)


async def test_returns_result_when_coro_finishes_before_any_disconnect_check():
    async def quick():
        return "done"

    # empty sequence: is_disconnected() must never be consulted since the
    # coroutine already finished by the time asyncio.wait() returns
    request = FakeRequest([])
    result = await run_cancellable(request, quick())
    assert result == "done"


async def test_cancels_promptly_when_client_disconnects_mid_flight():
    cancelled = False

    async def slow():
        nonlocal cancelled
        try:
            await asyncio.sleep(5)
            return "should not get here"
        except asyncio.CancelledError:
            cancelled = True
            raise

    # not disconnected on first poll, disconnected on second poll (~1s in)
    request = FakeRequest([False, True])
    start = time.monotonic()
    with pytest.raises(HTTPException) as exc_info:
        await run_cancellable(request, slow())
    elapsed = time.monotonic() - start

    assert exc_info.value.status_code == 499
    assert cancelled is True
    assert elapsed < 3, f"expected cancellation well before the 5s sleep, took {elapsed}s"


async def test_cancels_immediately_when_already_disconnected():
    async def slow():
        await asyncio.sleep(5)
        return "should not get here"

    request = FakeRequest([True])
    start = time.monotonic()
    with pytest.raises(HTTPException) as exc_info:
        await run_cancellable(request, slow())
    elapsed = time.monotonic() - start

    assert exc_info.value.status_code == 499
    assert elapsed < 1.5


async def test_propagates_exception_raised_by_the_coroutine_itself():
    async def failing():
        raise ValueError("boom")

    request = FakeRequest([])
    with pytest.raises(ValueError, match="boom"):
        await run_cancellable(request, failing())
