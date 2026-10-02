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
| astra6_n10-10 | gpt-6-astra | max | 73 | 0.7633 (8096331) | 0.7591 | -0.0042 | 2h02m40s | 59.0% | valid |

## Statistics

All 10 runs (7 clean + 3 with the prepare.py caveat):

| metric | count | mean | std dev | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 10 | 0.7616 | 0.0027 | 0.7589 | 0.7609 | 0.7663 |
| Eval AUC | 10 | 0.7669 | 0.0027 | 0.7633 | 0.7662 | 0.7713 |
| Gap (holdout - eval) | 10 | -0.0053 | 0.0005 | -0.0062 | -0.0053 | -0.0042 |

The 7 clean runs (1, 2, 3, 6, 7, 8, 10):

| metric | count | mean | std dev | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 7 | 0.7617 | 0.0030 | 0.7591 | 0.7604 | 0.7663 |
| Eval AUC | 7 | 0.7668 | 0.0032 | 0.7633 | 0.7657 | 0.7713 |
| Gap (holdout - eval) | 7 | -0.0051 | 0.0005 | -0.0056 | -0.0053 | -0.0042 |

The 3 runs with the caveat (4, 5, 9):

| metric | count | mean | std dev | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 3 | 0.7614 | 0.0022 | 0.7589 | 0.7623 | 0.7631 |
| Eval AUC | 3 | 0.7670 | 0.0017 | 0.7651 | 0.7674 | 0.7684 |
| Gap (holdout - eval) | 3 | -0.0055 | 0.0006 | -0.0062 | -0.0053 | -0.0051 |

Caveat runs: 3 (4, 5, 9), all for the same reason as in sol6_n10 - the
agent read `prepare.py` in its first batch of setup reads (in parallel with
its first `cat program.md`, so before it had seen the restriction) and
disclosed it itself, in turn 1 and in research-log.md. None went further (no
holdout.csv, S3 or `2005.csv` access, no holdout rows in the logs, train.py
reads only train.csv), their AUCs are not higher than the clean runs' and
their holdout-eval gap is the same. In holdout_auc.tsv they have `valid` =
`caveat`. No run was excluded.

Notes:
- Clocks: stopped by the agent in 9 runs. In run 2 codex failed the turn
  ~5 min before the end with an OpenAI "Selected model is at capacity" error;
  the driver waited 300 s to retry, TIME IS UP had arrived, so it stopped the
  clock (the agent's last experiment got no results row).
- All runs used only the README prompt and one "go". No extra "go" and no
  "keep going" was needed in any run.
- The container peaked at 4.6-13.3 GB; no process was killed at the 24 GB cap in any run.
- Run 1 was launched twice: the first launch was aborted during the driver's
  setup check (before codex got any prompt) because my background task had a
  2-hour limit; it was restarted from scratch, detached.
- Runs 2 and 3 were started by hand after a hold to check the ChatGPT usage
  limit (about 11-12% of the weekly limit per run); after a usage reset,
  runs 4-10 ran back to back. Wall time per run 2h14m-2h23m (mean 2h17m).
- Run 9 re-ran its best commit as a "final confirmation", so `3651943` has
  two rows in results.tsv and driver-summary.json's best AUC fields hold the
  value twice (cosmetic).
- Runs 3 and 10 ran a transtats.bts.gov-restricted search but opened no such
  page.
- Compared with sol6_n10 (gpt-6-sol): holdout mean 0.7616 vs 0.7585, with a
  smaller spread (sd 0.0027 vs 0.0035); one run of astra beats one run of
  sol with probability 0.76 (ties half; 90% bootstrap interval 0.55-0.93), see
  SUMMARY/holdout_auc_pairwise.png.
- Recurring ideas in the best models: a categorical flight date (every run),
  airport coordinates from an MDS embedding of the training route graph
  (runs 3, 5, 8), small XGBoost ensembles / soft-voting blends (runs 1, 3, 6,
  7, 8, 9).
