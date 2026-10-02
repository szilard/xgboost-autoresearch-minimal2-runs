# astra6_n10-7

- **Status:** valid
- **Date:** 2026-10-02 (clock 14:08:42 -> 16:09:24 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 9.0 GB (8966447104 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and research-log.md and asked for "go".
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 16:09:24 (2h00m41s, before the
   driver's next poll saw TIME IS UP).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 71 rows = baseline + 70 experiments (28 keep, 43 discard, 0 crash)
- Best Eval AUC: **0.7644** at `10d2bfa` (three-model XGBoost ensemble), up from the 0.7203 baseline
- Model: soft-voting ensemble of three XGBoost models sharing shallow, heavily regularized settings (3600 trees, depth 4, learning rate 0.025, reg_lambda 100, min_child_weight 100, colsample_bynode 0.34, feature_weights) - one standard, one with max_bin 4, one deeper (depth 5, 1800 trees); native categoricals plus a categorical date.
- Its Holdout AUC: **0.7592**
- Gap (holdout - eval): -0.0052
- Time (report.txt): total 2h00m41s; XGBoost runs 0h46m36s (38.6%: training 15.8%, row-by-row eval 22.8%); AI 1h14m05s (61.4%)

## Validity checks

- **Holdout vs eval gap:** -0.0052, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (23+, 9-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from the scikit-learn bike-sharing (cyclical
  features) docs page, not from plot_auc_history.py. 0 holdout rows in the
  log. No tool call names prepare.py, check_groundtruth.py,
  run_groundtruth_all.sh, plot_auc_history.py, holdout.csv or 2005.csv; a
  setup check stats `data/eval.csv` (exists, size) without reading it.
  train.py reads only `data/train.csv`. OK.
- **Web calls:** 15 search calls and ~20 page opens: XGBoost and
  scikit-learn docs and GitHub issues, arXiv/PMLR ML papers, a EUROCONTROL
  delay-propagation publication page, the Berkeley iSchool flight-delay
  project. No BTS TranStats page, no S3 data URL, no `2005.csv`, no
  curl/wget. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
