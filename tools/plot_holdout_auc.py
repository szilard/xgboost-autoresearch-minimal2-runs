#!/usr/bin/env python3
"""Plot the holdout AUC of all run groups in run-multi/, coloured by model.

Reads each group's holdout_auc.tsv (written by /xgb-multi), the model from each
run's driver-summary.json and the per-experiment scores from its
groundtruth_all.tsv. Groups with the same model are pooled (all runs are effort
max). Runs with valid = "no" are left out; caveat runs are drawn hollow/dashed.

run-multi/SUMMARY/holdout_auc.png - one row per model, one dot per run
  (modelled on Fig. 1 of arXiv:2609.33812): a filled dot per valid run and a
  hollow dot per caveat run, a grey bar over the full range, the mean with its
  90% interval (t) and the 10th/90th percentiles (nearest run) when the row has
  >= 5 runs.

run-multi/SUMMARY/holdout_auc_path.png - one line per run: the holdout AUC of
  the kept model after each experiment (x: experiment number n as in the runs'
  auc_history.png, the baseline is n = 1; y: holdout AUC of each kept commit,
  held until the next keep).

Usage:
    tools/plot_holdout_auc.py
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy import stats

# categorical slots in fixed order (reference palette, light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
# colour follows the model in every plot: add new models here with the next free slot;
# models not listed get the remaining slots in sorted order (and a warning)
MODEL_SLOT = {"gpt-6-astra": 0, "gpt-6-sol": 1, "gpt-6-luna": 2, "gpt-5.6-luna": 3}
SURFACE, INK, INK2, GRID, RANGE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#d9d8d3"
MIN_N_STATS = 5  # interval and percentiles only from this many runs up
XLIM = None  # fixed holdout AUC range of the strip plot, e.g. (0.74, 0.77); None: the runs' range
RUN_MULTI = Path(__file__).resolve().parent.parent / "run-multi"
OUT_DIR = RUN_MULTI / "SUMMARY"


def load_group(gdir):
    """Runs of one group as dicts: run, dir, model, holdout, valid."""
    runs = []
    with open(gdir / "holdout_auc.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["valid"] not in ("yes", "caveat") or not r["holdout_auc"]:
                continue
            summary = json.loads((gdir / r["run"] / "driver-summary.json").read_text())
            runs.append({"run": r["run"], "dir": gdir / r["run"], "model": summary["model"],
                         "holdout": float(r["holdout_auc"]), "valid": r["valid"]})
    return runs


def keep_path(run_dir):
    """(n, holdout AUC) of each kept commit, n counted over all rows of groundtruth_all.tsv."""
    path = []
    with open(run_dir / "groundtruth_all.tsv") as f:
        for n, r in enumerate(csv.DictReader(f, delimiter="\t"), 1):
            if r["status"] == "keep" and r["holdout_auc"] not in ("", "N/A"):
                path.append((n, float(r["holdout_auc"])))
    return path


def model_colours(models):
    """{model: colour}: the fixed MODEL_SLOT colour, else the next free slot (with a warning)."""
    models = sorted(models)
    colour = {m: SERIES[MODEL_SLOT[m]] for m in models if m in MODEL_SLOT}
    free = [c for i, c in enumerate(SERIES) if i not in MODEL_SLOT.values()]
    for m in (m for m in models if m not in MODEL_SLOT):
        if not free:
            sys.exit(f"too many models; the palette has {len(SERIES)} colours")
        colour[m] = free.pop(0)
        print(f"warning: {m} has no fixed colour; add it to MODEL_SLOT", file=sys.stderr)
    return colour


def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.set_title(title, color=INK, fontsize=11, loc="left", pad=16)


def save(fig, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / name
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    print(out)


def strip_plot(runs, colour):
    # rows top to bottom by mean holdout AUC, best on top
    rows = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    fig, ax = plt.subplots(figsize=(9, 1.6 + 0.55 * len(rows)), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.85 / (1.6 + 0.55 * len(rows)), right=0.97)
    lo, hi = min(r["holdout"] for r in runs), max(r["holdout"] for r in runs)
    if XLIM:
        if lo < XLIM[0] or hi > XLIM[1]:
            print(f"warning: runs span {lo:.4f}-{hi:.4f}, outside XLIM; some are cut off", file=sys.stderr)
        ax.set_xlim(*XLIM)
    else:
        pad = (hi - lo) * 0.05 or 0.001
        ax.set_xlim(lo - pad, hi + pad)

    for i, m in enumerate(rows):
        y = len(rows) - 1 - i
        rr = [r for r in runs if r["model"] == m]
        x = np.array([r["holdout"] for r in rr])
        n = len(x)
        ax.plot([x.min(), x.max()], [y, y], color=RANGE, lw=6, solid_capstyle="round", zorder=1)
        for r in rr:
            filled = r["valid"] == "yes"
            ax.scatter(r["holdout"], y, s=46, zorder=3, linewidths=1.4,
                       facecolors=colour[m] if filled else SURFACE, edgecolors=colour[m])
        mean = x.mean()
        if n >= MIN_N_STATS:
            half = stats.t.ppf(0.95, n - 1) * x.std(ddof=1) / np.sqrt(n)
            ax.errorbar(mean, y + 0.22, xerr=half, fmt="none", ecolor=INK, elinewidth=1.6, capsize=3, zorder=4)
            # "nearest": each percentile is an actual run (with n = 10, the 2nd and 9th)
            p10, p90 = np.percentile(x, [10, 90], method="nearest")
            ax.scatter([p10, p90], [y, y], marker="|", s=260, color=INK, linewidths=1.6, zorder=2)
        ax.scatter(mean, y + 0.22, s=34, color=INK, zorder=5)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(list(reversed(rows)), color=INK)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("holdout AUC", color=INK2)
    ax.grid(axis="x", color=GRID, lw=0.8)
    style(ax, "Holdout AUC per run")
    legend = [
        Line2D([], [], marker="o", ls="", color=INK2, markersize=7, label="run"),
        Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=INK2, markersize=7,
               label="run with caveat"),
        Line2D([], [], marker="o", color=INK, markersize=5, lw=1.6, label=f"mean, 90% interval (n >= {MIN_N_STATS})"),
        Line2D([], [], marker="|", ls="", color=INK2, markersize=9, markeredgewidth=1.6, label="10th and 90th percentile"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc.png")


def path_plot(runs, colour):
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.2, right=0.97)
    for r in runs:
        path = keep_path(r["dir"])
        if not path:
            continue
        n, auc = zip(*path)
        # hold each kept model's holdout AUC until the next keep, and to the run's last experiment
        with open(r["dir"] / "groundtruth_all.tsv") as f:
            n_last = sum(1 for _ in f) - 1
        ax.step(list(n) + [n_last], list(auc) + [auc[-1]], where="post", color=colour[r["model"]],
                lw=0.8, alpha=0.85, ls="-" if r["valid"] == "yes" else (0, (4, 2)), zorder=2)
        ax.scatter(n_last, auc[-1], s=14, zorder=3, color=colour[r["model"]])
    ax.set_xlabel("experiment n (baseline = 1)", color=INK2)
    ax.set_ylabel("holdout AUC", color=INK2)
    ax.grid(color=GRID, lw=0.8)
    ax.set_xlim(left=0)
    style(ax, "Holdout AUC path per run")
    models = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    legend = [Line2D([], [], color=colour[m], lw=2, label=m) for m in models] + [
        Line2D([], [], color=INK2, lw=0.8, label="run"),
        Line2D([], [], color=INK2, lw=0.8, ls=(0, (4, 2)), label="run with caveat"),
        Line2D([], [], marker="o", ls="", color=INK2, markersize=5, label="end of run"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc_path.png")


def main():
    groups = sorted(d for d in RUN_MULTI.iterdir() if (d / "holdout_auc.tsv").is_file())
    runs = [r for g in groups for r in load_group(g)]
    if not runs:
        sys.exit(f"no valid runs in {RUN_MULTI}")

    colour = model_colours({r["model"] for r in runs})
    strip_plot(runs, colour)
    path_plot(runs, colour)


if __name__ == "__main__":
    main()
