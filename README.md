## Optimizing XGBoost Machine Learning Models with AI Agents

Running [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2) with various LLMs

This is a follow-up to [xgboost-autoresearch](https://github.com/szilard/xgboost-autoresearch).
Another follow-up project is [identical-runs-different-results](https://github.com/earino/identical-runs-different-results).


### How the runs are done

- Each run gets a fresh Docker container (`agents2` image): codex as the
  agent, on a ChatGPT subscription, and a clean copy of
  xgboost-autoresearch-minimal2 with no history and no earlier results, so
  the agent cannot see previous runs.
- The agent gets the prompt from the minimal2 README and then works on its
  own for 2 hours (enforced by the minimal2 harness): it edits `train.py`,
  runs experiments and keeps what improves the eval AUC.
- Afterwards every kept experiment is scored on a holdout set the agent never
  saw, and the run is checked for validity (eval/holdout gap, only
  `train.py` changed, no access to the holdout data).
- All of this is orchestrated by Claude Code with the project skill
  `/xgb-run`. Results go to `runs/<run>/`, one row per run in
  `results_summary.md`.

Setup and usage: [setup/README.md](setup/README.md).

Recommended machine (training XGBoost): m8i.2xlarge (8 cores, 32GB RAM)

