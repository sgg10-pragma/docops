from typing import Protocol, runtime_checkable, Set, Optional

from pydantic import BaseModel, Field

from wikiops.domain.results import ApplyResult
from wikiops.domain.context import ExecutionContext
from wikiops.domain.models import ChangeSet, Document, DocumentRef, ProviderCapability


class ProviderSettings(BaseModel):
    """Base provider settings model."""

    provider_name: str = Field(..., description="Name of the provider")


@runtime_checkable
class DocumentProvider(Protocol):
    """Protocol implemented by backend document providers."""

    provider_id: str

    def capabilities(self) -> Set[ProviderCapability]: ...

    def validate_settings(self) -> None: ...

    def resolve_ref(
        self, ref: DocumentRef, ctx: Optional[ExecutionContext]
    ) -> DocumentRef: ...

    def exists(self, ref: DocumentRef) -> bool: ...

    def get_document(self, ref: DocumentRef) -> Document: ...

    def build_link(self, ref: DocumentRef) -> Optional[str]: ...

    def apply_changeset(self, changeset: ChangeSet) -> ApplyResult: ...
