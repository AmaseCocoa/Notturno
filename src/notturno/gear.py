from .app import Notturno
from .core.router.regexp import RegExpRouter


class Gear(Notturno):
    def __init__(self, root_path: str = "", async_backend="asyncio"):
        super().__init__(async_backend)
        self._router = RegExpRouter(root_path=root_path)
        self._internal_router = RegExpRouter(root_path=root_path)
