# sol6_n10-10

- **Status:** valid (but see "Web research on the same task" below)
- **Date:** 2026-09-30 (clock 11:20:38 -> 13:22:10 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.6 GB (12582625280 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `sep30`, initialized results.tsv and research-log.md and asked for "go".
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 13:22:10, 41 s after TIME IS UP.

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 66 rows = baseline + 65 experiments (22 keep, 43 discard, 1 crash - a calendar parse error)
- Best Eval AUC: **0.7639** at `12b4005` ("20 leaves with L1 4; higher AUC smaller model"), up from the 0.7203 baseline.
  The agent's next commit `fc90376` (16 leaves) ties at 0.7639 / holdout 0.7572; the agent names
  `fc90376` as best and the branch ends there, the driver takes the first of the tied keeps.
- Its Holdout AUC: **0.7572** (same for both tied commits)
- Gap (holdout - eval): -0.0067
- Time (report.txt): total 2h01m31s; XGBoost runs 0h43m28s (35.8%: training 4.1%, row-by-row eval 31.7%); AI 1h18m03s (64.2%)

## Validity checks

- **Holdout vs eval gap:** -0.0067, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (13+, 2-). OK.
- **leak_check.txt:** CONTENT HITS 2, both false positives:
  - prepare.py line `for col in ["Month", "DayofMonth", "DayOfWeek"]:` - it
    is in the agent's own train.py edit at 11:31 (numeric calendar columns),
    not from the file; the agent never named or read prepare.py (its setup
    listing was `ls -la`).
  - plot_auc_history.py line `import matplotlib.pyplot as plt` - from a
    scikit-learn docs page the agent opened.
  0 holdout rows in the log. The 4 listed commands are setup reads of
  allowed files, two web opens and loading its own artifact pickle. OK.
- **Web calls:** 39 search queries, 11 page opens, no downloads, no S3,
  `2005.csv` or BTS access. OK by the rules - but see below.

## Web research on the same task

This run went further than the others in researching the task itself. It
searched for "flight delay 2005 dep_delayed_15min winning solution target
encoding origin destination carrier" (`dep_delayed_15min` is this dataset's
target column), a site:kaggle.com search, and a site:mlcourse.ai search, and
opened:

- the mlcourse.ai "flight delays" Kaggle assignment (the course competition
  whose data has the same columns and `c-` coded values as ours),
- a GitHub gist "A2 Flights solution" (akatasonov) - a solution script for
  that competition,
- two GitHub flight-delay repos (Prashant-4527, AhmedFaizanDev),
- the GBM-in-the-age-of-LLMs PDF on r-consortium.org (szilard_GBM_LLM.pdf),
- the Berkeley iSchool project and XGBoost docs.

It used ideas from them and cites them in research-log.md: numeric calendar
columns, route / airline-origin features (discarded), and departure minute
from the HHMM time (the gist extracts hour and minute) - the best train.py
keeps `DepMinute = CRSDepTime % 100`. No data was downloaded and no
solution code was copied wholesale. The rules only forbid the human-only
files and the source data, so the run is valid, but its result had help from
public solutions to an equivalent task that the other runs did not use.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
