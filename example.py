from nocturne import Nocturne, Gear
from nocturne.models.request import Request
from nocturne.models.response import Response
from nocturne.models.websocket import WebSocket

app = Nocturne()
child = Gear()

class MyService:
    def __init__(self):
        self.name = "My Service"

app.add_dependency("my_service", MyService())

@app.get("/")
async def test(request: Request):
    return Response(body="Hello, World!")


@app.get("/noreq")
async def noreq():
    return "Hello, World2!", 201

@app.get("/hello")
@app.di("my_service")
async def hello_handler(request: Request, my_service: MyService):
    return f"Hello from {my_service.name}!", 200

@child.get("/gear")
async def from_gear():
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

app.merge_route(child)
#app.serve(port=8080, ssl=False)