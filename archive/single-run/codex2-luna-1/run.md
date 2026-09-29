# Run codex2-luna-1

| | |
|---|---|
| Agent | codex-cli 0.158.0 (`codex exec` / `codex exec resume`), ChatGPT login |
| Model | gpt-5.6-luna |
| Reasoning effort | max |
| Upstream minimal2 commit | 20e1f9850ca0ff4a2433ca63b48992dc057d4779 |
| Run tag / branch | sep28 |
| Date | 2026-09-28 (clock 19:08:13 -> 21:08:46 UTC) |
| Session id | 01a0e969-6a07-7ee2-8d46-f4c2a6875846 |
| Container | codex2-luna-1 (image agents2, left running) |

Confirmed from the `turn_context` entries of the session log (all 3 turns):
`model` = gpt-5.6-luna, `effort` = max, `approval_policy` = never,
`sandbox_policy` = danger-full-access. `codex debug models` lists
low/medium/high/xhigh/max for gpt-5.6-luna, so max is its top level (no `ultra`
level exists for this model, unlike gpt-5.6-sol/terra).

## Turns

| # | Sent | Outcome |
|---|---|---|
| 1 | `Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.` | Read program.md, checked data, proposed tag `sep28`, asked to create the branch |
| 2 | `go` | Created branch `sep28`, initialized results.tsv and research-log.md, then asked for confirmation before starting the clock |
| 3 | `go` | Started the clock, ran all experiments, stopped the clock itself at 2h00m33s |

No "keep going" was needed; one session file throughout.

## Results

- Runs: 70 (baseline + 69 experiments): 21 keep (incl. baseline), 48 discard, 1 crash (DART, training timeout)
- Best Eval AUC: **0.7611** at `887375a` ("add IsMonthEndWeekend interaction"), baseline 0.7203
- Holdout AUC of `887375a`: **0.7567** (gap holdout - eval = -0.0044)
- Best Holdout AUC among kept commits: 0.7574 at `5e01c82` (Eval 0.7606)
- Timing (report.txt): total 2h00m33s; XGBoost runs 52m47s (43.8%); AI 1h07m46s (56.2%)

Final model: loss-guided histogram trees, 300 trees, lr 0.05, max_leaves 512,
min_child_weight 3, colsample_bytree 0.4, plus row-local calendar features
(DayOfYear, its annual sin/cos, IsWeekend, IsMonthEnd, IsMonthEndWeekend).
Gains came first from capacity/tree count, then feature subsampling, then
lossguide growth, then the calendar features.

## Validity checks

- Holdout vs eval gap at the best commit: -0.0044 (within the normal range; the minimal2 test run had ~-0.005). Gaps across all kept commits range from -0.0026 to -0.0050. PASS
- `git diff c294417 887375a --stat`: `train.py` only (23+, 3-). PASS
- Session log: no reads/runs of holdout.csv, prepare.py, check_groundtruth.py, run_groundtruth_all.sh, plot_auc_history.py, and no access to 2005.csv or the S3 URL. The only contact was file-name listings during setup (`rg --files` over the repo, `find data -printf '%f'`), which show names only. All other grep hits are the `prepare(df)` function in train.py and hard-coded 2005 calendar constants (month offsets, federal holidays). Content check: the log records the output of all 303 commands, and none of it contains distinctive text from prepare.py (S3 URL, `split_4_1_1`, `150_000`), check_groundtruth.py, run_groundtruth_all.sh, plot_auc_history.py or the first holdout row. A search for broad reads (globs, `rg` without `--files`, `find`, `git show`/`grep`, paths outside the repo) found only the two setup listings and reads of data/train.csv. Limits: this is based on the log only (file atimes in the container are not updated, so they give no evidence), and it would not catch a deliberately obfuscated path. PASS
- Web research (6 `web.run` calls): XGBoost parameter/categorical docs, flight-delay feature papers, holiday features, target-encoding leakage (Micci-Barreca, CatBoost). No data downloads.

**Verdict: valid.**

## Notable

- The agent asked for confirmation twice before starting (after tag proposal, and again after setup before starting the clock), so it took two "go"s.
- It stopped experimenting at 20:49 with ~19 minutes left on the clock (after the last experiment, `e510bc0`), then idled in a sleep/status loop until the clock ran out and ran `harness.py stop` at 2h00m33s. Those ~19 idle minutes are counted in the 56.2% AI share.
- Experiments with train-set target statistics (smoothed carrier/origin/dest and route delay priors, route median departure time) were tried near the end and discarded; they were computed from train.csv only.
- Three `apply_patch` verification failures (stale context) appear in turn 3 stderr; the agent retried and they had no effect on results.
- Setup notes: `codex debug models` (run by me to check effort levels, before turn 1) created `~/.codex/models_cache.json`; my setup check `python3 train.py` left a `__pycache__/` in the repo (gitignored). Neither is a prior session or config.
