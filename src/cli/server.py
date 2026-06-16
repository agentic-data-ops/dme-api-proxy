"""CLI entry: dme-proxy-server."""

import argparse
import uvicorn
from proxy.queue.memory import MemoryQueue
from proxy.server.app import init_app


def main() -> None:
    parser = argparse.ArgumentParser(description="DME Proxy Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=80, help="Bind port")
    parser.add_argument("--request-timeout", type=int, default=30,
                        help="Max seconds to wait for a proxy client to consume a request (default: 30)")
    args = parser.parse_args()

    queue = MemoryQueue(response_timeout=args.request_timeout)
    app = init_app(queue)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
