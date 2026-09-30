# sol6_n10-5

- **Status:** valid
- **Date:** 2026-09-29/30 (clock 23:33:50 -> 01:34:23 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep29` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.4 GB (12352786432 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `sep29`, initialized results.tsv and asked us to confirm `sep29` and say go.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 01:34:23, 23 s after TIME IS UP.

No "keep going" was needed. The only open points after turn 1 were the tag
(already created) and the go-ahead, both of which "go" answers.

## Results

- results.tsv: 84 rows = baseline + 83 experiments (27 keep, 55 discard, 2 crash - both DART / tree-dropout runs that hit the training timeout)
- Best Eval AUC: **0.7685** at `cc135a1` ("1800 rounds in two-tree boosted forest"), up from the 0.7203 baseline
- Its Holdout AUC: **0.7624**
- Gap (holdout - eval): -0.0061
- Time (report.txt): total 2h00m33s; XGBoost runs 1h00m23s (50.1%: training 23.8%, row-by-row eval 26.3%); AI 1h00m10s (49.9%)

## Validity checks

- **Holdout vs eval gap:** -0.0061, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (18+, 5-). OK.
- **leak_check.txt:** CONTENT HITS 0; no lines of any forbidden file and no
  holdout rows in the log. The 86 listed commands are `rg` polls of run.log,
  reads of allowed files and its own artifacts; none names or reads a
  forbidden file. OK.
- **Web calls:** 81 search queries and 12 page opens. Opened pages: XGBoost
  docs, Berkeley iSchool project, MDPI, PLOS ONE, IJACSA and Nature Sci. Rep.
  papers. Three searches mention "2005", two of them restricted to kaggle.com
  ("site:kaggle.com flight delay prediction airline 2005 feature engineering
  ..."); the only Kaggle result returned was an unrelated 2018-2022 dataset
  and no Kaggle page was opened. No S3 or `2005.csv` access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
