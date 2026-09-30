# Run luna-test-3 (group luna-test, run 3 of 3)

| | |
|---|---|
| Agent | codex-cli 0.158.0 (`codex exec` / `codex exec resume`), ChatGPT login |
| Model | gpt-5.6-luna |
| Reasoning effort | max |
| turn_context (all turns) | gpt-5.6-luna, max, approval never, sandbox danger-full-access |
| Upstream minimal2 commit | 20e1f9850ca0ff4a2433ca63b48992dc057d4779 |
| Run tag / branch | sep29 |
| Date | 2026-09-29 (clock 03:10:30 -> 05:12:26 UTC) |
| Session id | 01a0eb22-dae0-7da2-bc70-a3592ece05ca |
| Driven by | `.claude/skills/xgb-multi/run_one.sh` (container deleted after copy) |

## Turns

| # | Sent | Outcome |
|---|---|---|
| 1 | `Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.` | Proposed tag `sep29` ("Please confirm sep29, and I'll create the branch and finish setup") |
| 2 | `go` | Created branch `sep29`, finished setup, started the clock without asking again, ran all experiments, stopped the clock itself at 2h01m56s |

The only question was the expected tag confirmation; "go" accepted `sep29`.

## Results

- Runs: 82 (baseline + 81 experiments): 29 keep (incl. baseline), 52 discard, 1 crash (carrier-hour interaction category list bug)
- Best Eval AUC: **0.7569** at `4c7b3d0` ("gamma 0.15 with tuned depth, sampling, and regularization"), baseline 0.7203
- Holdout AUC of `4c7b3d0`: **0.7513** (gap -0.0056). The best holdout AUC of the run is 0.7521 at `c3f4948` (Eval 0.7568)
- Timing (report.txt): total 2h01m56s; XGBoost runs 52m38s (43.2%); AI 1h09m18s (56.8%)

Final model: depth-wise trees (no lossguide), 200 trees, lr 0.025,
max_depth 16, min_child_weight 3, gamma 0.15, reg_lambda 2, reg_alpha 2.5,
subsample 0.95, colsample_bytree 0.65, max_cat_threshold 256; no new
features. The lowest score of the group: unlike runs 1 and 2 it never
switched to loss-guided growth, and unlike run 1 (and codex2-luna-1) it
never gained from calendar features.

## Validity checks

- Gap at the best commit: -0.0056; across all kept commits -0.0034 to -0.0057. PASS
- diff-stat.txt (first -> best commit): `train.py` only (10+, 3-). PASS
- leak_check.txt: 2 flagged calls, both edits of research-log.md whose text mentions "the human-only holdout" (a note to not read it) - harmless. CONTENT HITS 0. PASS
- Web calls (8): XGBoost docs, flight-delay papers, CatBoost target statistics, DART. No data downloads.

**Verdict: valid.**

## Notable

- Clock stopped by the agent 1m56s after the budget (the driver logged TIME IS UP at 05:10:58; the agent stopped at 05:12:26, well within the 15-min window). The last experiment ended ~14 min before the stop, as in runs 1 and 2.
- Most experiments of the group (81) and most discards (52).
