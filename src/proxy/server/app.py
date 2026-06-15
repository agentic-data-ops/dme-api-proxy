"""FastAPI application for the DME Proxy Server."""

import uuid
from fastapi import FastAPI, Request, Response
from proxy.models import ProxyRequest, ProxyResponse
from proxy.queue.interface import MessageQueue
from proxy.server.handler import ProxyHandler

app = FastAPI(title="DME Proxy Server")
handler: ProxyHandler | None = None


def init_app(queue: MessageQueue) -> FastAPI:
    """Initialize the FastAPI app with a message queue backend."""
    global handler
    handler = ProxyHandler(queue)
    return app


@app.get("/api/v1/proxy/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/proxy/poll")
async def poll_request():
    """Poll endpoint — client consumes a request from the queue."""
    if handler is None:
        return Response("Server not initialized", status_code=500)
    req = await handler.poll_request()
    if req is None:
        return Response("", status_code=204)
    return req.model_dump()


@app.post("/api/v1/proxy/respond")
async def submit_response(resp: ProxyResponse):
    """Respond endpoint — client submits a DME response back."""
    if handler is None:
        return Response("Server not initialized", status_code=500)
    await handler.submit_response(resp)
    return Response("ok", status_code=200)


@app.get("/")
async def root():
    """Root endpoint — returns pending requests in the queue."""
    if handler is None:
        return Response("Server not initialized", status_code=500)
    return handler.list_pending()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_entry(path: str, request: Request):
    """Catch-all proxy endpoint — forwards to DME via the message queue."""
    if handler is None:
        return Response("Server not initialized", status_code=500)

    body = await request.body()
    proxy_req = ProxyRequest(
        request_id=str(uuid.uuid4()),
        method=request.method,
        uri=f"/{path}",
        headers=dict(request.headers),
        params=dict(request.query_params),
        body=body.decode("utf-8") if body else None,
    )
    return await handler.handle_request(proxy_req)
