try:
    import orjson
except ModuleNotFoundError:
    orjson = None
    import json

class JSONError(Exception):
    pass

class JSONDecodeError(JSONError):
    pass

class JSONEncodeError(JSONError):
    pass

def dumps(obj: dict) -> bytes:
    if orjson:
        try:
            return orjson.dumps(obj)
        except orjson.JSONEncodeError as e:
            raise JSONEncodeError(*e.args)
    return json.dumps(obj).encode()

def loads(obj: str | bytes | bytearray) -> bytes:
    if orjson:
        try:
            return orjson.loads(obj)
        except orjson.JSONDecodeError as e:
            raise JSONDecodeError(*e.args)
    try:
        return json.loads(obj)
    except json.JSONDecodeError as e:
        raise JSONDecodeError(*e.args)