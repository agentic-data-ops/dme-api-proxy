"""Tests for Proxy Client configuration."""

import os
from proxy.client.config import ProxyClientConfig


class TestProxyClientConfig:
    def test_defaults_with_endpoint(self):
        cfg = ProxyClientConfig(
            endpoint="http://dme.example.com",
            username="admin",
            password="secret",
        )
        assert cfg.endpoint == "http://dme.example.com"
        assert cfg.server == "http://127.0.0.1:8000"
        assert cfg.username == "admin"
        assert cfg.password == "secret"

    def test_missing_endpoint_raises(self):
        if "DME_API_ENDPOINT" in os.environ:
            del os.environ["DME_API_ENDPOINT"]
        try:
            ProxyClientConfig(username="u", password="p")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_missing_credentials_raises(self):
        if "DME_API_USERNAME" in os.environ:
            del os.environ["DME_API_USERNAME"]
        if "DME_API_PASSWORD" in os.environ:
            del os.environ["DME_API_PASSWORD"]
        try:
            ProxyClientConfig(endpoint="http://dme.example.com")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_constructor_overrides_env(self):
        os.environ["DME_PROXY_SERVER"] = "http://from-env:9000"
        os.environ["DME_API_ENDPOINT"] = "http://from-env-dme/api"
        os.environ["DME_API_USERNAME"] = "env-user"
        os.environ["DME_API_PASSWORD"] = "env-pass"
        try:
            cfg = ProxyClientConfig(
                server="http://explicit:8000",
                endpoint="http://explicit-dme/api",
                username="explicit-user",
                password="explicit-pass",
            )
            assert cfg.server == "http://explicit:8000"
            assert cfg.endpoint == "http://explicit-dme/api"
            assert cfg.username == "explicit-user"
        finally:
            for k in ["DME_PROXY_SERVER", "DME_API_ENDPOINT",
                      "DME_API_USERNAME", "DME_API_PASSWORD"]:
                os.environ.pop(k, None)

    def test_env_vars_fallback(self):
        os.environ["DME_PROXY_SERVER"] = "http://env-srv:8000"
        os.environ["DME_API_ENDPOINT"] = "http://env-dme/api"
        os.environ["DME_API_USERNAME"] = "admin"
        os.environ["DME_API_PASSWORD"] = "secret"
        try:
            cfg = ProxyClientConfig()
            assert cfg.server == "http://env-srv:8000"
            assert cfg.endpoint == "http://env-dme/api"
            assert cfg.username == "admin"
            assert cfg.password == "secret"
        finally:
            for k in ["DME_PROXY_SERVER", "DME_API_ENDPOINT",
                      "DME_API_USERNAME", "DME_API_PASSWORD"]:
                os.environ.pop(k, None)
