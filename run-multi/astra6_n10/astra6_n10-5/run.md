# astra6_n10-5

- **Status:** valid with caveat - the agent read `prepare.py` during setup (accidentally, before reading program.md; it disclosed this itself); no further access
- **Date:** 2026-10-02 (clock 09:35:54 -> 11:37:38 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 8.0 GB (8049299456 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and research-log.md and asked for "go".
   Its message included: "I accidentally read `prepare.py` before seeing its
   restriction. It wasn't executed, and no held-out data was accessed."
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 11:36:51; one prepared cleanup (`a7bdbc9`) was
   refused by the harness as the clock had expired (not run, no row), and
   the agent stopped the clock itself at 11:37:38 (turn ended 11:38:53).

No "keep going" was needed. The "go" carried on past the agent's
prepare.py disclosure (a report, not a question).

## Results

- results.tsv: 67 rows = baseline + 66 experiments (23 keep, 44 discard, 0 crash)
- Best Eval AUC: **0.7651** at `a8dea74` ("Increase histogram capacity to 2048 bins"), up from the 0.7203 baseline
- Model: XGBoost with 16 parallel trees per round (a boosted random forest; depth 7, min_child_weight 50, reg_lambda 20, max_bin 2048, subsample 0.8, colsample_bynode 0.8) and a learning-rate schedule callback; native categoricals plus a categorical flight date; origin/destination airport coordinates from classical MDS of shortest-path route distances in train.csv, with their diagonal sum/difference projections.
- Its Holdout AUC: **0.7589**
- Gap (holdout - eval): -0.0062
- Time (report.txt): total 2h01m43s; XGBoost runs 1h00m43s (49.9%: training 21.9%, row-by-row eval 28.0%); AI 1h01m01s (50.1%)

## Validity checks

- **Holdout vs eval gap:** -0.0062, slightly larger than usual but within the normal eval optimism (> -0.01). OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (52+, 5-). OK.
- **leak_check.txt:** CONTENT HITS 26 = all 26 distinctive lines of
  `prepare.py`. They come from one setup command at 09:33:07, `cat train.py
  && cat prepare.py`, issued in the same parallel batch as the agent's first
  `cat program.md` - before it had read the restriction. **This is a
  forbidden read.** After it: no tool call uses the S3 URL, `2005.csv`, the
  split seeds or sizes; the only "holdout" mentions are web searches for the
  CatBoost paper's "holdout TS" (target statistics), which the agent notes
  refers to a subset of train.csv; a setup check stats `data/eval.csv`
  without opening it; train.py reads only `data/train.csv`; 0 holdout rows
  in the log; check_groundtruth.py, run_groundtruth_all.sh and
  plot_auc_history.py were never read or run. The agent disclosed the read
  in turn 1 and research-log.md. Per the group rule (prepare.py read,
  nothing further) the run is kept as **valid with caveat**.
- **Web calls:** 14 search calls and ~20 page opens: XGBoost docs, source
  and GitHub issues, LightGBM, scikit-learn and scipy docs, CatBoost,
  rotation-forest and other ensemble papers, the Berkeley iSchool
  flight-delay project. No BTS TranStats page, no S3 data URL, no
  `2005.csv`, no curl/wget. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
- Second run in a row (after run 4) with the same accidental setup-time
  `cat prepare.py`.
