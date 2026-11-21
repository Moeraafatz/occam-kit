# Occam-Kit Reproducible Token Benchmarks

> Method: `Deterministic offline BPE estimate (~4 chars/token)` — reproduce locally in <1s with `python3 benchmarks/run_benchmarks.py`.

| Scenario | Tier 0 Tool | Raw Context | With Occam-Kit | Saved | Verification |
| :--- | :--- | ---: | ---: | ---: | :--- |
| Codebase Discovery (24 files, 4 languages) | `occam.py map` | 9,065 tok | 950 tok | **-89.5%** | All 24/24 files mapped |
| Verbose Passing Test Suite (300 tests) | `occam.py run` | 7,633 tok | 54 tok | **-99.3%** | Exit status + 300 passed summary preserved |
| Verbose Failing Test Suite (298 pass / 2 fail) | `occam.py run` | 7,845 tok | 547 tok | **-93.0%** | 100% of failing tests + errors preserved |
| 15-Turn Session Resume vs. Ledger Handoff | `occam.py ledger handoff` | 4,293 tok | 150 tok | **-96.5%** | Goal, locked decisions, dead ends, next tier kept |
| Skill Startup Context Tax (Progressive Disclosure) | `occam.py audit` | 3,090 tok | 262 tok | **-91.5%** | All 4 skills valid (agentskills.io) |
| **Combined Across All 5 Scenarios** | **All Tier 0** | **31,926 tok** | **1,963 tok** | **-93.9%** | **Zero accuracy/evidence lost** |

## Notes on Honesty
- Token counts are measured deterministically offline (`ceil(chars / 4)`) so anyone can reproduce exact results with zero API keys.
- Actual tokenizer counts (tiktoken / Claude / Gemini) vary by ~5–10%, while relative reduction percentages remain closely aligned.
- Full raw command logs are always preserved in `.occam/last_run.log` so zero diagnostic detail is lost.
