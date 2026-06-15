"""
Visualization script for LiveRAG evaluation results.

Reads from:
  - shared/liverag_retrieval_analysis.csv  (retrieval metrics)
  - evaluation_results/eval_results_liveRAG*.json  (judge scores & aggregates)

Saves PNG figures to visualizations/ at the project root.

Run with:
    python -m src.utils.evaluation.visualize
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns



def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _out_dir() -> Path:
    d = _project_root() / "visualizations"
    d.mkdir(exist_ok=True)
    return d



def _save(fig: plt.Figure, name: str, out_dir: Path) -> None:
    path = out_dir / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path.relative_to(_project_root())}")


def _apply_style() -> None:
    sns.set_theme(style="whitegrid", palette="muted")
    plt.rcParams.update({"figure.dpi": 150, "font.size": 11})



def _compute_retrieval_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'first_hit_rank' and 'rr' columns to the retrieval analysis frame.

    Handles two CSV layouts:
      - single-doc: single 'context_id' column holds the numeric GT ID.
      - multi-doc:  'context_id_1', 'context_id_2', … columns each hold one GT ID.
    """
    k_cols = [c for c in df.columns if c.startswith("retrieved_context_id_")]
    k_cols.sort(key=lambda c: int(c.split("_")[-1]))

    # Detect all context_id_N columns for multi-doc, sorted by suffix number.
    gt_cols = sorted(
        [c for c in df.columns if c.startswith("context_id_")],
        key=lambda c: int(c.split("_")[-1]),
    )
    is_multi = len(gt_cols) > 0

    first_hit_rank = []
    for _, row in df.iterrows():
        if is_multi:
            gt_set = {
                str(row[c]).strip()
                for c in gt_cols
                if str(row[c]).strip() and str(row[c]).strip() != "nan"
            }
        else:
            gt_set = {str(row["context_id"])}

        rank = 0
        for i, col in enumerate(k_cols, start=1):
            if str(row[col]) in gt_set:
                rank = i
                break
        first_hit_rank.append(rank)

    df = df.copy()
    df["first_hit_rank"] = first_hit_rank
    df["rr"] = df["first_hit_rank"].apply(lambda r: 1.0 / r if r > 0 else 0.0)
    return df


def plot_retrieval_rr_distribution(
    df: pd.DataFrame, out_dir: Path, k: int = 5, *, suffix: str, label: str
) -> None:
    """Histogram of per-question reciprocal rank values."""
    rr_buckets = {f"1/{i} ({1/i:.2f})" if i > 1 else "1.0": 1.0 / i for i in range(1, k + 1)}
    rr_buckets["0.0"] = 0.0
    rr_labels = list(rr_buckets.keys())
    values = list(rr_buckets.values())
    counts = [int((df["rr"] == v).sum()) for v in values]

    fig, ax = plt.subplots(figsize=(8, 4))
    palette = sns.color_palette("muted", len(rr_labels))
    bars = ax.bar(rr_labels, counts, color=palette)
    ax.set_xlabel("Reciprocal Rank")
    ax.set_ylabel("Number of questions")
    for bar, cnt in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.01,
            str(cnt),
            ha="center",
            va="bottom",
            fontsize=10,
        )
    mrr = df["rr"].mean()
    ax.set_title(f"Per-question Reciprocal Rank Distribution — {label}  (MRR = {mrr:.4f})")
    fig.tight_layout()
    _save(fig, f"retrieval_rr_distribution_{suffix}.png", out_dir)


_RETRIEVAL_SUBSETS: list[tuple[str, str, str]] = [
    ("liverag_retrieval_analysis_single_doc.csv", "single_doc", "Single-Doc"),
    ("liverag_retrieval_analysis_multi_doc.csv",  "multi_doc",  "Multi-Doc"),
]


def generate_retrieval_charts(out_dir: Path) -> None:
    any_found = False
    for csv_name, suffix, label in _RETRIEVAL_SUBSETS:
        csv_path = _project_root() / "shared" / csv_name
        if not csv_path.exists():
            print(f"  [skip] {csv_name} not found.")
            continue

        any_found = True
        df = pd.read_csv(csv_path)
        df = _compute_retrieval_metrics(df)
        k = len([c for c in df.columns if c.startswith("retrieved_context_id_")])

        print(f"  Loaded {len(df)} rows from {csv_name}  (K={k})")
        plot_retrieval_rr_distribution(df, out_dir, k, suffix=suffix, label=label)

    if not any_found:
        print("  [skip] No retrieval analysis CSVs found in shared/.")



_SUBSETS: list[tuple[str, str]] = [
    ("single_doc", "Single-Doc"),
    ("multi_doc",  "Multi-Doc"),
    ("all_docs",   "All Questions"),
]


def _load_eval_jsons(
    subset: str,
    search_type: str | None = None,
    results_dirs: list[Path] | None = None,
) -> list[dict]:
    """Load eval JSONs filtered by subset/search_type from one or more directories."""
    if results_dirs is None:
        results_dirs = [_project_root() / "evaluation_results"]

    files = []
    for results_dir in results_dirs:
        if not results_dir.exists():
            continue
        for f in sorted(results_dir.glob("*.json")):
            stem = f.stem.lower()
            if "eval_results_liverag" not in stem:
                continue
            if f"_{subset.lower()}_" not in f"_{stem}_":
                continue
            if search_type and f"_{search_type.lower()}_" not in f"_{stem}_":
                continue
            files.append(f)

    loaded = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            loaded.append(json.load(fh))
        print(f"  Loaded {f.name}")
    return loaded


def plot_judge_score_distribution(
    all_data: list[dict], out_dir: Path, *, suffix: str, label: str
) -> None:
    """Bar chart of judge score (1–5) distribution for a single subset."""
    all_results = []
    for run in all_data:
        all_results.extend(run.get("results", []))

    scores = [r["score"] for r in all_results if isinstance(r.get("score"), int)]
    if not scores:
        print(f"  [skip] No valid judge scores found for '{suffix}'.")
        return

    counts = {s: scores.count(s) for s in range(1, 6)}
    total = len(scores)
    palette = ["#3A0CA3"] * 5

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(
        [str(k) for k in counts],
        list(counts.values()),
        color=palette,
    )
    ax.set_xlabel("Judge Score")
    ax.set_ylabel("Number of questions")
    avg = sum(scores) / total
    ax.set_title(f"Judge Score Distribution — {label}  (avg = {avg:.2f}/5,  n = {total})")
    for bar, cnt in zip(bars, counts.values()):
        pct = 100.0 * cnt / total
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + total * 0.001,
            f"{cnt}\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )
    fig.tight_layout()
    _save(fig, f"judge_score_distribution_{suffix}.png", out_dir)


def plot_judge_score_boxplot(out_dir: Path, results_dirs: list[Path] | None = None) -> None:
    """Side-by-side boxplot of judge scores for single-doc, multi-doc, and all questions."""
    subset_records: list[tuple[str, list[int]]] = []
    for subset_key, subset_label in _SUBSETS[:2]:
        data = _load_eval_jsons(subset_key, results_dirs=results_dirs)
        scores = [
            r["score"]
            for run in data
            for r in run.get("results", [])
            if isinstance(r.get("score"), int)
        ]
        if scores:
            subset_records.append((subset_label, scores))

    if not subset_records:
        print("  [skip] No valid judge scores found for boxplot.")
        return

    labels = [rec[0] for rec in subset_records]
    score_lists = [rec[1] for rec in subset_records]
    colors = sns.color_palette("muted", len(labels))

    fig, ax = plt.subplots(figsize=(8, 5))
    boxplot_kwargs = {
        "patch_artist": True,
        "medianprops": {"color": "red", "linewidth": 2.5},
        "whiskerprops": {"linewidth": 1.5},
        "capprops": {"linewidth": 1.5},
        "flierprops": {"marker": "o", "markersize": 4, "alpha": 0.5},
    }
    try:
        bp = ax.boxplot(score_lists, tick_labels=labels, **boxplot_kwargs)
    except TypeError:
        bp = ax.boxplot(score_lists, labels=labels, **boxplot_kwargs)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    for i, scores in enumerate(score_lists, start=1):
        mean_val = sum(scores) / len(scores)
        ax.plot(i, mean_val, marker="D", color="crimson", markersize=7, zorder=5, label="Mean" if i == 1 else "")

    ax.set_ylabel("Judge Score (1–5)")
    ax.set_title("Judge Score Distribution by Question Group")
    ax.set_ylim(0.5, 5.5)
    ax.set_yticks(range(1, 6))
    ax.legend(loc="lower right")
    fig.tight_layout()
    _save(fig, "judge_score_boxplot.png", out_dir)


def plot_metrics_by_group(all_data: list[dict], out_dir: Path) -> None:
    """Grouped bar chart comparing overall / single / multi across key metrics."""
    group_keys = ["overall", "single_supporting_doc", "multi_supporting_doc"]
    group_labels = ["Overall", "Single GT doc", "Multi GT docs"]
    metric_keys = ["mrr.mean_reciprocal_rank", "recall_at_k.mean_recall"]
    metric_labels = ["MRR", "Recall@K"]

    merged: dict[str, dict] = {g: {} for g in group_keys}
    run_count = 0
    for run in all_data:
        stats = run.get("statistics", {})
        run_count += 1
        for g in group_keys:
            group_stats = stats.get(g)
            if not group_stats:
                continue
            for mk in metric_keys:
                keys = mk.split(".")
                val = group_stats
                for k in keys:
                    val = val.get(k) if isinstance(val, dict) else None
                    if val is None:
                        break
                if val is not None:
                    merged[g][mk] = merged[g].get(mk, 0.0) + float(val)

    if run_count > 1:
        for g in merged:
            for mk in merged[g]:
                merged[g][mk] /= run_count

    x = np.arange(len(metric_labels))
    width = 0.25
    colors = sns.color_palette("muted", len(group_keys))

    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (gk, gl, color) in enumerate(zip(group_keys, group_labels, colors)):
        vals = [merged[gk].get(mk) for mk in metric_keys]
        valid = [v if v is not None else 0 for v in vals]
        bars = ax.bar(x + i * width, valid, width, label=gl, color=color)
        for bar, v in zip(bars, vals):
            if v is not None:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01,
                    f"{v:.3f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    ax.set_xticks(x + width)
    ax.set_xticklabels(["MRR", "Recall@K"])
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score (0–1)")
    ax.set_title("Key Metrics by Question Group")
    ax.legend()
    fig.tight_layout()
    _save(fig, "metrics_by_group.png", out_dir)


def judge_score_single_multi_comparison(
    all_data: list[dict], out_dir: Path, results_dirs: list[Path] | None = None, search_type: str | None = None
) -> None:
    """Grouped bar chart: for each judge score value (1-5) show count for single-doc vs multi-doc."""
    def _collect_scores(subset_key: str, search_type: str) -> tuple[dict[int, int], int]:
        data = _load_eval_jsons(
            subset_key,
            search_type=search_type,
            results_dirs=results_dirs,
        )
        scores = [
            r["score"]
            for run in data
            for r in run.get("results", [])
            if isinstance(r.get("score"), int)
        ]
        return {s: scores.count(s) for s in range(1, 6)}, len(scores)

    single_counts, single_n = _collect_scores("single_doc", search_type)
    multi_counts, multi_n = _collect_scores("multi_doc", search_type)

    if single_n == 0 and multi_n == 0:
        print("[skip] No valid judge scores found for single/multi comparison.")
        return

    score_vals = list(range(1, 6))
    x = np.arange(len(score_vals))
    width = 0.35

    colors = sns.color_palette("muted", 2)
    single_bars = [single_counts[s] for s in score_vals]
    multi_bars = [multi_counts[s] for s in score_vals]

    single_avg = sum(s * single_counts[s] for s in score_vals) / single_n if single_n else 0
    multi_avg = sum(s * multi_counts[s] for s in score_vals) / multi_n if multi_n else 0

    fig, ax = plt.subplots(figsize=(10, 6))

    b1 = ax.bar(x - width / 2, single_bars, width, label=f"Single-Doc (avg={single_avg:.2f}, n={single_n})", color=colors[0])
    b2 = ax.bar(x + width / 2, multi_bars, width, label=f"Multi-Doc  (avg={multi_avg:.2f}, n={multi_n})", color=colors[1])

    max_cnt = max(max(single_bars, default=0), max(multi_bars, default=0))
    for bar, cnt in zip(b1, single_bars):
        if cnt:
            pct = 100.0 * cnt / single_n if single_n else 0
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_cnt * 0.01,
                f"{cnt}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=8, fontweight="bold",
            )
    for bar, cnt in zip(b2, multi_bars):
        if cnt:
            pct = 100.0 * cnt / multi_n if multi_n else 0
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_cnt * 0.01,
                f"{cnt}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=8, fontweight="bold",
            )

    ax.set_xticks(x)
    ax.set_xticklabels([str(s) for s in score_vals])
    ax.set_xlabel("Judge Score")
    ax.set_ylabel("Number of questions")
    ax.set_title(f"{search_type.upper()} retrieval")
    ax.legend()
    fig.tight_layout()
    _save(fig, f"{search_type}_judge_score_single_multi_comparison.png", out_dir)

# def judge_score_single_multi_comparison_mmr_vs_similarity(
#     all_data: list[dict], out_dir: Path, results_dirs: list[Path] | None = None
# ) -> None:
#     """Compare similarity scores and MMR scores for single-doc vs multi-doc questions grouped by judge score."""
#     _ = all_data

#     def _collect_scores(subset_key: str, search_type: str) -> tuple[dict[int, int], int]:
#         data = _load_eval_jsons(
#             subset_key,
#             search_type=search_type,
#             results_dirs=results_dirs,
#         )
#         scores = [
#             r["score"]
#             for run in data
#             for r in run.get("results", [])
#             if isinstance(r.get("score"), int)
#         ]
#         return {s: scores.count(s) for s in range(1, 6)}, len(scores)

#     mmr_single, n_mmr_single = _collect_scores("single_doc", "mmr")
#     mmr_multi, n_mmr_multi = _collect_scores("multi_doc", "mmr")
#     sim_single, n_sim_single = _collect_scores("single_doc", "similarity")
#     sim_multi, n_sim_multi = _collect_scores("multi_doc", "similarity")

#     if (n_mmr_single + n_mmr_multi + n_sim_single + n_sim_multi) == 0:
#         print("  [skip] No MMR/similarity eval files found for single/multi comparison.")
#         return

#     score_vals = list(range(1, 6))
#     x = np.arange(len(score_vals))
#     width = 0.2
#     offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
#     colors = sns.color_palette("muted", 4)

#     series = [
#         ("mmr_single_doc", [mmr_single[s] for s in score_vals], n_mmr_single, offsets[0], colors[0]),
#         ("mmr_multi_doc", [mmr_multi[s] for s in score_vals], n_mmr_multi, offsets[1], colors[1]),
#         ("similarity_single_doc", [sim_single[s] for s in score_vals], n_sim_single, offsets[2], colors[2]),
#         ("similarity_multi_doc", [sim_multi[s] for s in score_vals], n_sim_multi, offsets[3], colors[3]),
#     ]

#     fig, ax = plt.subplots(figsize=(12, 6))
#     max_cnt = max((max(vals, default=0) for _, vals, _, _, _ in series), default=0)

#     for label, vals, n, x_off, color in series:
#         bars = ax.bar(x + x_off, vals, width, color=color, label=f"{label} (n={n})")
#         for bar, cnt in zip(bars, vals):
#             if cnt:
#                 ax.text(
#                     bar.get_x() + bar.get_width() / 2,
#                     bar.get_height() + max_cnt * 0.01,
#                     str(cnt),
#                     ha="center",
#                     va="bottom",
#                     fontsize=8,
#                     fontweight="bold",
#                 )

#     ax.set_xticks(x)
#     ax.set_xticklabels([str(s) for s in score_vals])
#     ax.set_xlabel("Judge Score")
#     ax.set_ylabel("Number of questions")
#     ax.set_title("Judge Score Distribution by Retrieval Strategy and Question Group")
#     ax.legend()
#     fig.tight_layout()
#     _save(fig, "judge_score_single_multi_comparison_mmr_vs_similarity.png", out_dir)





def generate_eval_charts(out_dir: Path) -> None:
    results_dir_MMR = _project_root() / "shared" / "MMR"
    results_dir_similarity = _project_root() / "shared" / "STANDARD"

    merged_results_dirs = [
        d for d in [results_dir_MMR, results_dir_similarity] if d.exists()
    ]
    if not merged_results_dirs:
        print("[skip] No evaluation result directories found in shared/MMR and shared/STANDARD.")
        return

    if not any(any(d.glob("*.json")) for d in merged_results_dirs):
        print("[skip] No evaluation result JSONs found in shared/MMR or shared/STANDARD.")
        return

    for subset_key, subset_label in _SUBSETS:
        data = _load_eval_jsons(subset_key, results_dirs=merged_results_dirs)
        if not data:
            print(f"[skip] No files found for subset '{subset_key}'.")
            continue
        print(f"-- {subset_label} ({subset_key}) --")
        plot_judge_score_distribution(data, out_dir, suffix=subset_key, label=subset_label)
    plot_judge_score_boxplot(out_dir, results_dirs=merged_results_dirs)

    all_docs_data = _load_eval_jsons("all_docs", results_dirs=merged_results_dirs)
    if all_docs_data:
        plot_metrics_by_group(all_docs_data, out_dir)
        judge_score_single_multi_comparison(
            all_docs_data,
            out_dir,
            results_dirs=merged_results_dirs,
            search_type="mmr",
        )
        judge_score_single_multi_comparison(
            all_docs_data,
            out_dir,
            results_dirs=merged_results_dirs,
            search_type="standard",
        )
        # judge_score_single_multi_comparison_mmr_vs_similarity(
        #     all_docs_data,
        #     out_dir,
        #     results_dirs=merged_results_dirs,
        # )


def main() -> None:
    _apply_style()
    out_dir = _out_dir()
    print(f"Output directory: {out_dir}")

    print("\n[Retrieval charts — shared/liverag_retrieval_analysis.csv]")
    generate_retrieval_charts(out_dir)

    print("\n[Evaluation charts — evaluation_results/*.json]")
    generate_eval_charts(out_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
