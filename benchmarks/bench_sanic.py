from sanic import Sanic
from sanic.response import json

app = Sanic(__name__)

@app.get("/")
async def index(request):
    return json({"status": 200, "message": "Success"})

#if __name__ == "__main__":
#    app.run(host="127.0.0.1", port=8000)