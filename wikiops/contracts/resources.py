from typing import Protocol, runtime_checkable, Iterable


@runtime_checkable
class PlugingResourceProvider(Protocol):
    """Protocol for plugin-owned resources."""

    def has(self, relative_path: str) -> bool: ...

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str: ...

    def list(self, prefix: str = "") -> Iterable[str]: ...
