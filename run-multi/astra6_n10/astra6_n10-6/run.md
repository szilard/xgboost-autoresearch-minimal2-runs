# astra6_n10-6

- **Status:** valid
- **Date:** 2026-10-02 (clock 11:55:40 -> 13:57:35 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 13.2 GB (13239218176 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and research-log.md and asked for "go".
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 13:56:28; it stopped the clock itself at
   13:57:35 (turn ended 13:58:30).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 75 rows = baseline + 74 experiments (21 keep, 53 discard, 1 crash - a training timeout)
- Best Eval AUC: **0.7712** at `22dfab8` ("disjoint interaction groups on the short-path member only"), up from the 0.7203 baseline. (A discarded blend `fd98cd0` reached 0.7713; the agent kept the faster model.)
- Model: weighted soft-voting blend (3:3:2) of three XGBoost models - depth 10 and depth 8 (1200 trees, learning rate 0.05, min_child_weight 20, reg_lambda 10, reg_alpha 5, max_cat_threshold 16) and a fast 320-tree member at learning rate 0.1 with interaction constraints ([FlightDate, Month, Origin, Dest] / [CRSDepTime, Distance, IsWeekend, UniqueCarrier]); native categoricals plus a categorical flight date and an IsWeekend flag. No airport geometry.
- Its Holdout AUC: **0.7656**
- Gap (holdout - eval): -0.0056
- Time (report.txt): total 2h01m54s; XGBoost runs 0h42m18s (34.7%: training 18.4%, row-by-row eval 16.3%); AI 1h19m36s (65.3%)

## Validity checks

- **Holdout vs eval gap:** -0.0056, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (33+, 10-). OK.
- **leak_check.txt:** CONTENT HITS 0, 0 holdout rows in the log. No tool
  call names prepare.py, check_groundtruth.py, run_groundtruth_all.sh,
  plot_auc_history.py, holdout.csv or 2005.csv. Setup checks stat
  `data/eval.csv` (size, `os.access` readable) without reading it.
  train.py reads only `data/train.csv`. OK.
- **Web calls:** 19 search calls and a handful of page opens: XGBoost and
  scikit-learn docs, the CatBoost paper, the Berkeley iSchool flight-delay
  project. No BTS TranStats page, no S3 data URL, no `2005.csv`, no
  curl/wget. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
- Second-best astra run so far (holdout 0.7656), close to run 3 (0.7663).
