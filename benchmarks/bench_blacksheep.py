from blacksheep import Application, get, Response, JSONContent

app = Application()

@get("/")
async def index() -> Response:
    return Response(200, content=JSONContent({"status": 200, "message": "Success"}))

