# sol6_n10-2

- **Status:** valid
- **Date:** 2026-09-29 (clock 16:21:54 -> 18:22:01 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep29` (chosen by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.7 GB (12684042240 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent read the code, created
   branch `sep29`, initialized results.tsv and asked for "go" before starting
   the clock.
2. "go" - the agent started the clock and worked for the full 2 hours in
   this single turn, stopping the clock itself at 18:22:01, 5 s after TIME IS UP.

No "keep going" was needed. No real question was glossed over: the only
open point after turn 1 was the go-ahead that "go" gives.

## Results

- results.tsv: 74 rows = baseline + 73 experiments (32 keep, 41 discard, 1 crash - a day-of-year parse error)
- Best Eval AUC: **0.7670** at `fad5697` ("categorical split threshold 256 at depth eight alpha 5"), up from the 0.7203 baseline
- Its Holdout AUC: **0.7611**
- Gap (holdout - eval): -0.0059
- Time (report.txt): total 2h00m06s; XGBoost runs 1h00m06s (50.0%: training 13.9%, row-by-row eval 36.1%); AI 1h00m01s (50.0%)

## Validity checks

- **Holdout vs eval gap:** -0.0059, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (33+, 6-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive. The one "distinctive"
  line of plot_auc_history.py found in the log is `import matplotlib.pyplot as
  plt`, and it comes from a scikit-learn documentation page the agent opened
  (permutation importance example), not from the file. The one holdout data
  row found in the log also occurs in train/eval (0 rows only in holdout).
  The 3 listed commands are `cat` of program.md, the READMEs and .gitignore,
  `find .. -name AGENTS.md`, a file listing of data/ (names and sizes), and
  git/harness status. None reads or runs a forbidden file. OK.
- **Web calls:** 34 search queries / page opens, on XGBoost and scikit-learn
  docs, flight-delay papers and the OPM list of 2005 federal holidays (used
  for a "distance to 2005 holidays" feature, discarded). Two searches mention
  "2005" in looking for flight-delay papers. No S3 or `2005.csv` access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
- The agent's final message says 72 experiments; results.tsv has 73 after the
  baseline, one of them the crash.
