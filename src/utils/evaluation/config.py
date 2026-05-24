"""
Configuration constants for RAG evaluation.
"""

# Evaluation dataset and output settings
EVAL_FILE_NAME = "liverag_eval.json"          # Evaluation dataset file
QUESTION_DOCIDS_FILE = "liverag_question_docids.json"  # Question → doc_ids map
OUTPUT_DIR_NAME = "evaluation_results"        # Directory for results
OUTPUT_FILE_PREFIX_SINGLE_DOC = "eval_results_liveRAG_single_doc"   # Prefix for output JSON files
OUTPUT_FILE_PREFIX_MULTI_DOC = "eval_results_liveRAG_multi_doc"   # Prefix for output JSON files
OUTPUT_FILE_PREFIX_ALL_DOCS = "eval_results_liveRAG_all_docs"   # Prefix for output JSON files
JUDGE_LLM_TEMPERATURE = 0                     # Temperature for judge LLM (0 = deterministic)
MEMORY_CLEAR_INTERVAL = 5                     # Clear memory every N questions
