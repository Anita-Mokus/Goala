"""
Evaluation configuration constants.
"""
# Evaluation dataset file
EVAL_FILE_NAME = "mbh_junior_hu_evalset.json"

# Directory for results
OUTPUT_DIR_NAME = "evaluation_results"

# Prefix for output JSON files
OUTPUT_FILE_PREFIX = "eval_results_"

# Temperature for judge LLM (0 = deterministic)
JUDGE_LLM_TEMPERATURE = 0

# Clear memory every N questions
MEMORY_CLEAR_INTERVAL = 5
