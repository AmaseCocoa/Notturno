import platform

import uvicorn

#from bench_starlette import app
#from bench_sanic import app
#from bench_quart import app
#from bench_nocturne_asyncio import app
#from bench_litestar import app
#from bench_fastapi import app
from bench_blacksheep import app
#from bench_asgi import app

if platform.system() == "Windows":
    uvicorn.config.LOOP_SETUPS["winloop"] = "nocturne.loops.winloop:winloop_setup"
    loop = "winloop"

uvicorn.run(app, host="0.0.0.0", loop=loop)