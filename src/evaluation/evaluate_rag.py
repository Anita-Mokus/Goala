"""
RAG Evaluation Script.
Tests the RAG system using evaluation datasets and evaluates responses using an LLM judge.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.chat import RAGService
from src.llm import get_llm_provider
from src.config import EMBEDDING_MODEL, OLLAMA_BASE_URL, CHUNK_MULTIPAGE_SECTIONS
from src.config.settings import (
    get_current_llm_model,
    get_current_llm_temperature,
    get_current_llm_provider,
    get_current_retriever_k,
    get_current_chunk_max_characters,
    get_current_chunk_new_after_n_chars,
    get_current_chunk_overlap,
    get_current_pdf_strategy,
    get_current_pdf_language,
)
from src.evaluation.config import (
    EVAL_FILE_NAME,
    OUTPUT_DIR_NAME,
    OUTPUT_FILE_PREFIX,
    JUDGE_LLM_TEMPERATURE,
)
from src.evaluation.judge_prompt import JUDGE_PROMPT_TEMPLATE, parse_judge_response


def get_chunk_config():
    """Get chunking and RAG configuration from DB or env."""
    return {
        "chunking_strategy": "chunk_by_title",
        "chunk_max_characters": get_current_chunk_max_characters(),
        "chunk_new_after_n_chars": get_current_chunk_new_after_n_chars(),
        "chunk_overlap": get_current_chunk_overlap(),
        "chunk_multipage_sections": CHUNK_MULTIPAGE_SECTIONS,
        "pdf_strategy": get_current_pdf_strategy(),
        "pdf_language": get_current_pdf_language(),
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
        print(f"ERROR: RAG service: {e}")
        sys.exit(1)
    
    # Initialize judge LLM using configured provider
    print("Initializing judge LLM...")
    llm_provider = get_current_llm_provider()
    llm_model = get_current_llm_model()
    judge_provider = get_llm_provider(llm_provider, llm_model, JUDGE_LLM_TEMPERATURE, base_url=OLLAMA_BASE_URL)
    judge_llm = judge_provider.get_llm()
    
    # Get chunking configuration
    chunk_config = get_chunk_config()
    
    # Prepare metadata
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata = {
        "timestamp": timestamp,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_temperature": get_current_llm_temperature(),
        "embedding_model": EMBEDDING_MODEL,
        "retriever_k": get_current_retriever_k(),
        "chunking": {
            "strategy": chunk_config["chunking_strategy"],
            "max_characters": chunk_config["chunk_max_characters"],
            "new_after_n_chars": chunk_config["chunk_new_after_n_chars"],
            "overlap": chunk_config["chunk_overlap"],
            "multipage_sections": chunk_config["chunk_multipage_sections"],
        },
        "pdf_processing": {
            "strategy": chunk_config["pdf_strategy"],
            "language": chunk_config["pdf_language"],
        },
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
    print("=" * 60)


if __name__ == "__main__":
    evaluate_rag()
