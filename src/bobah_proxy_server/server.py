import asyncio


class ProxyServer:
    def __init__(self, host, port, protocol, backlog=100, ioloop=None):
        self._host = host
        self._port = port
        self._protocol = protocol
        self._backlog = backlog
        self._ioloop = ioloop
    
    async def run_forever(self):
        self._ioloop = self._ioloop or asyncio.get_event_loop()
        server = await self._ioloop.create_server(self._protocol, self._host, self._port, 
                                                  backlog=self._backlog, start_serving=False)
        print(f"Serving on {self._host}:{self._port}")
        async with server:
            await server.serve_forever()
