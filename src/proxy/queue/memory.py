"""In-memory message queue using asyncio.Queue."""

import asyncio
from proxy.models import ProxyRequest, ProxyResponse
from proxy.queue.interface import MessageQueue


class MemoryQueue(MessageQueue):
    """In-memory queue for single-process development/testing."""

    def __init__(self, response_timeout: float = 30.0) -> None:
        self._request_queue: asyncio.Queue[ProxyRequest] = asyncio.Queue()
        self._response_map: dict[str, asyncio.Future[ProxyResponse]] = {}
        self._response_timeout = response_timeout

    async def publish_request(self, req: ProxyRequest) -> None:
        await self._request_queue.put(req)

    async def consume_request(self) -> ProxyRequest | None:
        try:
            return await asyncio.wait_for(self._request_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    async def publish_response(self, resp: ProxyResponse) -> None:
        future = self._response_map.get(resp.request_id)
        if future is not None and not future.done():
            future.set_result(resp)

    async def consume_response(self, request_id: str) -> ProxyResponse | None:
        future = asyncio.get_event_loop().create_future()
        self._response_map[request_id] = future
        try:
            return await asyncio.wait_for(future, timeout=self._response_timeout)
        except asyncio.TimeoutError:
            self._response_map.pop(request_id, None)
            return None

    def list_pending(self) -> list[dict]:
        """Snapshot of all queued (not yet consumed) requests."""
        return [
            {"id": req.request_id, "method": req.method, "uri": req.uri}
            for req in list(self._request_queue._queue)
        ]
