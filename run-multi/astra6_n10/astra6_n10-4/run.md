# astra6_n10-4

- **Status:** valid with caveat - the agent read `prepare.py` during setup (accidentally, before reading program.md; it disclosed this itself); no further access
- **Date:** 2026-10-02 (clock 07:21:41 -> 09:23:59 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 13.1 GB (13078646784 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and research-log.md and asked for "go".
   Its message ended with a setup note: "I accidentally read `prepare.py`
   before seeing its restriction. This is documented in the research log;
   it was not executed, and no held-out data was accessed."
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 09:22:33; it stopped the clock itself at
   09:23:59 (turn ended 09:25:35).

No "keep going" was needed. The "go" carried on past the agent's
prepare.py disclosure (it was a report, not a question).

## Results

- results.tsv: 78 rows = baseline + 77 experiments (20 keep, 53 discard, 5 crash - 2 crashes and 3 training timeouts)
- Best Eval AUC: **0.7684** at `6e0aed7` ("colsample_bytree=0.8 instead of colsample_bynode=0.8"), up from the 0.7203 baseline. The agent's final selected commit `a43b44b` (depth cap 16) ties at 0.7684 eval / 0.7629 holdout; the driver takes the first.
- Model: a single XGBoost model with 3 parallel trees per round (600 rounds), loss-guided, max_leaves 64, learning rate 0.05, min_child_weight 20, reg_lambda 100, reg_alpha 5, max_bin 1024, colsample_bytree 0.8; native categoricals for carrier, origin, destination, a month-day categorical date and a 53-level week block; month/day-of-month/weekday dropped as separate features.
- Its Holdout AUC: **0.7631**
- Gap (holdout - eval): -0.0053
- Time (report.txt): total 2h02m18s; XGBoost runs 0h43m28s (35.5%: training 18.9%, row-by-row eval 16.6%); AI 1h18m50s (64.5%)
- The copied train.py is the final HEAD (`a43b44b`), not `6e0aed7`.

## Validity checks

- **Holdout vs eval gap:** -0.0053, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (33+, 10-). OK.
- **leak_check.txt:** CONTENT HITS 27 = all 26 distinctive lines of
  `prepare.py` + `import matplotlib.pyplot as plt` (from web docs, not
  plot_auc_history.py). The prepare.py lines come from one setup command at
  07:16:58, `cat train.py && cat prepare.py && cat README.md`, issued in the
  same parallel batch as the agent's first `cat program.md` - i.e. before it
  had read the restriction. **This is a forbidden read.** After it: no tool
  call uses the S3 URL, `2005.csv`, the split seeds or sizes, or the
  holdout; train.py reads only `data/train.csv`; artifact checks use
  `train.csv` samples; 0 holdout rows in the log; check_groundtruth.py,
  run_groundtruth_all.sh and plot_auc_history.py were never read or run.
  The agent disclosed the read in turn 1 and in research-log.md and states
  it did not use it for experiment design. Per the group rule (prepare.py
  read, nothing further) the run is kept as **valid with caveat**.
- **Web calls:** 16 search calls and ~25 page opens: XGBoost, scikit-learn,
  pandas and scipy docs, boosting papers (Friedman/Hastie/Tibshirani,
  Wyner, Isomap), a NASA report and two flight-delay papers. No BTS
  TranStats page, no S3 data URL, no `2005.csv`, no curl/wget. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
