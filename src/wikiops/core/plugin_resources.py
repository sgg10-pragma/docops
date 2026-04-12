from importlib import import_module, resources
from importlib.metadata import EntryPoint
from pathlib import PurePosixPath
from typing import Iterable


class PackagePluginResourceProvider:
    """Expose plugin package files through the SDK resource contract."""

    def __init__(self, package: str) -> None:
        self._package = package
        self._root = resources.files(package)

    @classmethod
    def from_entry_point(cls, entry_point: EntryPoint) -> "PackagePluginResourceProvider":
        module = import_module(entry_point.module)
        package = module.__package__ or module.__name__
        return cls(package)

    @staticmethod
    def _normalize_path(relative_path: str, *, allow_empty: bool = False) -> tuple[str, ...]:
        path = PurePosixPath(relative_path)
        if path.is_absolute():
            raise ValueError("Plugin resource paths must be relative.")

        parts = tuple(part for part in path.parts if part not in ("", "."))
        if any(part == ".." for part in parts):
            raise ValueError("Plugin resource paths must not traverse parent directories.")
        if not parts and not allow_empty:
            raise ValueError("Plugin resource path must not be empty.")
        return parts

    def _resolve(self, relative_path: str):
        node = self._root
        for part in self._normalize_path(relative_path):
            node = node.joinpath(part)
        return node

    def _iter_files(self, node, prefix: tuple[str, ...]) -> Iterable[str]:
        for child in node.iterdir():
            child_prefix = (*prefix, child.name)
            if child.is_file():
                yield "/".join(child_prefix)
                continue
            if child.is_dir():
                yield from self._iter_files(child, child_prefix)

    def has(self, relative_path: str) -> bool:
        try:
            node = self._resolve(relative_path)
        except ValueError:
            return False
        return node.is_file() or node.is_dir()

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str:
        node = self._resolve(relative_path)
        if not node.is_file():
            raise FileNotFoundError(
                f"Plugin resource '{relative_path}' was not found in package '{self._package}'."
            )
        return node.read_text(encoding=encoding)

    def read_bytes(self, relative_path: str) -> bytes:
        node = self._resolve(relative_path)
        if not node.is_file():
            raise FileNotFoundError(
                f"Plugin resource '{relative_path}' was not found in package '{self._package}'."
            )
        return node.read_bytes()

    def list(self, prefix: str = "") -> Iterable[str]:
        normalized_prefix = "/".join(
            self._normalize_path(prefix, allow_empty=True)
        )
        for relative_path in self._iter_files(self._root, ()):
            if not normalized_prefix or relative_path.startswith(normalized_prefix):
                yield relative_path
