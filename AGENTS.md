# Occam-Kit — Universal Agent Operating Rules

Follow **Occam's Razor** for every engineering task: minimal complexity, verified primary evidence, smallest context window, cheapest capable model tier.

## Mandatory Tier 0 Commands (Zero LLM Tokens)
Run these local stdlib scripts (`python3 scripts/occam.py` or `.occam/scripts/occam.py`) instead of burning context tokens:
- **Map codebase before reading files:** `python3 scripts/occam.py map --max-tokens 1800 --stats`
- **Wrap noisy tests/builds:** `python3 scripts/occam.py run -- <cmd>` (keeps errors + summary, saves full raw log to `.occam/last_run.log`)
- **Persist state & avoid loops:** `python3 scripts/occam.py ledger <init|decide|step|deadend|checkpoint|handoff>`
- **Verify research citations:** `python3 scripts/occam.py cite .occam/research.md`

## Core Execution Protocol
1. **Brainstorm first** on new projects or ambiguous tasks (`occam-brainstorm`): ask 3–5 high-leverage questions in one batch, expose contradictions, lock a <400-word `.occam/decision-spec.md`.
2. **Verify load-bearing claims** (`occam-research-gate`): prefer primary sources (T1: official docs, source code, peer-reviewed papers, local benchmarks). Never mark a claim `Verified` from secondary blogs or memory alone.
3. **Route to minimum capability** (`occam-frugal-router`): `T0` local scripts -> `T1` small/fast model (search, boilerplate, mechanical edits) -> `T2` standard model (locked-spec code) -> `T3` frontier model (ONLY architecture tradeoffs, security audit, or bugs after 2 logged dead ends).
4. **Prevent context poisoning:** Read targeted line ranges, never paste full raw logs, record failed attempts with `ledger deadend`, and resume long tasks from `ledger handoff`.
