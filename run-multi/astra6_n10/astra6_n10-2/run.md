# astra6_n10-2

- **Status:** valid (clock stopped by the driver after an OpenAI "model at capacity" error ~5 min before the end)
- **Date:** 2026-10-01 (clock 20:07:41 -> 22:11:35 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-astra, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-astra, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `oct1` (created by the agent during setup)
- **Container:** 24 GB memory cap, no swap. Peak 8.3 GB (8281247744 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent created branch
   `oct1`, initialized results.tsv and asked for "go".
2. "go" - the agent started the clock and worked in this single turn until
   22:06:33, when codex failed the turn with **"Selected model is at
   capacity. Please try a different model."** (an OpenAI-side capacity
   error, not the subscription usage limit). The agent had just committed
   `56adee7` ("Check whether geography permits a smaller leaf budget") and
   launched its run; that experiment never got a results row. Per its
   rules, the driver waited 300 s to retry; by then TIME IS UP had arrived
   (22:11:35), so it did not resend and stopped the clock itself.

No "keep going" was needed. No real question was glossed over. There is no
turns/2.txt (the turn has no final message); turns/2.err also has two
harmless `write_stdin failed: Unknown process id` errors at 20:49-20:51.

## Results

- results.tsv: 82 rows = baseline + 81 experiments (23 keep, 58 discard, 1 crash - a DART model that hit the 60 s training timeout)
- Best Eval AUC: **0.7657** at `5851c0c` ("reduce numeric histogram resolution to sixty-four bins"), up from the 0.7203 baseline
- Model: a single XGBoost model, loss-guided, max_leaves 64, max_bin 64, min_child_weight 100, reg_lambda 500, colsample_bynode 0.3, learning rate 0.015, 2000 trees; native categoricals for carrier, origin, destination and a categorical flight date; airport "landmark distances" (median route distance to LAX and ATL, from train.csv) for origin and destination; month/day-of-month/weekday as separate features dropped.
- Its Holdout AUC: **0.7604**
- Gap (holdout - eval): -0.0053
- Time (report.txt): total 2h03m55s; XGBoost runs 0h49m03s (39.6%: training 21.7%, row-by-row eval 17.9%); AI 1h14m52s (60.4%)
- The copied train.py is the HEAD commit `56adee7` (the unrecorded last experiment), which differs from `5851c0c` only in the leaf budget.

## Validity checks

- **Holdout vs eval gap:** -0.0053, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (26+, 10-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive: `import
  matplotlib.pyplot as plt` from a scikit-learn docs example the agent
  opened, not from plot_auc_history.py. 0 holdout rows in the log. The 5
  listed commands are an `rg --files` listing at setup (which names
  `prepare.py` as a glob - listing only), `cat program.md`, `git show` of
  train.py and web lookups. The only tool call naming a forbidden file is
  that listing; the `python3 prepare.py` strings in the log are README text.
  train.py reads only `data/train.csv`. OK.
- **Web calls:** 27 search calls and ~24 page opens: XGBoost, LightGBM,
  scikit-learn and pandas docs, a few arXiv/PMLR papers, Breiman's random
  forest page. No BTS/TranStats, no S3 data URL, no `2005.csv`, no
  curl/wget. OK.

## Notes

- No NOTE lines in driver.log: repo clean on `main`.
- Clock stopped by the driver, not the agent, because of the capacity error;
  the agent lost the last ~5 minutes (one experiment). Holdout/eval are
  unaffected.
