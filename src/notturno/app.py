import asyncio
import inspect
from functools import partial, wraps
from typing import Any, Callable, Dict

try:
    import uvicorn
except ModuleNotFoundError:
    uvicorn = None

from .core.http.serv import NoctServ
from .core.router.regexp import PathRouter
from .models.request import Request, from_asgi
from .models.response import Response
from .types import LOOP
from .utils import jsonenc


class Notturno:
    def __init__(self, lifespan=None):
        self._router = PathRouter()
        self.dependencies = {}
        self._internal_router = PathRouter()
        self.__is_main = self.__is_non_gear()
        self.lifespan = lifespan
        self.middlewares = []
        self.http = NoctServ(self)

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
            cls.middlewares = list(set(cls.middlewares))
            self.middlewares += cls.middlewares
            self.middlewares = list(set(self.middlewares))
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
        arg_name = await self._route(func=route, is_type=Request)
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
        resp = await self._convert_response(resp)
        content_type = None
        if isinstance(resp.body, dict):
            resp.body = jsonenc.dumps(resp.body)
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

    async def _convert_response(self, response):
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

    async def _route(self, func: Callable, is_type) -> Any:
        return next(
            (
                param_name
                for param_name, param in inspect.signature(func).parameters.items()
                if param.annotation is is_type
            ),
            None,
        )

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

    async def _resolve_internal(
        self, method: str, path: str
    ) -> tuple[None, dict] | tuple[Any | None, dict]:
        route = self._internal_router.match(path)
        if not route:
            return (None, None)
        return (route.get(method)["func"], route.get(method)["params"])

    def serve_asgi(
        self, host: str = "127.0.0.1", port: int = 8765, loop: LOOP = "auto"
    ) -> None:
        if uvicorn:
            if loop == "winloop":
                import platform

                if platform.system() == "Windows":
                    uvicorn.config.LOOP_SETUPS["winloop"] = (
                        "notturno.loops.winloop:winloop_setup"
                    )
            uvicorn.run(self, host=host, port=port, loop=loop)
        else:
            raise ModuleNotFoundError(
                "uvicorn not found, can be installed with pip install uvicorn."
            )

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
        self.ssl = ssl

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(
                self.http.serve(
                    host=host,
                    port=port,
                    server_hide=hide_server_version,
                    use_ssl=ssl,
                    certfile=certfile,
                    keyfile=keyfile,
                )
            )
        except KeyboardInterrupt:
            loop.run_until_complete(self.http.graceful_exit())
        except SystemExit:
            loop.run_until_complete(self.http.graceful_exit())

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
