# astra6_n10 — gpt-6-astra, effort max, 10 runs, codex-cli 0.159.0, 2026-10-01, container memory cap 24 GB (no swap)

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid |
|---|---|---|---|---|---|---|---|---|---|
| astra6_n10-1 | gpt-6-astra | max | 66 | 0.7652 (c1e763d) | 0.7598 | -0.0054 | 2h02m02s | 40.0% | valid |
| astra6_n10-2 | gpt-6-astra | max | 81 | 0.7657 (5851c0c) | 0.7604 | -0.0053 | 2h03m55s | 60.4% | valid (clock stopped by the driver after an OpenAI "model at capacity" error ~5 min before the end) |
| astra6_n10-3 | gpt-6-astra | max | 86 | 0.7713 (0f6bd05) | 0.7663 | -0.0050 | 2h02m10s | 58.1% | valid |
| astra6_n10-4 | gpt-6-astra | max | 77 | 0.7684 (6e0aed7) | 0.7631 | -0.0053 | 2h02m18s | 64.5% | valid with caveat: agent read prepare.py during setup (disclosed it), no further access (leak check: 27 content hits) |
| astra6_n10-5 | gpt-6-astra | max | 66 | 0.7651 (a8dea74) | 0.7589 | -0.0062 | 2h01m43s | 50.1% | valid with caveat: agent read prepare.py during setup (disclosed it), no further access (leak check: 26 content hits) |
| astra6_n10-6 | gpt-6-astra | max | 74 | 0.7712 (22dfab8) | 0.7656 | -0.0056 | 2h01m54s | 65.3% | valid |
| astra6_n10-7 | gpt-6-astra | max | 70 | 0.7644 (10d2bfa) | 0.7592 | -0.0052 | 2h00m41s | 61.4% | valid |
| astra6_n10-8 | gpt-6-astra | max | 66 | 0.7667 (bdfa919) | 0.7614 | -0.0053 | 2h02m04s | 69.5% | valid |
| astra6_n10-9 | gpt-6-astra | max | 76 | 0.7674 (3651943) | 0.7623 | -0.0051 | 2h01m59s | 58.9% | valid with caveat: agent read prepare.py during setup (disclosed it), no further access (leak check: 26 content hits) |
