from quart import Quart, jsonify

app = Quart(__name__)

@app.route('/', methods=['GET'])
async def index():
    return jsonify(status=200, message="Success")

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000)