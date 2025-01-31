from litestar import Litestar, get, Response

@get("/")
def index() -> Response:
    return Response({"status": 200, "message": "Success"})

app = Litestar(route_handlers=[index])