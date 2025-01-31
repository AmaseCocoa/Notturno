import struct

import anyio
from anyio import client


# NoctHTTP
# An Tiny HTTP Server
class NoctHTTP:
    def __init__(self, handler):
        self.handler = handler
        self.server_hide = None

    def parse_http_message(self, http_message):
        if not http_message.strip():
            return None, {}, ""

        lines = http_message.splitlines()

        start_line = lines[0] if lines else ""

        parts = start_line.split()
        if len(parts) < 3:
            return None, {}, ""

        method = parts[0]
        path = parts[1]
        http_version = parts[2]

        headers = {}
        header_lines = []
        for line in lines[1:]:
            if line == "":
                break
            header_lines.append(line)

        for header in header_lines:
            key, value = header.split(": ", 1)
            headers[key] = value

        body_start_index = len(header_lines) + 2
        body = "\n".join(lines[body_start_index:])

        return method, path, headers, body, http_version

    async def __handle(self, client):
        async with client:
            request_line = await client.receive(1024)
            reqline = request_line.decode()
            method, path, headers, body, http_version = self.parse_http_message(reqline)

            response: str = await self.handler._native_http_handle(
                method, path, headers, body, http_version
            )
            await client.send(response.encode())
            """
            if path == "/ws":
                if "Sec-WebSocket-Key" not in headers:
                    await self.send_error_response(client, 400, "Bad Request")
                    return

                webkey = headers["Sec-WebSocket-Key"]
                webaccept = base64.b64encode(
                    hashlib.sha1(
                        (webkey + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
                    ).digest()
                ).decode()

                response = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {webaccept}\r\n\r\n"
                )
                await client.send(response.encode())

                try:
                    while True:
                        data = await client.receive(2)
                        if len(data) < 2:
                            break

                        length = data[1] & 127
                        if length == 126:
                            length_data = await client.receive(2)
                            length = struct.unpack(">H", length_data)[0]
                        elif length == 127:
                            length_data = await client.receive(8)
                            length = struct.unpack(">Q", length_data)[0]

                        mask = await client.receive(4)
                        message = await client.receive(length)

                        decoded_message = bytearray(
                            b ^ mask[i % 4] for i, b in enumerate(message)
                        )

                        try:
                            print(decoded_message.decode("utf-8"))
                        except UnicodeDecodeError:
                            print("Skipped Decoding: Received an invalid UTF-8 message.")
                            continue

                        await self.send_message(client, bytes(decoded_message))

                except anyio.EndOfStream:
                    pass

                
            elif path == "/":
                response_body = "Hello, this is a normal HTTP response."
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/plain\r\n"
                    f"Content-Length: {len(response_body)}\r\n"
                    "\r\n"
                    f"{response_body}"
                )
                await client.send(response.encode())
            else:
                print("404 :(")
                await self.send_error_response(client, 404, "Not Found")
            """

    async def send_error_response(self, client, status_code, message):
        response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(message)}\r\n"
            "\r\n"
            f"{message}"
        )
        await client.send(response.encode())

    async def send_message(self, client, message):
        length = len(message)
        if length <= 125:
            header = struct.pack("B", 129) + struct.pack("B", length)
        elif length >= 126 and length <= 65535:
            header = (
                struct.pack("B", 129)
                + struct.pack("B", 126)
                + struct.pack(">H", length)
            )
        else:
            header = (
                struct.pack("B", 129)
                + struct.pack("B", 127)
                + struct.pack(">Q", length)
            )

        await client.send(header + message)

    async def serve(self, host: str = "127.0.0.1", port: int = 8765, server_hide: bool=False):
        self.server_hide = server_hide
        listener = await anyio.create_tcp_listener(local_host=host, local_port=port)
        print(f"Server is running on http://{host}:{port}")
        await listener.serve(self.__handle)
