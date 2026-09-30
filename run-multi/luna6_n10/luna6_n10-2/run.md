# luna6_n10-2

- **Status:** valid
- **Date:** 2026-09-30 (clock 18:47:05 -> 20:47:23 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-luna, max (levels offered: low medium high xhigh max)
- **turn_context (confirmed from the session log):** gpt-6-luna, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (proposed by the agent; it took the first "go" as approval)
- **Container:** 24 GB memory cap, no swap. Peak 12.7 GB (12726231040 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - preflight checks only; the agent
   asked us to confirm the tag `sep30` before creating the branch.
2. "go" - the agent took this as approval of the tag, created branch `sep30`,
   initialized results.tsv and asked for another "go" to start the clock.
3. "go" (extra, the driver sent it because the clock had not started) - the
   agent started the clock and worked the full 2 hours, stopping the clock
   itself at 20:47:23, 35 s after TIME IS UP.

The run-tag question was a real question that "go" glossed over (the agent
went with its own proposal). One extra "go" was needed.

## Results

- results.tsv: 70 rows = baseline + 69 experiments (25 keep, 43 discard, 2 crash - DART and tree-dropout runs that hit the training timeout)
- Best Eval AUC: **0.7503** at `6eba65f` ("reduce depth-9 model to 210 trees ..."), up from the 0.7203 baseline.
  Three kept commits tie at 0.7503 (in results.tsv order `6eba65f`, `0b85c54`, `b2529d9`, holdout 0.7465 / 0.7466 / 0.7468); the driver
  takes the first of them in results.tsv, `6eba65f`; the agent's branch ends at `b2529d9`.
- Its Holdout AUC: **0.7465**
- Gap (holdout - eval): -0.0038
- Time (report.txt): total 2h00m18s; XGBoost runs 0h41m20s (34.4%: training 4.7%, row-by-row eval 29.7%); AI 1h18m58s (65.6%)

## Validity checks

- **Holdout vs eval gap:** -0.0038, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (8+, 3-). OK.
- **leak_check.txt:** CONTENT HITS 0; no lines of any forbidden file and no
  holdout rows in the log; 0 of 638 tool calls listed. No `prepare.py` access. OK.
- **Web calls:** 42 search queries and 10 page opens: XGBoost and
  scikit-learn docs, the Stanford CS229 flight-delay project, a NeurIPS
  paper and two flight-delay papers (ScienceDirect, MDPI). No S3, `2005.csv`,
  BTS or Kaggle access. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
- The lowest result so far across sol6_n10 and luna6_n10 (Eval 0.7503): the
  agent spent the run on deep (depth-9, loss-guided) trees with few rounds
  and ended at 210 trees, and 65.6% of the clock was the AI's own time.
