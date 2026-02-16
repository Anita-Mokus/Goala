"""
RAG Evaluation Script.
Tests the RAG system using questions from mbh_junior_hu_evalset.json
and evaluates responses using an LLM judge.
Outputs results in JSON format with configuration metadata.
"""
import sys
import json
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
from src.core.config import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_PROVIDER,
    RETRIEVER_K
)


# ============================================================================
# CONFIGURATION - Modify these variables to change evaluation behavior
# ============================================================================
EVAL_FILE_NAME = "mbh_junior_hu_evalset.json"  # Evaluation dataset file
OUTPUT_DIR_NAME = "evaluation_results"         # Directory for results
OUTPUT_FILE_PREFIX = "eval_results_"           # Prefix for output JSON files
JUDGE_LLM_TEMPERATURE = 0                      # Temperature for judge LLM (0 = deterministic)
MEMORY_CLEAR_INTERVAL = 5                      # Clear memory every N questions
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
    """Get chunk size and overlap from IngestService."""
    try:
        from src.services.ingest_service import IngestService
        ingest_service = IngestService()
        return {
            "chunk_size": ingest_service.text_splitter._chunk_size,
            "chunk_overlap": ingest_service.text_splitter._chunk_overlap
        }
    except Exception:
        return {
            "chunk_size": 'default',  # default values
            "chunk_overlap": 'default'
        }


def evaluate_rag():
    """Run the RAG evaluation."""
    print("\n" + "=" * 60)
    print("AI Chat Flow - RAG Evaluation")
    print("=" * 60 + "\n")
    
    # Load evaluation dataset
    eval_file = project_root / 'shared' / EVAL_FILE_NAME
    if not eval_file.exists():
        print(f"ERROR: Evaluation file not found: {eval_file}")
        sys.exit(1)
    
    with open(eval_file, 'r', encoding='utf-8') as f:
        eval_data = json.load(f)
    
    # Initialize RAG service
    print("Initializing RAG service...")
    try:
        rag_service = RAGService()
    except Exception as e:
        print(f"ERROR:  RAG service: {e}")
        sys.exit(1)
    
    # Initialize judge LLM using configured provider
    print("Initializing judge LLM...")
    judge_provider = get_llm_provider(LLM_PROVIDER, LLM_MODEL, JUDGE_LLM_TEMPERATURE)
    judge_llm = judge_provider.get_llm()
    
    # Get chunking configuration
    chunk_config = get_chunk_config()
    
    # Prepare metadata
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata = {
        "timestamp": timestamp,
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": chunk_config["chunk_size"],
        "chunk_overlap": chunk_config["chunk_overlap"],
        "retriever_k": RETRIEVER_K,
        "llm_model": LLM_MODEL,
        "llm_temperature": LLM_TEMPERATURE
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
            question = item.get("input", "")
            expected_output = item.get("expected_output", "")
            
            print(f"[{i}/{len(questions)}] Question: {question[:60]}...")
            
            # Get RAG answer
            try:
                llm_answer = rag_service.query(question)
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
            
            # Store result
            results.append({
                "question": question,
                "expected_output": expected_output,
                "llm_answer": llm_answer,
                "score": score,
                "explanation": explanation
            })
            
            # Clear memory every N questions to prevent slowdown; !!! this caused issues
            # if i % MEMORY_CLEAR_INTERVAL == 0:
            #     gc.collect()
            #     if torch.cuda.is_available():
            #         torch.cuda.empty_cache()
            
            print()
    
    # Calculate statistics
    scores = [r["score"] for r in results if isinstance(r["score"], int)]
    statistics = {}
    if scores:
        statistics = {
            "total_questions": len(results),
            "average_score": round(sum(scores) / len(scores), 2),
            "score_distribution": {
                "score_5": {"count": scores.count(5), "percentage": round(scores.count(5)/len(scores)*100, 1)},
                "score_4": {"count": scores.count(4), "percentage": round(scores.count(4)/len(scores)*100, 1)},
                "score_3": {"count": scores.count(3), "percentage": round(scores.count(3)/len(scores)*100, 1)},
                "score_2": {"count": scores.count(2), "percentage": round(scores.count(2)/len(scores)*100, 1)},
                "score_1": {"count": scores.count(1), "percentage": round(scores.count(1)/len(scores)*100, 1)}
            }
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
    
    print("\n" + "=" * 60)
    print("Evaluation completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    evaluate_rag()
