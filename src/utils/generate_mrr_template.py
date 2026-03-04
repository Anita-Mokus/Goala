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
            ctx_fh.write(f"{SEPARATOR}\n")
            ctx_fh.write(f"QUESTION INDEX: {idx}\n")
            ctx_fh.write(f"QUESTION: {question}\n")
            ctx_fh.write(f"{SEPARATOR}\n\n")

            for rank, doc in enumerate(retrieved_docs, start=1):
                doc_id  = doc.metadata.get("doc_id", "n/a")
                snippet = doc.page_content.strip().replace("\n", " ")
                ctx_fh.write(f"  Rank {rank}  [doc_id: {doc_id}]\n")
                ctx_fh.write(f"  {snippet}\n\n")

            if not retrieved_docs:
                ctx_fh.write("  (no documents retrieved)\n\n")

            # ── CSV row: all zeros — user fills in the correct rank ───────
            # Pad to RETRIEVER_K columns in case fewer docs were returned
            n = len(retrieved_docs)
            labels = [0] * RETRIEVER_K
            # Mark unreturned positions so the user knows they are empty
            # (they stay 0; the review file makes this clear)
            writer.writerow([idx] + labels[:RETRIEVER_K])

    print(f"\n✓ Context review saved to:  {contexts_path}")
    print(f"✓ Blank CSV template saved: {labels_path}")
    print()
    # print("Next steps:")
    # print(f"  1. Open {CONTEXTS_FILE} and read each question's retrieved contexts.")
    # print(f"  2. In {LABELS_CSV_FILE}, set the column to 1 for the rank that gives")
    # print(f"     the correct answer (leave all 0 if none of the contexts are correct).")
    # print(f"  3. Re-run evaluate_rag.py — it will read the filled CSV and compute MRR.")


if __name__ == "__main__":
    main()
