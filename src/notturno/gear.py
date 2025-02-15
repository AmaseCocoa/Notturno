from .app import Notturno
from .core.router.regexp import PathRouter


class Gear(Notturno):
    def __init__(self, root_path: str = ""):
        super().__init__()
        self._router = PathRouter(root_path=root_path)
        self._internal_router = PathRouter(root_path=root_path)
