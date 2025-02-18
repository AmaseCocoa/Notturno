import asyncio
import ssl
import traceback
from functools import partial
from http.client import responses

from colorama import Fore, Style
from yarl import URL

from ...lib import __version__
from ...logger import logger
from ...models.request import Request
from ...models.response import Response
from ...models.websocket import WebSocket
from ...utils import http, jsonenc
from ...utils.log import stat_color


class NoctServ:
    def __init__(self, handler):
        self.handler = handler
        self.server_hide = None
        self.connections = {}
        self.__gen = (
            self.handler.lifespan(self.handler) if self.handler.lifespan else None
        )
        self.__current = None

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

    async def __handle_http(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        method,
        path,
        headers,
        body,
        http_version,
    ):
        route, params = await self.handler.resolve(method.upper(), path)
        client_ip, client_port = writer.get_extra_info("peername")
        if not route:
            msg = "Not Found"
            response = (
                f"HTTP/1.1 404 NotFound\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(msg)}\r\n"
                "\r\n"
                f"{msg}"
            )
            logger.info(
                f'{client_ip}:{client_port} - "{Style.BRIGHT}{Fore.WHITE}{method.upper()} {path} HTTP/1.1{Style.RESET_ALL}" {stat_color(404)}404 {responses.get(404)}{Fore.RESET}'
            )
            return response
        url = URL(f"{'https' if self.ssl else 'http'}://{headers['Host']}/{path}")

        if self.handler.middleware:
            arg_name = await self.handler._route(func=route, is_type=Request)
            req = Request(
                method=method.upper(),
                url=url,
                headers=headers,
                query={key: url.query.getlist(key) for key in url.query.keys()},
                body=body,
            )
            route = partial(route, **params)
            resp = await http.wrap_middleware(
                route,
                req,
                http.convert_body,
                self.handler.middlewares,
                arg_name,
            )
        else:
            arg_name = await self.handler._route(func=route, is_type=Request)
            if arg_name:
                req = Request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    query={key: url.query.getlist(key) for key in url.query.keys()},
                    body=body,
                )
                params[arg_name] = req
            if asyncio.iscoroutinefunction(route):
                resp = await route(**params)
            else:
                resp = route(**params)

        if isinstance(resp, Response):
            resp = http.convert_body(resp, without_convert=True)
            resp_desc = responses.get(resp.status_code)
            if not resp.headers.get("Content-Length"):
                resp.headers["Content-Length"] = len(resp.body if not isinstance(resp.body, bytes) else resp.body.decode("utf-8"))
            if not self.server_hide:
                resp.headers["Server"] = f"NoctServ/{__version__}"
            else:
                resp.headers["Server"] = "NoctServ"
            resp.headers["Connection"] = "close"

            headers = [f"{key}: {value}" for key, value in resp.headers.items()]
            response = (
                f"HTTP/1.1 {resp.status_code} {resp_desc if resp_desc else 'UNKNOWN'}\r\n"
                f"{'\r\n'.join(headers)}\r\n"
                "\r\n"
                f"{resp.body}"
            )
            status_code = resp.status_code
        elif isinstance(resp, dict):
            dumped = jsonenc.dumps(resp)
            response = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Length: {len(dumped)}\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{dumped}"
            )
            status_code = 200
        writer.write(response.encode("utf-8"))
        await writer.drain()
        logger.info(
            f'{client_ip}:{client_port} - "{Style.BRIGHT}{Fore.WHITE}{method.upper()} {path} HTTP/1.1{Style.RESET_ALL}" {stat_color(status_code)}{status_code} {responses.get(status_code)}{Fore.RESET}'
        )
        writer.close()
        await writer.wait_closed()

    async def __native_ws(
        self,
        writer: asyncio.StreamWriter,
        reader: asyncio.StreamReader,
        path,
        headers,
        http_version,
    ):
        client_ip, client_port = writer.get_extra_info("peername")
        if "Sec-WebSocket-Key" not in headers:
            logger.error(
                f'{client_ip}:{client_port} - "{Style.BRIGHT}{Fore.WHITE}Websocket {path} HTTP/1.1{Style.RESET_ALL}" {stat_color(400)}400 {responses.get(400)}{Fore.RESET}'
            )
            return "HTTP/1.1 400 Bad Request\r\nServer: NoctServ\r\n\r\nBad Request"
        route, params = await self.handler._resolve_internal("WS", path)
        if not route:
            msg = "Not Found"
            response = (
                f"HTTP/1.1 404 NotFound\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(msg)}\r\n"
                "\r\n"
                f"{msg}"
            )
            writer.write(response.encode("utf-8"))
            await writer.drain()
            writer.close()
            logger.error(
                f'{client_ip}:{client_port} - "{Style.BRIGHT}{Fore.WHITE}Websocket {path} HTTP/1.1{Style.RESET_ALL}" {stat_color(404)}404 {responses.get(404)}{Fore.RESET}'
            )
            return
        ws = WebSocket(path, headers, http_version)
        ws._is_native = True
        ws._webkey = headers.get("Sec-WebSocket-Key")
        ws._reader = reader
        ws._writer = writer
        ws._logger = logger
        arg_name = await self.handler._route(func=route, is_type=WebSocket)
        params[arg_name] = ws
        if asyncio.iscoroutinefunction(route):
            await route(**params)
        else:
            raise TypeError("Websocket is Only to use in coroutine function.")

    async def _lifespan(self, shutdown: bool = False):
        if self.__gen:
            self.__gen = self.handler.lifespan(self.handler)
            if shutdown:
                try:
                    await anext(self.__gen)
                except StopAsyncIteration:
                    pass
            else:
                try:
                    await anext(self.__gen)
                except StopAsyncIteration:
                    pass

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
                await self.__handle_http(
                    reader, writer, method, path, headers, body, http_version
                )
            else:
                conn_type = "websocket"
                await self.__native_ws(writer, reader, path, headers, http_version)
        except (ssl.SSLError, Exception) as e:
            if isinstance(e, ssl.SSLError):
                if e.reason == "APPLICATION_DATA_AFTER_CLOSE_NOTIFY":
                    logger.error(
                        "An error occurred while running the application:\nSSL error: application data after close notify"
                    )
                elif e.reason == "UNEXPECTED_EOF_WHILE_READING":
                    logger.error(
                        "An error occurred while running the application:\nSSL error: unexpected EOF while reading"
                    )
            elif not isinstance(e, ssl.SSLError) and isinstance(e, Exception):
                logger.error(
                    "An error occurred while running the application:\n"
                    + traceback.format_exc()
                )
                if conn_type == "http":
                    await self.send_error_response(writer, 500, method, path)

    async def send_error_response(
        self, writer: asyncio.StreamWriter, status_code, method, path
    ):
        client_ip, client_port = writer.get_extra_info("peername")
        response = (
            f"HTTP/1.1 {status_code} {responses.get(status_code)}\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(responses.get(status_code))}\r\n"
            "\r\n"
            f"{responses.get(status_code)}"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()
        logger.error(
            f'{client_ip}:{client_port} - "{Style.BRIGHT}{Fore.WHITE}{method.upper()} {path} HTTP/1.1{Style.RESET_ALL}" {stat_color(status_code)}{status_code} {responses.get(status_code)}{Fore.RESET}'
        )

    async def graceful_exit(self):
        await self.lifespan_handler()
        self.listener.close()
        await self.listener.wait_closed()

    async def lifespan_handler(self):
        if self.handler.lifespan:
            try:
                self.__current = await anext(self.__gen)
            except StopAsyncIteration:
                pass

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
        self._running = True
        await self.lifespan_handler()
        if use_ssl:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(certfile, keyfile)
            ctx.set_alpn_protocols(["http/1.1"])
            self.listener = await asyncio.start_server(
                self.__handle, host, port, ssl=ctx
            )
            url = f"https://{host}:{port}"
        else:
            self.listener = await asyncio.start_server(self.__handle, host, port)
            url = f"http://{host}:{port}"
        logger.debug(f"Current using: NoctServ v{__version__}")
        logger.info(f"Server is running on {url}")
        async with self.listener:
            await self.listener.serve_forever()
