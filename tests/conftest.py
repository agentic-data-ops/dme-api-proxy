"""pytest fixtures for DME Proxy tests."""

import pytest
from proxy.queue.memory import MemoryQueue
from proxy.server.handler import ProxyHandler
from proxy.server.app import init_app


@pytest.fixture
def memory_queue():
    return MemoryQueue()


@pytest.fixture
def proxy_handler(memory_queue):
    return ProxyHandler(memory_queue)


@pytest.fixture
def server_app(memory_queue):
    return init_app(memory_queue)
