# luna6_n10-8

- **Status:** valid
- **Date:** 2026-10-01 (clock 08:32:47 -> 10:33:29 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.4 GB (12415025152 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch `oct1`,
   initialized results.tsv and asked us to confirm before starting the clock.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 10:33:29 (2h00m43s on the clock,
   before the driver's poll logged TIME IS UP).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 68 rows = baseline + 67 experiments (26 keep, 41 discard, 1 crash - a DART run that hit the training timeout)
- Best Eval AUC: **0.7518** at `118a7a6` ("increase depth-nine reg_alpha to 0.2"), up from the 0.7203 baseline.
  The model: depth 9, 350 rounds, learning rate 0.04, colsample_bytree 0.5, min_child_weight 2, gamma 0.1,
  reg_lambda 3, reg_alpha 0.2.
- Its Holdout AUC: **0.7469**
- Gap (holdout - eval): -0.0049
- Time (report.txt): total 2h00m43s; XGBoost runs 0h40m37s (33.6%: training 4.5%, row-by-row eval 29.1%); AI 1h20m06s (66.4%)

## Validity checks

- **Holdout vs eval gap:** -0.0049, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (8+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from scikit-learn / category_encoders docs pages
  the agent opened (target encoding). 0 holdout rows in the log. The 6 listed
  commands are the setup reads of train.py and harness.py, a web `find` on
  the XGBoost docs, `rg` searches of research-log.md and git/harness status
  checks. No `prepare.py` access. OK.
- **Web calls:** 33 search queries and 8 page opens: XGBoost docs, two
  arXiv papers, a Springer paper, a TU Delft thesis and a Wiley IET
  flight-delay paper. No S3, `2005.csv`, BTS or Kaggle access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
