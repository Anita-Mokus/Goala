"""Helpers for deterministic retrieval-analysis structures."""

from typing import Any


def build_doc_id_numbering(question_docids_map: dict[str, list[str]]) -> dict[str, int]:
    """Build a stable raw-doc-id -> numeric-id mapping (1-based)."""
    numbering: dict[str, int] = {}
    for doc_ids in question_docids_map.values():
        for doc_id in doc_ids:
            if doc_id and doc_id not in numbering:
                numbering[doc_id] = len(numbering) + 1
    return numbering


def to_numeric_doc_id(doc_id: str, doc_id_numbering: dict[str, int]) -> int | str:
    """Convert raw doc_id to a numeric ID, assigning a new number on first sight."""
    if not doc_id:
        return ""
    if doc_id not in doc_id_numbering:
        doc_id_numbering[doc_id] = len(doc_id_numbering) + 1
    return doc_id_numbering[doc_id]


def build_retrieved_context_ids(
    retrieved_docs: list[Any], retriever_k: int, doc_id_numbering: dict[str, int]
) -> dict[str, int | str]:
    """Return rank-ordered numeric retrieved context IDs padded to retriever_k."""
    ids = [
        to_numeric_doc_id(doc.metadata.get("doc_id", ""), doc_id_numbering)
        for doc in retrieved_docs[:retriever_k]
    ]
    while len(ids) < retriever_k:
        ids.append("")
    return {f"retrieved_context_id_{rank}": value for rank, value in enumerate(ids, start=1)}
