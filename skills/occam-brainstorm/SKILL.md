---
name: occam-brainstorm
description: Structured Socratic brainstorming and user-answer analyzer that exposes contradictions, evaluates tradeoffs, and produces a compact 1-page decision spec before writing code. Use when scoping new projects or ambiguous features.
license: MIT
metadata:
  author: Moeraafatz
  version: "1.0.0"
---

# Occam Brainstorm — Socratic Requirements Analyzer

Prevent wasted implementation tokens by converting vague ideas into a tight, contradiction-free 1-page spec **before** writing code.

## When to Trigger
- New project, architecture decision, or multi-file feature with ambiguity.
- Skip if the request is a single-file fix with unambiguous acceptance criteria.

## Step 1 — Ask One High-Leverage Question Batch (Max 5 Questions)
Never interrogate the user across 10 turns. Ask **3 to 5 surgical questions in one message**, covering only what is NOT already answered by the prompt or repo:
1. **Core Outcome:** What single concrete result defines "done" for v1?
2. **Hard Constraints:** What cannot change (budget = $0, offline-only, target OS/runtime, latency, zero external deps)?
3. **Explicit Non-Goals:** What features must we intentionally leave OUT of v1 to stay lean?
4. **Target User & Workflow:** Who runs this and what is their exact 30-second happy path?
5. **Failure Tolerance:** What is the worst thing that could break (data loss, cost blowup, security leak)?

Offer a concise **default recommendation** beside each question so the user can reply "all defaults" if they want speed.

## Step 2 — Deeply Analyze the User's Answers (Do Not Blindly Echo)
Before proposing a plan, run a 4-point analytical audit on the answers:
1. **Contradiction Check:** Flag any conflicting goals (e.g., "zero budget + paid hosted API" or "zero latency + unindexed full-disk scan"). Present 2 concrete resolutions and recommend the leaner one.
2. **Hidden Assumption Check:** Name 1–3 unstated dependencies (auth, OS permissions, build toolchain, network access).
3. **Scope-Cut Check (Occam Pass):** Identify any feature that adds >30% complexity for <10% user value and propose moving it to v2.
4. **Simplest Viable Architecture:** Pick the minimal stack that satisfies every hard constraint without premature abstraction.

## Step 3 — Lock the 1-Page Decision Spec
- Write `.occam/decision-spec.md` using `assets/decision-spec.template.md`.
- Keep it **under 400 words** (~500 tokens max) so any downstream agent can ingest it cheaply.
- Sync goal, constraints, non-goals, and locked decisions into the Tier 0 ledger:
  ```bash
  python3 scripts/occam.py ledger init --goal "..." --constraint "..." --non-goal "..."
  python3 scripts/occam.py ledger decide --id D1 --decision "..." --reason "..."
  ```
- Get one explicit user confirmation ("Lock spec & build") before transitioning to `occam-research-gate` or coding.
