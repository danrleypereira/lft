# Brief: generates the report's complexity-in-practice figures from
# pca_routing/results/scaling.csv (produced by experiment.scaling_experiment).
# Run with the project's venv (matplotlib/numpy are the "analysis" uv group,
# not a base dependency of pca_routing itself): .venv/bin/python -m
# pca_routing.assignment.figures.make_plots

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
SCALING_CSV = ROOT / "results" / "scaling.csv"
OUT_DIR = Path(__file__).resolve().parent

COLORS = {"dijkstra": "#1f628f", "bellman_ford": "#a8781f", "bfs": "#2f6f62"}


def load():
    rows = defaultdict(list)
    with SCALING_CSV.open() as f:
        for row in csv.DictReader(f):
            rows[row["algorithm"]].append(row)
    for algo in rows:
        rows[algo].sort(key=lambda r: int(r["n"]))
    return rows


def plot_metric(rows, field, ylabel, title, fname, log=False):
    fig, ax = plt.subplots(figsize=(6, 4))
    for algo, data in rows.items():
        xs = [int(r["n"]) for r in data]
        ys = [float(r[field]) for r in data]
        ax.plot(xs, ys, marker="o", label=algo, color=COLORS.get(algo, "#666"))
    ax.set_xlabel("|V| (nodes)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log:
        ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_DIR / fname, dpi=150)
    plt.close(fig)
    print(f"wrote {OUT_DIR / fname}")


def main():
    if not SCALING_CSV.exists():
        raise SystemExit(f"{SCALING_CSV} not found - run `python3 -m pca_routing.experiment` first")
    rows = load()
    plot_metric(rows, "elapsed_ns", "elapsed time (ns)", "Execution time vs. graph size", "time_vs_n.png", log=True)
    plot_metric(rows, "comparisons", "comparisons", "Algorithmic work (comparisons) vs. graph size", "comparisons_vs_n.png", log=True)
    plot_metric(rows, "relaxations", "relaxations", "Edge relaxations vs. graph size", "relaxations_vs_n.png", log=True)


if __name__ == "__main__":
    main()
