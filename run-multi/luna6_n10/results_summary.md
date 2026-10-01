# luna6_n10 — gpt-6-luna, effort max, 10 runs, codex-cli 0.159.0, 2026-09-30, container memory cap 24 GB (no swap)

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid |
|---|---|---|---|---|---|---|---|---|---|
| luna6_n10-1 | gpt-6-luna | max | 79 | 0.7652 (993b867) | 0.7598 | -0.0054 | 2h00m17s | 54.7% | valid |
| luna6_n10-2 | gpt-6-luna | max | 69 | 0.7503 (6eba65f) | 0.7465 | -0.0038 | 2h00m18s | 65.6% | valid (needed an extra "go") |
| luna6_n10-3 | gpt-6-luna | max | 80 | 0.7621 (adccf54) | 0.7557 | -0.0064 | 2h00m09s | 53.4% | valid |
| luna6_n10-4 | gpt-6-luna | max | 56 | 0.7382 (31ee1bc) | 0.7348 | -0.0034 | 2h00m10s | 71.0% | valid |
| luna6_n10-5 | gpt-6-luna | max | 58 | 0.7540 (4e521f0) | 0.7496 | -0.0044 | 2h00m13s | 59.0% | valid |
| luna6_n10-6 | gpt-6-luna | max | 80 | 0.7628 (26de1ad) | 0.7572 | -0.0056 | 1h59m39s | 56.9% | valid |
| luna6_n10-7 | gpt-6-luna | max | 71 | 0.7597 (5a6da1e) | 0.7550 | -0.0047 | 2h00m28s | 56.6% | valid |
| luna6_n10-8 | gpt-6-luna | max | 67 | 0.7518 (118a7a6) | 0.7469 | -0.0049 | 2h00m43s | 66.4% | valid |
| luna6_n10-9 | gpt-6-luna | max | 65 | 0.7594 (72ddc2a) | 0.7543 | -0.0051 | 2h00m48s | 62.2% | valid |
| luna6_n10-10 | gpt-6-luna | max | 70 | 0.7479 (af9b4d9) | 0.7437 | -0.0042 | 2h00m11s | 59.7% | valid |

## Statistics over the valid runs (10 of 10)

| metric | count | mean | std dev | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 10 | 0.7504 | 0.0076 | 0.7348 | 0.7520 | 0.7598 |
| Eval AUC | 10 | 0.7551 | 0.0083 | 0.7382 | 0.7567 | 0.7652 |
| Gap (holdout - eval) | 10 | -0.0048 | 0.0009 | -0.0064 | -0.0048 | -0.0034 |

Notes:
- All 10 runs are valid: no run read prepare.py or any other forbidden file; the leak-check content hits (runs 1, 5-10) are all the `import matplotlib.pyplot as plt` line from scikit-learn docs pages.
- All clocks were stopped by the agent itself; no run was stopped by the driver.
- Run 2 needed one extra "go"; all others used only the README prompt and one "go". No "keep going" was needed in any run.
- The container peaked at 7.0-12.2 GiB; no process was killed at the 24 GB cap in any run.
- Wide spread compared with sol6_n10 (gpt-6-sol): holdout 0.7348-0.7598 here vs 0.7510-0.7626.
- No run's best model uses an ensemble or early stopping; 5 runs tried target encoding (all discarded).
