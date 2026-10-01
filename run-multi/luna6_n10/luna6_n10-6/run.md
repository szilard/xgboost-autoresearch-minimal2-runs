# luna6_n10-6

- **Status:** valid
- **Date:** 2026-10-01 (clock 03:59:17 -> 05:58:55 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (proposed by the agent, not confirmed by us)
- **Container:** 24 GB memory cap, no swap. Peak 7.5 GB (7525359616 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - preflight checks and results.tsv
   header; the agent proposed `oct1` and waited for our choice.
2. "go" - the agent created branch `oct1`, started the clock and worked in
   this single turn, stopping the clock itself at 05:58:55 with 21 s left
   (1h59m39s on the clock).

No "keep going" was needed. The run-tag question was a real question that
"go" glossed over; the agent went with `oct1`.

## Results

- results.tsv: 81 rows = baseline + 80 experiments (22 keep, 58 discard, 1 crash - a DART run that hit the training timeout)
- Best Eval AUC: **0.7628** at `26de1ad` ("reg_alpha 5.0 with depth 11 and subsample 0.99"), up from the 0.7203 baseline.
  The model: 600 trees, depth 11, L1 5.0, L2 5, subsample 0.99, column sampling 0.7 per tree / 0.8 per node.
- Its Holdout AUC: **0.7572**
- Gap (holdout - eval): -0.0056
- Time (report.txt): total 1h59m39s; XGBoost runs 0h51m36s (43.1%: training 8.1%, row-by-row eval 35.0%); AI 1h08m02s (56.9%)

## Validity checks

- **Holdout vs eval gap:** -0.0056, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (10+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from scikit-learn docs pages the agent opened
  (cyclical feature engineering). 0 holdout rows in the log. The 6 listed
  commands are a web `find` on the XGBoost docs, `rg` searches of
  research-log.md and harness/git status checks. No `prepare.py` access. OK.
- **Web calls:** 32 search queries and 8 page opens: XGBoost docs and arXiv
  2002.10254. One search mentions "2005 US airline data" in looking for
  papers. No S3, `2005.csv`, BTS or Kaggle access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
