# sol6_n10 — gpt-6-sol, effort max, 10 runs, codex-cli 0.159.0, 2026-09-29, container memory cap 24 GB (no swap)

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid |
|---|---|---|---|---|---|---|---|---|---|
| sol6_n10-1 | gpt-6-sol | max | 100 | 0.7618 (8eb7b32) | 0.7570 | -0.0048 | 2h00m32s | 49.6% | valid |
| sol6_n10-2 | gpt-6-sol | max | 73 | 0.7670 (fad5697) | 0.7611 | -0.0059 | 2h00m06s | 50.0% | valid |
| sol6_n10-3 | gpt-6-sol | max | 93 | 0.7640 (52303aa) | 0.7580 | -0.0060 | 2h00m51s | 38.5% | valid |
| sol6_n10-4 | gpt-6-sol | max | 81 | 0.7673 (e0e874d) | 0.7626 | -0.0047 | 2h00m39s | 37.2% | valid with caveat: agent read prepare.py during setup, no further access (leak check: 26 content hits) |
| sol6_n10-5 | gpt-6-sol | max | 83 | 0.7685 (cc135a1) | 0.7624 | -0.0061 | 2h00m33s | 49.9% | valid |
| sol6_n10-6 | gpt-6-sol | max | 71 | 0.7630 (78b7ef8) | 0.7583 | -0.0047 | 2h00m18s | 39.5% | valid |
| sol6_n10-7 | gpt-6-sol | max | 74 | 0.7626 (3be07a8) | 0.7565 | -0.0061 | 2h01m07s | 54.2% | valid with caveat: agent read prepare.py during setup, no further access (leak check: 26 content hits) |
| sol6_n10-8 | gpt-6-sol | max | 58 | 0.7572 (40f546a) | 0.7510 | -0.0062 | 2h00m24s | 66.3% | valid with caveat: agent read prepare.py during setup, no further access (leak check: 26 content hits) |
| sol6_n10-9 | gpt-6-sol | max | 65 | 0.7669 (0569a41) | 0.7614 | -0.0055 | 2h01m21s | 63.6% | valid with caveat: agent read prepare.py during setup, no further access (leak check: 27 content hits, 26 from prepare.py) |
| sol6_n10-10 | gpt-6-sol | max | 65 | 0.7639 (12b4005) | 0.7572 | -0.0067 | 2h01m31s | 64.2% | valid (used public solutions to the equivalent mlcourse.ai Kaggle task, see run.md) |

## Statistics

All 10 runs (6 clean + 4 with the prepare.py caveat):

| metric | count | mean | std dev | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 10 | 0.7585 | 0.0035 | 0.7510 | 0.7581 | 0.7626 |
| Eval AUC | 10 | 0.7642 | 0.0034 | 0.7572 | 0.7640 | 0.7685 |
| Gap (holdout - eval) | 10 | -0.0057 | 0.0007 | -0.0067 | -0.0060 | -0.0047 |

The 6 clean runs (1, 2, 3, 5, 6, 10):

| metric | count | mean | std dev | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 6 | 0.7590 | 0.0022 | 0.7570 | 0.7581 | 0.7624 |
| Eval AUC | 6 | 0.7647 | 0.0025 | 0.7618 | 0.7640 | 0.7685 |
| Gap (holdout - eval) | 6 | -0.0057 | 0.0008 | -0.0067 | -0.0060 | -0.0047 |

The 4 runs with the caveat (4, 7, 8, 9):

| metric | count | mean | std dev | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 4 | 0.7579 | 0.0053 | 0.7510 | 0.7590 | 0.7626 |
| Eval AUC | 4 | 0.7635 | 0.0047 | 0.7572 | 0.7648 | 0.7673 |
| Gap (holdout - eval) | 4 | -0.0056 | 0.0007 | -0.0062 | -0.0058 | -0.0047 |

Caveat runs: 4 (4, 7, 8, 9), all for the same reason - the agent read
`prepare.py` in its first batch of setup reads (in parallel with, or before,
`cat program.md`, so before it had seen the restriction), and disclosed it
itself. They were first excluded, then re-classified as valid with a caveat
(user decision, 2026-09-30): none went further (no holdout.csv, S3 or
`2005.csv` access, no holdout rows in the logs), prepare.py gives nothing
usable without the source data, their AUCs are not higher than the clean
runs' and their holdout-eval gap is the same. In holdout_auc.tsv they have
`valid` = `caveat`.

Notes:
- All clocks were stopped by the agent itself; no run was stopped by the driver.
- Run 4 needed one extra "go"; all others used only the README prompt and one "go". No "keep going" was needed in any run.
- The container peaked at 6.0-14.3 GB; no process was killed at the 24 GB cap in any run.
- Run 10 is valid by the rules, but used public solutions to the equivalent
  mlcourse.ai Kaggle flight-delays task (a solution gist, GitHub repos) for
  feature ideas - see sol6_n10-10/run.md. Runs 3 and 5 ran bts.gov- and
  kaggle.com-restricted searches but opened no such page.
