import asyncio
import base64
import hashlib
import struct
from http.client import responses

from colorama import Fore, Style

from ..exceptions import WebsocketClosed
from ..utils.log import stat_color


class WebSocket:
    def __init__(self, path: str, headers: str, http_version: str):
        self._webkey = None
        self._reader: asyncio.StreamReader = None
        self._writer: asyncio.StreamWriter = None
        self._is_native = True

        self.path = path
        self.headers = headers
        self.http_version = http_version

        self._send = None
        self._receive = None
        self._logger = None

    async def accept(self):
        if self._is_native:
            client_ip, client_port = self._writer.get_extra_info("peername")
            webaccept = base64.b64encode(
                hashlib.sha1(
                    (self._webkey + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
                ).digest()
            )
            response_headers = [
                b"HTTP/1.1 101 Switching Protocols\r\n",
                b"Upgrade: websocket\r\n",
                b"Connection: Upgrade\r\n",
                b"Sec-WebSocket-Accept: " + webaccept + b"\r\n",
                b"Sec-WebSocket-Version: 13\r\n\r\n",
            ]
            if self._logger:
                self._logger.info(
                    f'{client_ip}:{client_port} - "{Style.BRIGHT}{Fore.WHITE}Websocket (Accepted) {self.path} HTTP/1.1{Style.RESET_ALL}" {stat_color(101)}101 {responses.get(101)}{Fore.RESET}'
                )
            self._writer.write(b"".join(response_headers))
            await self._writer.drain()
        else:
            await self._send(
                {
                    "type": "websocket.accept",
                }
            )

    async def recv(self):
        if self._is_native:
            data = await self._reader.read(2)
            if len(data) < 2:
                raise WebsocketClosed

            length = data[1] & 127
            if length == 126:
                length_data = await self._reader.read(2)
                length = struct.unpack(">H", length_data)[0]
            elif length == 127:
                length_data = await self._reader.read(8)
                length = struct.unpack(">Q", length_data)[0]

            mask = await self._reader.read(4)

            message = await self._reader.read(length)

            decoded_message = bytearray(b ^ mask[i % 4] for i, b in enumerate(message))

            try:
                return decoded_message.decode()
            except UnicodeDecodeError:
                return None
        else:
            message = await self._receive()
            if message["type"] == "websocket.disconnect":
                raise WebsocketClosed
            elif message["type"] == "websocket.receive":
                return message["text"]
            raise Exception("Invalid message type")

    def __create_websocket_frame(self, message):
        byte_message = message.encode("utf-8") if isinstance(message, str) else message
        if not byte_message:
            raise WebsocketClosed
        length = len(byte_message)
        if length <= 125:
            frame = bytearray([0b10000001]) + bytearray([length]) + byte_message
        elif length >= 126 and length <= 65535:
            frame = (
                bytearray([0b10000001])
                + bytearray([126])
                + bytearray(length.to_bytes(2, "big"))
                + byte_message
            )
        else:
            raise Exception("Message too long")
        return frame

    async def send(self, message: str | bytes):
        if self._is_native:
            self._writer.write(self.__create_websocket_frame(message))
            await self._writer.drain()
        else:
            tmpl = {
                "type": "websocket.send",
            }
            if isinstance(message, bytes):
                tmpl["bytes"] = message
            else:
                tmpl["text"] = message
            await self._send(tmpl)

    async def close(self):
        if self._is_native:
            self._writer.close()
        else:
            await self._send(
                {
                    "type": "websocket.close",
                }
            )
