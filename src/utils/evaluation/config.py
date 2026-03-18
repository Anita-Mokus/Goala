"""
Configuration constants for RAG evaluation.
"""

# Evaluation dataset and output settings
EVAL_FILE_NAME = "liverag_eval.json"          # Evaluation dataset file
MRR_LABELS_FILE = "liverag_mrr_labels.csv"    # Manually-labelled relevance CSV
QUESTION_DOCIDS_FILE = "liverag_question_docids.json"  # Question → doc_ids map
OUTPUT_DIR_NAME = "evaluation_results"        # Directory for results
OUTPUT_FILE_PREFIX = "eval_results_liveRAG"   # Prefix for output JSON files
JUDGE_LLM_TEMPERATURE = 0                     # Temperature for judge LLM (0 = deterministic)
MEMORY_CLEAR_INTERVAL = 5                     # Clear memory every N questions
