---
name: xgb-multi
description: Run the xgboost-autoresearch-minimal2 experiment with codex N times in a row (fresh agents2 container each, deleted afterwards) and write the results to run-multi/<run-group>/, with a group summary and a holdout AUC table.
argument-hint: <run-group> <model> <n-runs> [effort, default max]
disable-model-invocation: true
---

Arguments: $ARGUMENTS

They are RUN_GROUP, MODEL (the exact OpenAI slug, e.g. gpt-5.6-luna), N_RUNS
(a positive integer) and optionally REASONING_EFFORT (default: max). If any
of the first three is missing or N_RUNS isn't a positive integer, stop and
ask.

This is /xgb-run repeated N_RUNS times, with one difference: the mechanical
part of each run is done by `.claude/skills/xgb-multi/run_one.sh` (DRIVER
below), so every run gets exactly the same messages under the same rules.
Your job is to launch it, review each finished run, and write the run and
group files. Everything in /xgb-run about codex, the ChatGPT login (no API
keys, never `codex logout`) and "max" meaning the level literally named max
applies here too.

Run i (1..N_RUNS) is named `RUN_GROUP-i`: that is its container name and its
directory `run-multi/RUN_GROUP/RUN_GROUP-i/` (RUN_DIR below).

Run everything below without waiting on me, except where it says stop.

## Before the first run

1. Stop and tell me if `run-multi/RUN_GROUP/` already exists, or if any
   container named `RUN_GROUP-<number>` exists.
2. Check free disk space (`df -h /`). A run needs a few GB while its
   container exists; tell me if there's less than ~15 GB free, and stop.
3. Tell me the plan in one line (group, model, effort, N_RUNS, ~2.5-3 h per
   run, sequential) and carry on.

## Each run, one after another

Runs are strictly sequential: each uses all 8 cores, like the single runs.

4. Launch DRIVER in the background (it takes ~2.5-3 h):

       .claude/skills/xgb-multi/run_one.sh RUN_GROUP-i MODEL REASONING_EFFORT run-multi/RUN_GROUP/RUN_GROUP-i

   It starts the container, runs the setup checks of /xgb-run steps 1-5,
   checks that MODEL has a level named REASONING_EFFORT, sends the README
   prompt, then "go" until the harness clock starts and "keep going" while
   it has time left, stops codex and the clock itself if the agent hasn't
   stopped it 15 min after TIME IS UP, then runs the report, the ground
   truth scoring and the plot, runs `leak_check.py` in the container, copies
   the results out, and deletes the container. The session log is archived
   as `codex-session.jsonl.gz`, slimmed by `../xgb-run/slim_session.py`
   (encrypted reasoning dropped, account ids redacted); of turns/ only each
   turn's final message and stderr are kept.
   Everything it sends and sees is in RUN_DIR/driver.log.

   Wait for it to finish (you are notified; schedule a ~1 h fallback wakeup,
   and look at the tail of driver.log on each wakeup).

5. When it finishes, by exit code:
   - **2** (precondition failed: image, volume, container name, login, no
     such effort level): stop the whole group and tell me what driver.log
     says. Don't start further runs.
   - **0** or **1**: start the next run right away (step 4), then review
     this one (step 6) while the next one runs. Exit 1 means the run failed
     partway (driver-summary.json has the reason): record it as excluded.

6. Review run i from RUN_DIR (the container is gone, so this is all there
   is):
   - driver-summary.json and driver.log: turns sent, who stopped the clock,
     failures, NOTE lines about an unexpected repo state.
   - turns/*.txt: the agent's final message of each turn. If the agent asked
     a real question that "go" or "keep going" glossed over, say so.
   - The validity checks of /xgb-run step 13:
     - gap between the best commit's Holdout AUC and its Eval AUC (from
       groundtruth_all.tsv): below -0.01 means it overfit eval; holdout
       clearly above eval is suspicious;
     - diff-stat.txt (first commit to best commit) touches train.py only;
     - leak_check.txt: CONTENT HITS must be 0, and look at each listed
       command yourself - listing file names is fine, reading or running a
       forbidden file (or fetching 2005.csv) is not. Look at the web calls
       in codex-session.jsonl.gz too.
   If a check fails, the run is excluded: say so plainly in run.md and the
   summary, and don't present its AUC as an achievement.
   - Write RUN_DIR/run.md with what /xgb-run step 14 asks for (codex
     version, model, effort and turn_context as confirmed, upstream minimal2
     commit, run tag, date, turns and what was sent in each, number of
     experiments, best Eval AUC and its commit, its Holdout AUC, the
     validity checks, anything notable), plus how the clock was stopped.
   - Add the run's row to `run-multi/RUN_GROUP/results_summary.md` and
     `run-multi/RUN_GROUP/holdout_auc.tsv` (below).

## Group files

`run-multi/RUN_GROUP/results_summary.md`: a header line with the group,
model, effort, N_RUNS, codex version and date, then one row per run with
the same columns as `runs/results_summary.md` (run, model, effort,
experiments, best Eval AUC (commit), its Holdout AUC, gap, total time, AI
share, valid or excluded - with the reason). Once all runs are done, add
the statistics over the valid runs: count, mean, standard deviation, min,
median and max of the Holdout AUC, the Eval AUC and the gap.

`run-multi/RUN_GROUP/holdout_auc.tsv`: one line per run, for plotting
later, tab-separated with this header:

    run	best_commit	eval_auc	holdout_auc	gap	experiments	valid

Excluded runs stay in it with `valid` = `no` (empty AUCs if they have
none), so the plotting step decides what to filter.

## At the end

7. When all N_RUNS runs are done, give me a short summary: the statistics,
   how many runs were excluded and why, and anything that went wrong or
   differed between runs (extra "go"s, runs stopped by the driver).

Don't commit or push anything - I review and commit the results myself.

## Notes

- Containers are deleted by DRIVER after the copy, to save disk. If DRIVER
  says it did NOT delete one (essential files missing), leave it and tell
  me. Never remove the `codex-auth` volume.
- Don't change DRIVER's rules (messages, limits, timings) in the middle of a
  group: every run of a group must be driven the same way. If something in
  DRIVER is broken, stop and tell me.
- If codex hits a usage limit, DRIVER retries a failed turn after 5 min, up
  to 3 times in a row, then fails the run (excluded). If two runs in a row
  fail like that, stop the group and tell me rather than burning through
  the remaining runs.
