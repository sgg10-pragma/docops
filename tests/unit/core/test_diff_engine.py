from __future__ import annotations

from wikiops.core.diff_engine import DiffEngine
from wikiops_sdk.domain import (
    CreateDocumentOperation,
    PluginResourceAssetSource,
    PutAssetOperation,
    UpdateDocumentOperation,
)


def test_render_builds_unified_diff_for_updates(
    doc_ref_factory,
    document_factory,
    changeset_factory,
) -> None:
    ref = doc_ref_factory(path="/inventory")
    documents = {"inventory": document_factory(ref=ref, content="old\nline\n")}
    change_set = changeset_factory(
        operations=[UpdateDocumentOperation(ref=ref, new_content="new\nline\n")]
    )

    diff = DiffEngine().render(documents, change_set)

    assert "# Operation" in diff
    assert "--- current" in diff
    assert "+++ planned" in diff
    assert "-old" in diff
    assert "+new" in diff


def test_render_describes_non_update_operations(
    doc_ref_factory,
    changeset_factory,
) -> None:
    ref = doc_ref_factory(path="/new")
    change_set = changeset_factory(
        operations=[CreateDocumentOperation(ref=ref, title="New", content="# New\n")]
    )

    diff = DiffEngine().render({}, change_set)

    assert "Type: create_document" in diff
    assert "has no line diff against an existing document" in diff


def test_render_keeps_operation_order(
    doc_ref_factory,
    document_factory,
    changeset_factory,
) -> None:
    first_ref = doc_ref_factory(path="/first")
    second_ref = doc_ref_factory(path="/second")
    documents = {"first": document_factory(ref=first_ref, content="one\n")}
    change_set = changeset_factory(
        operations=[
            UpdateDocumentOperation(ref=first_ref, new_content="two\n"),
            CreateDocumentOperation(ref=second_ref, title="Second", content="# Second\n"),
        ]
    )

    diff = DiffEngine().render(documents, change_set)

    assert diff.index("Type: create_document") > diff.index("--- current")


def test_render_describes_asset_upload_operations(changeset_factory) -> None:
    change_set = changeset_factory(
        operations=[
            PutAssetOperation(
                asset_key="logo",
                source=PluginResourceAssetSource(relative_path="resources/logo.png"),
            )
        ]
    )

    diff = DiffEngine().render({}, change_set)

    assert "Type: put_asset" in diff
    assert "Asset key: logo" in diff
    assert "uploads an asset" in diff
