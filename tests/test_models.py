"""Tests for data models."""

from proxy.models import ProxyRequest, ProxyResponse


class TestProxyRequest:
    def test_create(self):
        req = ProxyRequest(
            request_id="abc-123",
            method="POST",
            uri="/api/v1/objects",
            headers={"Content-Type": "application/json"},
            params={"foo": "bar"},
            body='{"key": "value"}',
        )
        assert req.request_id == "abc-123"
        assert req.method == "POST"
        assert req.body == '{"key": "value"}'

    def test_json_roundtrip(self):
        req = ProxyRequest(
            request_id="x",
            method="GET",
            uri="/health",
            headers={},
            params={},
            body=None,
        )
        data = req.model_dump()
        restored = ProxyRequest(**data)
        assert restored.request_id == req.request_id
        assert restored.method == req.method
        assert restored.body is None

    def test_optional_body_none(self):
        req = ProxyRequest(
            request_id="1", method="GET", uri="/", headers={}, params={}
        )
        assert req.body is None


class TestProxyResponse:
    def test_create(self):
        resp = ProxyResponse(
            request_id="abc-123",
            status_code=200,
            headers={"X-Custom": "val"},
            body='{"result": "ok"}',
        )
        assert resp.status_code == 200

    def test_json_roundtrip(self):
        resp = ProxyResponse(
            request_id="r", status_code=404, headers={}, body="Not Found"
        )
        data = resp.model_dump()
        restored = ProxyResponse(**data)
        assert restored.status_code == 404
