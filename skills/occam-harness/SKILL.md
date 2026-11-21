---
name: occam-harness
description: End-to-end scientific, token-frugal project harness combining Socratic brainstorming, verified-source research, minimum-capability routing, and zero-token local scripts. Use when starting a project, planning features, or optimizing agent cost and accuracy.
license: MIT
compatibility: Python 3.9+ (stdlib only) for Tier 0 scripts; compatible with Claude Code, Codex CLI, Cursor, Gemini CLI, and Antigravity.
metadata:
  author: Moeraafatz
  version: "1.0.0"
---

# Occam Harness — Five-Phase Execution Protocol

Apply **Occam's Razor** to software engineering: use the simplest verified design, the smallest context window, and the cheapest capable intelligence tier at every step.

## Core Invariants
1. **Zero-Token First (Tier 0):** Never burn LLM tokens on work a local script solves deterministically (`repo_map.py`, `trim_run.py`, `ledger.py`, `cite_check.py`).
2. **Clarify Before Coding:** Ambiguous scope multiplies token burn through rework. Resolve contradictions upfront.
3. **Verify Before Asserting:** Lock technical choices only on primary sources (official docs, source code, peer-reviewed papers, or local benchmarks).
4. **Prevent Context Poisoning:** Keep durable state in `.occam/state.md`; never drag raw test logs or abandoned dead ends across turns.

## Workflow Phases

### Phase 1 — Brainstorm & Analyze (`occam-brainstorm`)
- Skip for trivial 1-file bug fixes with crystal-clear requirements.
- For new projects or multi-file features, activate `occam-brainstorm`: ask 3–5 decision-forcing questions, analyze user answers for contradictions/tradeoffs, and lock a compact 1-page `.occam/decision-spec.md`.
- Initialize the state ledger:
  ```bash
  python3 scripts/occam.py ledger init --goal "<1-sentence goal>" --constraint "<key constraint>" --non-goal "<explicit non-goal>"
  ```

### Phase 2 — Verified-Source Research Gate (`occam-research-gate`)
- Before adopting any library, API, architecture pattern, or scientific claim, activate `occam-research-gate`.
- Record claims in `.occam/research.md` with source tier (`T1`/`T2`/`T3`), URL/path, and version/date.
- Run the zero-token evidence check:
  ```bash
  python3 scripts/occam.py cite .occam/research.md
  ```
- Lock validated choices with `python3 scripts/occam.py ledger decide ...`.

### Phase 3 — Map & Route (`occam-frugal-router`)
- Map the codebase without reading every file:
  ```bash
  python3 scripts/occam.py map --root . --max-tokens 1800 --stats
  ```
- Read ONLY the targeted files and line ranges needed for the active step.
- Break work into small atomic steps in the ledger, tagging each with its **minimum viable tier** (`T0`, `T1`, `T2`, or `T3`):
  ```bash
  python3 scripts/occam.py ledger step add --title "<atomic task>" --tier T1
  ```
- Delegate mechanical/routine tasks to `T1` (small/fast model) and reserve `T3` (frontier model) strictly for architecture decisions, hard bugs after 2 failed tries, or security review.

### Phase 4 — Execute & Verify with Compressed Output
- Make minimal, surgical diffs directly tied to the active step.
- Run builds, tests, and linters through the zero-token log reducer so raw output never floods context:
  ```bash
  python3 scripts/occam.py run -- <test_or_build_command>
  ```
- If an approach fails, log it immediately as a dead end so neither you nor a subagent retries it:
  ```bash
  python3 scripts/occam.py ledger deadend --tried "<attempt>" --why "<root cause>"
  ```
- Escalate to `T3` only after 2 distinct hypotheses fail and are logged.

### Phase 5 — Checkpoint & Handoff
- After completing a milestone (or when chat history grows long), update the checkpoint and emit a compact `<350`-token resume brief:
  ```bash
  python3 scripts/occam.py ledger step done --index <N>
  python3 scripts/occam.py ledger checkpoint --summary "<verified done>" --next "<next atomic step>" --tier T1
  python3 scripts/occam.py ledger handoff --stats
  ```
- Start fresh sessions or cheaper-model turns from that handoff brief instead of replaying full history.

## Deep References (On Demand)
- Read `references/research-foundations.md` only when asked for the scientific basis or citations behind this harness.
