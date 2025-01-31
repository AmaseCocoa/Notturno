from typing import Any, Dict

class NocturneASGI:
    def __init__(self, router):
        self.router = router
    
    async def _http(self, scope: Dict[str, Any], receive: Any, send: Any):
        pass

    async def _websocket(self, scope: Dict[str, Any], receive: Any, send: Any):
        pass

    async def _lifespan(self, scope: Dict[str, Any], receive: Any, send: Any):
        pass