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
    parser.add_argument("--once", action="store_true", help="Single poll cycle, then exit")
    args = parser.parse_args()

    config = ProxyClientConfig(
        server=args.server or ProxyClientConfig().server,
        endpoint=args.endpoint or ProxyClientConfig().endpoint,
        username=args.username,
        password=args.password,
    )

    client = DMEProxyClient(config)

    if args.once:
        asyncio.run(client.poll_once())
    else:
        asyncio.run(client.run())


if __name__ == "__main__":
    main()
