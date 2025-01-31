from nocturne import Nocturne

app = Nocturne()

@app.get("/")
def index():
    return {"status": 200, "message": "Success"}