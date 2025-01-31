from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

app = FastAPI()

@app.get("/")
def index() -> ORJSONResponse:
    return ORJSONResponse({"status": 200, "message": "Success"})

