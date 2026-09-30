# sol6_n10 — gpt-6-sol, effort max, 10 runs, codex-cli 0.159.0, 2026-09-29, container memory cap 24 GB (no swap)

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid |
|---|---|---|---|---|---|---|---|---|---|
| sol6_n10-1 | gpt-6-sol | max | 100 | 0.7618 (8eb7b32) | 0.7570 | -0.0048 | 2h00m32s | 49.6% | valid |
| sol6_n10-2 | gpt-6-sol | max | 73 | 0.7670 (fad5697) | 0.7611 | -0.0059 | 2h00m06s | 50.0% | valid |
| sol6_n10-3 | gpt-6-sol | max | 93 | 0.7640 (52303aa) | 0.7580 | -0.0060 | 2h00m51s | 38.5% | valid |
| sol6_n10-4 | gpt-6-sol | max | 81 | 0.7673 (e0e874d) | 0.7626 | -0.0047 | 2h00m39s | 37.2% | **excluded**: agent read prepare.py during setup (leak check: 26 content hits) |
| sol6_n10-5 | gpt-6-sol | max | 83 | 0.7685 (cc135a1) | 0.7624 | -0.0061 | 2h00m33s | 49.9% | valid |
| sol6_n10-6 | gpt-6-sol | max | 71 | 0.7630 (78b7ef8) | 0.7583 | -0.0047 | 2h00m18s | 39.5% | valid |
| sol6_n10-7 | gpt-6-sol | max | 74 | 0.7626 (3be07a8) | 0.7565 | -0.0061 | 2h01m07s | 54.2% | **excluded**: agent read prepare.py during setup (leak check: 26 content hits) |
