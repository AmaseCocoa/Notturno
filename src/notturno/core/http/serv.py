import asyncio
import ssl
import traceback

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
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        conn_type = None
        try:
            data = await reader.read(1024)
            reqline = data.decode()
            method, path, headers, body, http_version = self.parse_http_message(reqline)
            if not headers.get("Upgrade") == "websocket":
                conn_type = "http"
                response = await self.handler._native_http_handle(
                    method, path, headers, body, http_version
                )
                writer.write(response.encode("utf-8"))
                await writer.drain()
            else:
                conn_type = "websocket"
                await self.handler._native_ws_handle(
                    writer, reader, path, headers, body, http_version
                )
        except (ssl.SSLError, Exception) as e:
            if isinstance(e, ssl.SSLError):
                if e.reason == "APPLICATION_DATA_AFTER_CLOSE_NOTIFY":
                    print("SSL error: application data after close notify")
                elif e.reason == "UNEXPECTED_EOF_WHILE_READING":
                    print("SSL error: unexpected EOF while reading")
            elif not isinstance(e, ssl.SSLError) and isinstance(
                e, Exception
            ):
                print(traceback.format_exc())
                if conn_type == "http":
                    await self.send_error_response(writer, 500, "Internal Server Error")

    async def send_error_response(self, writer: asyncio.StreamWriter, status_code, message):
        response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(message)}\r\n"
            "\r\n"
            f"{message}"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()

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
        self.ssl = use_ssl
        if use_ssl:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(certfile, keyfile)
            ctx.set_alpn_protocols(['http/1.1'])
            listener = await asyncio.start_server(self.__handle, host, port, ssl=ctx)
            url = f"https://{host}:{port}"
        else:
            listener = await asyncio.start_server(self.__handle, host, port)
            url = f"http://{host}:{port}"
        print(f"Server is running on {url}")
        async with listener:
            await listener.serve_forever()
