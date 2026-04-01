"""
MRR Template Generator.

Runs the retriever for every question in the evaluation dataset and
produces three output files in ``shared/``:

  liverag_mrr_contexts.txt  — human-readable review: each question followed
                               by its retrieved contexts numbered by rank.

  liverag_retrieval_analysis_single_doc.csv — retrieval analysis for single-doc questions.
                               Format: question_id,context_id,retrieved_context_id_1,...,K

  liverag_retrieval_analysis_multi_doc.csv  — retrieval analysis for multi-doc questions.
                               Format: question_id,context_ids (pipe-separated),retrieved_context_id_1,...,K

  liverag_context_id_map.csv  — lookup table: context_id → raw_doc_id.

Run with:
    python -m src.utils.generate_mrr_template
"""
import csv
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services.rag_service import RAGService
from src.core.config import RETRIEVER_K
from src.utils.retrieval_analysis import (
    build_retrieved_context_ids,
    build_doc_id_numbering,
    to_numeric_doc_id,
)

EVAL_FILE_NAME   = "liverag_eval.json"
CONTEXTS_FILE    = "liverag_mrr_contexts.txt"
QUESTION_DOCIDS_FILE = "liverag_question_docids.json"
# Single-doc: question_id, context_id, retrieved_context_id_1..K
RETRIEVAL_ANALYSIS_SINGLE_DOC_FILE = "liverag_retrieval_analysis_single_doc.csv"
# Multi-doc:  question_id, context_ids (pipe-separated), retrieved_context_id_1..K
RETRIEVAL_ANALYSIS_MULTI_DOC_FILE  = "liverag_retrieval_analysis_multi_doc.csv"
CONTEXT_ID_MAP_FILE = "liverag_context_id_map.csv"  # context_id, raw_doc_id
SEPARATOR        = "=" * 72


def main() -> None:
    eval_file = project_root / "shared" / EVAL_FILE_NAME
    if not eval_file.exists():
        print(f"ERROR: {eval_file} not found")
        sys.exit(1)

    with open(eval_file, "r", encoding="utf-8") as fh:
        eval_data = json.load(fh)

    all_questions: list[tuple[int, str]] = []
    for dataset in eval_data.get("datasets", []):
        for item in dataset.get("questions", []):
            q = item.get("input", "").strip()
            if q:
                all_questions.append((len(all_questions), q))

    if not all_questions:
        print("ERROR: No questions found in the evaluation file.")
        sys.exit(1)

    print(f"Loaded {len(all_questions)} questions from {EVAL_FILE_NAME}")

    docids_path = project_root / "shared" / QUESTION_DOCIDS_FILE
    question_docids_map: dict = {}
    if docids_path.exists():
        with open(docids_path, "r", encoding="utf-8") as fh:
            question_docids_map = json.load(fh)
        print(f"  Auto-labeling enabled: {len(question_docids_map)} questions in doc_ids map")
    else:
        print(f"  INFO: {QUESTION_DOCIDS_FILE} not found — CSV labels will be all-zeros (fill manually)")

    print("Initializing RAG service...")
    rag_service = RAGService()
    doc_id_numbering = build_doc_id_numbering(question_docids_map)

    analysis_single_path = project_root / "shared" / RETRIEVAL_ANALYSIS_SINGLE_DOC_FILE
    analysis_multi_path  = project_root / "shared" / RETRIEVAL_ANALYSIS_MULTI_DOC_FILE
    context_map_path     = project_root / "shared" / CONTEXT_ID_MAP_FILE

    analysis_headers = [f"retrieved_context_id_{r}" for r in range(1, RETRIEVER_K + 1)]

    with open(analysis_single_path, "w", encoding="utf-8", newline="") as single_fh, \
         open(analysis_multi_path,  "w", encoding="utf-8", newline="") as multi_fh:

        single_writer = csv.writer(single_fh)
        single_writer.writerow(["question_id", "context_id"] + analysis_headers)

        
        multi_writer = csv.writer(multi_fh)
        multi_writer.writerow(["question_id", "context_id_1", "context_id_2"] + analysis_headers)

        single_count = 0
        multi_count  = 0

        for idx, question in all_questions:
            print(f"  [{idx + 1}/{len(all_questions)}] Retrieving: {question[:70]}...")

            try:
                retrieved_docs = rag_service.retriever.invoke(question)
            except Exception as exc:
                print(f"    ERROR: {exc}")
                retrieved_docs = []

            gt_ids_list = question_docids_map.get(question, [])
            gt_ids = set(gt_ids_list)

            for rank, doc in enumerate(retrieved_docs, start=1):
                doc_id  = doc.metadata.get("doc_id", "n/a")

            retrieved_context_fields = build_retrieved_context_ids(
                retrieved_docs, RETRIEVER_K, doc_id_numbering
            )
            retrieved_row_suffix = [
                retrieved_context_fields[f"retrieved_context_id_{r}"]
                for r in range(1, RETRIEVER_K + 1)
            ]

            if len(gt_ids_list) > 1:
                context_id_1 = to_numeric_doc_id(gt_ids_list[0], doc_id_numbering)
                context_id_2 = to_numeric_doc_id(gt_ids_list[1], doc_id_numbering)
                multi_writer.writerow([idx, context_id_1, context_id_2] + retrieved_row_suffix)
                multi_count += 1
            else:
                context_id = to_numeric_doc_id(gt_ids_list[0], doc_id_numbering) if gt_ids_list else ""
                single_writer.writerow([idx, context_id] + retrieved_row_suffix)
                single_count += 1

    print(f"✓ Retrieval analysis (single-doc) saved to: {analysis_single_path}  ({single_count} questions)")
    print(f"✓ Retrieval analysis (multi-doc)  saved to: {analysis_multi_path}  ({multi_count} questions)")
    with open(context_map_path, "w", encoding="utf-8", newline="") as map_fh:
        map_writer = csv.writer(map_fh)
        map_writer.writerow(["context_id", "raw_doc_id"])
        for raw_doc_id, numeric_id in sorted(doc_id_numbering.items(), key=lambda item: item[1]):
            map_writer.writerow([numeric_id, raw_doc_id])
    print(f"✓ Context ID map saved to:    {context_map_path}")
    print(f"  (Labels set to 1 where retrieved doc_id matches ground truth;")
    print(f"   edit the CSV manually to override any labels.)")
    print()


if __name__ == "__main__":
    main()
