from notturno import Notturno

app = Notturno()


@app.get("/")
async def index():
    return {"status": 200, "message": "Success"}
