"""
LiveRAG Dataset Ingestion Service.

The LiveRAG/Benchmark dataset is a Q&A benchmark whose supporting documents
are stored as JSON objects inside the `Supporting_Documents` column:
  [{"content": "...", "doc_id": "..."}, ...]

Each row's supporting docs are extracted, de-duplicated, and stored in PGVector.
A side-output ``shared/liverag_question_docids.json`` maps every question text
to its list of ground-truth doc_ids; this file is consumed by the MRR
computation in the evaluation script.

No chunking is performed — each passage is already a standalone unit.
"""
import gc
from pathlib import Path
from typing import List, Optional, Set

from langchain_core.documents import Document
from langchain_postgres import PGVector

from src.config import (
    HUGGINGFACE_TOKEN,
    DATABASE_URL,
    DEFAULT_DATASET_KEY,
    get_dataset_collection_name,
    normalize_dataset_key,
)
from src.embeddings import get_embeddings
from src.ingest.vector_store import ensure_extension_exists

from .dataset_parser import (
    parse_supporting_document,
    extract_question_answer,
    extract_doc_ids_from_row,
)
from .persistence import save_question_docids_map, save_question_answers

LIVERAG_DEFAULT_KEY = "liverag"


def _store_batch(
    documents: List[Document],
    store: Optional[PGVector],
    first_batch: bool,
    embedding_function,
    connection_string: str,
    collection_name: str,
) -> PGVector:
    """Embed and store a batch of documents. Recreates the collection on the first batch."""
    if first_batch or store is None:
        store = PGVector.from_documents(
            documents=documents,
            embedding=embedding_function,
            connection=connection_string,
            collection_name=collection_name,
            use_jsonb=True,
            pre_delete_collection=True,
        )
    else:
        store.add_documents(documents)
    return store


class LiveRAGIngestService:
    """Ingest pre-chunked passages from the LiveRAG/Benchmark HuggingFace dataset."""

    def __init__(self, dataset_key: str = LIVERAG_DEFAULT_KEY):
        self.dataset_key = normalize_dataset_key(dataset_key)
        self.embedding_function = get_embeddings()
        self.connection_string = DATABASE_URL
        self.collection_name = get_dataset_collection_name(self.dataset_key)
        self._project_root = Path(__file__).parent.parent.parent.parent

    def ingest(
        self,
        split: str = "train",
        batch_size: int = 100,
        max_rows: Optional[int] = None,
    ) -> None:
        """
        Load the LiveRAG/Benchmark dataset in streaming mode and store all
        passages in PGVector.

        Args:
            split:      Dataset split to load (default: 'train').
            batch_size: Number of rows to buffer before each embed+store flush.
            max_rows:   Stop after this many rows (useful for smoke tests).
        """
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise ImportError(
                "The 'datasets' package is required for LiveRAG ingestion. "
                "Install it with: pip install datasets"
            ) from exc

        print(f"Loading LiveRAG/Benchmark (split='{split}') in streaming mode...")
        ds = load_dataset(
            "LiveRAG/Benchmark",
            split=split,
            token=HUGGINGFACE_TOKEN or None,
            streaming=True,
        )
        ensure_extension_exists(self.connection_string)
        print(f"Target collection: '{self.collection_name}'")
        total_docs, question_docids_map, question_answers = self._streaming_pass(
            ds, batch_size, max_rows
        )
        print("Saving question → doc_ids map for MRR evaluation...")
        save_question_docids_map(question_docids_map, self._project_root)
        print("Saving question-answer pairs...")
        save_question_answers(question_answers, self._project_root)
        print(f"✓ Done! {total_docs} passages stored in collection '{self.collection_name}'.")

    def _streaming_pass(self, ds, batch_size: int, max_rows: Optional[int]):
        """Single streaming pass: embed+store docs, accumulate Q&A side outputs."""
        store: Optional[PGVector] = None
        seen_ids: Set[str] = set()
        question_docids_map: dict = {}
        question_answers: List[tuple] = []
        doc_buffer: List[Document] = []
        total_docs = 0
        row_count = 0
        first_batch = True

        for row in ds:
            row_count += 1
            if max_rows is not None and row_count > max_rows:
                print(f"  Reached max_rows={max_rows}, stopping early.")
                break

            qa_pair = extract_question_answer(row)
            if qa_pair:
                question_answers.append(qa_pair)

            question = (row.get("Question") or "").strip()
            doc_ids_for_q: List[str] = extract_doc_ids_from_row(row)
            if question:
                question_docids_map[question] = doc_ids_for_q

            for entry in (row.get("Supporting_Documents") or []):
                content, doc_id = parse_supporting_document(entry)
                if not content or (doc_id and doc_id in seen_ids):
                    continue
                if doc_id:
                    seen_ids.add(doc_id)
                metadata: dict = {"doc_id": doc_id, "dataset": self.dataset_key}
                if row.get("Index") is not None:
                    metadata["question_index"] = row["Index"]
                doc_buffer.append(Document(page_content=content, metadata=metadata))

            if row_count % batch_size == 0:
                if doc_buffer:
                    store = _store_batch(
                        doc_buffer, store, first_batch,
                        self.embedding_function, self.connection_string, self.collection_name
                    )
                    first_batch = False
                    total_docs += len(doc_buffer)
                    doc_buffer = []
                    gc.collect()
                print(f"  Processed {row_count} rows ({total_docs} docs stored)...")

        if doc_buffer:
            store = _store_batch(
                doc_buffer, store, first_batch,
                self.embedding_function, self.connection_string, self.collection_name
            )
            total_docs += len(doc_buffer)

        if total_docs == 0:
            raise RuntimeError("No documents produced — check the dataset field names.")

        print(f"  → {row_count} rows processed, {total_docs} documents stored")
        return total_docs, question_docids_map, question_answers
