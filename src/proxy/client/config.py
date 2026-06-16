"""Configuration for DMEProxyClient — env vars with constructor override."""

import os
from dataclasses import dataclass, field


@dataclass
class ProxyClientConfig:
    """Client configuration.

    Constructor args take precedence over environment variables.
    """

    server: str = field(
        default_factory=lambda: os.environ.get("DME_PROXY_SERVER", "http://127.0.0.1:8000")
    )
    endpoint: str = field(
        default_factory=lambda: os.environ.get("DME_API_ENDPOINT", "")
    )
    username: str | None = field(
        default_factory=lambda: os.environ.get("DME_API_USERNAME")
    )
    password: str | None = field(
        default_factory=lambda: os.environ.get("DME_API_PASSWORD")
    )
    response_limit: int = 20000

    def __post_init__(self) -> None:
        if not self.endpoint:
            raise ValueError(
                "DME endpoint is required — set DME_API_ENDPOINT or pass endpoint="
            )
        if not self.username or not self.password:
            raise ValueError(
                "DME username and password are required — "
                "set DME_API_USERNAME and DME_API_PASSWORD or pass username=, password="
            )
