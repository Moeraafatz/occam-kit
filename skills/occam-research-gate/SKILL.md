---
name: occam-research-gate
description: Evidence-first technical and scientific verification gate that ranks primary sources, blocks unverified assumptions, and validates citations via a local ledger before implementation. Use when choosing libraries, APIs, algorithms, or scientific claims.
license: MIT
metadata:
  author: Moeraafatz
  version: "1.0.0"
---

# Occam Research Gate — Verified Evidence Before Code

Stop hallucination-driven rework by verifying high-impact technical and scientific claims against primary sources **before** writing code.

## Source Hierarchy (Strict)
| Tier | Allowed Source Types | Can Lock Core Architecture Alone? |
| :--- | :--- | :--- |
| **T1 (Primary)** | Official versioned docs, actual source code/headers, RFCs/specs, peer-reviewed papers (DOI/arXiv), reproducible local benchmarks | **Yes** |
| **T2 (Corroborating)** | Independent reproducible benchmarks, maintainer GitHub issues/PRs with code, official changelogs | **Yes** (if version-matched) |
| **T3 (Secondary)** | Blog posts, Reddit/HN threads, Q&A forums, unverified model memory | **No** — must confirm via T1/T2 or mark `Provisional` |

## Protocol (Token-Efficient)
1. **Identify Only Load-Bearing Claims (Max 5–8):** Do NOT research trivial language syntax. Research only claims where being wrong wastes hours:
   - API signatures, breaking version changes, OS/platform permissions.
   - Performance, latency, or security claims.
   - Scientific or algorithmic choices and benchmark baselines.
2. **Verify From Primary Artifacts First:**
   - Local codebase/environment check (`--version`, local headers/source) beats web search.
   - Official docs / primary papers beat blog summaries.
   - Always record the exact **version or date** (`v3.12`, `2026-11-21`, `commit:abc1234`).
3. **Log Into `.occam/research.md`:**
   - Use the 5-column table format in `assets/research-ledger.template.md`:
     `| Claim | Tier | Source | Version/Date | Status |`
   - Valid Status values: `Verified`, `Provisional`, `Contradicted`, `Rejected`.
   - If a source contradicts an assumption, log `Contradicted` and update the plan immediately.
4. **Run the Zero-Token Gate:**
   ```bash
   python3 scripts/occam.py cite .occam/research.md --strict
   ```
   - Fix any error (missing URL/path, missing date/version, or `Verified` backed only by `T3`) before locking decisions into `ledger.py`.

## Hard Honesty Rule
- If primary verification is unavailable (e.g., offline or paywalled), mark the row `Provisional` and inform the user explicitly. Never fabricate citations, DOIs, benchmark numbers, or API flags.
