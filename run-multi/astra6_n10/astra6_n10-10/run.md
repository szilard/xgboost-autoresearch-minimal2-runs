# astra6_n10-10

- **Status:** valid
- **Date:** 2026-10-02 (clock 21:07:56 -> 23:10:36 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 6.2 GB (6201204736 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and research-log.md and asked for "go".
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 23:08:48; it stopped the clock itself at
   23:10:36 (turn ended 23:10:49).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 74 rows = baseline + 73 experiments (24 keep, 48 discard, 2 crash - one crash and one training timeout)
- Best Eval AUC: **0.7633** at `8096331`, up from the 0.7203 baseline
- Model: a single XGBoost model with 4 parallel trees per round (400 rounds), loss-guided, max_leaves 64, learning rate 0.05, min_child_weight 20, reg_alpha 1, max_cat_threshold 256, subsample 0.8, colsample_bytree 0.8; native categoricals for carrier, origin, destination and a month-day categorical date; month/day/weekday dropped as separate features. The simplest best model of the group.
- Its Holdout AUC: **0.7591**
- Gap (holdout - eval): -0.0042
- Time (report.txt): total 2h02m40s; XGBoost runs 0h50m14s (41.0%: training 23.5%, row-by-row eval 17.5%); AI 1h12m26s (59.0%)

## Validity checks

- **Holdout vs eval gap:** -0.0042, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (22+, 9-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from a scikit-learn docs example, not from
  plot_auc_history.py. 0 holdout rows in the log. No tool call names
  prepare.py, check_groundtruth.py, run_groundtruth_all.sh,
  plot_auc_history.py, holdout.csv or 2005.csv; a setup check stats
  `data/eval.csv` (exists, size) without reading it. train.py reads only
  `data/train.csv`. OK.
- **Web calls:** 21 search calls and ~20 page opens: XGBoost docs and
  source, LightGBM and scikit-learn docs, arXiv/NeurIPS ML papers, a
  Scientific Reports flight-delay paper, the Berkeley iSchool flight-delay
  project. One search was restricted to transtats.bts.gov (data
  dictionary); it returned glossary snippets and the agent cited the BTS
  departures page in its research log, but no TranStats page was opened and
  no data was downloaded. No S3 data URL, no `2005.csv`, no curl/wget. OK,
  noted.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
