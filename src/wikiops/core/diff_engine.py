from typing import Dict, List
from difflib import unified_diff

from wikiops_sdk.domain import ChangeSet, UpdateDocumentOperation


class DiffEngine:
    """Builds preview diffs for update operations."""

    @staticmethod
    def _find_document(documents: Dict[str, object], ref: object):
        for document in documents.values():
            if getattr(document, "ref", None) == ref:
                return document
        return None

    def render(self, documents: Dict[str, object], change_set: ChangeSet) -> str:
        chunks: List[str] = []
        for op in change_set.operations:
            if not isinstance(op, UpdateDocumentOperation):
                chunks.append(
                    f"# Operation {op.operation_id}\n"
                    f"Type: {op.operation}\n"
                    f"This operation creates a new content and has no line diff against an existing document."
                )
                continue

            current_doc = self._find_document(documents, op.ref)
            current_lines = (current_doc.content if current_doc else "").splitlines()
            new_lines = op.new_content.splitlines()

            diff = unified_diff(
                current_lines,
                new_lines,
                fromfile="current",
                tofile="planned",
                lineterm="",
            )

            chunks.append(f"# Operation {op.operation_id}\n" + "\n".join(diff))

        return "\n\n".join(chunks)
