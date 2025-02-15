from typing import Any, Dict, Optional

from yarl import URL

from ..utils.jsonenc import loads
from ..utils.multipart import parse_multipart
from ..utils.query import parse_qs

async def from_asgi(scope: Dict[str, Any], receive: Any):
    headers = {
        key.decode("utf-8"): value.decode("utf-8")
        for key, value in scope["headers"]
    }
    response_body = b""
    while True:
        message = await receive()
        response_body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    if scope["method"].lower() == "POST" or scope["method"].lower() == "PUT":
        if 'multipart/form-data' in headers["content-type"]:
            response_body = await parse_multipart(scope, receive)
        else:
            response_body = response_body.decode("utf-8")
    else:
        response_body = response_body.decode("utf-8")
    return Request(
        method=scope["method"].upper(),
        url=URL(f"{scope['scheme']}://{headers['host']}{scope['path']}"),
        headers=headers,
        query=parse_qs(scope["query_string"]),
        body=response_body,
    )

class Request:
    def __init__(self, method: str, url: str | URL, headers: Dict[str, str]={}, query: Dict[str, str]={}, body: Any=""):
        self.method: str = method
        self.url: URL = url if isinstance(url, URL) else URL(url)
        self.headers: Optional[Dict[str, str]] = headers
        self.query: Optional[Dict[str, Any]] = query
        self.body: Optional[Any] = body

    def json(self) -> dict: return loads(self.body).decode("utf-8")