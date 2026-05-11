from typing import Dict

from docops_sdk.contracts import DocumentProvider
from docops_sdk.domain import Document, DocumentRef


class DocumentLoader:
    """Loads source documents through the provider."""

    def load(
        self, provider: DocumentProvider, refs: Dict[str, DocumentRef]
    ) -> Dict[str, Document]:
        documents: Dict[str, Document] = {}
        for alias, ref in refs.items():
            documents[alias] = provider.get_document(ref)
        return documents
