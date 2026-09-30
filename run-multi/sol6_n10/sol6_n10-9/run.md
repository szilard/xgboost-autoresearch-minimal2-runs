# sol6_n10-9

- **Status:** EXCLUDED - the agent read `prepare.py` (forbidden) during setup
- **Date:** 2026-09-30 (clock 09:00:33 -> 11:01:55 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep30` (proposed by the agent, not confirmed by us)
- **Container:** 24 GB memory cap, no swap. Peak 12.6 GB (12612214784 bytes), 0 processes killed at the cap.

## Why it is excluded

At 08:55:08, in its first batch of setup reads, the agent ran three commands
in parallel, one of them

    cat .gitignore && rg --files data && sed -n '1,240p' prepare.py && sed -n '1,200p' train.py

alongside `cat program.md` - so it read `prepare.py` (which builds the
train/eval/holdout split and contains the S3 URL of the source data) before
it had seen the restriction in program.md. leak_check.txt: CONTENT HITS 27 -
all 26 distinctive lines of prepare.py, plus one false positive (`import
matplotlib.pyplot as plt`, from scikit-learn docs pages the agent opened).
The agent disclosed the read itself in turn 1 ("I accidentally opened
`prepare.py` during the initial survey before seeing its restriction in
`program.md`") and again in its final message. No later command touches S3,
`2005.csv` or any URL download. The rule is that the agent must not read it,
so the run's AUCs are not a result. Same failure as sol6_n10-4, -7 and -8.

The numbers below are recorded for completeness only.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - preflight checks, disclosed the
   prepare.py read, asked us to confirm `sep30` or give another tag.
2. "go" - the agent created branch `sep30`, started the clock and worked the
   full 2 hours in this single turn, stopping the clock itself at 11:01:55,
   67 s after TIME IS UP.

No "keep going" was needed. The run-tag question and the prepare.py
disclosure were real points that "go" glossed over.

## Results (not valid)

- results.tsv: 66 rows = baseline + 65 experiments (22 keep, 44 discard, 0 crash)
- Best Eval AUC: 0.7669 at `0569a41` ("L2 regularization 20 with L1 four")
- Its Holdout AUC: 0.7614
- Gap (holdout - eval): -0.0055
- Time (report.txt): total 2h01m21s; XGBoost runs 0h44m08s (36.4%: training 3.5%, row-by-row eval 32.9%); AI 1h17m13s (63.6%)

## Validity checks

- **leak_check.txt: FAILED** - CONTENT HITS 27 (26 from the prepare.py read
  above, 1 false positive). No lines of the other forbidden files and no
  holdout rows in the log.
- Holdout vs eval gap: -0.0055, normal.
- diff-stat.txt: first commit to best commit touches `train.py` only (9+, 2-).
- Web calls: 40 search queries; opened pages were XGBoost docs and
  flight-delay papers (Berkeley iSchool, MDPI, Wiley). One search was
  restricted to kaggle.com and two mention 2005; no Kaggle page opened, no
  S3, `2005.csv` or BTS access.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
