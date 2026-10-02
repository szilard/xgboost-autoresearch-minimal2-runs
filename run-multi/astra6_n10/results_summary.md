# astra6_n10 — gpt-6-astra, effort max, 10 runs, codex-cli 0.159.0, 2026-10-01, container memory cap 24 GB (no swap)

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid |
|---|---|---|---|---|---|---|---|---|---|
| astra6_n10-1 | gpt-6-astra | max | 66 | 0.7652 (c1e763d) | 0.7598 | -0.0054 | 2h02m02s | 40.0% | valid |
| astra6_n10-2 | gpt-6-astra | max | 81 | 0.7657 (5851c0c) | 0.7604 | -0.0053 | 2h03m55s | 60.4% | valid (clock stopped by the driver after an OpenAI "model at capacity" error ~5 min before the end) |
| astra6_n10-3 | gpt-6-astra | max | 86 | 0.7713 (0f6bd05) | 0.7663 | -0.0050 | 2h02m10s | 58.1% | valid |
| astra6_n10-4 | gpt-6-astra | max | 77 | 0.7684 (6e0aed7) | 0.7631 | -0.0053 | 2h02m18s | 64.5% | valid with caveat: agent read prepare.py during setup (disclosed it), no further access (leak check: 27 content hits) |
