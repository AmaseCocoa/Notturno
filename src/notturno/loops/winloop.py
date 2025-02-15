import asyncio
import warnings

try:
    import winloop
except ModuleNotFoundError:
    winloop = None

from uvicorn.loops.auto import auto_loop_setup



if winloop:
    def winloop_setup(use_subprocess: bool = False) -> None:
        asyncio.set_event_loop_policy(winloop.EventLoopPolicy())
else:
    def winloop_setup(use_subprocess: bool = False) -> None:
        warnings.warn("Winloop not found. Trying auto...", ImportWarning)
        return auto_loop_setup(use_subprocess)