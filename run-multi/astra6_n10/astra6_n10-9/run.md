# astra6_n10-9

- **Status:** valid with caveat - the agent read `prepare.py` during setup (accidentally, before reading program.md; it disclosed this itself); no further access
- **Date:** 2026-10-02 (clock 18:45:17 -> 20:47:16 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.8 GB (12793946112 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and research-log.md and asked for "go".
   Its message included: "The accidental read of human-only `prepare.py` is
   documented in research-log.md; it wasn't executed or changed."
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 20:45:49; it stopped the clock itself at
   20:47:16 (turn ended 20:47:50).

No "keep going" was needed. The "go" carried on past the agent's
prepare.py disclosure (a report, not a question).

## Results

- results.tsv: 77 rows = baseline + 76 experiments (31 keep, 46 discard, 0 crash). The last row is a re-run of the unchanged best commit `3651943` ("final confirmation", same 0.7674), so `3651943` appears twice; this makes driver-summary.json's `best_eval_auc` / `best_holdout_auc` fields hold the value twice ("0.7674\n0.7674") - a cosmetic driver parsing quirk, the values are right.
- Best Eval AUC: **0.7674** at `3651943` ("modest label smoothing improves AUC to 0.7674"), up from the 0.7203 baseline
- Model: mean-margin blend of three XGBoost regressors on label-smoothed targets (0.9*y + 0.05): a loss-guided model (1200 trees, learning rate 0.05), a depth-4 and a depth-8 depthwise copy; native categoricals plus a 365-level categorical date and categorical departure hour; on top, additive correction stages - one regularized Newton score per origin-date and destination-date key (soft-thresholded, L2 10), fitted on the training residuals and stored as lookup tables.
- Its Holdout AUC: **0.7623**
- Gap (holdout - eval): -0.0051
- Time (report.txt): total 2h01m59s; XGBoost runs 0h50m05s (41.1%: training 8.8%, row-by-row eval 32.3%); AI 1h11m54s (58.9%)

## Validity checks

- **Holdout vs eval gap:** -0.0051, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (82+, 11-). OK.
- **leak_check.txt:** CONTENT HITS 26 = all 26 distinctive lines of
  `prepare.py`. They come from one setup command at 18:40:30, `...; ls -la;
  sed -n '1,260p' prepare.py; sed -n '1,280p' train.py`, issued in the same
  parallel batch as the agent's first `cat program.md` - before it had read
  the restriction. **This is a forbidden read.** After it: no tool call uses
  the S3 URL, `2005.csv`, the split seeds or sizes, or the holdout; a setup
  check stats `data/eval.csv` without opening it; train.py reads only
  `data/train.csv` (the correction tables are fitted on training residuals);
  0 holdout rows in the log; check_groundtruth.py, run_groundtruth_all.sh and
  plot_auc_history.py were never read or run. The agent disclosed the read
  in turn 1, its final message and research-log.md. Per the group rule
  (prepare.py read, nothing further) the run is kept as **valid with caveat**.
- **Web calls:** 21 search calls and ~20 page opens: XGBoost docs and
  source, scikit-learn docs, arXiv ML papers (label smoothing, matrix
  factorization, smoothing), Google ML pages, the Berkeley iSchool
  flight-delay project. No BTS TranStats page, no S3 data URL, no
  `2005.csv`, no curl/wget. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
- Third run (after 4 and 5) with the same accidental setup-time read of
  prepare.py.
