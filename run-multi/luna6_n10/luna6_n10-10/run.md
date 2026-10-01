# luna6_n10-10

- **Status:** valid
- **Date:** 2026-10-01 (clock 13:11:39 -> 15:11:50 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.8 GB (12800643072 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch `oct1`,
   initialized results.tsv and asked us to confirm before starting the clock.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 15:11:50 (2h00m11s on the clock,
   before the driver's poll logged TIME IS UP).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 71 rows = baseline + 70 experiments (27 keep, 44 discard, 0 crash)
- Best Eval AUC: **0.7479** at `af9b4d9` ("max_depth 6 with 31-leaf cap; new best by 0.0005"), up from the 0.7203 baseline.
  The model: 1200 trees, depth 6, 31-leaf cap, max_bin 128, max_cat_threshold 10, reg_lambda 4, reg_alpha 1.1,
  cyclic departure-hour sine/cosine features alongside the hourly category.
- Its Holdout AUC: **0.7437**
- Gap (holdout - eval): -0.0042
- Time (report.txt): total 2h00m11s; XGBoost runs 0h48m25s (40.3%: training 4.2%, row-by-row eval 36.1%); AI 1h11m46s (59.7%)

## Validity checks

- **Holdout vs eval gap:** -0.0042, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (20+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from scikit-learn / pandas docs pages the agent
  opened. 0 holdout rows in the log. The one listed command is the setup
  read of train.py and harness.py. No `prepare.py` access. OK.
- **Web calls:** 31 search queries and 10 page opens: XGBoost and
  scikit-learn docs, an MDPI and two Wiley IET flight-delay papers. One
  search mentions Kaggle, but no Kaggle page was opened. No S3, `2005.csv`
  or BTS access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
