import asyncio

import winloop
from nocturne import Nocturne

app = Nocturne()
asyncio.set_event_loop_policy(winloop.EventLoopPolicy())

@app.get("/")
async def index():
    return {"status": 200, "message": "Success"}

app.serve(port="8000")