from docops.core.asset_reference_rewriter import AssetReferenceRewriter
from docops.core.asset_source_resolver import AssetSourceResolver
from docops.core.exceptions import ConfigurationError
from wikiops_sdk.contracts import DocumentProvider, PluginResourceProvider
from wikiops_sdk.domain import (
    AppliedOperationResult,
    ApplyResult,
    ChangeSet,
    CreateChildDocumentOperation,
    CreateDocumentOperation,
    ExecutionContext,
    OperationStatus,
    PutAssetOperation,
    UpdateDocumentOperation,
)


class ApplyEngine:
    """Persists a planned change set through a provider."""

    def __init__(self) -> None:
        self.asset_source_resolver = AssetSourceResolver()
        self.asset_reference_rewriter = AssetReferenceRewriter()

    def apply(
        self,
        provider: DocumentProvider,
        change_set: ChangeSet,
        ctx: ExecutionContext,
        resources: PluginResourceProvider,
    ) -> ApplyResult:
        """Apply the given change set using the provided document provider."""

        results_by_operation_id: dict[str, AppliedOperationResult] = {}
        asset_references: dict[str, str] = {}
        document_operations = []

        for operation in change_set.operations:
            if not isinstance(operation, PutAssetOperation):
                document_operations.append(operation)
                continue

            try:
                resolved_upload = self.asset_source_resolver.resolve(
                    operation, ctx, resources
                )
                asset = provider.put_asset(
                    resolved_upload.operation, resolved_upload.content
                )
                asset_reference = provider.build_asset_reference(asset.ref)
                asset_references[resolved_upload.operation.asset_key] = asset_reference
                results_by_operation_id[operation.operation_id] = AppliedOperationResult(
                    operation_id=operation.operation_id,
                    status=OperationStatus.APPLIED,
                    resolved_asset_ref=asset.ref,
                    resolved_asset_reference=asset_reference,
                    resulting_version=asset.version,
                )
            except Exception as exc:  # noqa: PERF203, BLE001
                results_by_operation_id[operation.operation_id] = AppliedOperationResult(
                    operation_id=operation.operation_id,
                    status=OperationStatus.FAILED,
                    message=str(exc),
                )

        if any(
            result.status is OperationStatus.FAILED
            for result in results_by_operation_id.values()
        ):
            skip_message = (
                "One or more asset uploads failed, so document operations were not applied "
                "to avoid partial changes."
            )
            for operation in document_operations:
                results_by_operation_id[operation.operation_id] = AppliedOperationResult(
                    operation_id=operation.operation_id,
                    status=OperationStatus.SKIPPED,
                    message=skip_message,
                    resolved_ref=getattr(operation, "ref", None),
                )
            return ApplyResult(
                provider_name=self._provider_name(provider),
                results=[
                    results_by_operation_id[operation.operation_id]
                    for operation in change_set.operations
                    if operation.operation_id in results_by_operation_id
                ],
            )

        rewritten_document_operations = []
        for operation in document_operations:
            try:
                rewritten_document_operations.append(
                    self._rewrite_operation(operation, asset_references)
                )
            except ConfigurationError as exc:
                results_by_operation_id[operation.operation_id] = AppliedOperationResult(
                    operation_id=operation.operation_id,
                    status=OperationStatus.SKIPPED,
                    message=str(exc),
                    resolved_ref=getattr(operation, "ref", None),
                )

        if rewritten_document_operations:
            document_change_set = ChangeSet(
                plugin_id=change_set.plugin_id,
                operations=rewritten_document_operations,
                warnings=change_set.warnings,
                notes=change_set.notes,
            )
            document_result = provider.apply_changes(document_change_set)
            for result in document_result.results:
                results_by_operation_id[result.operation_id] = result
            provider_name = document_result.provider_name
        else:
            provider_name = self._provider_name(provider)

        return ApplyResult(
            provider_name=provider_name,
            results=[
                results_by_operation_id[operation.operation_id]
                for operation in change_set.operations
                if operation.operation_id in results_by_operation_id
            ],
        )

    def _rewrite_operation(self, operation, asset_references: dict[str, str]):
        if isinstance(operation, UpdateDocumentOperation):
            return operation.model_copy(
                update={
                    "new_content": self.asset_reference_rewriter.rewrite(
                        operation.new_content, asset_references
                    )
                }
            )
        if isinstance(operation, CreateDocumentOperation):
            return operation.model_copy(
                update={
                    "content": self.asset_reference_rewriter.rewrite(
                        operation.content, asset_references
                    )
                }
            )
        if isinstance(operation, CreateChildDocumentOperation):
            return operation.model_copy(
                update={
                    "child_content": self.asset_reference_rewriter.rewrite(
                        operation.child_content, asset_references
                    )
                }
            )
        return operation

    @staticmethod
    def _provider_name(provider: DocumentProvider) -> str:
        settings = getattr(provider, "settings", None)
        provider_name = getattr(settings, "provider_name", None)
        return provider_name or provider.provider_id
