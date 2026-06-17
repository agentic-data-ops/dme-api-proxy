"""CLI entry: dme-proxy-server."""

import argparse
import uvicorn
from proxy.queue.memory import MemoryQueue
from proxy.server.app import init_app


def main() -> None:
    parser = argparse.ArgumentParser(description="DME Proxy Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=80, help="Bind port")
    parser.add_argument("--request-timeout", type=int, default=300,
                        help="Max seconds to wait for a proxy client to consume a request (default: 300)")
    parser.add_argument("--queue-max-length", type=int, default=100,
                        help="Max number of pending requests in the queue (default: 100)")
    args = parser.parse_args()

    queue = MemoryQueue(
        response_timeout=args.request_timeout,
        max_queue_length=args.queue_max_length,
    )
    app = init_app(queue)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
