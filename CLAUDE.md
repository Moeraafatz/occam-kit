# Claude Code Instructions — Occam-Kit

Follow all core rules in `AGENTS.md` and use the installed `occam-*` skills under `.claude/skills/` on demand:
- `occam-harness`: Full 5-phase engineering protocol.
- `occam-brainstorm`: Socratic scoping + contradiction analysis before coding.
- `occam-research-gate`: Primary-source verification ledger + `cite_check.py`.
- `occam-frugal-router`: Minimum-capability routing (`T0` scripts -> `T1` Haiku subagents -> `T2` Sonnet -> `T3` Opus strictly on escalation).

Keep subagent prompts compact by passing `python3 scripts/occam.py ledger handoff` instead of full chat history.
