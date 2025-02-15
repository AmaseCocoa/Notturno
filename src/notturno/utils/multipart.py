from typing import Any, Dict

from multipart import MultipartParser


async def read_body(scope: Dict[str, Any], receive: Any):
    body = bytearray()
    while True:
        message = await receive()
        if message.get("type") == "http.request":
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
    return bytes(body)


def get_boundary(scope: Dict[str, Any]):
    content_type = dict(scope["headers"]).get(b"content-type", b"").decode("latin-1")
    if "boundary=" in content_type:
        return content_type.split("boundary=")[1].strip()
    return ""


async def parse_multipart(scope: Dict[str, Any], receive: Any) -> dict:
    body = await read_body(scope, receive)

    boundary = get_boundary(scope)

    parser = MultipartParser(body, boundary)

    form_data = {}

    for part in parser.parts:
        if part.filename:
            form_data[part.name] = {
                "filename": part.filename,
                "content_type": part.content_type,
                "content": part.file.read(),
            }
        else:
            form_data[part.name] = part.text
    return form_data
