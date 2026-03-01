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
import json
import os
from pathlib import Path
from typing import List, Optional

from datasets import load_dataset
from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

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

    def _dataset_to_documents(self, dataset) -> List[Document]:
        """
        Convert HuggingFace dataset rows to LangChain Document objects.

        Each LiveRAG/Benchmark row has a `Supporting_Documents` field that is a
        list of JSON strings (or already-parsed dicts), each with:
          - 'content' : the passage text
          - 'doc_id'  : unique document identifier

        Rows also carry `Question` and `Index` which are stored as metadata.
        Duplicate doc_ids across rows are de-duplicated.
        """
        documents = []
        seen_ids: set = set()

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

        print(len(documents))

        return documents

    def _store_documents(self, documents: List[Document]) -> None:
        """Embed and store documents in PGVector, replacing any existing collection."""
        PGVector.from_documents(
            documents=documents,
            embedding=self.embedding_function,
            connection=self.connection_string,
            collection_name=self.collection_name,
            use_jsonb=True,
            pre_delete_collection=True,
        )

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, split: str = "train", batch_size: int = 500) -> None:
        """
        Load the LiveRAG/Benchmark dataset and store all passages in PGVector.

        Args:
            split:      Dataset split to load (default: 'train').
            batch_size: Number of rows to convert at a time (memory safety).
        """
        print(f"Loading LiveRAG/Benchmark (split='{split}') from HuggingFace...")
        ds = load_dataset(
            "LiveRAG/Benchmark",
            split=split,
            token=HUGGINGFACE_TOKEN or None,
        )
        total = len(ds)
        print(f"  → {total} benchmark rows loaded")

        self._ensure_extension_exists()

        print("Extracting supporting documents and storing in PGVector...")
        all_docs: List[Document] = []

        for start in range(0, total, batch_size):
            batch = ds.select(range(start, min(start + batch_size, total)))
            docs = self._dataset_to_documents(batch)
            print(batch)
            print(50 * "*")
            all_docs.extend(docs)
            print(f"  Processed {min(start + batch_size, total)}/{total} rows...", end="\r")

        print(f"\n  → {len(all_docs)} non-empty documents ready")

        if not all_docs:
            raise RuntimeError("No documents produced — check the dataset field names.")

        print("Building question → doc_ids map for MRR evaluation...")
        question_docids_map = self._build_question_docids_map(ds)
        self._save_question_docids_map(question_docids_map)

        print("Saving embeddings to PostgreSQL...")
        self._store_documents(all_docs)
        print(f"✓ Done! {len(all_docs)} passages stored in collection '{self.collection_name}'.")

