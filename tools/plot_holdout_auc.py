#!/usr/bin/env python3
"""Plot the holdout AUC of run groups: one row per model, one dot per run.

Modelled on Fig. 1 of arXiv:2609.33812 (identical runs, different results).
Reads each group's holdout_auc.tsv (written by /xgb-multi) and the model from
each run's driver-summary.json. Groups with the same model are pooled into one
row (all runs are effort max).

Per row: a filled dot per valid run and a hollow dot per caveat run (runs with
valid = "no" are left out), a grey bar over the full range, the mean with its
95% interval (t) and the 10th/90th percentiles when the row has >= 5 runs, and
at right the SD, n and number of caveat runs. Dotted line: the starting code's
holdout AUC (baseline row of groundtruth_all.tsv).

Usage:
    tools/plot_holdout_auc.py run-multi/sol6_n10 run-multi/luna-test [-o out.png]

Default output: run-multi/plots/holdout_auc__<group>__<group>.png
"""
import argparse
import csv
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib
import matplotlib.transforms

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


def baseline_holdout(gdir):
    """Holdout AUC of the starting code, from the first run with a baseline row."""
    for gt in sorted(gdir.glob("*/groundtruth_all.tsv")):
        with open(gt) as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r["description"].startswith("baseline"):
                    return float(r["holdout_auc"])
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("groups", nargs="+", type=Path, help="run group directories (run-multi/<group>)")
    ap.add_argument("-o", "--output", type=Path, help="output file (.png or .svg)")
    args = ap.parse_args()

    runs, baselines = [], set()
    for g in args.groups:
        if not (g / "holdout_auc.tsv").is_file():
            sys.exit(f"{g}: no holdout_auc.tsv")
        runs += load_group(g)
        b = baseline_holdout(g)
        if b is not None:
            baselines.add(b)
    if not runs:
        sys.exit("no valid runs")
    if len(baselines) > 1:
        print(f"warning: groups have different baselines {sorted(baselines)}; not drawing one", file=sys.stderr)
    baseline = baselines.pop() if len(baselines) == 1 else None

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
    fig.subplots_adjust(bottom=0.85 / (1.6 + 0.55 * len(rows)), right=0.8)
    ax.set_facecolor(SURFACE)
    xs_all = [r["holdout"] for r in runs] + ([baseline] if baseline else [])
    lo, hi = min(xs_all), max(xs_all)
    pad = (hi - lo) * 0.05 or 0.001
    ax.set_xlim(lo - pad, hi + pad)

    table = []
    for i, m in enumerate(rows):
        y = len(rows) - 1 - i
        rr = [r for r in runs if r["model"] == m]
        x = np.array([r["holdout"] for r in rr])
        n, n_cav = len(x), sum(r["valid"] == "caveat" for r in rr)
        ax.plot([x.min(), x.max()], [y, y], color=RANGE, lw=6, solid_capstyle="round", zorder=1)
        for r in rr:
            filled = r["valid"] == "yes"
            ax.scatter(r["holdout"], y, s=46, zorder=3, linewidths=1.4,
                       facecolors=colour[m] if filled else SURFACE, edgecolors=colour[m])
        mean = x.mean()
        sd = x.std(ddof=1) if n > 1 else float("nan")
        if n >= MIN_N_STATS:
            half = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
            ax.errorbar(mean, y + 0.22, xerr=half, fmt="none", ecolor=INK, elinewidth=1.6, capsize=3, zorder=4)
            p10, p90 = np.percentile(x, [10, 90])
            ax.scatter([p10, p90], [y, y], marker="|", s=260, color=INK, linewidths=1.6, zorder=2)
        ax.scatter(mean, y + 0.22, s=34, color=INK, zorder=5)
        table.append((y, sd, n, n_cav))

    if baseline:
        ax.axvline(baseline, color=INK2, lw=1, ls=":", zorder=0)
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

    # right-hand columns: SD, n, caveat (x in axes fraction, y in data)
    trans = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)
    cols = [("SD", 1.10), ("n", 1.15), ("caveat", 1.23)]
    for name, cx in cols:
        ax.text(cx, len(rows) - 0.45, name, ha="right", va="bottom", fontsize=8, color=INK2, transform=trans)
    for y, sd, n, n_cav in table:
        vals = ["" if np.isnan(sd) else f"{sd:.4f}", str(n), str(n_cav)]
        for (name, cx), v in zip(cols, vals):
            ax.text(cx, y, v, ha="right", va="center", fontsize=8.5, color=INK, transform=trans)

    groups = ", ".join(g.name for g in args.groups)
    ax.set_title(f"Holdout AUC per run: {groups}", color=INK, fontsize=11, loc="left", pad=16)
    legend = [
        Line2D([], [], marker="o", ls="", color=INK2, markersize=7, label="run"),
        Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=INK2, markersize=7,
               label="run with caveat"),
        Line2D([], [], marker="o", color=INK, markersize=5, lw=1.6, label=f"mean, 95% interval (n >= {MIN_N_STATS})"),
        Line2D([], [], marker="|", ls="", color=INK2, markersize=9, markeredgewidth=1.6, label="10th and 90th percentile"),
    ]
    if baseline:
        legend.append(Line2D([], [], color=INK2, ls=":", label=f"starting code ({baseline:.4f})"))
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
              ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)

    out = args.output or Path("run-multi/plots") / ("holdout_auc__" + "__".join(g.name for g in args.groups) + ".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    print(out)


if __name__ == "__main__":
    main()
