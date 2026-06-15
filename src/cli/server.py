"""CLI entry: dme-proxy-server."""

import argparse
import uvicorn
from proxy.queue.memory import MemoryQueue
from proxy.server.app import init_app


def main() -> None:
    parser = argparse.ArgumentParser(description="DME Proxy Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=26335, help="Bind port")
    args = parser.parse_args()

    queue = MemoryQueue()
    app = init_app(queue)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
