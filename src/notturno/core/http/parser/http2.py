import asyncio
import h2.connection
import h2.config


class HTTP2ServerProtocol(asyncio.Protocol):
    def __init__(self):
        self.transport = None
        self.conn = h2.connection.H2Connection(h2.config.H2Configuration(client_side=False))

    def connection_made(self, transport: asyncio.Transport):
        self.transport: asyncio.Transport = transport
        self.conn.initiate_connection()
        self.transport.write(self.conn.data_to_send())

    def data_received(self, data):
        if data:
            try:
                events = self.conn.receive_data(data)
                for event in events:
                    if isinstance(event, h2.events.RequestReceived):
                        self.handle_request(event)
            except Exception as e:
                print(f"Error processing data: {e}")

    def handle_request(self, event):
        stream_id = event.stream_id
        response_data = b"<html><body><h1>Hello, World! (HTTP/2)</h1></body></html>"
        
        self.conn.send_headers(stream_id, [
            (':status', '200'),
            ('content-type', 'text/html'),
        ])
        self.conn.send_data(stream_id, response_data, end_stream=True)
        
        self.transport.write(self.conn.data_to_send())

    def connection_lost(self, exc):
        print("Connection closed")


async def main():
    loop = asyncio.get_running_loop()
    
    server = await loop.create_server(HTTP2ServerProtocol, '0.0.0.0', 8080)
    print("Server started on http://0.0.0.0:8080")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
