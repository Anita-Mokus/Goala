"""
SapientiaRAG Dataset Ingestion Service.

Loads the local questions_answers_with_content.json file and stores all
unique passages in PGVector.

A side-output ``shared/sapientia_question_docids.json`` maps every question
text to its ground-truth doc_id; consumed by the MRR evaluation script.
"""
import gc
import json
from pathlib import Path
from typing import List, Optional, Set

from langchain_core.documents import Document
from langchain_postgres import PGVector

from src.utils.generate_mrr_template import main as generate_mrr_template_main
from src.core.config import DATABASE_URL, PGVECTOR_COLLECTION_NAME
from src.services.embeddings import get_embeddings

from .dataset_parser import (
    parse_document_field,
    extract_question_answer,
    extract_doc_ids_from_row,
)
from .persistence import save_question_docids_map, save_question_answers
from .database import ensure_extension_exists, store_documents_batch

_DATA_FILE = Path(__file__).parent.parent.parent.parent / "data" / "questions_answers_with_content.json"


class IngestSapientiaRAG:
    """Ingest pre-chunked passages from the local SapientiaRAG dataset."""

    def __init__(self):
        self.embedding_function = get_embeddings()
        self.connection_string = DATABASE_URL
        self.collection_name = PGVECTOR_COLLECTION_NAME
        self._project_root = Path(__file__).parent.parent.parent

    def ingest(self, batch_size: int = 600) -> None:
        """
        Load the local JSON dataset and store all unique passages in PGVector.

        Rows are processed in order; duplicate doc_ids are skipped globally.
        Q&A pairs and the doc-id map are flushed to disk after the single pass.

        Args:
            batch_size: Number of rows to buffer before each embed + store flush.
                        Larger values reduce DB round-trips; tune to your RAM.
        """
        print(f"Loading dataset from {_DATA_FILE}...")
        with open(_DATA_FILE, encoding="utf-8") as fh:
            rows = json.load(fh)
        print(f"  {len(rows)} rows loaded.")

        ensure_extension_exists(self.connection_string)

        print("Processing dataset...")
        store: Optional[PGVector] = None
        seen_ids: Set[str] = set()
        question_docids_map: dict = {}
        question_answers: List[tuple] = []
        doc_buffer: List[Document] = []
        total_docs = 0
        row_count = 0
        first_batch = True

        for row in rows:
            row_count += 1

            qa_pair = extract_question_answer(row)
            if qa_pair:
                question_answers.append(qa_pair)

            question = (row.get("question_text") or "").strip()
            doc_ids_for_q: List[str] = extract_doc_ids_from_row(row)

            content, doc_id = parse_document_field(row.get("document") or {})
            if content and not (doc_id and doc_id in seen_ids):
                if doc_id:
                    seen_ids.add(doc_id)
                metadata: dict = {"doc_id": doc_id}
                if row.get("question_id") is not None:
                    metadata["question_id"] = row["question_id"]
                doc_buffer.append(Document(page_content=content, metadata=metadata))

            if question:
                question_docids_map[question] = doc_ids_for_q

            if row_count % batch_size == 0 and doc_buffer:
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

        if doc_buffer:
            store = store_documents_batch(
                doc_buffer, store, first_batch,
                self.embedding_function, self.connection_string, self.collection_name
            )
            total_docs += len(doc_buffer)

        if total_docs == 0:
            raise RuntimeError("No documents produced — check the dataset file and field names.")

        print(f"  → {row_count} rows processed, {total_docs} unique documents stored")

        print("Saving question → doc_ids map for MRR evaluation...")
        save_question_docids_map(question_docids_map, self._project_root)
        del question_docids_map

        print("Saving question-answer pairs...")
        save_question_answers(question_answers, self._project_root)
        del question_answers

        print("Generating MRR template contexts and labels files...")
        generate_mrr_template_main()

        print(f"✓ Done! {total_docs} passages stored in collection '{self.collection_name}'.")
