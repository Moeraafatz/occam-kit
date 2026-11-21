# GitHub Copilot Instructions — Occam-Kit

Apply Occam's Razor to every coding task:
1. **Use Tier 0 scripts first** (`python3 .occam/scripts/occam.py map`, `run`, `ledger`, `cite`) to minimize context bloat and avoid reading whole repos or raw passing test logs.
2. **Clarify before coding** on ambiguous requests: ask 3–5 decision-forcing questions, highlight contradictions, and lock a <400-word spec.
3. **Verify primary sources** (official docs, source code, papers, local checks) before asserting API signatures, versions, or performance claims.
4. **Minimize diffs and retries:** Record failed fixes in `.occam/state.md` via `ledger deadend` so you never repeat broken hypotheses.
