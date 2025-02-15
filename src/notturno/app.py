import asyncio
import inspect
from functools import partial, wraps
from http.client import responses
from typing import Any, Callable, Dict

import anyio
from yarl import URL

try:
    import uvicorn
except ModuleNotFoundError:
    uvicorn = None

from .core.http.serv import NoctServ
from .core.router.regexp import RegExpRouter
from .models.request import Request, from_asgi
from .models.response import Response
from .models.websocket import WebSocket
from .utils import jsonenc
from .types import LOOP

class Notturno:
    def __init__(self, async_backend: str = "asyncio", lifespan=None):
        self._router = RegExpRouter()
        self.dependencies = {}
        self._internal_router = RegExpRouter()
        self.http = NoctServ(self)
        self.async_backend = async_backend
        self.__server_hide = None
        self.__is_main = self.__is_non_gear()
        self.lifespan = lifespan
        self.middlewares = []

    def __is_non_gear(self):
        if isinstance(self, Notturno) and type(self) is Notturno:
            return True
        else:
            return False

    def merge(self, cls):
        if isinstance(cls, Notturno):
            self._router.combine(cls._router)
            self._internal_router.combine(cls._internal_router)
            cls.dependencies.update(self.dependencies)
            self.dependencies.update(cls.dependencies)
            cls.middlewares += self.middlewares
            self.middlewares += cls.middlewares
        else:
            raise TypeError(
                f"Notturno.Notturno or Notturno.Gear required, but got {cls.__class__}"
            )

    def add_dependency(self, name: str, instance):
        self.dependencies[name] = instance

    def inject(self, *dependency_names):
        """Injects dependencies into the granted function"""

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                #                for name in dependency_names:
                #                    if name in self.dependencies:
                #                        kwargs[name] = self.dependencies[name]
                kwargs.update(
                    {
                        name: self.dependencies[name]
                        for name in dependency_names
                        if name in self.dependencies
                    }
                )
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    async def __asgi_lifespan_handle(
        self, scope: Dict[str, Any], receive: Any, send: Any
    ):
        if self.lifespan:
            gen = self.lifespan(self)
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    try:
                        await anext(gen)
                    except StopAsyncIteration:
                        pass
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    try:
                        await anext(gen)
                    except StopAsyncIteration:
                        pass
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        else:
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return

    async def __asgi_http_handle(self, scope: Dict[str, Any], receive: Any, send: Any):
        route, params = await self.resolve(scope["method"], scope["path"])
        if not route:
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [[b"Content-Type", b"text/plain"]],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Not Found",
                    "more_body": False,
                }
            )
            return
        req = await from_asgi(scope, receive)
        arg_name = await self.__route(func=route, is_type=Request)
        if self.middleware:
            if self.middleware != []:
                route = partial(route, **params)
                async def call_next(request):
                    if arg_name:
                        return await route(**{arg_name: request})
                    else:
                        return await route()
                for middleware in reversed(self.middlewares):
                    call_next = partial(middleware, call_next=call_next)
                resp = await call_next(req)
        else:
            if arg_name:
                params[arg_name] = req
            if asyncio.iscoroutinefunction(route):
                resp = await route(**params)
            else:
                resp = route(**params)
        resp = await self.__convert_response(resp)
        content_type = None
        if isinstance(resp.body, dict):
            resp.body = jsonenc.dumps(resp)
            content_type = "application/json"
        elif isinstance(resp.body, list):
            resp.body = b"".join([s.encode("utf-8") for s in resp.body])
            content_type = "application/json"
        elif isinstance(resp.body, str):
            resp.body = resp.body.encode()
            content_type = "text/plain"
        elif isinstance(resp.body, bytes):
            content_type = "application/octet-stream"
        elif isinstance(resp.body, int) or isinstance(resp.body, float):
            resp.body = resp.body.to_bytes(4, byteorder="big")
            content_type = "text/plain"
        else:
            content_type = "application/octet-stream"
        if not resp.headers.get("Content-Type"):
            if resp.content_type:
                resp.headers["Content-Type"] = resp.content_type
            elif content_type:
                resp.headers["Content-Type"] = content_type
        await send(
            {
                "type": "http.response.start",
                "status": resp.status_code,
                "headers": [
                    [key.encode("utf-8"), value.encode("utf-8")]
                    for key, value in resp.headers.items()
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": resp.body,
                "more_body": False,
            }
        )

    def add_middleware(self, func):
        self.middlewares.append(func)
    
    def middleware(self):
        def decorator(func):
            self.middlewares.append(func)
            return func
        return decorator


    async def __convert_response(self, response):
        if isinstance(response, Response):
            return response
        elif isinstance(response, tuple):
            if len(response) == 2:
                return Response(body=response[0], status_code=response[1])
        elif isinstance(response, str) or isinstance(response, dict) or not response:
            return Response(body=response, status_code=200)
        else:
            raise ValueError("Unsupported Response Object")

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any):
        if not self.__is_main:
            raise TypeError(
                "You cannot start a server with anything Notturno.Gear as your main."
            )
        if scope["type"] == "http":
            await self.__asgi_http_handle(scope, receive, send)
        elif scope["type"] == "websocket":
            pass
        elif scope["type"] == "lifespan":
            await self.__asgi_lifespan_handle(scope, receive, send)

    def __normalize_path(self, path: str) -> str:
        return path.rstrip("/")

    async def __route(self, func: Callable, is_type) -> Any:
        # arg_name = None
        # for param_name, param in signature.parameters.items():
        #    if param.annotation is is_type:
        #        arg_name = param_name
        #        break
        # if request_arg_name is not None:
        #    kwargs[request_arg_name] = request_value

        # if asyncio.iscoroutinefunction(func):
        #    return await func(*args, **kwargs)
        # else:
        #    return func(*args, **kwargs)
        return next(
            (
                param_name
                for param_name, param in inspect.signature(func).parameters.items()
                if param.annotation is is_type
            ),
            None,
        )

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

    async def _native_ws_handle(self, writer: asyncio.StreamWriter, reader: asyncio.StreamReader, path, headers, body, http_version):
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
            writer.write(response.encode("utf-8"))
            await writer.drain()
            await writer.close()
            return
        #raise NotImplementedError("Websocket Native Support is Non-Ready :(")
        ws = WebSocket(path, headers, http_version)
        ws._is_native = True
        ws._webkey = headers.get("Sec-WebSocket-Key")
        ws._reader = reader
        ws._writer = writer
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

    def serve_asgi(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        loop: LOOP = "auto"
    ) -> None: 
        if uvicorn:
            if loop == "winloop":
                import platform
                if platform.system() == "Windows":
                    uvicorn.config.LOOP_SETUPS["winloop"] = "notturno.loops.winloop:winloop_setup"
            uvicorn.run(host=host, port=port, loop=loop)
        else:
            raise ModuleNotFoundError("uvicorn not found, can be installed with pip install uvicorn.")

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
                "You cannot start a server with anything Notturno.Gear as your main."
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

    def status(self, code: int):
        def decorator(func):
            if isinstance(func, staticmethod):
                func = func.__func__
            func._router_method = "HTTPSTAT"
            self._internal_router.add_route("HTTPSTAT", code, func)
            return func
        return decorator
