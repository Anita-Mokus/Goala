"""
File I/O operations for RAG evaluation.

Loading evaluation data and saving results.
"""
import json
from pathlib import Path


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
