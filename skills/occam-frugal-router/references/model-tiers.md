# Cross-Vendor Model Tier Mapping

Use this reference only when configuring concrete model names for `occam-frugal-router`. Always prefer the current lightweight, standard, and frontier tier equivalents available in your agent harness.

| Tier | Role | Anthropic (Claude Code) | OpenAI (Codex / API) | Google (Gemini CLI / Antigravity) | Local / Zero-Cost (Ollama) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T0** | Deterministic tooling | Local Python/shell (`scripts/occam.py`) | Local Python/shell (`scripts/occam.py`) | Local Python/shell (`scripts/occam.py`) | Local Python/shell |
| **T1** | Discovery, boilerplate, mechanical edits, test runs | Claude Haiku tier | GPT mini / nano / spark tier | Gemini Flash / Flash-Lite tier | 7B–14B local coder model |
| **T2** | Locked-spec feature code, targeted fixes | Claude Sonnet tier | Codex / GPT standard tier | Gemini Pro standard tier | 32B+ local coder model |
| **T3** | Architecture tradeoffs, hard bugs (>2 dead ends), security audit | Claude Opus tier | High-reasoning frontier tier | Gemini Pro high-reasoning tier | Frontier API (sparingly) |

## Cost-Discipline Heuristics
- **80/15/5 Rule:** Aim for ~80% of tool/mechanical work in `T0` + `T1`, ~15% implementation in `T2`, and <=5% deep reasoning in `T3`.
- **Subagent Prompt Budget:** Keep subagent task prompts under 400 tokens by passing `python3 scripts/occam.py ledger handoff` plus exact file paths and line numbers.
