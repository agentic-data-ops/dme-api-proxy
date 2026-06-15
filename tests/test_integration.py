"""Integration tests — end-to-end proxy flow tested at handler level."""

import asyncio
import pytest
from proxy.models import ProxyRequest, ProxyResponse
from proxy.queue.memory import MemoryQueue
from proxy.server.handler import ProxyHandler


@pytest.mark.asyncio
async def test_handler_request_response_cycle():
    """ProxyHandler full cycle: publish request → consume → publish response → receive."""
    queue = MemoryQueue(response_timeout=5.0)
    handler = ProxyHandler(queue)

    # 1. Publish a request
    req = ProxyRequest(
        request_id="int-1",
        method="POST",
        uri="/api/v1/data",
        headers={"Content-Type": "application/json"},
        params={"fmt": "json"},
        body='{"a": 1}',
    )

    # 2. Start handle_request in background (it will block waiting for response)
    async def proxy_call():
        return await handler.handle_request(req)

    task = asyncio.create_task(proxy_call())
    await asyncio.sleep(0.05)

    # 3. Poll the request (simulate client)
    polled = await handler.poll_request()
    assert polled is not None
    assert polled.request_id == "int-1"
    assert polled.method == "POST"
    assert polled.uri == "/api/v1/data"
    assert polled.body == '{"a": 1}'

    # 4. Submit response (simulate client callback)
    resp = ProxyResponse(
        request_id="int-1",
        status_code=200,
        headers={"X-Result": "success"},
        body='{"ok": true}',
    )
    await handler.submit_response(resp)

    # 5. The original handle_request should now return the response
    result = await asyncio.wait_for(task, timeout=5)
    assert result.status_code == 200
    assert result.body.decode("utf-8") == '{"ok": true}'


@pytest.mark.asyncio
async def test_handler_poll_empty():
    queue = MemoryQueue()
    handler = ProxyHandler(queue)
    result = await handler.poll_request()
    assert result is None


@pytest.mark.asyncio
async def test_handler_timeout_returns_504():
    queue = MemoryQueue()
    handler = ProxyHandler(queue)

    req = ProxyRequest(
        request_id="timeout-1",
        method="GET",
        uri="/slow",
        headers={},
        params={},
    )
    resp = await handler.handle_request(req)
    assert resp.status_code == 504
