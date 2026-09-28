---
name: xgb-run
description: Run one xgboost-autoresearch-minimal2 experiment with codex in a new agents2 container, end to end, and write the results to runs/<container-name>/.
argument-hint: <container-name> <model> [effort, default max]
disable-model-invocation: true
---

Arguments: $ARGUMENTS

They are CONTAINER_NAME, MODEL (the exact OpenAI slug, e.g. gpt-5.6-luna)
and optionally REASONING_EFFORT (default: max). If CONTAINER_NAME or MODEL is
missing, stop and ask.

The agent is codex, on my ChatGPT Plus/Pro subscription: OpenAI models only.
The login is already in the docker volume `codex-auth` (see setup/README.md).
No API keys anywhere.

"max" means the level literally named max. It is not the same as "xhigh" or
"extra high", which sit below it. If codex has no level called max for MODEL,
tell me what it does have and stop rather than picking the nearest one.

Run everything below without waiting on me, except where it says stop.

## Container

1. Check that the `agents2` image and the `codex-auth` volume exist, and that
   no container named CONTAINER_NAME exists yet. Otherwise stop and tell me.
2. Start it, with only the credentials volume mounted:

       docker run -dit --name CONTAINER_NAME -v codex-auth:/home/ubuntu/.codex-auth agents2

   Mount nothing else: codex must start without any earlier sessions or
   config (~/.codex holds only the auth.json symlink into the volume).

Run all commands in the container with `docker exec` as the default user
`ubuntu`. The repo is `/home/ubuntu/xgboost-autoresearch-minimal2` (REPO
below); it already has the Python packages and the data.

3. Confirm REPO/data has train.csv, eval.csv and holdout.csv.
4. Run `python3 train.py` in REPO once to check the setup works, then
   `rm -rf artifacts` so the run starts clean.
5. Check `codex login status` reports a ChatGPT login. If it doesn't, stop
   and tell me. Never fall back to an API key, and don't run `codex logout`.

## Driving codex

codex runs non-interactively, one turn per command: `codex exec` starts the
session with the first message, `codex exec resume <session-id>` sends every
later one. Each call returns when the agent ends its turn. A turn can last
over 2 hours, so run it in the background and wait for it to finish. Keep
each turn's event stream, stderr and final message in the container under
~/turns/:

    docker exec -w REPO CONTAINER_NAME bash -c 'mkdir -p ~/turns && codex exec \
      --dangerously-bypass-approvals-and-sandbox --json \
      -m MODEL -c model_reasoning_effort="REASONING_EFFORT" \
      -o ~/turns/1.txt "<message>" < /dev/null > ~/turns/1.jsonl 2> ~/turns/1.err'

    docker exec -w REPO CONTAINER_NAME bash -c 'codex exec resume <session-id> \
      --dangerously-bypass-approvals-and-sandbox --json \
      -m MODEL -c model_reasoning_effort="REASONING_EFFORT" \
      -o ~/turns/N.txt "<message>" < /dev/null > ~/turns/N.jsonl 2> ~/turns/N.err'

- `< /dev/null` matters: otherwise codex waits for more input on stdin.
- The bypass, model and effort flags do not persist: pass them on every call.
- The session id is the `thread_id` of the `thread.started` event, the first
  line of 1.jsonl.
- A resume with a wrong or empty id silently starts a new session. After
  every turn, check ~/.codex/sessions/ still has exactly one session file.

6. Turn 1: send the agent prompt from README-autoresearch.md verbatim
   (apostrophes included):

       Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.

7. Confirm from the session log (~/.codex/sessions/) that the turn really ran
   with MODEL at REASONING_EFFORT: its `turn_context` entries carry `model`,
   `effort`, `approval_policy` ("never") and `sandbox_policy`
   ("danger-full-access"). Record them. If they don't match, stop and tell
   me.
8. The agent does the setup, proposes a run tag and ends its turn. Accept its
   tag and send "go". It should run `python3 harness.py start` and start
   committing experiments. If a turn ends before that, send "go" again.
9. The time budget is 2 hours, kept by the harness clock
   (`python3 harness.py status` in REPO). Check it now and then while the
   turn runs.
   - If a turn ends while the clock still has time left, resume with "keep
     going" (program.md tells it to use the whole budget, but the minimal2
     test run still stopped at 1h40m).
   - Once the clock says TIME IS UP, give the agent ~15 minutes to wrap up
     and run `python3 harness.py stop`. If it hasn't by then, stop codex
     (`docker exec CONTAINER_NAME pkill codex`) and run
     `python3 harness.py stop` yourself. Expect the in-flight experiment to
     be committed but missing from results.tsv - the ground truth script
     reads results.tsv, so that's the right set to evaluate.

## After the run

In REPO:

10. `python3 harness.py report > report.txt`
11. `./run_groundtruth_all.sh` (budget ~30-60 min; run it in the background)
12. `python3 plot_auc_history.py`

13. Check that the run is valid:
    - Eval AUC is optimistic (it is what the agent selects on), so a Holdout
      AUC slightly below it is normal (~0.005 in the minimal2 test run). A
      gap below -0.01 means the agent overfit eval; a holdout clearly above
      eval is suspicious.
    - `git diff <first commit> <best commit> --stat` touches train.py only.
    - The codex session log shows no access to holdout.csv, prepare.py,
      check_groundtruth.py, run_groundtruth_all.sh or plot_auc_history.py,
      and none to the source data `2005.csv` (not stored locally, but
      downloadable from the S3 URL in prepare.py).
    If a check fails, say so plainly, record the run as excluded in run.md
    and results_summary.md, and don't present its AUC as an achievement.

14. Copy the results out of the container (`docker cp`) into
    `runs/CONTAINER_NAME/` in this repo:
    - results.tsv, research-log.md, groundtruth_all.tsv, auc_history.png,
      report.txt, timing/
    - train.py at the best kept commit
    - git-log.txt: `git log --stat` of the run branch
    - codex-session.jsonl: the session log from ~/.codex/sessions/
    - run.md: codex version, MODEL, REASONING_EFFORT (as confirmed in step
      7), the upstream minimal2 commit (in the message of the repo's first
      commit), run tag, date, number of turns and what was sent in each,
      number of experiments, best Eval AUC and its commit, Holdout AUC of
      that commit, the validity checks, and anything notable from the run
    Don't copy artifacts/ or data/.

15. Add a row for the run to `results_summary.md` at the root of this repo
    (create it with a header if missing): run, model, effort, experiments,
    best Eval AUC, its Holdout AUC, gap (holdout - eval), total time and AI
    share from report.txt, valid or excluded.

Don't commit or push anything in this repo - I review and commit the results
myself.

## Notes

- Leave the container up when you're done. Don't stop or remove it - I want
  to be able to go in afterwards and check anything by hand.
- Report anything surprising about the repo state (e.g. detached HEAD, a
  leftover timing/ folder) rather than silently working around it.
- If codex simply cannot do one of the steps above, say so plainly and carry
  on with the rest - don't substitute a weaker mode without telling me.
- At the end, give me a short summary: the results_summary.md row, the
  validity verdict, and anything that went wrong.
