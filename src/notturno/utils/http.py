import asyncio
from functools import partial

from . import jsonenc
from ..models.response import Response
from ..models.request import Request

content_type_map = {
    dict: "application/json",
    list: "application/json",
    str: "text/plain",
    bytes: "application/octet-stream",
    int: "text/plain",
    float: "text/plain",
}


def convert_body(resp, without_convert: bool = False):
    if isinstance(resp, Response):
        if isinstance(resp.body, (dict, list)):
            resp.body = (
                jsonenc.dumps(resp.body)
                if isinstance(resp.body, dict)
                else b"".join([s.encode("utf-8") for s in resp.body])
            )
            content_type = content_type_map[dict]
        elif isinstance(resp.body, (str, bytes)):
            content_type = content_type_map[type(resp.body)]
            if without_convert:
                resp.body = resp.body.decode("utf-8")
            else:
                resp.body = resp.body.encode("utf-8") if isinstance(resp.body, str) else resp.body
        elif isinstance(resp.body, (int, float)):
            if without_convert:
                resp.body = str(resp.body)
            else:
                resp.body = str(resp.body).encode("utf-8")
            content_type = content_type_map[int]
        else:
            content_type = "application/octet-stream"
        if not resp.headers.get("Content-Type"):
            if resp.content_type:
                resp.headers["Content-Type"] = resp.content_type
            elif content_type:
                resp.headers["Content-Type"] = content_type
    elif isinstance(resp, tuple):
        if len(resp) == 2:
            resp = Response(body=resp[0], status_code=resp[1])
            resp = convert_body(resp)
    elif isinstance(resp, str) or isinstance(resp, dict) or not resp:
        resp = Response(body=resp, status_code=200)
        resp = convert_body(resp)
    else:
        raise ValueError("Unsupported Response Object")
    return resp


async def wrap_middleware(
    route, req: Request, convert_response, middlewares=[], arg_name: str = None
):
    async def call_next(request):
        if asyncio.iscoroutinefunction(route):
            if arg_name:
                return convert_response(await route(**{arg_name: request}))
            else:
                return convert_response(await route())
        else:
            if arg_name:
                return convert_response(route(**{arg_name: request}))
            else:
                return convert_response(route())

    for middleware in reversed(middlewares):
        call_next = partial(middleware, call_next=call_next)

    resp = await call_next(req)
    return resp