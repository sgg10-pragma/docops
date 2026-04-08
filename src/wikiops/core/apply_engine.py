from wikiops_sdk.contracts import DocumentProvider
from wikiops_sdk.domain import ApplyResult, ChangeSet


class ApplyEngine:
    """Persists a planned change set through a provider."""

    def apply(self, provider: DocumentProvider, change_set: ChangeSet) -> ApplyResult:
        """Applies the given change set using the provided document provider."""
        return provider.apply_changes(change_set)
