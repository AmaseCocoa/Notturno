try:
    import orjson
except ModuleNotFoundError:
    orjson = None
    import json

def dumps(obj: dict) -> bytes:
    if orjson:
        return orjson.dumps(obj)
    return json.dumps(obj).encode()

def loads(obj: str | bytes | bytearray) -> bytes:
    if orjson:
        return orjson.loads(obj)
    return json.loads(obj)