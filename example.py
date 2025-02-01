from notturno import Gear, Notturno
from notturno.middleware.base import BaseMiddleware
from notturno.models.request import Request
from notturno.models.response import Response
from notturno.models.websocket import WebSocket
from notturno.middleware import CORSMiddleware

async def lifespan(app: Notturno):
    print("Starting...")
    yield
    print("Shutting Down...")


app = Notturno(lifespan=lifespan)
child = Gear()


class MyService:
    def __init__(self):
        self.name = "My Service"


class TestMiddleware(BaseMiddleware):
    async def __call__(self, request: Request, call_next):
        resp: Response = await call_next(request)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp


@app.middleware()
async def test_middleware(request: Request, call_next) -> Response:
    resp: Response = await call_next(request)
    resp.headers["Test"] = "MIDDLEWARE"
    return resp


app.add_dependency("my_service", MyService())
app.add_middleware(CORSMiddleware(
    allow_headers=["*"]
))


@app.get("/")
async def test(request: Request):
    return Response(body="Hello, World!")


@app.get("/noreq")
async def noreq():
    return "Hello, World2!", 201


@app.get("/DI")
@app.inject("my_service")
async def hello_handler(request: Request, my_service: MyService):
    return f"Hello from {my_service.name}!", 200


@child.get("/gear")
@child.inject("my_service")
async def from_gear(request: Request, my_service: MyService):
    return Response(body="From Gear!")


@app.ws("/ws")
async def ws_route(websocket: WebSocket):
    await websocket.accept()
    print("accepted")
    await websocket.send("Test")
    while True:
        print("Started loop")
        recv = await websocket.recv()
        print("Received message...")
        await websocket.send(recv)


app.merge(child)
# app.serve(port=8080, ssl=False)
