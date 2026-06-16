"""DMEProxyClient — polls proxy server and forwards requests to DME.

Implements automatic login to DME (reference: DMEAPIClient from pydme SDK).
Login flow: PUT {endpoint}/rest/plat/smapp/v1/sessions → X-Auth-Token.
"""

import asyncio
import json
import logging
import time
import httpx
from proxy.models import ProxyRequest, ProxyResponse
from proxy.client.config import ProxyClientConfig

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "Content-Type": "application/json;charset=utf8",
    "Accept": "application/json",
}
LOGIN_PATH = "/rest/plat/smapp/v1/sessions"
SESSION_TIMEOUT = 900  # seconds before re-login
REQUEST_TIMEOUT = 30
VERIFY_SSL = False


class DMEProxyClient:
    """Client that polls the proxy server request queue and forwards to DME."""

    def __init__(self, config: ProxyClientConfig | None = None) -> None:
        self._config = config or ProxyClientConfig()
        self._base_url = self._config.endpoint.rstrip("/")
        self._headers = dict(DEFAULT_HEADERS)
        self._last_accessed: float = 0

        # Auto-login on startup
        self._login()
        logger.info("Logged in to DME endpoint: %s", self._config.endpoint)

    # ── auth ────────────────────────────────────────────────────────────

    def _login(self) -> None:
        """Authenticate with DME using username/password.

        PUT {endpoint}/rest/plat/smapp/v1/sessions
        Response: {"accessSession": "..."} → sets X-Auth-Token header.
        """
        url = f"{self._base_url}{LOGIN_PATH}"
        body = {
            "grantType": "password",
            "userName": self._config.username,
            "value": self._config.password,
        }
        with httpx.Client(trust_env=False, verify=VERIFY_SSL, timeout=REQUEST_TIMEOUT) as c:
            resp = c.put(url, headers=self._headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError(
                f"DME login failed (HTTP {resp.status_code}): {resp.text}"
            )
        self._headers["X-Auth-Token"] = resp.json()["accessSession"]
        self._last_accessed = time.time()

    def _ensure_session(self) -> None:
        """Re-login if the session has timed out."""
        if time.time() - self._last_accessed > SESSION_TIMEOUT:
            logger.info("DME session timed out, re-logging in")
            self._login()
        self._last_accessed = time.time()

    # ── public API ──────────────────────────────────────────────────────

    async def run(self) -> None:
        """Run the polling loop indefinitely."""
        logger.info(
            "DMEProxyClient starting — server=%s, endpoint=%s",
            self._config.server,
            self._config.endpoint,
        )
        async with (
            httpx.AsyncClient() as http,
            httpx.AsyncClient(trust_env=False, verify=VERIFY_SSL) as dme_http,
        ):
            while True:
                try:
                    req = await self._poll(http)
                    if req is None:
                        await asyncio.sleep(0.5)
                        continue
                    resp = await self._forward_to_dme(req, dme_http)
                    await self._callback(http, resp)
                except Exception:
                    logger.exception("Poll cycle failed")

    async def poll_once(self) -> None:
        """Single poll cycle — for one-shot / testing use."""
        async with (
            httpx.AsyncClient() as http,
            httpx.AsyncClient(trust_env=False, verify=VERIFY_SSL) as dme_http,
        ):
            req = await self._poll(http)
            if req is None:
                logger.info("No pending request")
                return
            resp = await self._forward_to_dme(req, dme_http)
            await self._callback(http, resp)

    # ── internal: poll → forward → callback ────────────────────────────

    async def _poll(self, http: httpx.AsyncClient) -> ProxyRequest | None:
        url = f"{self._config.server}/api/v1/proxy/poll"
        r = await http.get(url, timeout=10)
        if r.status_code == 204:
            return None
        r.raise_for_status()
        data = r.json()
        return ProxyRequest(**data)

    async def _forward_to_dme(
        self, req: ProxyRequest, http: httpx.AsyncClient
    ) -> ProxyResponse:
        """Forward a proxied request to DME.

        The external request's original headers (from ProxyRequest.headers)
        are passed through to DME, merged on top of the auth headers.
        """
        self._ensure_session()

        # ── Separate path params from query params ──
        path_params: dict[str, str] = {}
        query_params: dict[str, str] = {}
        if req.params:
            for k, v in req.params.items():
                if f"{{{k}}}" in req.uri:
                    path_params[k] = v
                else:
                    query_params[k] = v

        # ── Parse body ──
        body_dict: dict | str | None = None
        if req.body:
            try:
                body_dict = json.loads(req.body)
            except (json.JSONDecodeError, TypeError):
                body_dict = req.body

        # ── Build URL ──
        url = f"{self._base_url}{req.uri.format(**path_params)}"

        # ── Merge headers: auth headers base + request headers override ──
        merged_headers = dict(self._headers)
        for k, v in req.headers.items():
            if k.lower() not in ("host", "content-length"):
                merged_headers[k] = v

        # ── Make the call ──
        r = await http.request(
            method=req.method,
            url=url,
            params=query_params or None,
            headers=merged_headers,
            json=body_dict if isinstance(body_dict, dict) else None,
            content=json.dumps(body_dict) if isinstance(body_dict, str) else None,
            timeout=REQUEST_TIMEOUT,
        )

        return ProxyResponse(
            request_id=req.request_id,
            status_code=r.status_code,
            headers=dict(r.headers),
            body=r.text,
        )

    async def _callback(self, http: httpx.AsyncClient, resp: ProxyResponse) -> None:
        url = f"{self._config.server}/api/v1/proxy/respond"
        r = await http.post(url, json=resp.model_dump(), timeout=10)
        r.raise_for_status()
        logger.info("Responded request_id=%s status=%d", resp.request_id, resp.status_code)
