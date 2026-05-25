"""
Dataset parsing helpers for LiveRAG ingestion.

Functions to convert HuggingFace dataset rows to document fields
and build question-to-doc_id mappings.
"""
import json
from typing import List


def parse_supporting_document(entry) -> tuple[str, str]:
    """
    Parse a single supporting document entry.

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


def extract_question_answer(row) -> tuple[str, str] | None:
    """
    Extract question and answer from a dataset row.

    Returns:
        Tuple of (question, answer), or None if either is missing.
    """
    question = (row.get("Question") or "").strip()
    answer = str(row.get("Answer", "")).strip()
    if question and answer:
        return (question, answer)
    return None


def extract_doc_ids_from_row(row) -> List[str]:
    """
    Extract all doc_ids from a single dataset row.

    Returns:
        List of doc_id strings.
    """
    supporting = row.get("Supporting_Documents") or []
    doc_ids = []
    for entry in supporting:
        _, doc_id = parse_supporting_document(entry)
        if doc_id:
            doc_ids.append(doc_id)
    return doc_ids
