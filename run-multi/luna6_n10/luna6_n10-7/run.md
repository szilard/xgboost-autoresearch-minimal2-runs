# luna6_n10-7

- **Status:** valid
- **Date:** 2026-10-01 (clock 06:14:57 -> 08:15:25 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.9 GB (12935831552 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch `oct1`,
   initialized results.tsv and research-log.md and asked us to confirm before
   starting the clock.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 08:15:25 (2h00m28s on the clock,
   before the driver's poll logged TIME IS UP).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 72 rows = baseline + 71 experiments (26 keep, 46 discard, 0 crash)
- Best Eval AUC: **0.7597** at `5a6da1e` ("reg_alpha 0.75 under lossguide"), up from the 0.7203 baseline.
  The model: 2300 trees, learning rate 0.03, loss-guided growth with 44 leaves, min_child_weight 50,
  max_cat_threshold 8, reg_alpha 0.75.
- Its Holdout AUC: **0.7550**
- Gap (holdout - eval): -0.0047
- Time (report.txt): total 2h00m28s; XGBoost runs 0h52m17s (43.4%: training 11.1%, row-by-row eval 32.3%); AI 1h08m11s (56.6%)

## Validity checks

- **Holdout vs eval gap:** -0.0047, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (9+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from scikit-learn docs pages the agent opened.
  0 holdout rows in the log. The 32 listed commands are a web `find` on the
  XGBoost docs and repeated `git status` / `git log` / `rg` checks of
  train.py and results.tsv. No `prepare.py` access. OK.
- **Web calls:** 34 search queries and 6 page opens: XGBoost and
  scikit-learn docs, a TU Delft aerospace paper and two Wiley IET
  flight-delay papers. No S3, `2005.csv`, BTS or Kaggle access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
