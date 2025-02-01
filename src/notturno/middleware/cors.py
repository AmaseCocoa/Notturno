from .. import Request, Response
from .base import BaseMiddleware


class CORSMiddleware(BaseMiddleware):
    def __init__(
        self,
        allow_origins: list = ["*"],
        allow_methods: list = ["GET", "POST", "OPTIONS"],
        allow_headers: list = ["Content-Type", "Authorization"],
    ):
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers

    async def __call__(self, request: Request, call_next):
        response: Response = await call_next(request)
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = ", ".join(
                self.allow_origins
            )
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                self.allow_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(
                self.allow_headers
            )
        if request.method == "OPTIONS":
            response.status_code = 204
            return response
        return response
