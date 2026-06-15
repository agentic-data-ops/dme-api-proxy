"""Data models for proxy request/response messages."""

from pydantic import BaseModel


class ProxyRequest(BaseModel):
    """A proxied REST API request enqueued by the server."""

    request_id: str
    method: str
    uri: str
    headers: dict[str, str]
    params: dict[str, str]
    body: str | None = None


class ProxyResponse(BaseModel):
    """A proxied REST API response to be delivered back to the caller."""

    request_id: str
    status_code: int
    headers: dict[str, str]
    body: str | None = None
