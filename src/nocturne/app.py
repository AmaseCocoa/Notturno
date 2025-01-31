import asyncio
import inspect
from functools import partial
from http.client import responses
from typing import Any, Callable, Dict

import anyio

from yarl import URL

from .core.http.serv import NoctServ
from .core.router.regexp import RegExpRouter
from .models.request import Request
from .models.response import Response
from .models.websocket import WebSocket
from .utils import jsonenc
from .utils.query import parse_qs


class Nocturne:
    def __init__(self, async_backend: str = "asyncio"):
        self._router = RegExpRouter()
        self._internal_router = RegExpRouter()
        self.http = NoctServ(self)
        self.async_backend = async_backend
        self.__server_hide = None
        self.__is_main = self.__is_non_gear()

    def __is_non_gear(self):
        if isinstance(self, Nocturne) and type(self) is Nocturne:
            return True
        else:
            return False
        
    def merge_route(self, cls):
        if isinstance(cls, Nocturne):
            self._router.combine(cls._router)
            self._internal_router.combine(cls._internal_router)
        else:
            raise TypeError(f"Nocturne.Nocturne or Nocturne.Gear required, but got {cls.__class__}")

    async def __asgi_http_handle(self, scope: Dict[str, Any], receive: Any, send: Any):
        route, params = await self.resolve(scope["method"], scope["path"])
        if not route:
            await send({
                'type': 'http.response.start',
                'status': 404,
                'headers': [[b"Content-Type", b"text/plain"]],
            })
            await send({
                'type': 'http.response.body',
                'body': b"Not Found",
                'more_body': False,
            })
            return
        response_body = b''
        while True:
            message = await receive()
            response_body += message.get('body', b'')
            if not message.get('more_body', False):
                break
        response_body_string = response_body.decode('utf-8')
        headers = {key.decode('utf-8'): value.decode('utf-8') for key, value in scope["headers"]}
        arg_name = await self.__route(func=route, is_type=Request)
        if arg_name:
            req = Request(
                method=scope["method"],
                url=f"{scope['scheme']}://{headers['host']}{scope['path']}",
                headers=headers,
                query=parse_qs(scope["query_string"]),
                body=response_body_string,
            )
            params[arg_name] = req
        if asyncio.iscoroutinefunction(route):
            resp = await route(**params)
        else:
            resp = route(**params)
        if isinstance(resp, Response):
            content_type = None
            if isinstance(resp.body, dict):
                resp.body = jsonenc.dumps(resp)
                content_type = "application/json"
            elif isinstance(resp.body, list):
                resp.body = b"".join([s.encode('utf-8') for s in resp.body])
                content_type = "application/json"
            elif isinstance(resp.body, str):
                resp.body = resp.body.encode()
                content_type = "text/plain"
            elif isinstance(resp.body, bytes):
                content_type = "application/octet-stream"
            elif isinstance(resp.body, int) or isinstance(resp.body, float):
                resp.body = resp.body.to_bytes(4, byteorder='big')
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"
            if not resp.headers.get("Content-Type"):
                if resp.content_type:
                    resp.headers["Content-Type"] = resp.content_type
                elif content_type:
                    resp.headers["Content-Type"] = content_type
            await send({
                'type': 'http.response.start',
                'status': resp.status_code,
                'headers': [[key.encode('utf-8'), value.encode('utf-8')] for key, value in resp.headers.items()],
            })
            await send({
                'type': 'http.response.body',
                'body': resp.body,
                'more_body': False,
            })
        elif isinstance(resp, dict):
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': jsonenc.dumps(resp),
                'more_body': False,
            })

        elif isinstance(resp, str):
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': resp.encode(),
                'more_body': False,
            })
        elif not resp:
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': b"",
                'more_body': False,
            })
        if isinstance(resp, tuple):
            if len(resp) == 2:
                if isinstance(resp[0], dict) and isinstance(resp[1], int):
                    await send({
                        'type': 'http.response.start',
                        'status': resp[1],
                        'headers': [[b'content-type', b'application/json']],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': jsonenc.dumps(resp[0]),
                        'more_body': False,
                    })
                elif isinstance(resp[0], str) and isinstance(resp[1], int):
                    await send({
                        'type': 'http.response.start',
                        'status': resp[1],
                        'headers': [[b'content-type', b'text/plain']],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': resp[0].encode(),
                        'more_body': False,
                    })
        
    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any):
        if not self.__is_main:
            raise TypeError(
                "You cannot start a server with anything nocturne.Gear as your main."
            )
        if scope["type"] == "http":
            await self.__asgi_http_handle(scope, receive, send)
        elif scope["type"] == "websocket":
            pass

    def __normalize_path(self, path: str) -> str:
        return path.rstrip("/")

    async def __route(self, func: Callable, is_type) -> Any:
        signature = inspect.signature(func)
        arg_name = None
        for param_name, param in signature.parameters.items():
            if param.annotation is is_type:
                arg_name = param_name
                break
        # if request_arg_name is not None:
        #    kwargs[request_arg_name] = request_value

        # if asyncio.iscoroutinefunction(func):
        #    return await func(*args, **kwargs)
        # else:
        #    return func(*args, **kwargs)
        return arg_name

    async def _native_http_handle(
        self, method: str, path, headers, body, http_version
    ) -> str:
        route, params = await self.resolve(method.upper(), path)
        if not route:
            msg = "Not Found"
            response = (
                f"HTTP/1.1 404 NotFound\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(msg)}\r\n"
                "\r\n"
                f"{msg}"
            )
            return response
        url = URL(f"{'https' if self.ssl else 'http'}://{headers['Host']}/{path}")

        arg_name = await self.__route(func=route, is_type=Request)
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
            content_type = None
            if isinstance(resp.body, dict):
                resp.body = jsonenc.dumps(resp)
                content_type = "application/json"
            elif isinstance(resp.body, list):
                content_type = "application/json"
            elif isinstance(resp.body, str):
                content_type = "text/plain"
            elif isinstance(resp.body, bytes):
                content_type = "application/octet-stream"
            elif isinstance(resp.body, int) or isinstance(resp.body, float):
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"
            resp_desc = responses.get(resp.status_code)
            if not resp.headers.get("Content-Length"):
                resp.headers["Content-Length"] = len(resp.body)
            if not resp.headers.get("Content-Type"):
                if resp.content_type:
                    resp.headers["Content-Type"] = resp.content_type
                elif content_type:
                    resp.headers["Content-Type"] = content_type
            if not self.__server_hide:
                resp.headers["Server"] = "NoctServ/0.1.0"
            else:
                resp.headers["Server"] = "NoctServ"
            headers = [f"{key}: {value}" for key, value in resp.headers.items()]
            response = (
                f"HTTP/1.1 {resp.status_code} {resp_desc if resp_desc else 'UNKNOWN'}\r\n"
                f"{'\r\n'.join(headers)}\r\n"
                "\r\n"
                f"{resp.body}"
            )
        elif isinstance(resp, dict):
            dumped = jsonenc.dumps(resp)
            response = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Length: {len(dumped)}\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{dumped}"
            )
        return response

    async def _native_ws_handle(self, client, path, headers, body, http_version):
        if "Sec-WebSocket-Key" not in headers:
            return "HTTP/1.1 400 Bad Request\r\nServer: NoctServe\r\n\r\nBad Request"
        route, params = await self.__resolve_internal("WS", path)
        if not route:
            msg = "Not Found"
            response = (
                f"HTTP/1.1 404 NotFound\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(msg)}\r\n"
                "\r\n"
                f"{msg}"
            )
            await client.send(response.encode())
            await client.aclose()
            return
        raise NotImplementedError("Websocket Native Support is Non-Ready :(")
        ws = WebSocket(path, headers, http_version)
        ws._is_native = True
        ws._webkey = "Sec-WebSocket-Key"
        ws._client = client
        arg_name = await self.__route(func=route, is_type=WebSocket)
        params[arg_name] = ws
        if asyncio.iscoroutinefunction(route):
            await route(**params)
        else:
            raise TypeError("Websocket is Only to use in coroutine function.")

    async def resolve(
        self, method: str, path: str
    ) -> tuple[None, dict] | tuple[Any | None, dict]:
        route = self._router.match(path)
        if not route or not route.get(method):
            return (None, None)
        return (route.get(method)["func"], route.get(method)["params"])

    def route(self, route: str, method: list = ["GET"]):
        def decorator(func):
            route_normalized = self.__normalize_path(route)
            if isinstance(func, staticmethod):
                func = func.__func__
            func._router_method = method
            for m in method:
                met = m.upper()
                self._router.add_route(met, route_normalized, func)
            return func

        return decorator

    async def __resolve_internal(
        self, method: str, path: str
    ) -> tuple[None, dict] | tuple[Any | None, dict]:
        route = self._internal_router.match(path)
        if not route:
            return (None, None)
        return (route.get(method)["func"], route.get(method)["params"])

    def serve(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        hide_server_version: bool = True,
        ssl: bool = False,
        certfile: str = "cert.pem",
        keyfile: str = "key.pem",
    ) -> None:
        if not self.__is_main:
            raise TypeError(
                "You cannot start a server with anything nocturne.Gear as your main."
            )
        self.__server_hide = hide_server_version
        self.ssl = ssl
        anyio.run(
            partial(
                self.http.serve,
                host=host,
                port=port,
                server_hide=hide_server_version,
                use_ssl=ssl,
                certfile=certfile,
                keyfile=keyfile,
            ),
            backend=self.async_backend,
        )

    def get(self, route: str):
        return self.route(route, method=["GET"])

    def post(self, route: str):
        return self.route(route, method=["POST"])

    def ws(self, route: str):
        def decorator(func):
            route_normalized = self.__normalize_path(route)
            if isinstance(func, staticmethod):
                func = func.__func__
            func._router_method = "WS"
            self._internal_router.add_route("WS", route_normalized, func)
            return func

        return decorator
