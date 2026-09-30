#!/usr/bin/env python3
"""Plot the holdout AUC of run groups: one row per model, one dot per run.

Modelled on Fig. 1 of arXiv:2609.33812 (identical runs, different results).
Reads each group's holdout_auc.tsv (written by /xgb-multi) and the model from
each run's driver-summary.json. Groups with the same model are pooled into one
row (all runs are effort max).

Per row: a filled dot per valid run and a hollow dot per caveat run (runs with
valid = "no" are left out), a grey bar over the full range, the mean with its
95% interval (t) and the 10th/90th percentiles (nearest run) when the row has
>= 5 runs.

Usage:
    tools/plot_holdout_auc.py                                          # all groups in run-multi/
    tools/plot_holdout_auc.py run-multi/sol6_n10 run-multi/luna-test [-o out.png]
    tools/plot_holdout_auc.py --xlim 0.72 0.77                         # fixed x range, to compare plots

The x axis spans the runs' holdout AUCs unless --xlim is given.

Default output: run-multi/SUMMARY/holdout_auc.png for all groups,
run-multi/SUMMARY/holdout_auc__<group>__<group>.png for the groups given
"""
import argparse
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
MODEL_SLOT = {"gpt-5.6-luna": 0, "gpt-6-sol": 1}
SURFACE, INK, INK2, GRID, RANGE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#d9d8d3"
MIN_N_STATS = 5  # interval and percentiles only from this many runs up
RUN_MULTI = Path(__file__).resolve().parent.parent / "run-multi"


def load_group(gdir):
    """Runs of one group as dicts: run, model, holdout, valid."""
    runs = []
    with open(gdir / "holdout_auc.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["valid"] not in ("yes", "caveat") or not r["holdout_auc"]:
                continue
            summary = json.loads((gdir / r["run"] / "driver-summary.json").read_text())
            runs.append({"run": r["run"], "model": summary["model"],
                         "holdout": float(r["holdout_auc"]), "valid": r["valid"]})
    return runs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("groups", nargs="*", type=Path,
                    help="run group directories (run-multi/<group>); default: all groups in run-multi/")
    ap.add_argument("-o", "--output", type=Path, help="output file (.png or .svg)")
    ap.add_argument("--xlim", nargs=2, type=float, metavar=("MIN", "MAX"),
                    help="fixed holdout AUC range of the x axis (default: the runs' range)")
    args = ap.parse_args()
    all_groups = not args.groups
    if all_groups:
        args.groups = sorted(d for d in RUN_MULTI.iterdir() if (d / "holdout_auc.tsv").is_file())
        if not args.groups:
            sys.exit(f"no groups with holdout_auc.tsv in {RUN_MULTI}")

    runs = []
    for g in args.groups:
        if not (g / "holdout_auc.tsv").is_file():
            sys.exit(f"{g}: no holdout_auc.tsv")
        runs += load_group(g)
    if not runs:
        sys.exit("no valid runs")

    models = sorted({r["model"] for r in runs})
    colour = {m: SERIES[MODEL_SLOT[m]] for m in models if m in MODEL_SLOT}
    free = [c for i, c in enumerate(SERIES) if i not in MODEL_SLOT.values()]
    for m in (m for m in models if m not in MODEL_SLOT):
        if not free:
            sys.exit(f"too many models; the palette has {len(SERIES)} colours")
        colour[m] = free.pop(0)
        print(f"warning: {m} has no fixed colour; add it to MODEL_SLOT", file=sys.stderr)
    # rows top to bottom by mean holdout AUC, best on top
    rows = sorted(models, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))

    fig, ax = plt.subplots(figsize=(9, 1.6 + 0.55 * len(rows)), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.85 / (1.6 + 0.55 * len(rows)), right=0.97)
    ax.set_facecolor(SURFACE)
    lo, hi = min(r["holdout"] for r in runs), max(r["holdout"] for r in runs)
    if args.xlim:
        if args.xlim[0] >= args.xlim[1]:
            sys.exit("--xlim: MIN must be below MAX")
        if lo < args.xlim[0] or hi > args.xlim[1]:
            print(f"warning: runs span {lo:.4f}-{hi:.4f}, outside --xlim; some are cut off", file=sys.stderr)
        ax.set_xlim(*args.xlim)
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
            half = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n)
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
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)

    groups = "all run groups" if all_groups else ", ".join(g.name for g in args.groups)
    ax.set_title(f"Holdout AUC per run: {groups}", color=INK, fontsize=11, loc="left", pad=16)
    legend = [
        Line2D([], [], marker="o", ls="", color=INK2, markersize=7, label="run"),
        Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=INK2, markersize=7,
               label="run with caveat"),
        Line2D([], [], marker="o", color=INK, markersize=5, lw=1.6, label=f"mean, 95% interval (n >= {MIN_N_STATS})"),
        Line2D([], [], marker="|", ls="", color=INK2, markersize=9, markeredgewidth=1.6, label="10th and 90th percentile"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
              ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)

    name = "holdout_auc.png" if all_groups else "holdout_auc__" + "__".join(g.name for g in args.groups) + ".png"
    out = args.output or RUN_MULTI / "SUMMARY" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    print(out)


if __name__ == "__main__":
    main()
