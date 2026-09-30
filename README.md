# Optimizing XGBoost Machine Learning Models with AI Agents: Runs

**TL;DR:** Runs [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2) (an AI coding agent autonomously tunes an XGBoost model, and its gains are then checked on a held-out test set it never sees) with various agents/LLMs, once or repeatedly, fully automated. Repeated runs show how much the result of the same agent/LLM varies from run to run.

This is the orchestrator for [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2), itself a follow-up to [xgboost-autoresearch](https://github.com/szilard/xgboost-autoresearch).
Another follow-up project is [identical-runs-different-results](https://github.com/earino/identical-runs-different-results) and the corresponding [arXiv paper](https://arxiv.org/abs/2609.33812).

How a run works (the task, the agent's loop and the guardrails are described in the [xgboost-autoresearch-minimal2 README](https://github.com/szilard/xgboost-autoresearch-minimal2)):

- **Isolation:** each run gets a fresh Docker container (`agents2` image) with a clean copy of `xgboost-autoresearch-minimal2`: no history and no earlier results, so the agent cannot see previous runs. Only the agent's login is shared with the container.
- **Agent:** currently codex, on a ChatGPT subscription (OpenAI models, at a chosen reasoning effort, e.g. `max`). It gets the prompt from the `xgboost-autoresearch-minimal2` README and then works on its own for 2 hours, enforced by the harness clock; the orchestrator only sends "go" to start and "keep going" if it stops early.
- **Ground truth:** after the run, every kept model is scored on the holdout set (`groundtruth_all.tsv`, `auc_history.png`).
- **Validity checks:** the model and effort actually used (from the agent's session log), the eval/holdout gap, only `train.py` changed, and no access to the holdout data or the human-only scripts (also searched for their content in the agent's commands and outputs). Runs that fail a check are recorded as excluded.
- **Orchestration:** by Claude Code, with the project skill `/xgb-multi <group> <model> <n-runs> [effort]`: N sequential runs of the same setup (N = 1 for a single run), each driven identically by a script, results in `run-multi/<group>/<group>-<i>/`, plus a group `results_summary.md` (with mean/sd/min/median/max over the valid runs) and `holdout_auc.tsv` (one line per run, for plots such as histograms). Claude reviews each run and writes up the results.

Each run's folder has the agent's `results.tsv`, `research-log.md` and final `train.py`, the ground truth scores and plot, the harness timing report, the git log, the agent's session log (gzipped, with the encrypted reasoning dropped and account ids redacted) and a `run.md` with the settings, the turns sent, the validity checks and anything notable.

Results so far (effort `max`, 24 GB container memory cap): [sol6_n10](run-multi/sol6_n10/results_summary.md), 10 runs of gpt-6-sol, and [luna6_n10](run-multi/luna6_n10/results_summary.md), gpt-6-luna (in progress). Plots over all groups: [run-multi/SUMMARY/](run-multi/SUMMARY/) (made by `tools/plot_holdout_auc.py`). Earlier runs - the first test group luna-test (3 runs of gpt-5.6-luna, before the memory cap) and a single run driven live by Claude with the retired `/xgb-run` skill - are in [archive/](archive/).

Recommended machine: m8i.2xlarge (8 cores, 32 GB RAM). The per-run time limits depend on the hardware, so compare results only across runs on the same machine type. Runs are sequential, since each uses all cores.

Setup and usage: [setup/README.md](setup/README.md).
