from __future__ import annotations

import pytest

from wikiops.core.document_loader import DocumentLoader


class RecordingProvider:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def get_document(self, ref):
        self.calls.append(ref)
        return self.documents[ref.locator["path"]]


def test_load_returns_documents_by_alias(doc_ref_factory, document_factory) -> None:
    first_ref = doc_ref_factory(path="/first")
    second_ref = doc_ref_factory(path="/second")
    provider = RecordingProvider(
        {
            "/first": document_factory(ref=first_ref, title="First"),
            "/second": document_factory(ref=second_ref, title="Second"),
        }
    )

    documents = DocumentLoader().load(
        provider,
        {"first": first_ref, "second": second_ref},
    )

    assert set(documents) == {"first", "second"}
    assert provider.calls == [first_ref, second_ref]


def test_load_returns_empty_mapping_for_empty_refs() -> None:
    provider = RecordingProvider({})

    assert DocumentLoader().load(provider, {}) == {}


def test_load_propagates_provider_errors(doc_ref_factory) -> None:
    ref = doc_ref_factory(path="/broken")

    class BrokenProvider:
        def get_document(self, _ref):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        DocumentLoader().load(BrokenProvider(), {"broken": ref})
