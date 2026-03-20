"""Helpers for deterministic retrieval-analysis structures."""

from typing import Any


def build_retrieved_context_ids(
    retrieved_docs: list[Any], retriever_k: int
) -> dict[str, str]:
    """Return rank-ordered retrieved context IDs padded to retriever_k."""
    ids = [doc.metadata.get("doc_id", "") for doc in retrieved_docs[:retriever_k]]
    while len(ids) < retriever_k:
        ids.append("")
    return {f"retrieved_context_id_{rank}": value for rank, value in enumerate(ids, start=1)}
