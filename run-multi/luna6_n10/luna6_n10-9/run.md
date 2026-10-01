# luna6_n10-9

- **Status:** valid
- **Date:** 2026-10-01 (clock 10:51:31 -> 12:52:20 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.9 GB (12929662976 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch `oct1`,
   initialized results.tsv and asked us to confirm before starting the clock.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 12:52:20 (2h00m48s on the clock,
   before the driver's poll logged TIME IS UP).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 66 rows = baseline + 65 experiments (24 keep, 38 discard, 4 crash - two DART/dropout runs that hit the training timeout, a cyclic-feature error on string columns, and an attempt to use CRSArrTime, which is not in the data)
- Best Eval AUC: **0.7594** at `72ddc2a` ("max_depth 12 with reg_alpha 5.0 and reg_lambda 0.0"), up from the 0.7203 baseline.
  The model: depth 12, 800 trees, reg_alpha 5, reg_lambda 0.
- Its Holdout AUC: **0.7543**
- Gap (holdout - eval): -0.0051
- Time (report.txt): total 2h00m48s; XGBoost runs 0h45m43s (37.8%: training 8.0%, row-by-row eval 29.8%); AI 1h15m05s (62.2%)

## Validity checks

- **Holdout vs eval gap:** -0.0051, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (13+, 4-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from scikit-learn / pandas docs pages the agent
  opened. 0 holdout rows in the log. The 4 listed commands are the setup
  reads (program.md, a check for AGENTS.md files), two web `find`s on docs
  pages and an `rg` search of program.md and README-autoresearch.md for
  words like "holdout" (reading the allowed instructions). No `prepare.py`
  access. OK.
- **Web calls:** 35 search queries and 12 page opens: XGBoost and
  scikit-learn docs, an arXiv paper, an engineering journal article, a TU
  Delft thesis and a Wiley IET flight-delay paper. Two searches were for
  Kaggle flight-delay solutions and one mentions 2005, but no Kaggle page
  was opened. No S3, `2005.csv` or BTS access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
