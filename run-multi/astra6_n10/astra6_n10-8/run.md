# astra6_n10-8

- **Status:** valid
- **Date:** 2026-10-02 (clock 16:26:48 -> 18:28:52 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 4.6 GB (4612186112 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and asked for "go".
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 18:27:44; it stopped the clock itself at
   18:28:52 (turn ended 18:29:46).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 67 rows = baseline + 66 experiments (23 keep, 42 discard, 2 crash - training timeouts)
- Best Eval AUC: **0.7667** at `bdfa919`, up from the 0.7203 baseline
- Model: weighted soft-voting blend (3:1) of a loss-guided XGBoost model (max_leaves 256, 500 trees, min_child_weight 100, reg_lambda 500, learning rate 0.12 with a decaying schedule) and a depth-8 depthwise copy; native categoricals, a 365-level categorical flight date plus numeric day-of-year/day-of-month, cyclical departure time (sin/cos) and a distance-adjusted arrival-ish time, and 2-D airport coordinates from classical MDS of shortest-path route distances in train.csv, with route direction vectors.
- Its Holdout AUC: **0.7614**
- Gap (holdout - eval): -0.0053
- Time (report.txt): total 2h02m04s; XGBoost runs 0h37m12s (30.5%: training 9.7%, row-by-row eval 20.8%); AI 1h24m52s (69.5%)

## Validity checks

- **Holdout vs eval gap:** -0.0053, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (60+, 10-). OK.
- **leak_check.txt:** CONTENT HITS 0, 0 holdout rows in the log. No tool
  call names prepare.py, check_groundtruth.py, run_groundtruth_all.sh,
  plot_auc_history.py, holdout.csv or 2005.csv; a setup check stats
  `data/eval.csv` (exists, size) without reading it. train.py reads only
  `data/train.csv`. OK.
- **Web calls:** 19 search calls and a handful of page opens: XGBoost and
  scikit-learn docs, two Stanford CS229 flight-delay project reports,
  Google's feature-crosses course page, ensemble papers. No BTS TranStats
  page, no S3 data URL, no `2005.csv`, no curl/wget. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
- Lowest memory peak of the group so far (4.6 GB).
