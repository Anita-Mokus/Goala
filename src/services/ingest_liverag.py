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
import os
from pathlib import Path
from typing import List, Optional, Set

from datasets import load_dataset
from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

from src.utils.generate_mrr_template import main as generate_mrr_template_main

from src.core.config import (
    HUGGINGFACE_TOKEN,
    DATABASE_URL,
    PGVECTOR_COLLECTION_NAME,
)
from src.services.embeddings import get_embeddings


class IngestLiveRAG:
    """Ingest pre-chunked passages from the LiveRAG/Benchmark HuggingFace dataset."""

    def __init__(self):
        self.embedding_function = get_embeddings()
        self.connection_string = DATABASE_URL
        self.collection_name = PGVECTOR_COLLECTION_NAME

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_extension_exists(self) -> None:
        """Ensure the pgvector extension is present in the database."""
        try:
            engine = create_engine(self.connection_string, echo=False)
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            engine.dispose()
            print("✓ pgvector extension confirmed")
        except Exception as e:
            print(f"ℹ Extension check: {type(e).__name__}: {e}")

    def _dataset_to_documents(self, dataset, seen_ids: Set[str]) -> List[Document]:
        """
        Convert HuggingFace dataset rows to LangChain Document objects.

        Each LiveRAG/Benchmark row has a `Supporting_Documents` field that is a
        list of JSON strings (or already-parsed dicts), each with:
          - 'content' : the passage text
          - 'doc_id'  : unique document identifier

        Rows also carry `Question` and `Index` which are stored as metadata.
        ``seen_ids`` is shared across all batch calls to deduplicate globally.
        """
        documents = []

        for row in dataset:
            supporting = row.get("Supporting_Documents") or []

            # The field may arrive as a list of dicts or a list of JSON strings.
            for entry in supporting:
                if isinstance(entry, str):
                    try:
                        entry = json.loads(entry)
                    except json.JSONDecodeError:
                        continue

                if not isinstance(entry, dict):
                    continue

                content = entry.get("content", "").strip()
                doc_id = entry.get("doc_id", "")

                if not content:
                    continue
                if doc_id and doc_id in seen_ids:
                    continue
                if doc_id:
                    seen_ids.add(doc_id)

                metadata: dict = {"doc_id": doc_id}
                # Attach the source question index for traceability
                if row.get("Index") is not None:
                    metadata["question_index"] = row["Index"]

                documents.append(Document(page_content=content, metadata=metadata))

        return documents

    def _store_documents_batch(
        self,
        documents: List[Document],
        store: Optional[PGVector],
        first_batch: bool,
    ) -> PGVector:
        """
        Embed and store a batch of documents in PGVector.

        On the first call the collection is recreated (pre_delete_collection=True)
        and the PGVector store object is returned so subsequent calls can reuse
        it via ``store.add_documents()`` instead of reconnecting each time.
        """
        if first_batch or store is None:
            store = PGVector.from_documents(
                documents=documents,
                embedding=self.embedding_function,
                connection=self.connection_string,
                collection_name=self.collection_name,
                use_jsonb=True,
                pre_delete_collection=True,
            )
        else:
            store.add_documents(documents)
        return store

    def _build_question_docids_map(self, dataset) -> dict:
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
                if isinstance(entry, str):
                    try:
                        entry = json.loads(entry)
                    except json.JSONDecodeError:
                        continue
                if isinstance(entry, dict):
                    doc_id = entry.get("doc_id", "")
                    if doc_id:
                        doc_ids.append(doc_id)
            mapping[question] = doc_ids
        return mapping

    def _save_question_docids_map(self, mapping: dict) -> None:
        """
        Persist the question → doc_ids mapping to ``shared/liverag_question_docids.json``.

        The file is written relative to this module's project root so it works
        both inside and outside Docker.
        """
        project_root = Path(__file__).parent.parent.parent
        output_path = project_root / "shared" / "liverag_question_docids.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(mapping, fh, ensure_ascii=False, indent=2)
        print(f"✓ Question→doc_ids map saved to {output_path} ({len(mapping)} entries)")

    def _save_question_answers(self, question_answers: List[tuple]) -> None:
        """
        Persist question-answer pairs to ``shared/liverag_eval.json``.

        The output matches the existing eval file schema:
          { "datasets": [ { "name": ..., "questions": [ {"input": ..., "expected_output": ...} ] } ] }
        """
        project_root = Path(__file__).parent.parent.parent
        output_path = project_root / "shared" / "liverag_eval.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "datasets": [
                {
                    "name": "liverag_benchmark_eval",
                    "description": (
                        f"Questions and ground-truth answers from the LiveRAG/Benchmark dataset "
                        f"({len(question_answers)} rows, FineWeb-10BT supporting documents)."
                    ),
                    "questions": [
                        {"input": q, "expected_output": a} for q, a in question_answers
                    ],
                }
            ]
        }
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"✓ Question-answer pairs saved to {output_path} ({len(question_answers)} entries)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, split: str = "train", batch_size: int = 100) -> None:
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
                        store flush (default: 100, ≈500 docs per flush).
        """
        print(f"Loading LiveRAG/Benchmark (split='{split}') in streaming mode...")
        ds = load_dataset(
            "LiveRAG/Benchmark",
            split=split,
            token=HUGGINGFACE_TOKEN or None,
            streaming=True,
        )

        self._ensure_extension_exists()

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

            question = (row.get("Question") or "").strip()
            answer = str(row.get("Answer", "")).strip()
            if question and answer:
                question_answers.append((question, answer))

            supporting = row.get("Supporting_Documents") or []
            doc_ids_for_q: List[str] = []

            for entry in supporting:
                if isinstance(entry, str):
                    try:
                        entry = json.loads(entry)
                    except json.JSONDecodeError:
                        continue
                if not isinstance(entry, dict):
                    continue

                doc_id = entry.get("doc_id", "")
                content = entry.get("content", "").strip()

                if doc_id:
                    doc_ids_for_q.append(doc_id)

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
                    store = self._store_documents_batch(doc_buffer, store, first_batch)
                    first_batch = False
                    total_docs += len(doc_buffer)
                    doc_buffer = []
                    gc.collect()
                print(f"  Processed {row_count} rows ({total_docs} docs stored)...")

        # Flush any remaining docs
        if doc_buffer:
            store = self._store_documents_batch(doc_buffer, store, first_batch)
            total_docs += len(doc_buffer)
            doc_buffer = []

        if total_docs == 0:
            raise RuntimeError("No documents produced — check the dataset field names.")

        print(f"  → {row_count} rows processed, {total_docs} documents stored")

        # Persist side outputs
        print("Saving question → doc_ids map for MRR evaluation...")
        self._save_question_docids_map(question_docids_map)
        del question_docids_map

        print("Saving question-answer pairs...")
        self._save_question_answers(question_answers)
        del question_answers

        print("Generating MRR template contexts and labels files...")
        generate_mrr_template_main()

        print(f"✓ Done! {total_docs} passages stored in collection '{self.collection_name}'.")

