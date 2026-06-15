"""Request/response handling logic for the Proxy Server."""

from fastapi import Response
from proxy.models import ProxyRequest, ProxyResponse
from proxy.queue.interface import MessageQueue


class ProxyHandler:
    """Manages request publishing and response waiting."""

    def __init__(self, queue: MessageQueue) -> None:
        self._queue = queue

    async def handle_request(self, req: ProxyRequest) -> Response:
        """Publish request to queue + wait for response."""
        await self._queue.publish_request(req)
        resp = await self._queue.consume_response(req.request_id)
        if resp is None:
            return Response("Gateway Timeout", status_code=504)
        return Response(
            content=resp.body,
            status_code=resp.status_code,
            headers=resp.headers,
        )

    async def poll_request(self) -> ProxyRequest | None:
        """Consume a pending request (called by client via /poll)."""
        return await self._queue.consume_request()

    async def submit_response(self, resp: ProxyResponse) -> None:
        """Publish a response back (called by client via /respond)."""
        await self._queue.publish_response(resp)
