import ssl
import traceback

import anyio
from anyio.streams.tls import TLSListener, TLSStream
from anyio._backends._asyncio import SocketStream as AIOSocketStream
from anyio._backends._trio import SocketStream as TrioSocketStream


class NoctServ:
    def __init__(self, handler):
        self.handler = handler
        self.server_hide = None
        self.connections = {}

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

    async def __handle(
        self,
        client: TLSStream
        | AIOSocketStream
        | TrioSocketStream,
    ):
        conn_type = None
        try:
            
            async with client:
                data = await client.receive(1024)
                reqline = data.decode()
                method, path, headers, body, http_version = self.parse_http_message(
                    reqline
                )
                if not headers.get("Upgrade") == "websocket":
                    conn_type = "http"
                    response = await self.handler._native_http_handle(
                        method, path, headers, body, http_version
                    )
                    await client.send(response.encode())
                else:
                    conn_type = "websocket"
                    await self.handler._native_ws_handle(
                        client, path, headers, body, http_version
                    )
        except (ssl.SSLError, anyio.BrokenResourceError, Exception) as e:
            if isinstance(e, ssl.SSLError):
                if e.reason == "APPLICATION_DATA_AFTER_CLOSE_NOTIFY":
                    print("SSL error: application data after close notify")
                elif e.reason == "UNEXPECTED_EOF_WHILE_READING":
                    print("SSL error: unexpected EOF while reading")
            elif not isinstance(e, anyio.BrokenResourceError) and isinstance(
                e, Exception
            ):
                print(traceback.format_exc())
                if conn_type == "http":
                    await self.send_error_response(client, 500, "Internal Server Error")

    async def send_error_response(self, client, status_code, message):
        response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(message)}\r\n"
            "\r\n"
            f"{message}"
        )
        await client.send(response.encode())

    async def serve(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        server_hide: bool = False,
        use_ssl: bool = False,
        certfile: str = "cert.pem",
        keyfile: str = "key.pem",
    ):
        self.server_hide = server_hide
        listener = await anyio.create_tcp_listener(local_host=host, local_port=port)
        self.ssl = use_ssl
        if use_ssl:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=certfile, keyfile=keyfile)
            context.set_alpn_protocols(["http/1.1", "h2", "h3"])
            listener = TLSListener(listener, context, standard_compatible=False)
            print(f"Server is running on https://{host}:{port}")
        else:
            print(f"Server is running on http://{host}:{port}")
        await listener.serve(self.__handle)
