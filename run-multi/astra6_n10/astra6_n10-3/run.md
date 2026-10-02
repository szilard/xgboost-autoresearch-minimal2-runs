# astra6_n10-3

- **Status:** valid
- **Date:** 2026-10-02 (clock 05:02:41 -> 07:04:51 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct2` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 12.7 GB (12657770496 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct2`, initialized results.tsv and research-log.md and asked for "go".
2. "go" - the agent started the clock and worked the full 2 hours in this
   single turn. TIME IS UP at 07:03:41; it stopped the clock itself at
   07:04:51 (turn ended 07:05:43).

No "keep going" was needed. No real question was glossed over.

## Results

- results.tsv: 87 rows = baseline + 86 experiments (23 keep, 63 discard, 1 crash - a training timeout)
- Best Eval AUC: **0.7713** at `0f6bd05` ("node-level column sampling gives a small ensemble gain"), up from the 0.7203 baseline. The agent's final selected commit is `812d7ef` (0.7711 eval / 0.7655 holdout: destination geometry removed for faster evaluation); the driver takes the eval maximum.
- Model: average of two XGBoost models (1200 trees, depth 8, learning rate 0.05, min_child_weight 20, reg_lambda 10, reg_alpha 5, max_bin 1024, colsample_bynode 0.8), each given a different pair of airport coordinate axes. The coordinates are a 2-D classical MDS embedding of shortest-path distances in the training route graph (median route Distance from train.csv), plus the 45-degree-rotated axes. Also native categoricals (month, weekday, carrier, origin, destination) and day-of-year as a 365-level categorical flight date.
- Its Holdout AUC: **0.7663**
- Gap (holdout - eval): -0.0050
- Time (report.txt): total 2h02m10s; XGBoost runs 0h51m14s (41.9%: training 11.7%, row-by-row eval 30.2%); AI 1h10m56s (58.1%)
- The copied train.py is the final HEAD (`812d7ef`), not `0f6bd05`.

## Validity checks

- **Holdout vs eval gap:** -0.0050, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (61+, 10-). OK.
- **leak_check.txt:** CONTENT HITS 0, 0 holdout rows in the log. The 21
  listed commands are an `rg --files` listing at setup (`prepare.py` as a
  glob - listing only), `cat program.md`/README, `git show <commit>:train.py`,
  artifact inspections (feature importances, booster config of the agent's
  own saved models), a results.tsv consistency check and web lookups. A
  setup check stats `data/eval.csv` (exists, size) without reading it. No
  tool call reads or runs a forbidden file. train.py reads only
  `data/train.csv`. OK.
- **Web calls:** 17 search calls and ~21 page opens: XGBoost docs and
  source, scikit-learn and pandas docs, CatBoost paper, a spherical MDS
  paper, a PLOS ONE flight-delay paper, the Berkeley iSchool flight-delay
  project. One search was restricted to transtats.bts.gov (delay causes);
  no TranStats page was opened. No S3 data URL, no `2005.csv`, no
  curl/wget. OK, noted.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
- Clearly the best astra run so far (holdout 0.7663 vs 0.7598/0.7604), and
  above every sol and luna run; the eval-holdout gap is normal.
