"""Run a coroutine while watching for client disconnect, cancelling it if the client goes away."""
import asyncio
import contextlib
from typing import Coroutine, TypeVar

from fastapi import HTTPException, Request

T = TypeVar("T")


async def run_cancellable(request: Request, coro: Coroutine[None, None, T]) -> T:
    task = asyncio.ensure_future(coro)
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=0.5)
            if task in done:
                return task.result()
            if await request.is_disconnected():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                raise HTTPException(status_code=499, detail="Cancelled by client")
    finally:
        if not task.done():
            task.cancel()
