# astra6_n10-1

- **Status:** valid
- **Date:** 2026-10-01 (clock 17:38:48 -> 19:40:50 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 13.3 GB (13328977920 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct1`, initialized results.tsv and research-log.md and asked for "go".
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 19:38:57; its last run had started before the
   deadline, and it stopped the clock itself (turn ended 19:42:00, ~3 min
   after TIME IS UP).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 67 rows = baseline + 66 experiments (25 keep, 41 discard, 1 crash - a soft-voting ensemble that hit the 60 s training timeout)
- Best Eval AUC: **0.7652** at `c1e763d` ("remove numeric day-of-year while retaining categorical date"), up from the 0.7203 baseline. The later `204378f` (a memory refactor of the same features, the agent's final selected commit) ties at 0.7652 eval / 0.7598 holdout; the driver takes the first.
- Model: soft-voting ensemble of a DART booster (300 trees, depth 4, rate_drop 0.05) and an ordinary booster, native categoricals incl. a categorical flight date, carrier-month cross, and CatBoost-style ordered (hash-permuted, training-only) airport/date target statistics.
- Its Holdout AUC: **0.7598**
- Gap (holdout - eval): -0.0054
- Time (report.txt): total 2h02m02s; XGBoost runs 1h13m14s (60.0%: training 22.2%, row-by-row eval 37.8%); AI 0h48m47s (40.0%)

## Validity checks

- **Holdout vs eval gap:** -0.0054, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (114+, 7-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `artifact =
  load_artifact(commit)` appears in the agent's own sanity-check script,
  which imports `load_artifact` from harness.py (allowed; the function is
  defined there). 0 holdout rows in the log. The 15 listed commands are
  `rg --files` listings at setup, harness status checks, `run.log` tails and
  web lookups. None reads or runs a forbidden file. No `prepare.py` access.
  train.py reads only `data/train.csv`. OK.
- **Web calls:** 22 search calls and ~28 page opens: XGBoost docs and
  source, scikit-learn/scipy/numpy docs, CatBoost and DART papers, flight
  delay papers. No BTS/TranStats page, no S3 data URL, no `2005.csv`, no
  curl/wget. (Two amazonaws.com URLs appear only as search results - book
  PDFs - and were not opened.) OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
- gpt-6-astra offers a level `ultra` above `max`; this group runs `max` as requested.
- The first launch of this run was aborted by me during the driver's setup
  check (before any prompt was sent to codex) because the background task
  limit was too short; the container and directory were removed and the run
  was restarted from scratch at 17:35. The agent never saw the aborted attempt.
