from litestar import Litestar, get, Response

@get("/")
async def index() -> Response:
    return Response({"status": 200, "message": "Success"})

app = Litestar(route_handlers=[index])