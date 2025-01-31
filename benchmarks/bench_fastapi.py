from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def index():
    return {"status": 200, "message": "Success"}