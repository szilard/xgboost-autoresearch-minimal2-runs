## Setup

- `Dockerfile` - the `agents2` image: Ubuntu 26.04, codex installed as the
  unprivileged user `ubuntu` (nothing AI as root), the Python packages, and a
  copy of [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2)
  with fresh git history (no upstream `.git`, no `results/`) and the data
  already prepared.

Runs are driven by the Claude Code skill `/xgb-run` (see [Running an
experiment](#running-an-experiment-xgb-run)), after the one-time build and
login below.

### Build

From the repo root:

```bash
docker build -t agents2 setup/
```

### Log in (once)

The ChatGPT login goes into the docker volume `codex-auth`:

```bash
docker run -it --rm -e CODEX_HOME=/home/ubuntu/.codex-auth \
  -v codex-auth:/home/ubuntu/.codex-auth agents2 bash -c \
  'codex login --device-auth && find "$CODEX_HOME" -mindepth 1 ! -name auth.json -exec rm -rf {} +'
```

`CODEX_HOME` is needed because `codex login` first deletes
`~/.codex/auth.json`, which in the image is a symlink into the volume. The
`find` leaves only `auth.json` in the volume. Check it with:

```bash
docker run --rm -v codex-auth:/v agents2 ls -la /v
```

### Running an experiment: `/xgb-run`

The project skill `.claude/skills/xgb-run/SKILL.md` runs one experiment end
to end. Start `claude` in this repo (inside tmux: a run takes ~3 hours) and
type:

```
/xgb-run <container-name> <model> [effort]
```

e.g. `/xgb-run codex-luna-1 gpt-5.6-luna` (effort defaults to `max`). It
only runs when invoked like this, never on its own. It:

- starts a new `agents2` container named `<container-name>`, with the
  `codex-auth` volume mounted
- runs codex with `codex exec` / `codex exec resume`, one command per turn:
  the README prompt, then "go", and "keep going" if it stops early; the
  harness enforces the 2-hour budget
- checks from the codex session log that the model and effort took effect
- runs the harness report, the ground truth scoring and the plot, and checks
  the run is valid (eval/holdout gap, train.py-only diff, no access to the
  holdout data)
- copies the results into `runs/<container-name>/` and adds a row to
  `runs/results_summary.md`, without committing anything - review and commit
  them yourself
- leaves the container up for inspection

`.claude/settings.json` pre-approves the docker commands and file writes a
run needs, so it can run unattended (also in auto mode), and denies
`docker volume rm` to protect the login.

### The container

This is what the skill starts:

```bash
docker run -dit --name <run> -v codex-auth:/home/ubuntu/.codex-auth agents2
```

Only `auth.json` is shared, through the symlink; sessions, history and config
stay in the container. Codex rewrites `auth.json` in place when it refreshes
the token, so the refreshed token lands in the volume.

Don't run `codex logout` in a container. To remove the login, run
`docker volume rm codex-auth`.
