"""
Persistence functions for LiveRAG ingestion.

Save question-docid mappings and evaluation files to disk.
"""
import json
from pathlib import Path
from typing import List


def save_question_docids_map(mapping: dict, project_root: Path) -> None:
    """
    Persist the question → doc_ids mapping to ``shared/liverag_question_docids.json``.

    The file is written relative to the project root so it works
    both inside and outside Docker.
    
    Args:
        mapping: Dict mapping question text → list of doc_id strings.
        project_root: Path to the project root directory.
    """
    output_path = project_root / "shared" / "liverag_question_docids.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, ensure_ascii=False, indent=2)
    print(f"✓ Question→doc_ids map saved to {output_path} ({len(mapping)} entries)")


def save_question_answers(question_answers: List[tuple], project_root: Path) -> None:
    """
    Persist question-answer pairs to ``shared/liverag_eval.json``.

    The output matches the existing eval file schema:
      { "datasets": [ { "name": ..., "questions": [ {"input": ..., "expected_output": ...} ] } ] }
      
    Args:
        question_answers: List of (question, answer) tuples.
        project_root: Path to the project root directory.
    """
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
