# sol6_n10-4

- **Status:** valid with a caveat - the agent read `prepare.py` (forbidden) during setup, no further access
- **Date:** 2026-09-29 (clock 21:10:25 -> 23:11:04 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep29` (proposed by the agent; it took the first "go" as approval)
- **Container:** 24 GB memory cap, no swap. Peak 14.3 GB (14349885440 bytes), 0 processes killed at the cap.

## Caveat: the agent read prepare.py

At 21:06:23, in its first batch of setup reads, the agent ran

    rg --files data | sort && cat .gitignore && sed -n '1,240p' harness.py && cat train.py && cat prepare.py

so the full content of `prepare.py` - which builds the train/eval/holdout
split from the source data - reached the agent before the clock started.
leak_check.txt: CONTENT HITS 26 (all 26 distinctive lines of prepare.py are in
the log). The agent noticed and disclosed it itself in turn 1 and again in
turn 2 ("I accidentally read `prepare.py`; a strict blind run would require a
fresh agent session"), and did not access it again. The rule is that the agent must not read it; the run was first excluded for this.

Re-classified on 2026-09-30 from excluded to valid with a caveat (user decision):
the agent read prepare.py but went no further - no command touched holdout.csv,
S3 or `2005.csv`, no holdout row is in the log, and the file gives nothing usable
without the source data. The four runs that read it (4, 7, 8, 9) do not score
higher than the others (mean holdout 0.7579 vs 0.7590) and their holdout-eval gap
is the same.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - preflight checks, results.tsv
   header, proposed tag `sep29` and asked us to confirm it; disclosed the
   prepare.py read.
2. "go" - the agent took this as approval of the tag, created branch
   `sep29`, and asked for a separate reply ("start") before starting the
   clock. It repeated the prepare.py disclosure.
3. "go" (extra, driver sent it because the clock had not started) - the
   agent started the clock and worked the full 2 hours, stopping the clock
   itself at 23:11:04, 31 s after TIME IS UP.

The run-tag question and the prepare.py disclosure were real points that
"go" glossed over. This is the first run of the group that needed an extra "go".

## Results

- results.tsv: 82 rows = baseline + 81 experiments (32 keep, 50 discard, 0 crash)
- Best Eval AUC: 0.7673 at `e0e874d` ("L1 regularization 9")
- Its Holdout AUC: 0.7626
- Gap (holdout - eval): -0.0047
- Time (report.txt): total 2h00m39s; XGBoost runs 1h15m46s (62.8%: training 19.4%, row-by-row eval 43.5%); AI 0h44m53s (37.2%).
  report.txt notes that runs overlapped (summed run time 1h15m47s, 1 s more).

## Validity checks

- **leak_check.txt: FAILED** (the caveat above) - CONTENT HITS 26, from the `cat prepare.py`
  above. No lines of the other forbidden files and no holdout rows in the log.
- Holdout vs eval gap: -0.0047, normal.
- diff-stat.txt: first commit to best commit touches `train.py` only (22+, 3-).
- Web calls: 71 search queries / page opens (XGBoost docs, flight-delay
  papers, OPM 2005 federal holidays). One search mentions "2005 BTS" in
  looking for papers. No S3 or `2005.csv` access.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
