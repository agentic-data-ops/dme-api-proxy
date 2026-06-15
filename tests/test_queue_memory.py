"""Tests for MemoryQueue."""

import pytest
from proxy.models import ProxyRequest, ProxyResponse
from proxy.queue.memory import MemoryQueue


@pytest.mark.asyncio
async def test_publish_and_consume_request():
    q = MemoryQueue()
    req = ProxyRequest(
        request_id="r1",
        method="GET",
        uri="/test",
        headers={},
        params={},
    )
    await q.publish_request(req)
    consumed = await q.consume_request()
    assert consumed is not None
    assert consumed.request_id == "r1"


@pytest.mark.asyncio
async def test_consume_request_empty():
    q = MemoryQueue()
    result = await q.consume_request()
    assert result is None


@pytest.mark.asyncio
async def test_publish_and_consume_response():
    q = MemoryQueue()
    resp = ProxyResponse(
        request_id="r1",
        status_code=200,
        headers={},
        body="ok",
    )
    # Start consumer first, then publish
    async def consume():
        return await q.consume_response("r1")

    import asyncio
    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)  # let consumer register
    await q.publish_response(resp)
    result = await task
    assert result is not None
    assert result.request_id == "r1"
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_consume_response_timeout():
    q = MemoryQueue()
    q = MemoryQueue(response_timeout=0.5)
    result = await q.consume_response("nonexistent")
    assert result is None
