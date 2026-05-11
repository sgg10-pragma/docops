from __future__ import annotations

from docops.core.apply_engine import ApplyEngine
from wikiops_sdk.domain import (
    ApplyResult,
    AppliedOperationResult,
    Asset,
    AssetPathBase,
    AssetRef,
    AssetRefKind,
    ChangeSet,
    CreateDocumentOperation,
    UpdateDocumentOperation,
    DocumentVersion,
    ExecutionContext,
    OperationStatus,
    PluginResourceAssetSource,
    PutAssetOperation,
)


class DemoResources:
    def has(self, relative_path: str) -> bool:
        return relative_path == "resources/logo.png"

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str:
        return f"{relative_path}:{encoding}"

    def read_bytes(self, relative_path: str) -> bytes:
        return b"PNG"

    def list(self, prefix: str = "") -> list[str]:
        return [f"{prefix}logo.png"]


def _ctx(*, plugin_config: dict | None = None) -> ExecutionContext:
    return ExecutionContext(
        run_id="run-1",
        profile_name="default",
        provider_name="default",
        dry_run=False,
        plugin_config=plugin_config or {},
        runtime_vars={"config_dir": "/tmp", "input_dir": "/tmp"},
    )


def test_apply_delegates_document_only_changes_to_provider(
    doc_ref_factory,
) -> None:
    ref = doc_ref_factory(path="/Docs/Page")
    changeset = ChangeSet(
        plugin_id="demo.plugin",
        operations=[CreateDocumentOperation(ref=ref, title="Page", content="# Page\n")],
    )
    calls = []

    class Provider:
        provider_id = "demo-provider"

        def apply_changes(self, candidate):
            calls.append(candidate)
            return ApplyResult(
                provider_name="demo-provider",
                results=[
                    AppliedOperationResult(
                        operation_id=candidate.operations[0].operation_id,
                        status=OperationStatus.APPLIED,
                        resolved_ref=candidate.operations[0].ref,
                    )
                ],
            )

        def put_asset(self, operation, content):  # pragma: no cover - not used here
            raise AssertionError("should not upload assets")

        def build_asset_reference(self, ref):  # pragma: no cover - not used here
            raise AssertionError("should not build asset references")

    result = ApplyEngine().apply(Provider(), changeset, _ctx(), DemoResources())

    assert result.provider_name == "demo-provider"
    assert result.results[0].status is OperationStatus.APPLIED
    assert result.results[0].resolved_ref == ref
    assert calls == [changeset]


def test_apply_uploads_assets_and_rewrites_document_content(doc_ref_factory) -> None:
    page_ref = doc_ref_factory(path="/Docs/Page")
    change_set = ChangeSet(
        plugin_id="demo.plugin",
        operations=[
            PutAssetOperation(
                asset_key="logo",
                source=PluginResourceAssetSource(relative_path="resources/logo.png"),
                name="logo.png",
                media_type="image/png",
            ),
            CreateDocumentOperation(
                ref=page_ref,
                title="Page",
                content='![Logo](asset://logo)\n<img src="asset://logo" alt="Logo" />\n',
            ),
        ],
    )
    captured = {"uploads": [], "documents": []}

    class Provider:
        provider_id = "demo-provider"

        def put_asset(self, operation, content):
            captured["uploads"].append((operation, content))
            return Asset(
                ref=AssetRef(
                    provider="default",
                    kind=AssetRefKind.PATH,
                    locator={"path": "/.attachments/logo--abcd1234.png"},
                ),
                name=operation.name,
                media_type=operation.media_type,
                size_bytes=len(content),
                version=DocumentVersion(etag='"asset-v1"'),
            )

        def build_asset_reference(self, ref):
            return ref.locator["path"]

        def apply_changes(self, candidate):
            captured["documents"].append(candidate)
            return ApplyResult(
                provider_name="default",
                results=[
                    AppliedOperationResult(
                        operation_id=candidate.operations[0].operation_id,
                        status=OperationStatus.APPLIED,
                        resolved_ref=candidate.operations[0].ref,
                    )
                ],
            )

    result = ApplyEngine().apply(Provider(), change_set, _ctx(), DemoResources())

    assert captured["uploads"][0][0].name == "logo.png"
    assert captured["uploads"][0][1] == b"PNG"
    assert (
        captured["documents"][0].operations[0].content
        == '![Logo](/.attachments/logo--abcd1234.png)\n<img src="/.attachments/logo--abcd1234.png" alt="Logo" />\n'
    )
    assert [item.status for item in result.results] == [
        OperationStatus.APPLIED,
        OperationStatus.APPLIED,
    ]


def test_apply_skips_document_when_asset_reference_is_missing(doc_ref_factory) -> None:
    page_ref = doc_ref_factory(path="/Docs/Page")
    change_set = ChangeSet(
        plugin_id="demo.plugin",
        operations=[
            CreateDocumentOperation(
                ref=page_ref,
                title="Page",
                content='![Logo](asset://missing)',
            )
        ],
    )

    class Provider:
        provider_id = "demo-provider"

        def put_asset(self, operation, content):  # pragma: no cover - not used here
            raise AssertionError("unexpected asset upload")

        def build_asset_reference(self, ref):  # pragma: no cover - not used here
            raise AssertionError("unexpected asset reference build")

        def apply_changes(self, candidate):
            raise AssertionError("document apply should be skipped when references are missing")

    result = ApplyEngine().apply(Provider(), change_set, _ctx(), DemoResources())

    assert result.results[0].status == OperationStatus.SKIPPED
    assert "references asset key 'missing'" in result.results[0].message


def test_apply_resolves_relative_local_files_against_allowed_roots(
    tmp_path,
    doc_ref_factory,
) -> None:
    input_dir = tmp_path / "input"
    asset_dir = tmp_path / "trusted-assets"
    input_dir.mkdir()
    asset_dir.mkdir()
    asset_path = asset_dir / "diagram.png"
    asset_path.write_bytes(b"PNG")
    change_set = ChangeSet(
        plugin_id="demo.plugin",
        operations=[
            PutAssetOperation(
                asset_key="diagram",
                source={
                    "kind": "local_file",
                    "path": str(asset_path.relative_to(input_dir.parent)),
                    "relative_to": AssetPathBase.INPUT_DIR,
                },
            )
        ],
    )
    captured = []
    ctx = ExecutionContext(
        run_id="run-1",
        profile_name="default",
        provider_name="default",
        dry_run=False,
        plugin_config={
            "asset_policy": {"allowed_asset_roots": [str(asset_dir.relative_to(tmp_path))]}
        },
        runtime_vars={"config_dir": str(tmp_path), "input_dir": str(tmp_path)},
    )

    class Provider:
        provider_id = "demo-provider"

        def put_asset(self, operation, content):
            captured.append((operation.name, operation.media_type, content))
            return Asset(
                ref=AssetRef(
                    provider="default",
                    kind=AssetRefKind.PATH,
                    locator={"path": "/.attachments/diagram.png"},
                ),
                name=operation.name,
                media_type=operation.media_type,
                size_bytes=len(content),
            )

        def build_asset_reference(self, ref):
            return ref.locator["path"]

        def apply_changes(self, candidate):
            return ApplyResult(provider_name="default", results=[])

    ApplyEngine().apply(Provider(), change_set, ctx, DemoResources())

    assert captured == [("diagram.png", "image/png", b"PNG")]


def test_apply_skips_all_document_operations_when_asset_upload_fails(
    doc_ref_factory,
) -> None:
    page_ref = doc_ref_factory(path="/Docs/Page")
    change_set = ChangeSet(
        plugin_id="demo.plugin",
        operations=[
            PutAssetOperation(
                asset_key="logo",
                source=PluginResourceAssetSource(relative_path="resources/logo.png"),
                name="logo.png",
                media_type="image/png",
            ),
            CreateDocumentOperation(
                ref=page_ref,
                title="Page",
                content='![Logo](asset://logo)',
            ),
            UpdateDocumentOperation(
                ref=page_ref,
                new_content="# updated",
            ),
        ],
    )

    class Provider:
        provider_id = "demo-provider"

        def put_asset(self, operation, content):
            raise RuntimeError("upload failed")

        def build_asset_reference(self, ref):  # pragma: no cover - not used here
            raise AssertionError("unexpected asset reference build")

        def apply_changes(self, candidate):
            raise AssertionError("document apply should not happen after asset upload failure")

    result = ApplyEngine().apply(Provider(), change_set, _ctx(), DemoResources())

    assert [item.status for item in result.results] == [
        OperationStatus.FAILED,
        OperationStatus.SKIPPED,
        OperationStatus.SKIPPED,
    ]
    assert result.results[1].message.startswith("One or more asset uploads failed")
