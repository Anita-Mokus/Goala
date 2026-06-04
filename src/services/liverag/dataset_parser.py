"""
Dataset parsing helpers for SapientiaRAG ingestion.

Functions to convert local JSON dataset rows to LangChain Document objects
and build question-to-doc_id mappings.


"""
import json
from typing import List, Set

from langchain_core.documents import Document


def parse_document_field(entry) -> tuple[str, str]:
    """
    Parse the 'document' field of a dataset row.

    Args:
        entry: Either a dict or JSON string with 'content' and 'doc_id' fields.

    Returns:
        Tuple of (content, doc_id). Both may be empty strings if parsing fails.
    """
    if isinstance(entry, str):
        try:
            entry = json.loads(entry)
        except json.JSONDecodeError:
            return "", ""

    if not isinstance(entry, dict):
        return "", ""

    content = entry.get("content", "").strip()
    doc_id = entry.get("doc_id", "")
    return content, doc_id


def dataset_row_to_documents(row, seen_ids: Set[str]) -> List[Document]:
    """
    Convert a single JSON dataset row to a LangChain Document object.

    Each row carries a single `document` dict with 'content' and 'doc_id'.
    ``seen_ids`` is shared across all rows to deduplicate globally.

    Args:
        row: A single row from the local JSON dataset.
        seen_ids: Set of already-seen doc_ids (modified in-place).

    Returns:
        List with 0 or 1 Document objects.
    """
    content, doc_id = parse_document_field(row.get("document") or {})

    if not content:
        return []
    if doc_id and doc_id in seen_ids:
        return []
    if doc_id:
        seen_ids.add(doc_id)

    metadata: dict = {"doc_id": doc_id}
    if row.get("question_id") is not None:
        metadata["question_id"] = row["question_id"]

    return [Document(page_content=content, metadata=metadata)]


def build_question_docids_map(dataset) -> dict:
    """
    Build a mapping of question text → list of ground-truth doc_ids.

    Used during evaluation to compute MRR: for each question we need to
    know which doc_ids are relevant so we can check whether the retriever
    surfaces them at the top of its ranking.

    Args:
        dataset: Full list of JSON rows.

    Returns:
        Dict mapping question string → list of doc_id strings.
    """
    mapping: dict = {}
    for row in dataset:
        question = (row.get("question_text") or "").strip()
        if not question:
            continue
        _, doc_id = parse_document_field(row.get("document") or {})
        mapping[question] = [doc_id] if doc_id else []
    return mapping


def extract_question_answer(row) -> tuple[str, str] | None:
    """
    Extract question and answer from a dataset row.

    Args:
        row: A single row from the local JSON dataset.

    Returns:
        Tuple of (question, answer), or None if either is missing.
    """
    question = (row.get("question_text") or "").strip()
    answer = str(row.get("expected_output", "")).strip()
    if question and answer:
        return (question, answer)
    return None


def extract_doc_ids_from_row(row) -> List[str]:
    """
    Extract all doc_ids from a single dataset row.

    Args:
        row: A single row from the local JSON dataset.

    Returns:
        List of doc_id strings (0 or 1 element).
    """
    _, doc_id = parse_document_field(row.get("document") or {})
    return [doc_id] if doc_id else []
