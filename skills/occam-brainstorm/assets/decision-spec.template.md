# Decision Spec — <Project / Feature Name>

> Cap: Keep under 400 words so any model tier can read it in <500 tokens.

## 1. Goal (1 Sentence)
- <Exact measurable v1 outcome>

## 2. Hard Constraints
- Budget / Infra: <e.g., $0, local-only, no paid APIs>
- Platform / Runtime: <e.g., macOS 15+, Python 3.9+ stdlib>
- Security / Safety: <e.g., read-only by default, no destructive deletes>

## 3. Explicit Non-Goals (Out of Scope for v1)
- <Non-goal 1>
- <Non-goal 2>

## 4. Contradictions & Tradeoffs Resolved
| Conflict / Question | Options Considered | Locked Choice | Why |
| :--- | :--- | :--- | :--- |
| <e.g., Sync vs. Offline> | <Cloud DB vs. Local SQLite> | <Local SQLite> | <Zero cost, zero latency> |

## 5. Minimal Architecture & Verification
- Components: <2–4 core modules only>
- Acceptance Test: <Exact command or check that proves v1 works>
