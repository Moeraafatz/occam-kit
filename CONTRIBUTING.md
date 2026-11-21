# Contributing to occam-kit

`occam-kit` is MIT-licensed and open to everyone. Contributions should follow the same Occam's Razor discipline the toolkit enforces: **zero external runtime dependencies, verifiable claims, minimal startup token tax, and automated tests.**

## Ways to Contribute
1. **Language extractors (`scripts/repo_map.py`)** — Add or refine lightweight AST/regex symbol extractors (e.g., Ruby, PHP, Elixir, Zig, SQL, Terraform).
2. **Log patterns (`scripts/trim_run.py`)** — Improve failure/summary detection for additional test runners and build tools (Vitest, Cargo, Go test, Xcodebuild, Gradle).
3. **Agent adapters (`adapters/` & `install.sh`)** — Add clean adapters for additional coding agents while keeping startup context under budget.
4. **Benchmarks (`benchmarks/run_benchmarks.py`)** — Add realistic offline scenarios with strict evidence-preservation assertions.

## Contribution Rules (Checked by CI)
- **Python 3.9+ stdlib only** — Do not add `pip` dependencies to `scripts/` or `benchmarks/`.
- **Startup Token Cap** — Combined startup metadata across `skills/` must remain `<= 350` tokens (`python3 scripts/occam.py audit skills --max-startup-tokens 350`).
- **Tests Required** — Add unit tests in `tests/test_occam_kit.py` for every bug fix or new feature.
- **Honest Benchmarks** — Regenerate `benchmarks/results.md` and `assets/benchmark-chart.svg` via `python3 benchmarks/run_benchmarks.py --write` whenever changing Tier 0 reducers.

## Local Verification
```bash
bash -n install.sh
python3 scripts/occam.py audit skills --max-startup-tokens 350
python3 -m unittest discover -s tests -v
python3 benchmarks/run_benchmarks.py --write
```
