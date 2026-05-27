"""
Metrics computation functions for RAG evaluation.

Includes MRR, Recall@K, and score statistics.
"""


def compute_reciprocal_rank_from_docids(
    retrieved_docs: list, ground_truth_doc_ids: list
) -> float:
    """
    Compute the reciprocal rank by matching retrieved doc_ids against ground truth.

    Args:
        retrieved_docs:       Ordered list of LangChain Document objects from the retriever.
        ground_truth_doc_ids: List of relevant doc_id strings for the question.

    Returns:
        ``1 / rank`` of the first retrieved doc whose doc_id is in
        ``ground_truth_doc_ids``, or ``0.0`` if none match.
    """
    gt_set = set(ground_truth_doc_ids)
    for rank, doc in enumerate(retrieved_docs, start=1):
        if doc.metadata.get("doc_id", "") in gt_set:
            return 1.0 / rank
    return 0.0


def compute_recall_at_k(retrieved_docs: list, ground_truth_doc_ids: list) -> float:
    """
    Compute Recall@K: fraction of ground-truth doc_ids found anywhere in the
    retrieved list.

    Args:
        retrieved_docs:       Ordered list of LangChain Document objects from the retriever.
        ground_truth_doc_ids: List of relevant doc_id strings for the question.

    Returns:
        Number of hits / total ground-truth docs, in [0.0, 1.0].
        Returns 0.0 when ``ground_truth_doc_ids`` is empty.
    """
    if not ground_truth_doc_ids:
        return 0.0
    retrieved_ids = {doc.metadata.get("doc_id", "") for doc in retrieved_docs}
    hits = sum(1 for doc_id in ground_truth_doc_ids if doc_id in retrieved_ids)
    return hits / len(ground_truth_doc_ids)


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
    recall_values = [r["recall_at_k"] for r in results if r.get("recall_at_k") is not None]

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

    if recall_values:
        stats["recall_at_k"] = {
            "mean_recall": round(sum(recall_values) / len(recall_values), 4),
            "questions_with_ground_truth": len(recall_values),
            "perfect_recall_count": sum(1 for r in recall_values if r == 1.0),
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
    if "recall_at_k" in stats:
        rc = stats["recall_at_k"]
        n = rc["questions_with_ground_truth"]
        print(f"  Retrieval — Recall@K:")
        print(f"    Mean Recall@K:    {rc['mean_recall']:.4f}")
        print(f"    Questions w/ GT:  {n}")
        print(f"    Perfect recall:   {rc['perfect_recall_count']} ({round(rc['perfect_recall_count']/n*100,1)}%)")
