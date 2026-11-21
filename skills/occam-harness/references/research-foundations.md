# Scientific & Empirical Foundations of Occam-Kit

Every design rule in Occam-Kit maps to an empirical principle in software engineering or LLM systems research. Load this file only when explaining rationale or auditing methodology.

## 1. Progressive Disclosure & Context-Tax Minimization
- **Principle:** Injecting all tool docs, full files, and prompt rules upfront consumes working memory and degrades instruction adherence.
- **Evidence:**
  - *Lost in the Middle: How Language Models Use Long Contexts* (Liu et al., TACL 2024) — shows sharp accuracy drops when relevant facts sit in the middle of long prompts.
  - *Agent Skills Open Specification* (`agentskills.io`, 2025–2026) — restricts startup discovery to compact `name` + `description` metadata (~50–100 tokens/skill) and loads bodies/references only on trigger.
- **Occam-Kit Implementation:** Combined startup metadata across all 4 skills stays under 260 tokens (enforced by `scripts/token_budget.py audit-skills`).

## 2. Deterministic Code as the Agent Harness (Tier 0)
- **Principle:** Offloading mechanical operations (parsing ASTs, filtering logs, validating tables, persisting state) from probabilistic LLM calls to deterministic local scripts eliminates both token spend and transcription errors.
- **Evidence:**
  - Anthropic Engineering, *Building Effective Agents* (2024) and *Effective Harnesses for Long-Running Agents* (2025) — emphasizes simple composable harnesses, structured external progress files, and clean verification tools over bloated prompt loops.
  - *Code as Agent Harness: Toward Executable, Verifiable, and Stateful Agent Systems* (Ning et al., 2026) — demonstrates that executable harness code and externalized state outperform growing unstructured transcripts on long-horizon engineering tasks.
- **Occam-Kit Implementation:** Zero-dependency Python 3.9+ stdlib scripts (`repo_map.py`, `trim_run.py`, `ledger.py`, `cite_check.py`).

## 3. Output Reduction & Anti-Context-Poisoning
- **Principle:** Dumping thousands of lines of passing test output or repeated stack traces pollutes attention and triggers redundant retry spirals.
- **Evidence:**
  - *SoL-Pi / Harness-Layer Context Compaction* (2026) — evidence-preserving log reducers and online context compactors cut token traffic ~45–49% without hurting SWE accuracy.
- **Occam-Kit Implementation:** `trim_run.py` saves full raw logs to `.occam/last_run.log` (zero information loss) while returning only failure diagnostics, ±2 lines of context, and pass/fail summaries.

## 4. Minimum-Capability Model Routing (Cascading)
- **Principle:** Most software engineering steps (file lookup, boilerplate, test execution, formatting) do not require frontier reasoning. Routing step-by-step to the cheapest sufficient tier preserves accuracy while cutting API spend dramatically.
- **Evidence:**
  - *FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance* (Chen et al., 2023) — proves cascading from cheap to expensive models matches or beats frontier-only baselines at a fraction of cost.
  - *Agentic Routing: The Harness-Native Data Flywheel* (2026) — extends routing from single queries to step-level agent trajectories conditioned on harness state and failure history.
- **Occam-Kit Implementation:** Explicit `T0` / `T1` / `T2` / `T3` tier tagging per step + automatic escalation strictly after 2 logged dead ends.

## 5. Early Clarification & Evidence-Based Engineering
- **Principle:** Resolving requirements contradictions and verifying primary APIs before implementation avoids costly multi-turn rework.
- **Evidence:**
  - Barry Boehm, *Software Engineering Economics* — cost of fixing a requirements defect rises exponentially across design, coding, and testing phases.
  - Barbara Kitchenham et al., *Evidence-Based Software Engineering* (ICSE 2004) — formalizes ranking primary empirical evidence over anecdotal opinion when making engineering decisions.
- **Occam-Kit Implementation:** Mandatory Socratic analysis (`occam-brainstorm`) + machine-checked primary-source ledger (`occam-research-gate` + `cite_check.py`).
