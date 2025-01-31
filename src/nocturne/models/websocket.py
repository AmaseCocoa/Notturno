import base64
import hashlib
import struct

from anyio.streams.tls import TLSStream
from anyio._backends._asyncio import SocketStream as AIOSocketStream
from anyio._backends._trio import SocketStream as TrioSocketStream

from ..exceptions import WebsocketClosed


class WebSocket:
    def __init__(self, path: str, headers: str, http_version: str):
        self._webkey = None
        self._client: TLSStream | AIOSocketStream | TrioSocketStream = None
        self._is_native = True

        self.path = path
        self.headers = headers
        self.http_version = http_version

        self.send = None
        self.receive = None

    async def accept(self):
        if self._is_native:
            webaccept = base64.b64encode(
                hashlib.sha1(
                    (self._webkey + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
                ).digest()
            ).decode()
            headers = [f"{key}: {value}" for key, value in {
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Accept": f"{webaccept}",
                "Sec-WebSocket-Version": "13"
            }.items()]
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                f"{'\r\n'.join(headers)}\r\n"
            )
            await self._client.send(response.encode())
        else:
            await self.send({
                "type": "websocket.accept",
            })

    async def recv(self):
        if self._is_native:
            data = await self._client.receive(2)
            if len(data) < 2:
                raise WebsocketClosed
            
            length = data[1] & 127
            if length == 126:
                length_data = await self._client.receive(2)
                length = struct.unpack(">H", length_data)[0]
            elif length == 127:
                length_data = await self._client.receive(8)
                length = struct.unpack(">Q", length_data)[0]

            mask = await self._client.receive(4)

            message = await self._client.receive(length)

            decoded_message = bytearray(
                b ^ mask[i % 4] for i, b in enumerate(message)
            )

            try:
                return decoded_message.decode()
            except UnicodeDecodeError:
                return None
        else:
            message = await self.receive()
            if message["type"] == "websocket.disconnect":
                raise WebsocketClosed
            elif message["type"] == "websocket.receive":
                return message["text"]
            raise Exception("Invalid message type")
        
    async def send(self, message: str | bytes):
        if self._is_native:
            if isinstance(message, str):
                message = message.encode()
            length = len(message)
            if length <= 125:
                frame = struct.pack("B", 129) + struct.pack("B", length) + message
            elif length >= 126 and length <= 65535:
                frame = (
                    struct.pack("B", 129)
                    + struct.pack("B", 126)
                    + struct.pack(">H", length)
                    + message
                )
            else:
                raise Exception("Message too long")
            await self._client.send(frame)
        else:
            tmpl = {
                "type": "websocket.send",
            }
            if isinstance(message, bytes):
                tmpl["bytes"] = message
            else:
                tmpl["text"] = message
            await self.send(tmpl)
        
    async def close(self):
        if self._is_native:
            await self.client.aclose()
        else:
            await self.send({
                "type": "websocket.close",
            })