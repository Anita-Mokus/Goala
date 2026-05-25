from datasets import load_dataset
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from pathlib import Path
import warnings

from src.utils.evaluation.visualize import (_save, _out_dir, _project_root)

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"figure.dpi": 150, "font.size": 11})

OUT_DIR = _out_dir()


def load_data() -> pd.DataFrame:
    """Load the data from the Hugging Face Hub."""
    ds = load_dataset("LiveRAG/Benchmark", split="train")
    return ds.to_pandas()

def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["n_supporting_docs"] = df["Supporting_Documents"].apply(len)
    df["total_context_chars"] = df["Supporting_Documents"].apply(lambda x: sum(len(doc["content"]) for doc in x))
    df["question_type"] = df["n_supporting_docs"].apply(lambda n: "Single-doc" if n == 1 else "Multi-doc")

    return df

def plot_context_length(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    vals = df["total_context_chars"].dropna()
    mean = np.mean(vals)
    
    ax.hist(vals, bins=40, color="#4C8BE0", edgecolor="white", linewidth=0.6)
    ax.axvline(mean, color="#1a1a2e", linestyle="--", linewidth=1.8,
               label=f"Mean = {mean:,.0f}")
    ax.set_title("Context Length Distribution", fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Context Length (characters)", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.legend(fontsize=9)

    _save(fig, "context_length_distribution.png", OUT_DIR)

def plot_question_type(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    counts = df["question_type"].value_counts()
    total = counts.sum()
    colors = ["#4C8BE0", "#E05252"]
    bars = ax.bar(counts.index, counts.values, color=colors, edgecolor="white", linewidth=0.8, width=0.5)

    for bar, val in zip(bars, counts.values):
        pct = val / total * 100
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 5,
                f"{val:,}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_title("Question Type Distribution", fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Question Type", fontsize=11)
    ax.set_ylabel("Number of Questions", fontsize=11)
    ax.set_ylim(0, counts.max() * 1.2)

    summary = df.groupby("question_type")["total_context_chars"].median()
    note = "\n".join([f"{k}: median {v:,.0f} chars" for k, v in summary.items()])
    ax.text(0.97, 0.97, note, transform=ax.transAxes,
            fontsize=8, verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.8))
    _save(fig, "question_type_distribution.png", OUT_DIR)

 
def plot_irt_difficulty_by_question_type(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))

    vals = df[["IRT-diff [-6 : 6]", "question_type"]].dropna()
    bin_edges = np.arange(-6, 6.5, 0.5)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_width = 0.5

    types = ["Single-doc", "Multi-doc"]
    colors = ["#4C8BE0", "#E05252"]
    bar_width = bin_width * 0.45

    for i, (qtype, color) in enumerate(zip(types, colors)):
        subset = vals[vals["question_type"] == qtype]["IRT-diff [-6 : 6]"]
        counts, _ = np.histogram(subset, bins=bin_edges)
        offset = (i - 0.5) * bar_width
        ax.bar(
            bin_centers + offset, counts, bar_width,
            label=qtype, color=color, edgecolor="white", linewidth=0.4, alpha=0.88,
        )

    ax.set_xticks(np.arange(-6, 7, 2))
    ax.set_xlim(-6.5, 6.5)
    ax.set_xlabel("IRT-diff", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.set_title("Distribution of IRT-diff", fontsize=13, fontweight="bold", pad=10)
    ax.legend(fontsize=9)
    _save(fig, "irt_difficulty_by_question_type.png", OUT_DIR)



def run_eda() -> None:
    """Load data, prepare features, and render all three EDA plots."""
 
    print("Loading dataset...")
    df = load_data()
 
    print("Preparing features...")
    df = prepare(df)
 
    print(f"Dataset ready: {len(df)} questions\n")
    print(df[["total_context_chars", "question_type", "IRT-diff [-6 : 6]"]].describe(include="all"))
 
 
    plot_context_length(df)
    plot_question_type(df)
    plot_irt_difficulty_by_question_type(df)
 
if __name__ == "__main__":
    run_eda()