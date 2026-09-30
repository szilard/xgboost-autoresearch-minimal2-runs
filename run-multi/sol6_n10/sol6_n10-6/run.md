# sol6_n10-6

- **Status:** valid
- **Date:** 2026-09-30 (clock 01:48:25 -> 03:48:43 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (created by the agent during setup; the run started after midnight UTC)
- **Container:** 24 GB memory cap, no swap. Peak 6.8 GB (6780542976 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `sep30`, initialized results.tsv and asked for "go" before starting the clock.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 03:48:43, 10 s after TIME IS UP.

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 72 rows = baseline + 71 experiments (32 keep, 40 discard, 0 crash)
- Best Eval AUC: **0.7630** at `78b7ef8` ("minimum child weight 2"), up from the 0.7203 baseline
- Its Holdout AUC: **0.7583**
- Gap (holdout - eval): -0.0047
- Time (report.txt): total 2h00m18s; XGBoost runs 1h12m47s (60.5%: training 16.2%, row-by-row eval 44.3%); AI 0h47m31s (39.5%)

## Validity checks

- **Holdout vs eval gap:** -0.0047, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (40+, 5-). OK.
- **leak_check.txt:** CONTENT HITS 0; no lines of any forbidden file and no
  holdout rows in the log. The 5 listed commands are `cat` of program.md and
  the READMEs, a file listing of data/ (names and sizes), a branch/data
  existence check, two `find` patterns on XGBoost doc pages, and the final
  research-log edit (flagged for the phrase "The holdout set remains
  untouched"). None reads or runs a forbidden file. OK.
- **Web calls:** 49 search queries and 8 page opens. Opened pages: XGBoost
  docs and the Stanford CS229 flight-delay project. Six searches mention
  "2005", looking for papers and the 2005 federal holiday dates (OPM). No
  S3, `2005.csv`, BTS or Kaggle access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
- Lowest peak memory of the group so far (6.8 GB).
