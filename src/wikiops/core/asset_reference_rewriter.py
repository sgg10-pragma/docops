from __future__ import annotations

import re

from wikiops.core.exceptions import ConfigurationError


ASSET_KEY_PATTERN = r"[A-Za-z0-9._-]+"


class AssetReferenceRewriter:
    """Rewrites logical ``asset://`` references inside document content."""

    _markdown_pattern = re.compile(
        rf"(?P<prefix>\]\()asset://(?P<key>{ASSET_KEY_PATTERN})(?P<suffix>[^)]*)\)"
    )
    _html_pattern = re.compile(
        rf"(?P<prefix>\b(?:src|href)\s*=\s*)(?P<quote>[\"\'])asset://(?P<key>{ASSET_KEY_PATTERN})(?P<suffix>[^\"\']*)(?P=quote)",
        re.IGNORECASE,
    )
    _scheme_pattern = re.compile(rf"asset://(?P<key>{ASSET_KEY_PATTERN})")

    def rewrite(self, content: str, references: dict[str, str]) -> str:
        rewritten = self._markdown_pattern.sub(
            lambda match: self._replace_markdown(match, references), content
        )
        return self._html_pattern.sub(
            lambda match: self._replace_html(match, references), rewritten
        )

    def collect_keys(self, content: str) -> set[str]:
        return {match.group("key") for match in self._scheme_pattern.finditer(content)}

    def _replace_markdown(
        self, match: re.Match[str], references: dict[str, str]
    ) -> str:
        key = match.group("key")
        reference = self._reference_for(key, references)
        return f"{match.group('prefix')}{reference}{match.group('suffix')})"

    def _replace_html(
        self, match: re.Match[str], references: dict[str, str]
    ) -> str:
        key = match.group("key")
        reference = self._reference_for(key, references)
        return (
            f"{match.group('prefix')}{match.group('quote')}{reference}"
            f"{match.group('suffix')}{match.group('quote')}"
        )

    @staticmethod
    def _reference_for(key: str, references: dict[str, str]) -> str:
        reference = references.get(key)
        if reference is None:
            raise ConfigurationError(
                f"Document content references asset key '{key}' but no uploaded asset is available for it."
            )
        return reference
