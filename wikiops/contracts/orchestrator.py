from typing import Protocol

from wikiops_sdk.domain import ApplyResult, ChangeSet


class PlanningResult(ChangeSet):
    """Semantic alias for a change plan."""


class DocumentationOrchestrator(Protocol):
    """Protocol implemented by the core orchestrator."""

    def plan(
        self,
        profile_name: str,
        plugin_id: str,
        raw_input: dict,
        dry_run: bool = True,
    ) -> PlanningResult: ...

    def apply(
        self,
        profile_name: str,
        plugin_id: str,
        raw_input: dict,
    ) -> ApplyResult: ...
