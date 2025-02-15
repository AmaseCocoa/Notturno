from .app import Notturno
from .core.router.regexp import RegExpRouter


class Gear(Notturno):
    def __init__(self, root_path: str = ""):
        super().__init__()
        self._router = RegExpRouter(root_path=root_path)
        self._internal_router = RegExpRouter(root_path=root_path)
