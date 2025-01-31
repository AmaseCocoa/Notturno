from nocturne import Nocturne

app = Nocturne()

@app.get("/")
async def index():
    return {"status": 200, "message": "Success"}