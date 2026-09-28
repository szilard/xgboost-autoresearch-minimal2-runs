## Setup

- `Dockerfile` - the `agents2` image: Ubuntu 26.04, codex installed as the
  unprivileged user `ubuntu` (nothing AI as root), the Python packages, and a
  copy of [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2)
  with fresh git history (no upstream `.git`, no `results/`) and the data
  already prepared.
- `prompt-setup_container_for_xgb_agent_run.txt` - the prompt that drives a
  run end to end in a new container.

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

### Run

```bash
docker run -dit --name <run> -v codex-auth:/home/ubuntu/.codex-auth agents2
```

Only `auth.json` is shared, through the symlink; sessions, history and config
stay in the container. Codex rewrites `auth.json` in place when it refreshes
the token, so the refreshed token lands in the volume.

Don't run `codex logout` in a container. To remove the login, run
`docker volume rm codex-auth`.
