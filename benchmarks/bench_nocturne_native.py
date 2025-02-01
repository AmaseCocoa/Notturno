import asyncio

import winloop

from notturno import Notturno

app = Notturno()
asyncio.set_event_loop_policy(winloop.EventLoopPolicy())


@app.get("/")
async def index():
    return {"status": 200, "message": "Success"}


app.serve(port="8000")
