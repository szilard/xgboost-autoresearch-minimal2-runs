# sol6_n10-8

- **Status:** valid with a caveat - the agent read `prepare.py` (forbidden) during setup, no further access
- **Date:** 2026-09-30 (clock 06:39:24 -> 08:39:48 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (proposed by the agent, not confirmed by us)
- **Container:** 24 GB memory cap, no swap. Peak 12.6 GB (12615528448 bytes), 0 processes killed at the cap.

## Caveat: the agent read prepare.py

At 06:34:19, in its first batch of setup reads, the agent ran three commands
in parallel, one of them

    cat .gitignore && sed -n '1,240p' harness.py && cat train.py && cat prepare.py

alongside `cat program.md` - so it read `prepare.py` (which builds the
train/eval/holdout split and contains the S3 URL of the source data
`2005.csv`) before it had seen the restriction in program.md.
leak_check.txt: CONTENT HITS 26 (all 26 distinctive lines of prepare.py are
in the log). The agent disclosed it itself in turn 1 ("I accidentally opened
the human-only `prepare.py` during the initial file read. I won't use or
inspect it further") and again in its final message. No later command
touches S3, `2005.csv` or any URL download. The rule is that the agent must not read it; the run was first excluded for this. Same failure as sol6_n10-4
and sol6_n10-7.

Re-classified on 2026-09-30 from excluded to valid with a caveat (user decision):
the agent read prepare.py but went no further - no command touched holdout.csv,
S3 or `2005.csv`, no holdout row is in the log, and the file gives nothing usable
without the source data. The four runs that read it (4, 7, 8, 9) do not score
higher than the others (mean holdout 0.7579 vs 0.7590) and their holdout-eval gap
is the same.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - preflight checks, results.tsv
   header, disclosed the prepare.py read, asked us to confirm `sep30`.
2. "go" - the agent created branch `sep30`, started the clock and worked the
   full 2 hours in this single turn, stopping the clock itself at 08:39:48,
   just before the driver's next poll (2h00m24s on the clock).

No "keep going" was needed. The run-tag question and the prepare.py
disclosure were real points that "go" glossed over.

## Results

- results.tsv: 59 rows = baseline + 58 experiments (19 keep, 40 discard, 0 crash)
- Best Eval AUC: 0.7572 at `40f546a` ("min_child_weight 2")
- Its Holdout AUC: 0.7510
- Gap (holdout - eval): -0.0062
- Time (report.txt): total 2h00m24s; XGBoost runs 0h40m31s (33.7%: training 1.9%, row-by-row eval 31.7%); AI 1h19m53s (66.3%)

## Validity checks

- **leak_check.txt: FAILED** (the caveat above) - CONTENT HITS 26, from the `cat prepare.py`
  above. No lines of the other forbidden files and no holdout rows in the log.
- Holdout vs eval gap: -0.0062, normal.
- diff-stat.txt: first commit to best commit touches `train.py` only (19+, 3-).
- Web calls: 48 search queries; one mentions 2005 (OPM federal holiday
  dates). No S3, `2005.csv`, BTS or Kaggle access.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
- Fewest experiments (58) and highest AI share (66.3%) of the group so far.
