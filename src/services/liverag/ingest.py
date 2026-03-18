"""
LiveRAG Dataset Ingestion Service.

The LiveRAG/Benchmark dataset is a Q&A benchmark whose supporting documents
are stored as JSON objects inside the `Supporting_Documents` column:
  [{"content": "...", "doc_id": "..."}, ...]

Each row's supporting docs are extracted, de-duplicated, and stored in PGVector.
A side-output ``shared/liverag_question_docids.json`` maps every question text
to its list of ground-truth doc_ids; this file is consumed by the MRR
computation in the evaluation script.
"""
import gc
import json
from pathlib import Path
from typing import List, Optional, Set

from datasets import load_dataset
from langchain_core.documents import Document
from langchain_postgres import PGVector

from src.utils.generate_mrr_template import main as generate_mrr_template_main
from src.core.config import (
    HUGGINGFACE_TOKEN,
    DATABASE_URL,
    PGVECTOR_COLLECTION_NAME,
)
from src.services.embeddings import get_embeddings

from .dataset_parser import (
    parse_supporting_document,
    extract_question_answer,
    extract_doc_ids_from_row,
)
from .persistence import save_question_docids_map, save_question_answers
from .database import ensure_extension_exists, store_documents_batch


class IngestLiveRAG:
    """Ingest pre-chunked passages from the LiveRAG/Benchmark HuggingFace dataset."""

    def __init__(self):
        self.embedding_function = get_embeddings()
        self.connection_string = DATABASE_URL
        self.collection_name = PGVECTOR_COLLECTION_NAME
        self._project_root = Path(__file__).parent.parent.parent

    def ingest(self, split: str = "train", batch_size: int = 600, max_rows: Optional[int] = None) -> None:
        """
        Load the LiveRAG/Benchmark dataset in streaming mode and store all
        passages in PGVector.

        Uses ``streaming=True`` so the dataset is **never fully loaded into
        RAM** — each row is fetched, processed, and discarded before the next
        one arrives.  Q&A pairs and the doc-id map are accumulated as lightweight
        string structures and flushed to disk after the single pass.

        Args:
            split:      Dataset split to load (default: 'train').
            batch_size: Number of dataset rows to buffer before each embed +
                        store flush (default: 600, ≈5000 docs per flush).
                        Larger values reduce DB round-trips; tune to your RAM.
            max_rows:   If set, stop after processing this many rows.  Useful
                        for smoke-testing the pipeline on a small slice without
                        waiting for the full dataset.
        """
        print(f"Loading LiveRAG/Benchmark (split='{split}') in streaming mode...")
        ds = load_dataset(
            "LiveRAG/Benchmark",
            split=split,
            token=HUGGINGFACE_TOKEN or None,
            streaming=True,
        )

        ensure_extension_exists(self.connection_string)

        # Single streaming pass — nothing is held in memory beyond one row at a time
        # except the lightweight side-output dicts and the current doc buffer.
        print("Processing dataset (single streaming pass)...")
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

            # Extract question-answer pair
            qa_pair = extract_question_answer(row)
            if qa_pair:
                question_answers.append(qa_pair)

            question = (row.get("Question") or "").strip()
            supporting = row.get("Supporting_Documents") or []
            doc_ids_for_q: List[str] = extract_doc_ids_from_row(row)

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
                doc_buffer.append(Document(page_content=content, metadata=metadata))

            if question:
                question_docids_map[question] = doc_ids_for_q

            # Flush the doc buffer every batch_size rows
            if row_count % batch_size == 0:
                if doc_buffer:
                    store = store_documents_batch(
                        doc_buffer, store, first_batch,
                        self.embedding_function, self.connection_string, self.collection_name
                    )
                    first_batch = False
                    total_docs += len(doc_buffer)
                    doc_buffer = []
                    gc.collect()
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass
                print(f"  Processed {row_count} rows ({total_docs} docs stored)...")

        # Flush any remaining docs
        if doc_buffer:
            store = store_documents_batch(
                doc_buffer, store, first_batch,
                self.embedding_function, self.connection_string, self.collection_name
            )
            total_docs += len(doc_buffer)
            doc_buffer = []

        if total_docs == 0:
            raise RuntimeError("No documents produced — check the dataset field names.")

        print(f"  → {row_count} rows processed, {total_docs} documents stored")

        # Persist side outputs
        print("Saving question → doc_ids map for MRR evaluation...")
        save_question_docids_map(question_docids_map, self._project_root)
        del question_docids_map

        print("Saving question-answer pairs...")
        save_question_answers(question_answers, self._project_root)
        del question_answers

        print("Generating MRR template contexts and labels files...")
        generate_mrr_template_main()

        print(f"✓ Done! {total_docs} passages stored in collection '{self.collection_name}'.")
