# luna6_n10-4

- **Status:** valid
- **Date:** 2026-09-30/10-01 (clock 23:33:24 -> 01:33:35 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (proposed by the agent, not confirmed by us)
- **Container:** 24 GB memory cap, no swap. Peak 12.7 GB (12658102272 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - preflight checks; the agent
   asked "Should I use `sep30`?" before creating the branch.
2. "go" - the agent created branch `sep30`, started the clock and worked the
   full 2 hours in this single turn, stopping the clock itself at 01:33:35,
   just after TIME IS UP (2h00m10s on the clock).

No "keep going" was needed. The run-tag question was a real question that
"go" glossed over; the agent went with `sep30`.

## Results

- results.tsv: 57 rows = baseline + 56 experiments (12 keep, 44 discard, 1 crash - a cyclic-weekday arithmetic error on string dtype)
- Best Eval AUC: **0.7382** at `31ee1bc` ("use 330 rounds with three hour count"), up from the 0.7203 baseline.
  The model: 330 trees, depth 5, learning rate 0.1, reg_lambda 5, numeric scheduled hour and a
  training-derived count of flights at the same origin, date and three-hour window.
- Its Holdout AUC: **0.7348**
- Gap (holdout - eval): -0.0034
- Time (report.txt): total 2h00m10s; XGBoost runs 0h34m50s (29.0%: training 2.2%, row-by-row eval 26.8%); AI 1h25m20s (71.0%)

## Validity checks

- **Holdout vs eval gap:** -0.0034, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (16+, 2-). OK.
- **leak_check.txt:** CONTENT HITS 0; no lines of any forbidden file and no
  holdout rows in the log. The 6 listed commands are the setup reads
  (program.md, README-autoresearch.md, a file listing, branch/data existence
  checks), a web `find` on the XGBoost docs and `rg` searches of
  research-log.md, train.py and program.md. No `prepare.py` access. OK.
- **Web calls:** 34 search queries and 14 page opens: XGBoost docs,
  flight-delay papers (CityU, MDPI, ScienceDirect) and arXiv 1911.01605.
  Two searches mention 2005 (one "... Kaggle 2005 dataset", one for the BTS
  field description of CRSDepTime), but no Kaggle or BTS page was opened. No
  S3 or `2005.csv` access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
- The weakest run of both groups so far (holdout 0.7348): only 12 keeps and
  56 experiments, and 71% of the clock was the AI's own time - the agent
  spent its time on feature engineering (schedule-density counts) with a
  small depth-5 model rather than on capacity and regularization.
