import json

async def app(scope, receive, send):
    assert scope['type'] == 'http'
    
    response_body = {
        "status": 200,
        "message": "Success"
    }
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'application/json')],
    })
    
    await send({
        'type': 'http.response.body',
        'body': json.dumps(response_body).encode('utf-8'),
    })