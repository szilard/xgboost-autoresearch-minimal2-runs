# Run luna-test-2 (group luna-test, run 2 of 3)

| | |
|---|---|
| Agent | codex-cli 0.158.0 (`codex exec` / `codex exec resume`), ChatGPT login |
| Model | gpt-5.6-luna |
| Reasoning effort | max |
| turn_context (all turns) | gpt-5.6-luna, max, approval never, sandbox danger-full-access |
| Upstream minimal2 commit | 20e1f9850ca0ff4a2433ca63b48992dc057d4779 |
| Run tag / branch | sep29 |
| Date | 2026-09-29 (clock 00:49:50 -> 02:50:28 UTC) |
| Session id | 01a0eaa1-b0fc-74a3-b493-34fef6d4716a |
| Driven by | `.claude/skills/xgb-multi/run_one.sh` (container deleted after copy) |

## Turns

| # | Sent | Outcome |
|---|---|---|
| 1 | `Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.` | Proposed tag `sep29` ("Confirm sep29, or provide another tag") |
| 2 | `go` | Created branch `sep29`, initialized results.tsv, asked for confirmation to start the clock |
| 3 | `go` | Started the clock, ran all experiments, stopped the clock itself at 2h00m38s |

Both questions were the expected confirmations (tag, clock start); "go"
accepted the proposed tag. Same pattern as codex2-luna-1; luna-test-1 did
setup and tag in one turn and needed a single "go".

## Results

- Runs: 72 (baseline + 71 experiments): 32 keep (incl. baseline), 39 discard, 1 crash (DART, training timeout)
- Best Eval AUC: **0.7614** at `044cc63` ("categorical feature weights 4x numeric"), baseline 0.7203
- Holdout AUC of `044cc63`: **0.7578** (gap -0.0036); it is also the best holdout AUC of the run
- Timing (report.txt): total 2h00m38s; XGBoost runs 50m41s (42.0%); AI 1h09m57s (58.0%)

Final model: loss-guided hist trees, 700 trees, lr 0.0286, max_leaves 575,
min_child_weight 1, reg_lambda 4, colsample_bytree 0.8, colsample_bylevel
0.9, max_cat_threshold 3, and `feature_weights` giving the categorical
columns 4x the sampling weight of the numeric ones. No new features (unlike
luna-test-1 and codex2-luna-1, which gained from calendar features).

## Validity checks

- Gap at the best commit: -0.0036; across all kept commits -0.0025 to -0.0058. PASS
- diff-stat.txt (first -> best commit): `train.py` only (12+, 4-). PASS
- leak_check.txt: 1 flagged call, a `web.run` find-in-page for "reg_alpha"/"L1" in XGBoost docs (matched the `find` pattern) - harmless. CONTENT HITS 0. PASS
- Web calls (9): XGBoost docs, flight-delay papers, CatBoost target statistics, LightGBM leaf-wise growth. No data downloads.

**Verdict: valid.**

## Notable

- Clock stopped by the agent, 38 s after the budget; the last experiment ended ~14 min before the stop (luna-test-1: ~14 min, codex2-luna-1: ~19 min).
- driver-summary.json values are correct in this run (the awk hash-comparison bug from luna-test-1 did not trigger: no second commit hash that parses as a number).
