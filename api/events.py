"""In-process SSE event bus.

The orchestrator calls `emit(run_id, event_dict)` after each step from a
background thread. The SSE endpoint subscribes with `subscribe(run_id)` and
gets an async generator that yields events as they arrive.

Design: one asyncio.Queue per active run_id. The event loop is captured at
subscribe-time (inside the async context) so that `call_soon_threadsafe` from
the worker thread always targets the correct running loop.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._loop:   asyncio.AbstractEventLoop | None = None

    def emit(self, run_id: str, event: dict) -> None:
        """Called from the orchestrator thread. Routes event to all subscriber queues."""
        if self._loop is None:
            return
        for q in list(self._queues.get(run_id, [])):
            self._loop.call_soon_threadsafe(q.put_nowait, event)

    def finish(self, run_id: str) -> None:
        """Signal end-of-run to all subscribers (sentinel None)."""
        if self._loop is None:
            return
        for q in list(self._queues.get(run_id, [])):
            self._loop.call_soon_threadsafe(q.put_nowait, None)

    async def subscribe(self, run_id: str) -> AsyncGenerator[dict, None]:
        """Async generator — yields events until run finishes."""
        # Capture the running event loop while we're inside async context.
        self._loop = asyncio.get_running_loop()

        q: asyncio.Queue = asyncio.Queue()
        self._queues[run_id].append(q)
        try:
            while True:
                event = await q.get()
                if event is None:   # sentinel: run finished
                    break
                yield event
        finally:
            self._queues[run_id].remove(q)
            if not self._queues[run_id]:
                del self._queues[run_id]


# Singleton used by both the API router and the live endpoint
bus = EventBus()


def format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
