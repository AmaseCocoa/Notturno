import importlib.metadata

try:
    __version__ = importlib.metadata.version('notturno')
except importlib.metadata.PackageNotFoundError:
    __version__ = "dev"