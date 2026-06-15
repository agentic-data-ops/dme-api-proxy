"""Abstract interface for the proxy message queue."""

from abc import ABC, abstractmethod
from proxy.models import ProxyRequest, ProxyResponse


class MessageQueue(ABC):
    """Message queue for passing proxy requests and responses."""

    @abstractmethod
    async def publish_request(self, req: ProxyRequest) -> None: ...

    @abstractmethod
    async def consume_request(self) -> ProxyRequest | None: ...

    @abstractmethod
    async def publish_response(self, resp: ProxyResponse) -> None: ...

    @abstractmethod
    async def consume_response(self, request_id: str) -> ProxyResponse | None: ...
