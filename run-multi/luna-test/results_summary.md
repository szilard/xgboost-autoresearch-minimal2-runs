# Results summary: luna-test

Group luna-test: codex-cli 0.158.0, gpt-5.6-luna, effort max, 3 runs, sequential, started 2026-09-28.

| Run | Model | Effort | Experiments | Best Eval AUC | Holdout AUC | Gap (holdout - eval) | Total time | AI share | Status |
|---|---|---|---|---|---|---|---|---|---|
| luna-test-1 | gpt-5.6-luna | max | 65 (+ baseline) | 0.7667 (7e80331) | 0.7622 | -0.0045 | 2h00m45s | 46.8% | valid |
| luna-test-2 | gpt-5.6-luna | max | 71 (+ baseline) | 0.7614 (044cc63) | 0.7578 | -0.0036 | 2h00m38s | 58.0% | valid |
| luna-test-3 | gpt-5.6-luna | max | 81 (+ baseline) | 0.7569 (4c7b3d0) | 0.7513 | -0.0056 | 2h01m56s | 56.8% | valid |

## Statistics over the valid runs (3 of 3)

| | Mean | SD | Min | Median | Max |
|---|---|---|---|---|---|
| Holdout AUC | 0.7571 | 0.0055 | 0.7513 | 0.7578 | 0.7622 |
| Eval AUC | 0.7617 | 0.0049 | 0.7569 | 0.7614 | 0.7667 |
| Gap (holdout - eval) | -0.0046 | 0.0010 | -0.0056 | -0.0045 | -0.0036 |

SD is the sample standard deviation (n - 1).
