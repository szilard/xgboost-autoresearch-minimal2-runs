# luna6_n10-5

- **Status:** valid
- **Date:** 2026-10-01 (clock 01:44:23 -> 03:44:37 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (created by the agent during setup; the run started after midnight UTC)
- **Container:** 24 GB memory cap, no swap. Peak 12.8 GB (12845813760 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch `oct1`
   ("I used the suggested `oct1` tag after no tag change came through"),
   initialized results.tsv and asked for confirmation before starting the clock.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 03:44:37 (2h00m13s on the clock,
   before the driver's poll logged TIME IS UP).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 59 rows = baseline + 58 experiments (19 keep, 37 discard, 3 crash - two DART/dropout runs that hit the training timeout and a cyclic-encoding error on the `c-` coded calendar columns)
- Best Eval AUC: **0.7540** at `4e521f0` ("colsample_bytree 0.55 with depth-24 cyclic features"), up from the 0.7203 baseline.
  The model: cyclic encodings of departure time, weekday and month, `max_depth=24`, `colsample_bytree=0.55`.
- Its Holdout AUC: **0.7496**
- Gap (holdout - eval): -0.0044
- Time (report.txt): total 2h00m13s; XGBoost runs 0h49m16s (41.0%: training 13.1%, row-by-row eval 27.9%); AI 1h10m57s (59.0%)

## Validity checks

- **Holdout vs eval gap:** -0.0044, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (27+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from scikit-learn docs pages the agent opened
  (TargetEncoder). The one data row in the log also occurs in train/eval (0
  rows only in holdout). The 22 listed commands are polls of run.log and
  `ps`, `cat results.tsv`, git status and `rg` searches of train.py,
  program.md and research-log.md. No `prepare.py` access. OK.
- **Web calls:** 24 search queries and 17 page opens: XGBoost and
  scikit-learn docs, arXiv papers, the CatBoost NeurIPS paper, an MIT thesis,
  a PMC article and an MDPI flight-delay paper. No S3, `2005.csv`, BTS or
  Kaggle access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
