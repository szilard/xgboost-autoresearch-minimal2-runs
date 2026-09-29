# Archived: single runs driven live by Claude

These runs were made with the retired `/xgb-run` skill: Claude drove codex
turn by turn and did the checks by hand, instead of the scripted driver of
`/xgb-multi` that all later runs use. The protocol was the same in substance
(README prompt, then "go", "keep going" if the agent stopped early, 2-hour
harness clock), but since the runs weren't driven identically, keep them out
of the group statistics.

- [codex2-luna-1](codex2-luna-1/run.md): gpt-5.6-luna, effort `max`, 2026-09-28 -
  one row in [results_summary.md](results_summary.md)

The `/xgb-run` skill itself is preserved in git at tags `v0.1` and `v0.2`
(`.claude/skills/xgb-run/SKILL.md`).
