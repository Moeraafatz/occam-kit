---
name: occam-frugal-router
description: Minimum-capability routing and context-budget policy that assigns each step to Tier 0 scripts or the cheapest capable model tier while preventing context poisoning. Use when planning tasks, delegating subagents, or cutting API token burn.
license: MIT
metadata:
  author: Moeraafatz
  version: "1.0.0"
---

# Occam Frugal Router — Minimum Viable Intelligence

Never spend frontier tokens on work a deterministic script or small model can solve cleanly. Route **every step** to the lowest tier that satisfies accuracy.

## Four-Tier Routing Ladder
| Tier | Executor | Use Strictly For | Token Cost |
| :--- | :--- | :--- | :--- |
| **T0** | Local deterministic scripts (`scripts/occam.py`, `rg`, linters, formatters, compilers) | Repo mapping, symbol lookup, test/log trimming, citation checks, state ledger, formatting | **0 LLM tokens** |
| **T1** | Small / fast model (Haiku, Flash, Mini, Nano, local small model) | File discovery, targeted grep review, boilerplate, mechanical refactors, simple test scaffolding, doc edits | **Lowest (~5–15x cheaper)** |
| **T2** | Standard coding model (Sonnet, Codex standard, Pro standard) | Feature implementation against locked spec, multi-file edits, scoped bug fixes | **Medium** |
| **T3** | Frontier / deep reasoning model (Opus, o-series/high-reasoning, Pro high) | Initial architecture tradeoffs, hard root-cause bugs **only after 2 logged dead ends**, security/correctness audit | **Highest — gate strictly** |

## Escalation & De-escalation Rules
1. **Start Low:** Default to `T0` first, then `T1` for read/search/mechanical work, `T2` for locked-spec implementation.
2. **Earn Escalation:** Escalate `T1 -> T2` or `T2 -> T3` ONLY when:
   - Two distinct attempts fail and both are recorded via `occam.py ledger deadend`, OR
   - The step involves irreversible security, concurrency, or architectural risk.
3. **Drop Back Down Immediately:** After `T3` resolves an architecture decision or root cause, lock the result into `ledger.py` and drop back to `T1`/`T2` for execution.

## Cross-Agent Execution Modes
- **Agents with subagent model selection (Claude Code, Antigravity, OpenCode):** Pass the explicit small/fast model flag when spawning `T1` investigator/builder subagents; pass a compact `ledger handoff` brief instead of full conversation history.
- **Single-model sessions (Cursor Composer, Codex CLI):** Enforce `T0` scripts on every repo scan and test run. When a milestone finishes, emit an explicit switch banner:
  ```text
  [OCCAM ROUTE] Spec locked -> Safe to switch to T1/T2 model. Resume with: python3 scripts/occam.py ledger handoff
  ```

## Context-Budget Guardrails
- **Map before reading:** Always run `python3 scripts/occam.py map --max-tokens 1800` before opening files. Read only the exact line range needed.
- **Trim every noisy command:** Wrap tests/builds in `python3 scripts/occam.py run -- <cmd>` so passing output never floods context.
- **Checkpoint early:** After 8–12 turns or any major milestone, update `ledger.py checkpoint` and resume from `ledger handoff` (<350 tokens).
- Load `references/model-tiers.md` only when mapping tiers to specific vendor model names.
