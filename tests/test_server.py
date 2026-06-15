"""Tests for Proxy Server FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from proxy.queue.memory import MemoryQueue
from proxy.server.app import init_app


@pytest.fixture
def client():
    queue = MemoryQueue(response_timeout=0.5)
    app = init_app(queue)
    return TestClient(app)


class TestHealth:
    def test_health(self, client):
        r = client.get("/api/v1/proxy/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestProxyEndpoint:
    def test_get_request_times_out(self, client):
        """Without a client polling, proxy requests time out with 504."""
        r = client.get("/api/v1/objects", params={"id": "42"})
        assert r.status_code == 504

    def test_post_with_body_times_out(self, client):
        r = client.post(
            "/api/v1/objects",
            json={"name": "test"},
            headers={"X-Custom": "val"},
        )
        assert r.status_code == 504

    def test_put_and_delete_time_out(self, client):
        r1 = client.put("/api/v1/objects/1", json={"name": "updated"})
        assert r1.status_code == 504
        r2 = client.delete("/api/v1/objects/1")
        assert r2.status_code == 504


class TestPollRespond:
    def test_poll_empty(self, client):
        r = client.get("/api/v1/proxy/poll")
        assert r.status_code == 204

    def test_poll_after_request(self, client):
        """A proxy request enqueues a message; poll retrieves it."""
        # Send a request (it will timeout, but the message is enqueued)
        client.get("/api/v1/test/something")

        # Poll should find the enqueued request
        r = client.get("/api/v1/proxy/poll")
        assert r.status_code == 200
        data = r.json()
        assert data["method"] == "GET"
        assert "/test/something" in data["uri"]

    def test_respond_works(self, client):
        """Submitting a response returns 200."""
        r = client.post(
            "/api/v1/proxy/respond",
            json={
                "request_id": "test-1",
                "status_code": 200,
                "headers": {},
                "body": "ok",
            },
        )
        assert r.status_code == 200

    def test_poll_then_respond_cycle(self, client):
        """Smoke test: proxy → poll → respond endpoints all work in sequence."""
        # health
        assert client.get("/api/v1/proxy/health").status_code == 200

        # trigger enqueue
        client.get("/api/v1/proxy/test-cycle")

        # poll
        r = client.get("/api/v1/proxy/poll")
        assert r.status_code == 200
        data = r.json()

        # respond
        r2 = client.post(
            "/api/v1/proxy/respond",
            json={
                "request_id": data["request_id"],
                "status_code": 200,
                "headers": {"X-Test": "1"},
                "body": '{"done": true}',
            },
        )
        assert r2.status_code == 200
