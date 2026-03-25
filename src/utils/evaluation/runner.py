"""
RAG Evaluation Runner.

Main evaluation loop that processes questions and computes metrics.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate

from src.services import RAGService
from src.services.llm_providers import get_llm_provider
from src.core.config import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_PROVIDER,
    RETRIEVER_K,
    JUDGE_LLM_MODEL,
    JUDGE_LLM_PROVIDER,
    LIVERAG_RAG_PROMPT_TEMPLATE,
)

from src.utils.evaluation.config import (
    EVAL_FILE_NAME,
    MRR_LABELS_FILE,
    QUESTION_DOCIDS_FILE,
    OUTPUT_DIR_NAME,
    OUTPUT_FILE_PREFIX,
    JUDGE_LLM_TEMPERATURE,
)
from src.utils.evaluation.metrics import (
    compute_reciprocal_rank_from_labels,
    compute_reciprocal_rank_from_docids,
    compute_recall_at_k,
    compute_score_stats,
    print_stats,
)
from src.utils.evaluation.judge import JUDGE_PROMPT_TEMPLATE, parse_judge_response
from src.utils.retrieval_analysis import (
    build_retrieved_context_ids,
    build_doc_id_numbering,
    to_numeric_doc_id,
)
from src.utils.evaluation.io import (
    load_mrr_labels,
    load_eval_data,
    load_question_docids_map,
    save_results,
)


# Project root for file paths
project_root = Path(__file__).parent.parent.parent.parent

def _get_rag_answer_and_score(
    question: str,
    expected_output: str,
    rag_service: RAGService,
    judge_llm,
) -> tuple[list, str, int, str]:
    """Call the RAG pipeline and judge LLM for one question.

    Returns:
        (retrieved_docs, llm_answer, score, explanation)
    """
    retrieved_docs: list = []
    try:
        llm_answer, retrieved_docs = rag_service.query_with_sources(question)
        print(f"  RAG Answer: {llm_answer[:200]}...")
    except Exception as e:
        print(f"  ERROR getting RAG answer: {e}")
        llm_answer = f"ERROR: {str(e)}"

    try:
        judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
            question=question,
            answer=expected_output,
            llm_answer=llm_answer,
        )
        judge_response = judge_llm.invoke(judge_prompt)
        judge_text = (
            judge_response.content
            if hasattr(judge_response, "content")
            else str(judge_response)
        )
        score, explanation = parse_judge_response(judge_text)
        print(f"  Score: {score}/5")
        print(f"  Explanation: {explanation[:60]}...")
    except Exception as e:
        print(f"  ERROR getting judge evaluation: {e}")
        score = 0
        explanation = f"ERROR: {str(e)}"

    return retrieved_docs, llm_answer, score, explanation


def _compute_retrieval_metrics(
    retrieved_docs: list,
    doc_ids: list[str],
    csv_labels: list[int],
) -> tuple[float | None, float | None, list[int]]:
    """Compute reciprocal rank and Recall@K for one question.

    Uses ground-truth doc_ids when available; falls back to manual CSV labels.

    Returns:
        (rr, recall, labels)  — rr and recall are None when neither source is available.
    """
    if doc_ids:
        rr = compute_reciprocal_rank_from_docids(retrieved_docs, doc_ids)
        recall = compute_recall_at_k(retrieved_docs, doc_ids)
        labels = csv_labels
        first_relevant = next(
            (
                rank
                for rank, doc in enumerate(retrieved_docs, start=1)
                if doc.metadata.get("doc_id", "") in set(doc_ids)
            ),
            None,
        )
        retrieved_doc_ids = [doc.metadata.get("doc_id", "") for doc in retrieved_docs]
        print(f"  Reciprocal Rank: {rr:.4f}  (first relevant at rank {first_relevant})")
        print(f"  GT doc_ids:      {doc_ids}")
        print(f"  Retrieved IDs:   {retrieved_doc_ids}")
        print(f"  Recall@K:        {recall:.4f}")
    elif csv_labels and any(csv_labels):
        labels = csv_labels
        rr = compute_reciprocal_rank_from_labels(labels)
        recall = None
        first_relevant = next((r + 1 for r, v in enumerate(labels) if v), None)
        print(
            f"  Reciprocal Rank: {rr:.4f}  "
            f"(CSV labels — first relevant at rank {first_relevant})"
        )
    else:
        labels = csv_labels
        rr = None
        recall = None

    return rr, recall, labels


def _evaluate_question(
    question_idx: int,
    item: dict,
    rag_service: RAGService,
    judge_llm,
    question_docids_map: dict,
    mrr_labels: dict,
    doc_id_numbering: dict,
    total: int,
    position: int,
) -> dict | None:
    """Evaluate a single question end-to-end.

    Returns a result dict ready to be appended to the results list,
    or None if the question has no ground-truth doc_ids and should be skipped.
    """
    question = item.get("input", "")
    expected_output = item.get("expected_output", "")
    doc_ids = question_docids_map.get(question, [])
    csv_labels = mrr_labels.get(question_idx, [])

    if not doc_ids:
        print(f"  WARNING: No supporting doc_ids found for question: {question[:60]}...")
        return None

    print(f"[{position}/{total}] Question: {question[:60]}...")

    retrieved_docs, llm_answer, score, explanation = _get_rag_answer_and_score(
        question, expected_output, rag_service, judge_llm
    )

    rr, recall, labels = _compute_retrieval_metrics(retrieved_docs, doc_ids, csv_labels)

    retrieved_context_fields = build_retrieved_context_ids(
        retrieved_docs, RETRIEVER_K, doc_id_numbering
    )

    print()
    return {
        "question": question,
        "question_index": question_idx,
        "question_id": question_idx,
        "context_id": to_numeric_doc_id(doc_ids[0], doc_id_numbering) if doc_ids else "",
        "context_ids": [to_numeric_doc_id(d, doc_id_numbering) for d in doc_ids],
        "expected_output": expected_output,
        "llm_answer": llm_answer,
        "score": score,
        "explanation": explanation,
        "reciprocal_rank": rr,
        "recall_at_k": recall,
        "mrr_labels": labels,
        "supporting_doc_count": len(doc_ids),
        "retrieved_doc_ids": [doc.metadata.get("doc_id", "") for doc in retrieved_docs],
        **retrieved_context_fields,
    }





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
    
    eval_data = load_eval_data(eval_file)

    # Load question → doc_ids map to know how many supporting docs each question has
    docids_path = project_root / 'shared' / QUESTION_DOCIDS_FILE
    question_docids_map = load_question_docids_map(docids_path)
    
    if question_docids_map:
        print(f"  Loaded question→doc_ids map: {len(question_docids_map)} entries")
    else:
        print(f"  INFO: {QUESTION_DOCIDS_FILE} not found — single/multi-doc split will be skipped.")    
    doc_id_numbering = build_doc_id_numbering(question_docids_map)
    
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

        # Partition questions into single-doc and multi-doc, preserving original 0-based index
        # so MRR CSV label look-up stays aligned with generate_mrr_template output.
        single_doc_items: list[tuple[int, dict]] = []
        multi_doc_items: list[tuple[int, dict]] = []
        for orig_idx, item in enumerate(questions):
            n = len(question_docids_map.get(item.get("input", ""), []))
            if n == 1:
                single_doc_items.append((orig_idx, item))
            elif n > 1:
                multi_doc_items.append((orig_idx, item))

        print(f"Questions with single supporting document:   {len(single_doc_items)}")
        print(f"Questions with multiple supporting documents: {len(multi_doc_items)}\n")

        # Phase 1: single-doc questions
        print(f"[Phase 1] Single-document questions ({len(single_doc_items)})\n")
        for position, (question_idx, item) in enumerate(single_doc_items, 1):
            result = _evaluate_question(
                question_idx, item, rag_service, judge_llm,
                question_docids_map, mrr_labels, doc_id_numbering,
                total=len(single_doc_items), position=position,
            )
            if result is not None:
                results.append(result)

        # Phase 2: multi-doc questions
        print(f"[Phase 2] Multi-document questions ({len(multi_doc_items)})\n")
        for position, (question_idx, item) in enumerate(multi_doc_items, 1):
            result = _evaluate_question(
                question_idx, item, rag_service, judge_llm,
                question_docids_map, mrr_labels, doc_id_numbering,
                total=len(multi_doc_items), position=position,
            )
            if result is not None:
                results.append(result)
    
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
    
    save_results(output_data, output_file)
    
    # Print statistics
    print(f"\nResults saved to: {output_file}")
    for stats_key in ("overall", "single_supporting_doc", "multi_supporting_doc"):
        s = statistics.get(stats_key)
        if s:
            print_stats(s)
    
    print("\n" + "=" * 60)
    print("Evaluation completed!")
    finish_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Started at: {start_time}")
    print(f"Finished at: {finish_time}")
    print(f"Duration: {datetime.strptime(finish_time, '%Y-%m-%d %H:%M:%S') - datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    evaluate_rag()
