from wikiops.domain.models import ChangeSet
from wikiops.domain.results import ApplyResult
from wikiops.contracts.provider import DocumentProvider


class ApplyEngine:
    """Persists a planned change set through a provider."""

    def apply(self, provider: DocumentProvider, change_set: ChangeSet) -> ApplyResult:
        """Applies the given change set using the provided document provider."""
        return provider.apply_changeset(change_set)
