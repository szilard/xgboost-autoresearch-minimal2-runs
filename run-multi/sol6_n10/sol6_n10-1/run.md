# sol6_n10-1

- **Status:** valid
- **Date:** 2026-09-29 (clock 14:04:18 -> 16:04:50 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep29` (chosen by the agent)
- **Container:** 24 GB memory cap, no swap. Peak 12.9 GB (12949700608 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent did the preflight
   checks and asked to agree on a run tag, proposing `sep29`.
2. "go" - the agent created branch `sep29`, started the clock and worked
   for the full 2 hours in this single turn, stopping the clock itself at
   16:04:50, 32 s after TIME IS UP.

No "keep going" was needed. The run-tag question in turn 1 was a real
question that "go" glossed over; the agent went with its own proposal.

## Results

- results.tsv: 101 rows = baseline + 100 experiments (25 keep, 74 discard, 2 crash - both training timeouts)
- Best Eval AUC: **0.7618** at `8eb7b32` ("900 boosting rounds after day ablation"), up from the 0.7203 baseline
- Its Holdout AUC: **0.7570**
- Gap (holdout - eval): -0.0048
- Time (report.txt): total 2h00m32s; XGBoost runs 1h00m47s (50.4%: training 8.0%, row-by-row eval 42.4%); AI 0h59m46s (49.6%)

## Validity checks

- **Holdout vs eval gap:** -0.0048, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (13+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 0; no distinctive lines of any forbidden file and no holdout rows in the log. The 104 listed commands are
  almost all `rg '^Eval AUC:...' run.log` polls. The others are file listings
  (`rg --files`, `find .. -name AGENTS.md`, `find data -maxdepth 1` for file
  names), `cat` of program.md, READMEs, train.py and harness.py (allowed), and
  loading its own artifact pickle for feature importances. None reads or runs
  a forbidden file. OK.
- **Web calls:** searches and page opens of XGBoost / scikit-learn docs and
  flight-delay papers (Berkeley iSchool, MDPI, PLOS ONE, Nature Sci. Rep.,
  ScienceDirect, PMLR). Two search queries mention "2005" ("flight delay
  prediction 2005 data ...", "Kaggle 2005 flight delay XGBoost ..."), but no
  result was opened from them for the data, and there is no S3 or `2005.csv` access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
- turns/2.err has harmless `apply_patch verification failed` errors on
  research-log.md edits; the agent retried them.
