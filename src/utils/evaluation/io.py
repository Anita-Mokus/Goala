"""
File I/O operations for RAG evaluation.

Loading labels, evaluation data, and saving results.
"""
import csv
import json
from pathlib import Path

from src.core.config import (
    CHUNK_MAX_CHARACTERS,
    CHUNK_NEW_AFTER_N_CHARS,
    CHUNK_OVERLAP,
    CHUNK_MULTIPAGE_SECTIONS,
)


def load_mrr_labels(labels_path: Path) -> dict[int, list[int]]:
    """
    Load the manually-filled MRR labels CSV.

    Expected CSV format (produced by generate_mrr_template.py)::

        question_index,c1,c2,c3,...,cK
        0,1,0,0,0,0,0,0,0
        1,0,0,1,0,0,0,0,0

    Returns a dict mapping ``question_index`` (int) → list of binary ints
    (one element per retrieved rank position, 1 = relevant).
    """
    labels: dict[int, list[int]] = {}
    with open(labels_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                idx = int(row["question_index"])
            except (KeyError, ValueError):
                continue
            # collect all cN columns in order
            rank_cols = sorted(
                (k for k in row if k.startswith("c")),
                key=lambda k: int(k[1:]),
            )
            labels[idx] = [int(row[col] or 0) for col in rank_cols]
    return labels


def get_chunk_config() -> dict:
    """Get chunking and RAG configuration from config module."""
    return {
        "chunking_strategy": "chunk_by_title",
        "chunk_max_characters": CHUNK_MAX_CHARACTERS,
        "chunk_new_after_n_chars": CHUNK_NEW_AFTER_N_CHARS,
        "chunk_overlap": CHUNK_OVERLAP,
        "chunk_multipage_sections": CHUNK_MULTIPAGE_SECTIONS,
    }


def load_eval_data(eval_file: Path) -> dict:
    """Load evaluation dataset from JSON file."""
    with open(eval_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_question_docids_map(docids_path: Path) -> dict:
    """Load question → doc_ids map from JSON file."""
    if not docids_path.exists():
        return {}
    with open(docids_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_results(output_data: dict, output_file: Path) -> None:
    """Save evaluation results to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
