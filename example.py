from nocturne import Nocturne, Gear
from nocturne.models.request import Request
from nocturne.models.response import Response
from nocturne.models.websocket import WebSocket

app = Nocturne()
child = Gear()

@app.get("/")
async def test(request: Request):
    return Response(body="Hello, World!")


@app.get("/noreq")
async def noreq():
    return "Hello, World2!", 201


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