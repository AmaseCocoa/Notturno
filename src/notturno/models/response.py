import asyncio
from typing import Any, Dict, Optional, Union

import h2
import h2.connection
import h11

from ..utils import jsonenc


class Response:
    def __init__(
        self,
        body: Optional[Union[Dict[str, Any], Any, str, bytes]] = "",
        headers: Dict[str, str] = {},
        status_code: int = 200,
        content_type: Union[str, None] = None,
    ):
        self.body: Optional[Union[Dict[str, Any], Any, str, bytes]] = body
        self.headers: Dict[str, str] = headers
        self.status_code: Optional[int] = status_code
        self.content_type: Union[str, None] = content_type

    def __export(self):
        if isinstance(self.body, dict):
            return jsonenc.dumps(self.body)
        elif isinstance(self.body, str):
            return self.body.encode("utf-8")
        return self.body

    async def _asgi(self, send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [
                    [key.encode("utf-8"), value.encode("utf-8")]
                    for key, value in self.headers.items()
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": self.body,
                "more_body": False,
            }
        )

    async def _http(self, conn: h11.Connection, writer: asyncio.StreamWriter):
        body = self.__export(self.body)
        self.headers["Content-Length"] = len(body)
        response = h11.Response(status_code=self.status_code)
        for key, value in self.headers.items():
            response.headers.append((key.encode("utf-8"), value.encode("utf-8")))
        conn.send(response)
        conn.send(h11.Data(data=body))
        conn.send(h11.EndOfMessage())
        writer.write(conn.send(h11.EndOfMessage()))

    async def _http2(self, stream_id, connection: h2.connection.H2Connection, writer: asyncio.StreamWriter, reader: asyncio.StreamReader):
        body = self.__export(self.body)
        self.headers["Content-Length"] = len(body)
        connection.send_headers(stream_id, [(key, value) for key, value in self.headers.items()])
        connection.send_data(stream_id, body, end_stream=True)
        data_to_send = connection.data_to_send()
        if data_to_send:
            writer.write(data_to_send)

    async def _quic(self):
        pass
