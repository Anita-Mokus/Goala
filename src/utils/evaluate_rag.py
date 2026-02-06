"""
RAG Evaluation Script.
Tests the RAG system using questions from clearservice_eval.json
and evaluates responses using an LLM judge.
"""
import sys
import json
import csv
import gc
import torch
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services import RAGService
from langchain_groq import ChatGroq
from src.core.config import LLM_MODEL


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


def evaluate_rag():
    """Run the RAG evaluation."""
    print("\n" + "=" * 60)
    print("AI Chat Flow - RAG Evaluation")
    print("=" * 60 + "\n")
    
    # Load evaluation dataset
    eval_file = project_root / "clearservice_eval.json"
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
        print(f"ERROR: Failed to initialize RAG service: {e}")
        sys.exit(1)
    
    # Initialize judge LLM
    print("Initializing judge LLM...")
    judge_llm = ChatGroq(model=LLM_MODEL, temperature=0)
    
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
                print(f"  RAG Answer: {llm_answer[:80]}...")
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
                "input": question,
                "expected_output": expected_output,
                "llm_answer": llm_answer,
                "score": score,
                "explanation": explanation
            })
            
            # Clear memory every 5 questions to prevent slowdown
            if i % 5 == 0:
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            print()
    
    # Save results to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / f"eval_results_{timestamp}.csv"
    
    print("\n" + "=" * 60)
    print("Saving results...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["input", "expected_output", "llm_answer", "score", "explanation"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Calculate statistics
    scores = [r["score"] for r in results if isinstance(r["score"], int)]
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"\nResults saved to: {output_file}")
        print(f"\nStatistics:")
        print(f"  Total questions: {len(results)}")
        print(f"  Average score: {avg_score:.2f}/5")
        print(f"  Score 5: {scores.count(5)} ({scores.count(5)/len(scores)*100:.1f}%)")
        print(f"  Score 4: {scores.count(4)} ({scores.count(4)/len(scores)*100:.1f}%)")
        print(f"  Score 3: {scores.count(3)} ({scores.count(3)/len(scores)*100:.1f}%)")
        print(f"  Score 2: {scores.count(2)} ({scores.count(2)/len(scores)*100:.1f}%)")
        print(f"  Score 1: {scores.count(1)} ({scores.count(1)/len(scores)*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("Evaluation completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    evaluate_rag()
