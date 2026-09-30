# luna6_n10-1

- **Status:** valid
- **Date:** 2026-09-30 (clock 16:22:43 -> 18:23:00 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.8 GB (12824465408 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `sep30`, initialized results.tsv and asked us to confirm the setup before
   starting the clock.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 18:23:00, 16 s after TIME IS UP.

No "keep going" was needed. No real question was glossed over (the tag was
already created; "go" is the confirmation it asked for).

## Results

- results.tsv: 80 rows = baseline + 79 experiments (30 keep, 49 discard, 1 crash - a duplicate `max_depth` keyword)
- Best Eval AUC: **0.7652** at `993b867` (loss-guided, max_leaves 256, reg_lambda 64, reg_alpha 7, gamma 0.15, learning rate 0.04, 1000 trees), up from the 0.7203 baseline
- Its Holdout AUC: **0.7598**
- Gap (holdout - eval): -0.0054
- Time (report.txt): total 2h00m17s; XGBoost runs 0h54m28s (45.3%: training 10.3%, row-by-row eval 35.0%); AI 1h05m49s (54.7%)

## Validity checks

- **Holdout vs eval gap:** -0.0054, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (10+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from scikit-learn docs pages the agent opened
  (TargetEncoder), not from plot_auc_history.py. 0 holdout rows in the log.
  The 20 listed commands are research-log appends (flagged for words like
  "held-out"), `git show --stat HEAD`, status/`rg` checks of train.py and a
  web `find` on the XGBoost docs. None reads or runs a forbidden file. No
  `prepare.py` access. OK.
- **Web calls:** 36 search queries and 16 page opens: XGBoost docs,
  flight-delay papers (ScienceDirect, MDPI, SDSU proceedings, Berkeley
  iSchool) and one BTS page - the TranStats *table information* page of the
  airline on-time table (a field description, not a data download). One
  search mentions 2005, one is restricted to transtats.bts.gov (data
  dictionary). No S3, `2005.csv` or other data download. OK, noted.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
