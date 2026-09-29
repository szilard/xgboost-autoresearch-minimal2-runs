# Run luna-test-1 (group luna-test, run 1 of 3)

| | |
|---|---|
| Agent | codex-cli 0.158.0 (`codex exec` / `codex exec resume`), ChatGPT login |
| Model | gpt-5.6-luna |
| Reasoning effort | max |
| turn_context (all turns) | gpt-5.6-luna, max, approval never, sandbox danger-full-access |
| Upstream minimal2 commit | 20e1f9850ca0ff4a2433ca63b48992dc057d4779 |
| Run tag / branch | sep28 |
| Date | 2026-09-28/29 (clock 22:28:18 -> 00:29:04 UTC) |
| Session id | 01a0ea21-07e5-7af3-ba33-9cc9b03b071c |
| Driven by | `.claude/skills/xgb-multi/run_one.sh` (container deleted after copy) |

## Turns

| # | Sent | Outcome |
|---|---|---|
| 1 | `Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.` | Created branch `sep28`, initialized results.tsv, asked for "go" to start the clock |
| 2 | `go` | Started the clock, ran all experiments, stopped the clock itself at 2h00m45s |

The agent's only question ("Say go when you want me to start") was the
expected confirmation; nothing was glossed over.

## Results

- Runs: 66 (baseline + 65 experiments): 30 keep (incl. baseline), 35 discard, 1 crash (DART, training timeout)
- Best Eval AUC: **0.7667** at `7e80331` ("seasonal features with reg_alpha 3"), baseline 0.7203
- Holdout AUC of `7e80331`: **0.7622** (gap -0.0045); it is also the best holdout AUC of the run
- Timing (report.txt): total 2h00m45s; XGBoost runs 1h04m12s (53.2%); AI 56m34s (46.8%)

Final model: loss-guided trees, 1200 trees, lr 0.025, max_leaves 512, gamma
0.01, reg_lambda 100, reg_alpha 3, colsample_bytree 0.7, max_cat_threshold
4, plus DayOfYear and its annual sin/cos.

## Validity checks

- Gap at the best commit: -0.0045; across all kept commits -0.0025 to -0.0050. PASS
- diff-stat.txt (first -> best commit): `train.py` only (21+, 3-). PASS
- leak_check.txt: 0 flagged commands (of 554 tool calls), CONTENT HITS 0 (no lines of the human-only scripts, no holdout-only rows). PASS
- Web calls (9): XGBoost docs, scikit-learn docs (target encoding, cyclical features), flight-delay and target-encoding papers. No data downloads.

**Verdict: valid.**

## Notable

- Clock stopped by the agent; the last experiment ended at 00:14:53, so the agent spent the last ~14 min without experiments before stopping (codex2-luna-1: ~19 min).
- Driver bug: driver-summary.json has two values each in `best_eval_auc` / `best_holdout_auc` (`0.7363\n0.7667`, `0.7324\n0.7622`). awk compared commit hashes numerically, and `7e80331` and `869e434` both parse as infinity. The correct values (from groundtruth_all.tsv) are 0.7667 / 0.7622. Only the summary is affected; driving, copying and the checks are not.
