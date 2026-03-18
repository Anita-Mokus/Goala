"""
Dataset parsing helpers for LiveRAG ingestion.

Functions to convert HuggingFace dataset rows to LangChain Document objects
and build question-to-doc_id mappings.
"""
import json
from typing import List, Set

from langchain_core.documents import Document


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


def dataset_row_to_documents(row, seen_ids: Set[str]) -> List[Document]:
    """
    Convert a single HuggingFace dataset row to LangChain Document objects.
    
    Each LiveRAG/Benchmark row has a `Supporting_Documents` field that is a
    list of JSON strings (or already-parsed dicts), each with:
      - 'content' : the passage text
      - 'doc_id'  : unique document identifier
    
    Rows also carry `Question` and `Index` which are stored as metadata.
    ``seen_ids`` is shared across all batch calls to deduplicate globally.
    
    Args:
        row: A single row from the HuggingFace dataset.
        seen_ids: Set of already-seen doc_ids (modified in-place for deduplication).
        
    Returns:
        List of Document objects created from this row.
    """
    documents = []
    supporting = row.get("Supporting_Documents") or []
    
    for entry in supporting:
        content, doc_id = parse_supporting_document(entry)
        
        if not content:
            continue
        if doc_id and doc_id in seen_ids:
            continue
        if doc_id:
            seen_ids.add(doc_id)
        
        metadata: dict = {"doc_id": doc_id}
        if row.get("Index") is not None:
            metadata["question_index"] = row["Index"]
        
        documents.append(Document(page_content=content, metadata=metadata))
    
    return documents


def build_question_docids_map(dataset) -> dict:
    """
    Build a mapping of question text → list of ground-truth doc_ids.

    This is used during evaluation to compute Mean Reciprocal Rank (MRR):
    for each question we need to know which doc_ids are relevant so we
    can check whether the retriever surfaces them at the top of its ranking.

    Args:
        dataset: Full HuggingFace dataset (all rows, not batched).

    Returns:
        Dict mapping question string → list of doc_id strings.
    """
    mapping: dict = {}
    for row in dataset:
        question = (row.get("Question") or "").strip()
        if not question:
            continue
        supporting = row.get("Supporting_Documents") or []
        doc_ids = []
        for entry in supporting:
            _, doc_id = parse_supporting_document(entry)
            if doc_id:
                doc_ids.append(doc_id)
        mapping[question] = doc_ids
    return mapping


def extract_question_answer(row) -> tuple[str, str] | None:
    """
    Extract question and answer from a dataset row.
    
    Args:
        row: A single row from the HuggingFace dataset.
        
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
    
    Args:
        row: A single row from the HuggingFace dataset.
        
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
