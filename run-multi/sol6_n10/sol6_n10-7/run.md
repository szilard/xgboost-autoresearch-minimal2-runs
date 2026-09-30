# sol6_n10-7

- **Status:** valid with a caveat - the agent read `prepare.py` (forbidden) during setup, no further access
- **Date:** 2026-09-30 (clock 04:16:28 -> 06:17:35 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 6.0 GB (6026031104 bytes), 0 processes killed at the cap.

## Caveat: the agent read prepare.py

At 04:14:29, in its first batch of setup reads, the agent ran four commands
in parallel, one of them

    cat prepare.py && cat train.py && cat .gitignore

alongside `cat program.md` - so it read `prepare.py` (which builds the
train/eval/holdout split from the source data) before it had seen the
restriction in program.md. leak_check.txt: CONTENT HITS 26 (all 26
distinctive lines of prepare.py are in the log). The agent disclosed it
itself in turn 1 ("I mistakenly opened the human-only `prepare.py` before
reading that restriction. I did not run, change, or use it") and again in
its final message. The rule is that the agent must not read it; the run was first excluded for this. Same failure as sol6_n10-4.

Re-classified on 2026-09-30 from excluded to valid with a caveat (user decision):
the agent read prepare.py but went no further - no command touched holdout.csv,
S3 or `2005.csv`, no holdout row is in the log, and the file gives nothing usable
without the source data. The four runs that read it (4, 7, 8, 9) do not score
higher than the others (mean holdout 0.7579 vs 0.7590) and their holdout-eval gap
is the same.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `sep30`, initialized results.tsv, disclosed the prepare.py read and asked
   us to confirm the tag and say go.
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn, stopping the clock itself at 06:17:35, 62 s after TIME IS UP.

No "keep going" was needed. The prepare.py disclosure was a real point that
"go" glossed over.

## Results

- results.tsv: 75 rows = baseline + 74 experiments (23 keep, 51 discard, 1 crash - a DART run that hit the training timeout)
- Best Eval AUC: 0.7626 at `3be07a8` ("450 trees per model in ensemble")
- Its Holdout AUC: 0.7565
- Gap (holdout - eval): -0.0061
- Time (report.txt): total 2h01m07s; XGBoost runs 0h55m27s (45.8%: training 6.8%, row-by-row eval 39.0%); AI 1h05m40s (54.2%)

## Validity checks

- **leak_check.txt: FAILED** (the caveat above) - CONTENT HITS 26, from the `cat prepare.py`
  above. No lines of the other forbidden files and no holdout rows in the log.
- Holdout vs eval gap: -0.0061, normal.
- diff-stat.txt: first commit to best commit touches `train.py` only (23+, 4-).
- Web calls: 44 search queries, none mentioning 2005, S3, BTS or Kaggle.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
