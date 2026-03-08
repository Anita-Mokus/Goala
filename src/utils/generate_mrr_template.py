"""
MRR Template Generator.

Runs the retriever for every question in the evaluation dataset and
produces two output files in ``shared/``:

  liverag_mrr_contexts.txt  — human-readable review: each question followed
                               by its retrieved contexts numbered by rank.
                               Use this file to decide which context(s) give
                               the correct answer.

  liverag_mrr_labels.csv    — blank template to fill in.
                               Format: question_index,c1,c2,...,cK
                               Set the column to 1 for the rank position that
                               contains the answer-giving context, 0 otherwise.
                               Example for 5 retrieved docs where rank-2 is correct:
                                 3,0,1,0,0,0

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

# ── configurable ────────────────────────────────────────────────────────────
EVAL_FILE_NAME   = "liverag_eval.json"
CONTEXTS_FILE    = "liverag_mrr_contexts.txt"
LABELS_CSV_FILE  = "liverag_mrr_labels.csv"
QUESTION_DOCIDS_FILE = "liverag_question_docids.json"
SEPARATOR        = "=" * 72
# ────────────────────────────────────────────────────────────────────────────


def main() -> None:
    eval_file = project_root / "shared" / EVAL_FILE_NAME
    if not eval_file.exists():
        print(f"ERROR: {eval_file} not found")
        sys.exit(1)

    with open(eval_file, "r", encoding="utf-8") as fh:
        eval_data = json.load(fh)

    # Flatten all questions across datasets while keeping a global index
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

    # Load ground-truth doc_ids for auto-labeling the CSV
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

    contexts_path = project_root / "shared" / CONTEXTS_FILE
    labels_path   = project_root / "shared" / LABELS_CSV_FILE

    # Column headers for the CSV: c1 … cK  (rank 1 = c1)
    col_headers = [f"c{r}" for r in range(1, RETRIEVER_K + 1)]

    with open(contexts_path, "w", encoding="utf-8") as ctx_fh, \
         open(labels_path,   "w", encoding="utf-8", newline="") as csv_fh:

        writer = csv.writer(csv_fh)
        writer.writerow(["question_index"] + col_headers)

        for idx, question in all_questions:
            print(f"  [{idx + 1}/{len(all_questions)}] Retrieving: {question[:70]}...")

            try:
                retrieved_docs = rag_service.retriever.invoke(question)
            except Exception as exc:
                print(f"    ERROR: {exc}")
                retrieved_docs = []

            # ── human-readable review file ───────────────────────────────
            gt_ids = set(question_docids_map.get(question, []))

            ctx_fh.write(f"{SEPARATOR}\n")
            ctx_fh.write(f"QUESTION INDEX: {idx}\n")
            ctx_fh.write(f"QUESTION: {question}\n")
            if gt_ids:
                ctx_fh.write(f"GROUND TRUTH DOC_IDs: {', '.join(gt_ids)}\n")
            ctx_fh.write(f"{SEPARATOR}\n\n")

            for rank, doc in enumerate(retrieved_docs, start=1):
                doc_id  = doc.metadata.get("doc_id", "n/a")
                snippet = doc.page_content.strip().replace("\n", " ")
                match_marker = " ← GT MATCH" if doc_id in gt_ids else ""
                ctx_fh.write(f"  Rank {rank}  [doc_id: {doc_id}]{match_marker}\n")
                ctx_fh.write(f"  {snippet}\n\n")

            if not retrieved_docs:
                ctx_fh.write("  (no documents retrieved)\n\n")

            # ── CSV row: auto-label using doc_id matching ─────────────────
            # 1 at the rank position(s) where a GT doc was retrieved, 0 elsewhere.
            # If liverag_question_docids.json is missing, defaults to all-zeros.
            labels = [0] * RETRIEVER_K
            for rank_i, doc in enumerate(retrieved_docs[:RETRIEVER_K]):
                if doc.metadata.get("doc_id", "") in gt_ids:
                    labels[rank_i] = 1

            writer.writerow([idx] + labels)

    print(f"\n✓ Context review saved to:  {contexts_path}")
    print(f"✓ Auto-labeled CSV saved to: {labels_path}")
    print(f"  (Labels set to 1 where retrieved doc_id matches ground truth;")
    print(f"   edit the CSV manually to override any labels.)")
    print()


if __name__ == "__main__":
    main()
