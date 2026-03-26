"""
RAG Evaluation module.

Provides the evaluate_rag function for evaluating RAG system performance.
"""
from .runner import evaluate_rag
from .metrics import (
    compute_reciprocal_rank_from_labels,
    compute_reciprocal_rank_from_docids,
    compute_recall_at_k,
    compute_score_stats,
    print_stats,
)
from .judge import JUDGE_PROMPT_TEMPLATE, parse_judge_response
from .io import load_mrr_labels
from .config import (
    EVAL_FILE_NAME,
    MRR_LABELS_FILE,
    QUESTION_DOCIDS_FILE,
    OUTPUT_DIR_NAME,
    OUTPUT_FILE_PREFIX_SINGLE_DOC,
    OUTPUT_FILE_PREFIX_MULTI_DOC,
    OUTPUT_FILE_PREFIX_ALL_DOCS,
    JUDGE_LLM_TEMPERATURE,
    MEMORY_CLEAR_INTERVAL,
)

__all__ = [
    "evaluate_rag",
    "compute_reciprocal_rank_from_labels",
    "compute_reciprocal_rank_from_docids",
    "compute_recall_at_k",
    "compute_score_stats",
    "print_stats",
    "JUDGE_PROMPT_TEMPLATE",
    "parse_judge_response",
    "load_mrr_labels",
    "EVAL_FILE_NAME",
    "MRR_LABELS_FILE",
    "QUESTION_DOCIDS_FILE",
    "OUTPUT_DIR_NAME",
    "OUTPUT_FILE_PREFIX_SINGLE_DOC",
    "OUTPUT_FILE_PREFIX_MULTI_DOC",
    "OUTPUT_FILE_PREFIX_ALL_DOCS",
    "JUDGE_LLM_TEMPERATURE",
    "MEMORY_CLEAR_INTERVAL",
]
