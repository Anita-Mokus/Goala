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
import matplotlib.ticker as mticker
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
      - single-doc: 'context_id' column holds one numeric GT ID.
      - multi-doc:  'context_ids' column holds pipe-separated numeric GT IDs.
    """
    k_cols = [c for c in df.columns if c.startswith("retrieved_context_id_")]
    k_cols.sort(key=lambda c: int(c.split("_")[-1]))

    is_multi = "context_ids" in df.columns

    first_hit_rank = []
    for _, row in df.iterrows():
        if is_multi:
            gt_set = {
                str(cid).strip()
                for cid in str(row["context_ids"]).split("|")
                if str(cid).strip()
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


def plot_retrieval_hit_at_k(
    df: pd.DataFrame, out_dir: Path, k: int = 5, *, suffix: str, label: str
) -> None:
    """Cumulative Hit@K bar chart (K = 1 … k)."""
    ks = list(range(1, k + 1))
    n = len(df)
    hit_pct = [
        100.0 * ((df["first_hit_rank"] > 0) & (df["first_hit_rank"] <= ki)).sum() / n
        for ki in ks
    ]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar([f"Hit@{ki}" for ki in ks], hit_pct, color=sns.color_palette("muted", k))
    ax.set_ylim(0, 105)
    ax.set_ylabel("Questions (%)")
    ax.set_title(f"Cumulative Hit@K — Retrieval — {label}")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    for bar, pct in zip(bars, hit_pct):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{pct:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    fig.tight_layout()
    _save(fig, f"retrieval_hit_at_k_{suffix}.png", out_dir)


def plot_retrieval_rank_distribution(
    df: pd.DataFrame, out_dir: Path, k: int = 5, *, suffix: str, label: str
) -> None:
    """Bar chart of the rank at which the GT doc was first found."""
    rank_labels = [str(i) for i in range(1, k + 1)] + ["Not found"]
    counts = [
        int((df["first_hit_rank"] == i).sum()) for i in range(1, k + 1)
    ] + [int((df["first_hit_rank"] == 0).sum())]

    palette = sns.color_palette("muted", k) + [(0.6, 0.6, 0.6)]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(rank_labels, counts, color=palette)
    ax.set_xlabel("Rank of first GT match")
    ax.set_ylabel("Number of questions")
    ax.set_title(f"Distribution of First GT Hit Rank — {label}")
    for bar, cnt in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.01,
            str(cnt),
            ha="center",
            va="bottom",
            fontsize=10,
        )
    fig.tight_layout()
    _save(fig, f"retrieval_rank_distribution_{suffix}.png", out_dir)


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
        plot_retrieval_hit_at_k(df, out_dir, k, suffix=suffix, label=label)
        plot_retrieval_rank_distribution(df, out_dir, k, suffix=suffix, label=label)
        plot_retrieval_rr_distribution(df, out_dir, k, suffix=suffix, label=label)

    if not any_found:
        print("  [skip] No retrieval analysis CSVs found in shared/.")



_SUBSETS: list[tuple[str, str]] = [
    ("single_doc", "Single-Doc"),
    ("multi_doc",  "Multi-Doc"),
    ("all_docs",   "All Questions"),
]


def _load_eval_jsons(subset: str) -> list[dict]:
    """Load all eval JSONs whose filename matches the given subset key."""
    results_dir = _project_root() / "evaluation_results"
    files = sorted(results_dir.glob(f"eval_results_liveRAG_{subset}_*.json"))
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


def plot_metrics_by_group(all_data: list[dict], out_dir: Path) -> None:
    """Grouped bar chart comparing overall / single / multi across key metrics."""
    group_keys = ["overall", "single_supporting_doc", "multi_supporting_doc"]
    group_labels = ["Overall", "Single GT doc", "Multi GT docs"]
    metric_keys = ["average_score", "mrr.mean_reciprocal_rank", "recall_at_k.mean_recall"]
    metric_labels = ["Avg Score / 5", "MRR", "Recall@K"]

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

    for g in merged:
        if "average_score" in merged[g]:
            merged[g]["average_score"] /= 5.0

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
    ax.set_xticklabels(["Avg Score\n(normalised)", "MRR", "Recall@K"])
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score (0–1)")
    ax.set_title("Key Metrics by Question Group")
    ax.legend()
    fig.tight_layout()
    _save(fig, "metrics_by_group.png", out_dir)


def plot_score_vs_rr(
    all_data: list[dict], out_dir: Path, *, suffix: str, label: str
) -> None:
    """Scatter plot of judge score vs reciprocal rank for a single subset."""
    rows = []
    for run in all_data:
        for r in run.get("results", []):
            score = r.get("score")
            rr = r.get("reciprocal_rank")
            if isinstance(score, int) and rr is not None:
                rows.append({"score": score, "rr": float(rr)})
    if not rows:
        print(f"  [skip] No score/rr pairs found for '{suffix}'.")
        return

    df = pd.DataFrame(rows)
    rng = np.random.default_rng(42)
    df["score_jittered"] = df["score"] + rng.uniform(-0.25, 0.25, len(df))

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(
        df["rr"],
        df["score_jittered"],
        alpha=0.35,
        s=18,
        color=sns.color_palette("muted")[0],
        edgecolors="none",
    )

    rr_vals = sorted(df["rr"].unique())
    mean_scores = [df.loc[df["rr"] == rv, "score"].mean() for rv in rr_vals]
    ax.plot(rr_vals, mean_scores, "o-", color="crimson", lw=2, ms=7, label="Mean score per RR")

    ax.set_xlabel("Reciprocal Rank")
    ax.set_ylabel("Judge Score (jittered)")
    ax.set_yticks(range(1, 6))
    ax.set_title(f"Judge Score vs Retrieval Reciprocal Rank — {label}")
    ax.legend()
    fig.tight_layout()
    _save(fig, f"score_vs_rr_scatter_{suffix}.png", out_dir)


def plot_multi_run_mrr(all_data: list[dict], out_dir: Path) -> None:
    """Line chart of MRR over multiple evaluation runs."""
    if len(all_data) < 2:
        return

    timestamps, mrr_vals = [], []
    for run in all_data:
        meta = run.get("metadata", {})
        ts = meta.get("timestamp", "?")
        stats = run.get("statistics", {})
        mrr = (stats.get("overall") or {}).get("mrr", {}).get("mean_reciprocal_rank")
        if mrr is not None:
            timestamps.append(ts)
            mrr_vals.append(float(mrr))

    if len(mrr_vals) < 2:
        return

    fig, ax = plt.subplots(figsize=(max(6, len(timestamps)), 4))
    ax.plot(timestamps, mrr_vals, "o-", lw=2, color=sns.color_palette("muted")[2])
    for x, y in zip(timestamps, mrr_vals):
        ax.text(x, y + 0.005, f"{y:.4f}", ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("Run timestamp")
    ax.set_ylabel("MRR")
    ax.set_title("MRR Across Evaluation Runs")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    _save(fig, "multi_run_mrr.png", out_dir)


def generate_eval_charts(out_dir: Path) -> None:
    results_dir = _project_root() / "evaluation_results"
    if not results_dir.exists() or not any(results_dir.glob("eval_results_liveRAG_*.json")):
        print("  [skip] No evaluation result JSONs found in evaluation_results/.")
        return

    for subset_key, subset_label in _SUBSETS:
        data = _load_eval_jsons(subset_key)
        if not data:
            print(f"  [skip] No files found for subset '{subset_key}'.")
            continue
        print(f"  -- {subset_label} ({subset_key}) --")
        plot_judge_score_distribution(data, out_dir, suffix=subset_key, label=subset_label)
        plot_score_vs_rr(data, out_dir, suffix=subset_key, label=subset_label)

    all_docs_data = _load_eval_jsons("all_docs")
    if all_docs_data:
        plot_metrics_by_group(all_docs_data, out_dir)
        plot_multi_run_mrr(all_docs_data, out_dir)



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
