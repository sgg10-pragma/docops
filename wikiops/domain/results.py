from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field

from wikiops.domain.models import DocumentRef, DocumentVersion


class OperationStatus(str, Enum):
    """Status for a persisted operation."""

    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"


class AppliedOperationResult(BaseModel):
    """Result for a single applied operation."""

    operation_id: str = Field(..., description="Unique identifier for the operation.")
    status: OperationStatus = Field(..., description="Status of the operation.")
    message: Optional[str] = Field(
        None, description="Detailed message about the operation result."
    )
    resolved_ref: Optional[DocumentRef] = Field(
        None, description="Reference to the document that was processed."
    )
    resulting_version: Optional[DocumentVersion] = Field(
        None, description="Version of the document after the operation was applied."
    )


class ApplyResult(BaseModel):
    """Aggregate apply result."""

    provider_name: str = Field(
        ..., description="Name of the provider that processed the operations."
    )
    results: List[AppliedOperationResult] = Field(
        default_factory=list, description="List of results for each applied operation."
    )

    def has_failures(self) -> bool:
        """Return whether any operation failed."""

        return any(result.status == OperationStatus.FAILED for result in self.results)
