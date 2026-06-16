"""CLI entry: dme-proxy-client."""

import argparse
import asyncio
import logging
from proxy.client.config import ProxyClientConfig
from proxy.client.client import DMEProxyClient


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="DME Proxy Client")
    parser.add_argument("--server", help="Proxy server URL (or DME_PROXY_SERVER)")
    parser.add_argument("--endpoint", help="DME API endpoint (or DME_API_ENDPOINT)")
    parser.add_argument("--username", help="DME username (or DME_API_USERNAME)")
    parser.add_argument("--password", help="DME password (or DME_API_PASSWORD)")
    parser.add_argument("--response-limit", type=int, default=500,
                        help="Max response body length from DME (default: 500)")
    parser.add_argument("--once", action="store_true", help="Single poll cycle, then exit")
    args = parser.parse_args()

    # Only pass explicitly provided args; let dataclass defaults
    # (which read env vars) handle the rest
    kwargs: dict[str, object] = {}
    if args.server:
        kwargs["server"] = args.server
    if args.endpoint:
        kwargs["endpoint"] = args.endpoint
    if args.username:
        kwargs["username"] = args.username
    if args.password:
        kwargs["password"] = args.password
    kwargs["response_limit"] = args.response_limit
    config = ProxyClientConfig(**kwargs)

    client = DMEProxyClient(config)

    if args.once:
        asyncio.run(client.poll_once())
    else:
        asyncio.run(client.run())


if __name__ == "__main__":
    main()
