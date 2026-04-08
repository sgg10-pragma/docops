from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("wikiops")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

all = ["__version__"]
