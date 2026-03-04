"""
RAG Evaluation Script.
Tests the RAG system using questions from mbh_junior_hu_evalset.json
and evaluates responses using an LLM judge.
Outputs results in JSON format with configuration metadata.
"""
import csv
import sys
import json
import time
import gc
import torch
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services import RAGService
from src.services.llm_provider import get_llm_provider
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_PROVIDER,
    RETRIEVER_K,
    CHUNK_MAX_CHARACTERS,
    CHUNK_NEW_AFTER_N_CHARS,
    CHUNK_OVERLAP,
    CHUNK_MULTIPAGE_SECTIONS,
    JUDGE_LLM_PROVIDER,
    JUDGE_LLM_MODEL,
    LIVERAG_RAG_PROMPT_TEMPLATE,
)


# ============================================================================
# CONFIGURATION - Modify these variables to change evaluation behavior
# ============================================================================
EVAL_FILE_NAME = "liverag_eval.json"          # Evaluation dataset file
MRR_LABELS_FILE = "liverag_mrr_labels.csv"    # Manually-labelled relevance CSV (see generate_mrr_template.py)
QUESTION_DOCIDS_FILE = "liverag_question_docids.json"  # Question → doc_ids map (produced by ingest)
OUTPUT_DIR_NAME = "evaluation_results"        # Directory for results
OUTPUT_FILE_PREFIX = "eval_results_liveRAG"   # Prefix for output JSON files
JUDGE_LLM_TEMPERATURE = 0                     # Temperature for judge LLM (0 = deterministic)
MEMORY_CLEAR_INTERVAL = 5                     # Clear memory every N questions
# ============================================================================


# Load the judge prompt template
JUDGE_PROMPT_TEMPLATE = """You are an impartial evaluator for question-answering tasks. 
 
Your job is to evaluate whether the LLM answer correctly answers the question, 
based on the provided ground truth answer. 
 
Rules: 
- Focus on factual correctness and completeness. 
- Ignore differences in wording or style. 
- Do not reward unsupported extra information. 
- Do not penalize correct paraphrasing. 
 
Scoring rubric: 
5 = Fully correct and equivalent to the ground truth 
4 = Mostly correct, very minor omission or imprecision 
3 = Partially correct, missing key information 
2 = Mostly incorrect, only small correct elements 
1 = Completely incorrect or unrelated 
 
Question: 
{question} 
 
Ground truth answer: 
{answer} 
 
LLM answer: 
{llm_answer} 
 
Output exactly two lines: 
 
SCORE: <integer from 1 to 5> 
EXPLANATION: <brief explanation> 
"""


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


def compute_reciprocal_rank_from_labels(labels: list[int]) -> float:
    """
    Compute the reciprocal rank from a binary relevance label list.

    Args:
        labels: List of 0/1 values aligned with retrieval rank order.
                ``labels[0]`` corresponds to rank 1 (highest-ranked doc).

    Returns:
        ``1 / rank`` of the first relevant position, or ``0.0`` if none.
    """
    for rank, relevant in enumerate(labels, start=1):
        if relevant:
            return 1.0 / rank
    return 0.0


def parse_judge_response(response: str) -> tuple[int, str]:
    """Parse the judge's response to extract score and explanation."""
    lines = response.strip().split('\n')
    score = None
    explanation = ""
    
    for line in lines:
        if line.startswith('SCORE:'):
            try:
                score = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                score = 0
        elif line.startswith('EXPLANATION:'):
            explanation = line.split(':', 1)[1].strip()
    
    return score, explanation


def get_chunk_config():
    """Get chunking and RAG configuration from config module."""
    return {
        "chunking_strategy": "chunk_by_title",
        "chunk_max_characters": CHUNK_MAX_CHARACTERS,
        "chunk_new_after_n_chars": CHUNK_NEW_AFTER_N_CHARS,
        "chunk_overlap": CHUNK_OVERLAP,
        "chunk_multipage_sections": CHUNK_MULTIPAGE_SECTIONS,
    }

def compute_score_stats(results: list, label: str) -> dict | None:
    """
    Compute score distribution and MRR statistics for a subset of results.

    Args:
        results: List of result dicts (full or filtered).
        label:   Human-readable group name used in console output.

    Returns:
        Statistics dict, or None if there are no results.
    """
    if not results:
        return None

    scores = [r["score"] for r in results if isinstance(r["score"], int)]
    rr_values = [r["reciprocal_rank"] for r in results if r.get("reciprocal_rank") is not None]

    stats: dict = {
        "label": label,
        "total_questions": len(results),
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "score_distribution": {
            "score_5": {"count": scores.count(5), "percentage": round(scores.count(5) / len(scores) * 100, 1)},
            "score_4": {"count": scores.count(4), "percentage": round(scores.count(4) / len(scores) * 100, 1)},
            "score_3": {"count": scores.count(3), "percentage": round(scores.count(3) / len(scores) * 100, 1)},
            "score_2": {"count": scores.count(2), "percentage": round(scores.count(2) / len(scores) * 100, 1)},
            "score_1": {"count": scores.count(1), "percentage": round(scores.count(1) / len(scores) * 100, 1)},
        } if scores else {},
    }

    if rr_values:
        mrr = round(sum(rr_values) / len(rr_values), 4)
        stats["mrr"] = {
            "mean_reciprocal_rank": mrr,
            "questions_with_ground_truth": len(rr_values),
            "questions_hit_at_1": sum(1 for rr in rr_values if rr == 1.0),
            "questions_hit_at_3": sum(1 for rr in rr_values if rr >= 1 / 3),
            "questions_hit_at_5": sum(1 for rr in rr_values if rr >= 1 / 5),
            "questions_hit_at_k": sum(1 for rr in rr_values if rr > 0),
        }

    return stats


def print_stats(stats: dict) -> None:
    """Print a statistics block to stdout."""
    print(f"\n--- {stats['label']} ({stats['total_questions']} questions) ---")
    if stats.get("average_score") is not None:
        print(f"  Average score: {stats['average_score']}/5")
    if stats.get("score_distribution"):
        print("  Score Distribution:")
        for level, data in stats["score_distribution"].items():
            print(f"    {level}: {data['count']} ({data['percentage']}%)")
    if "mrr" in stats:
        m = stats["mrr"]
        n = m["questions_with_ground_truth"]
        print(f"  Retrieval — Mean Reciprocal Rank (MRR):")
        print(f"    MRR:              {m['mean_reciprocal_rank']:.4f}")
        print(f"    Questions w/ GT:  {n}")
        print(f"    Hit@1:            {m['questions_hit_at_1']} ({round(m['questions_hit_at_1']/n*100,1)}%)")
        print(f"    Hit@3:            {m['questions_hit_at_3']} ({round(m['questions_hit_at_3']/n*100,1)}%)")
        print(f"    Hit@5:            {m['questions_hit_at_5']} ({round(m['questions_hit_at_5']/n*100,1)}%)")
        print(f"    Hit@K (any rank): {m['questions_hit_at_k']} ({round(m['questions_hit_at_k']/n*100,1)}%)")

def evaluate_rag():
    """Run the RAG evaluation."""
    print("\n" + "=" * 60)
    print("AI Chat Flow - RAG Evaluation")
    print("=" * 60 + "\n")
    print(f"Starting evalaution at {time.localtime().tm_hour}:{time.localtime().tm_min}:{time.localtime().tm_sec}")
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    
    # Load evaluation dataset
    eval_file = project_root / 'shared' / EVAL_FILE_NAME
    if not eval_file.exists():
        print(f"ERROR: Evaluation file not found: {eval_file}")
        sys.exit(1)
    
    with open(eval_file, 'r', encoding='utf-8') as f:
        eval_data = json.load(f)

    # Load question → doc_ids map to know how many supporting docs each question has
    docids_path = project_root / 'shared' / QUESTION_DOCIDS_FILE
    question_docids_map: dict = {}
    if docids_path.exists():
        with open(docids_path, 'r', encoding='utf-8') as f:
            question_docids_map = json.load(f)
        print(f"  Loaded question→doc_ids map: {len(question_docids_map)} entries")
    else:
        print(f"  INFO: {QUESTION_DOCIDS_FILE} not found — single/multi-doc split will be skipped.")    
    labels_file = project_root / 'shared' / MRR_LABELS_FILE
    mrr_labels: dict[int, list[int]] = {}
    if labels_file.exists():
        mrr_labels = load_mrr_labels(labels_file)
        labelled = sum(1 for v in mrr_labels.values() if any(v))
        print(f"  Loaded MRR labels: {len(mrr_labels)} questions "
              f"({labelled} with at least one relevant context marked)")
    else:
        print(f"  INFO: {MRR_LABELS_FILE} not found — MRR will be skipped.")
        print(f"        Run 'python -m src.utils.generate_mrr_template' to create it,")
        print(f"        then fill in the relevance labels and re-run evaluation.")
    
    # Initialize RAG service
    print("Initializing RAG service...")
    try:
        rag_service = RAGService()
        # Override the prompt with the LiveRAG-specific template so the
        # production MBH Bank prompt is not used during this evaluation.
        rag_service.prompt = ChatPromptTemplate.from_template(LIVERAG_RAG_PROMPT_TEMPLATE)
        print("  Prompt overridden with LIVERAG_RAG_PROMPT_TEMPLATE")
    except Exception as e:
        print(f"ERROR:  RAG service: {e}")
        sys.exit(1)
    
    # Initialize judge LLM using configured provider
    print("Initializing judge LLM...")
    judge_provider = get_llm_provider(JUDGE_LLM_PROVIDER, JUDGE_LLM_MODEL, JUDGE_LLM_TEMPERATURE)
    judge_llm = judge_provider.get_llm()
    print(f"  Judge: {JUDGE_LLM_PROVIDER} / {JUDGE_LLM_MODEL}")
    
    # Get chunking configuration
    chunk_config = get_chunk_config()
    
    # Prepare metadata
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata = {
        "timestamp": timestamp,
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "llm_temperature": LLM_TEMPERATURE,
        "judge_llm_provider": JUDGE_LLM_PROVIDER,
        "judge_llm_model": JUDGE_LLM_MODEL,
        "rag_prompt_template": "LIVERAG_RAG_PROMPT_TEMPLATE",
        "embedding_model": EMBEDDING_MODEL,
        "retriever_k": RETRIEVER_K,
    }
    
    print("\nConfiguration:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    print()
    
    # Prepare results
    results = []
    
    # Process each dataset
    for dataset in eval_data.get("datasets", []):
        dataset_name = dataset.get("name", "unknown")
        questions = dataset.get("questions", [])
        
        print(f"\nEvaluating dataset: {dataset_name}")
        print(f"Total questions: {len(questions)}\n")
        
        for i, item in enumerate(questions, 1):
            question     = item.get("input", "")
            expected_output = item.get("expected_output", "")
            question_idx = i - 1  # 0-based index used in the MRR CSV
            
            print(f"[{i}/{len(questions)}] Question: {question[:60]}...")

            # Get RAG answer + retrieved docs in one call (avoids double retrieval)
            retrieved_docs = []
            try:
                llm_answer, retrieved_docs = rag_service.query_with_sources(question)
                print(f"  RAG Answer: {llm_answer[:200]}...")
            except Exception as e:
                print(f"  ERROR getting RAG answer: {e}")
                llm_answer = f"ERROR: {str(e)}"
            
            # Get judge evaluation
            try:
                judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
                    question=question,
                    answer=expected_output,
                    llm_answer=llm_answer
                )
                judge_response = judge_llm.invoke(judge_prompt)
                judge_text = judge_response.content if hasattr(judge_response, 'content') else str(judge_response)
                score, explanation = parse_judge_response(judge_text)
                print(f"  Score: {score}/5")
                print(f"  Explanation: {explanation[:60]}...")
            except Exception as e:
                print(f"  ERROR getting judge evaluation: {e}")
                score = 0
                explanation = f"ERROR: {str(e)}"
            
            # Compute reciprocal rank from the manually-labelled CSV
            if question_idx in mrr_labels:
                labels = mrr_labels[question_idx]
                rr = compute_reciprocal_rank_from_labels(labels)
                first_relevant = next((r + 1 for r, v in enumerate(labels) if v), None)
                print(f"  Reciprocal Rank: {rr:.4f}  "
                      f"(first relevant at rank {first_relevant}, "
                      f"{sum(labels)} labelled relevant out of {len(labels)})")
            else:
                labels = []
                rr = None

            # Tag with number of supporting docs (for split statistics)
            supporting_doc_count = len(question_docids_map.get(question, []))

            # Store result
            results.append({
                "question": question,
                "question_index": question_idx,
                "expected_output": expected_output,
                "llm_answer": llm_answer,
                "score": score,
                "explanation": explanation,
                "reciprocal_rank": rr,
                "mrr_labels": labels,
                "supporting_doc_count": supporting_doc_count,
                "retrieved_doc_ids": [
                    doc.metadata.get("doc_id", "") for doc in retrieved_docs
                ],
            })
            
            # Clear memory every N questions to prevent slowdown; !!! this caused issues
            # if i % MEMORY_CLEAR_INTERVAL == 0:
            #     gc.collect()
            #     if torch.cuda.is_available():
            #         torch.cuda.empty_cache()
            
            print()
    
    # Calculate statistics — overall + split by single vs multi supporting doc
    single_doc = [r for r in results if r.get("supporting_doc_count") == 1]
    multi_doc  = [r for r in results if r.get("supporting_doc_count", 0) > 1]
    unknown    = [r for r in results if r.get("supporting_doc_count", 0) == 0]

    stats_overall = compute_score_stats(results, "Overall")
    stats_single  = compute_score_stats(single_doc, "Single supporting document")
    stats_multi   = compute_score_stats(multi_doc,  "Multiple supporting documents")

    statistics = {
        "overall": stats_overall,
        "single_supporting_doc": stats_single,
        "multi_supporting_doc": stats_multi,
        "unknown_doc_count": len(unknown),
    }
    
    # Prepare final output
    output_data = {
        "metadata": metadata,
        "results": results,
        "statistics": statistics
    }
    
    # Save results to JSON
    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / OUTPUT_DIR_NAME
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{OUTPUT_FILE_PREFIX}{timestamp_file}.json"
    
    print("\n" + "=" * 60)
    print("Saving results...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print statistics
    print(f"\nResults saved to: {output_file}")
    if statistics:
        print(f"\nStatistics:")
        print(f"  Total questions: {statistics['total_questions']}")
        print(f"  Average score: {statistics['average_score']}/5")
        print(f"\nScore Distribution:")
        for score_level, data in statistics['score_distribution'].items():
            print(f"  {score_level}: {data['count']} ({data['percentage']}%)")
        if "mrr" in statistics:
            m = statistics["mrr"]
            print(f"\nRetrieval — Mean Reciprocal Rank (MRR):")
            print(f"  MRR:              {m['mean_reciprocal_rank']:.4f}")
            print(f"  Questions w/ GT:  {m['questions_with_ground_truth']}")
            print(f"  Hit@1:            {m['questions_hit_at_1']} ({round(m['questions_hit_at_1']/m['questions_with_ground_truth']*100,1)}%)")
            print(f"  Hit@3:            {m['questions_hit_at_3']} ({round(m['questions_hit_at_3']/m['questions_with_ground_truth']*100,1)}%)")
            print(f"  Hit@5:            {m['questions_hit_at_5']} ({round(m['questions_hit_at_5']/m['questions_with_ground_truth']*100,1)}%)")
            print(f"  Hit@K (any rank): {m['questions_hit_at_k']} ({round(m['questions_hit_at_k']/m['questions_with_ground_truth']*100,1)}%)")
    
    print("\n" + "=" * 60)
    print("Evaluation completed!")
    finish_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Started at: {start_time}")
    print(f"Finished at: {finish_time}")
    print(f"Duration: {datetime.strptime(finish_time, '%Y-%m-%d %H:%M:%S') - datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    evaluate_rag()
