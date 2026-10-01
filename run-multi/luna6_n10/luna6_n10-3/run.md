# luna6_n10-3

- **Status:** valid
- **Date:** 2026-09-30 (clock 21:05:38 -> 23:05:48 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (chosen by the agent after "go"; not confirmed by us)
- **Container:** 24 GB memory cap, no swap. Peak 13.1 GB (13127114752 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - preflight checks; the agent
   waited for our run-tag choice before creating the branch.
2. "go" - the agent created branch `sep30`, started the clock and worked the
   full 2 hours in this single turn, stopping the clock itself at 23:05:48
   (2h00m09s on the clock, before the driver's poll logged TIME IS UP).

No "keep going" was needed. The run-tag question was a real question that
"go" glossed over; the agent went with `sep30`.

## Results

- results.tsv: 81 rows = baseline + 80 experiments (37 keep, 42 discard, 2 crash - a DART run that hit the training timeout, and a category-to-int cast error)
- Best Eval AUC: **0.7621** at `adccf54` ("n_estimators=550 at depth 12"), up from the 0.7203 baseline
- Its Holdout AUC: **0.7557**
- Gap (holdout - eval): -0.0064
- Time (report.txt): total 2h00m09s; XGBoost runs 0h56m02s (46.6%: training 6.8%, row-by-row eval 39.9%); AI 1h04m07s (53.4%)

## Validity checks

- **Holdout vs eval gap:** -0.0064, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (13+, 5-). OK.
- **leak_check.txt:** CONTENT HITS 0; no lines of any forbidden file and no
  holdout rows in the log. The one listed command is the first setup batch:
  `cat` of program.md and the READMEs, `rg --files` (a file listing) and
  `find .. -name AGENTS.md`. No `prepare.py` access. OK.
- **Web calls:** 36 search queries and 18 page opens: XGBoost docs,
  flight-delay papers (Berkeley iSchool, MDPI, Wiley IET, ScienceDirect) and
  two arXiv papers. No S3, `2005.csv`, BTS or Kaggle access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
