# sol6_n10-3

- **Status:** valid
- **Date:** 2026-09-29 (clock 18:47:22 -> 20:48:13 UTC)
- **Codex:** codex-cli 0.159.0, ChatGPT login
- **Model / effort:** gpt-6-sol, max (levels offered: low medium high xhigh max ultra)
- **turn_context (confirmed from the session log):** gpt-6-sol, max, approval never, sandbox danger-full-access
- **Upstream minimal2 commit:** 4f5e5e94b29c2b8b9ed9947d56cb622a8fa6cd89 (first commit `92e43e6`)
- **Run tag / branch:** `sep29` (proposed by the agent, not confirmed by us)
- **Container:** 24 GB memory cap, no swap. Peak 12.7 GB (12717027328 bytes), 0 processes killed at the cap.

## Turns

1. README prompt ("Hi have a look at program.md and let's kick off a new
   experiment! let's do the setup first.") - the agent did the preflight
   checks and asked us to confirm the run tag `sep29` or give another one.
2. "go" - the agent created branch `sep29`, started the clock and worked for
   the full 2 hours in this single turn, stopping the clock itself at
   20:48:13 (2h00m51s on the clock; the driver's 60 s poll hadn't logged
   TIME IS UP yet).

No "keep going" was needed. The run-tag question in turn 1 was a real
question that "go" glossed over; the agent went with its own proposal.

## Results

- results.tsv: 94 rows = baseline + 93 experiments (27 keep, 67 discard, 0 crash)
- Best Eval AUC: **0.7640** at `52303aa` ("30 percent seasonal prediction weight"), up from the 0.7203 baseline.
  The final model blends a global XGBoost model (70%) with four quarter-specific models (30%).
- Its Holdout AUC: **0.7580**
- Gap (holdout - eval): -0.0060
- Time (report.txt): total 2h00m51s; XGBoost runs 1h14m19s (61.5%: training 16.9%, row-by-row eval 44.6%); AI 0h46m33s (38.5%)

## Validity checks

- **Holdout vs eval gap:** -0.0060, the normal optimism of the eval set. OK.
- **diff-stat.txt:** first commit to best commit touches `train.py` only (56+, 4-). OK.
- **leak_check.txt:** CONTENT HITS 1, a false positive. The one "distinctive"
  line of plot_auc_history.py found in the log is `import matplotlib.pyplot as
  plt`, and it comes from two scikit-learn documentation pages the agent
  opened (target encoder cross fitting, time-related feature engineering),
  not from the file. 0 holdout data rows in the log. The 111 listed commands
  are `rg` polls of run.log, `cat` of allowed files, loading its own
  artifacts (`glob` of `artifacts/<commit>*.pkl`, `harness.load_artifact`)
  for feature importances, and a `datetime.date(2005, ...)` day-of-year
  lookup for holidays. None reads or runs a forbidden file. OK.
- **Web calls:** 101 search queries / page opens. Opened pages: a Wiley IET
  paper and a Stanford CS229 project on flight-delay prediction, arXiv
  2006.10562, an MDPI paper and XGBoost docs. Several searches mention
  "2005", and five are restricted to bts.gov / transtats.bts.gov (the Bureau of
  Transportation Statistics, the original source of the on-time data), e.g.
  "site:transtats.bts.gov on time holiday flight delay December
  Thanksgiving". Their results listed BTS pages, including the on-time
  download page, but the agent opened none of them and downloaded nothing. No
  S3 or `2005.csv` access, and the best train.py has no hard-coded external
  statistics (only the calendar month offsets). OK, but noted.

## Notes

- No NOTE lines in driver.log: repo clean on `main`, no leftover timing/ or artifacts/.
- This run had the highest XGBoost share of the clock so far (61.5%) and the
  lowest AI share (38.5%).
