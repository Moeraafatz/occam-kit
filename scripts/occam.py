#!/usr/bin/env python3
"""Occam-Kit unified Tier 0 CLI dispatcher.

Usage:
  python3 scripts/occam.py map [--root .] [--focus dir] [--max-tokens 1800] [--stats]
  python3 scripts/occam.py run [--max-lines 80] -- <command...>
  python3 scripts/occam.py ledger <init|decide|step|deadend|checkpoint|handoff|show> ...
  python3 scripts/occam.py cite [file] [--strict]
  python3 scripts/occam.py audit [skills_dir] [--max-startup-tokens 400]
  python3 scripts/occam.py budget <estimate|compare> ...
  python3 scripts/occam.py doctor [--root .]
"""

from __future__ import annotations

import argparse
import platform
import shutil
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cite_check  # noqa: E402
import ledger  # noqa: E402
import repo_map  # noqa: E402
import token_budget  # noqa: E402
import trim_run  # noqa: E402


def run_doctor(root: Path) -> int:
    print("Occam-Kit Doctor")
    print("-" * 52)
    print(f"Python:   {platform.python_version()} (requires >= 3.9)")
    git_bin = shutil.which("git")
    print(f"Git:      {git_bin or 'not found'}")

    candidates = [
        root / "skills",
        root / ".agents" / "skills",
        root / ".claude" / "skills",
        root / ".gemini" / "skills",
        root / ".gemini" / "antigravity" / "skills",
    ]
    found_skills = [p for p in candidates if p.exists() and any(p.iterdir())]
    overall_ok = True

    if found_skills:
        for sdir in found_skills:
            occam_rep = token_budget.audit_skills_dir(sdir, max_startup_tokens=400, prefix="occam-")
            full_rep = token_budget.audit_skills_dir(sdir, max_startup_tokens=400)
            has_occam = len(occam_rep.get("skills", [])) > 0
            total_count = len(full_rep.get("skills", []))
            total_tok = int(full_rep.get("total_startup_tokens", 0))

            if has_occam:
                occam_ok = bool(occam_rep["ok"])
                occam_tok = int(occam_rep["total_startup_tokens"])
                badge = "PASS" if occam_ok else "FAIL"
                if not occam_ok:
                    overall_ok = False
                if total_count > len(occam_rep["skills"]):
                    tax_note = (
                        f" | folder total: {total_count} skills = {total_tok} tok "
                        f"({'WARN: high context tax' if total_tok > 400 else 'OK'})"
                    )
                else:
                    tax_note = ""
                print(
                    f"Skills:   [{badge}] {sdir} "
                    f"(occam={occam_tok} tok{tax_note})"
                )
            else:
                badge = "PASS" if full_rep["ok"] else "WARN"
                print(
                    f"Skills:   [{badge}] {sdir} "
                    f"({total_count} skills, startup={total_tok} tok)"
                )
    else:
        print("Skills:   [INFO] No local skills directory found under repo root.")

    state_md = root / ".occam" / "state.md"
    research_md = root / ".occam" / "research.md"
    print(f"Ledger:   {'present' if state_md.exists() else 'not initialized'} ({state_md})")
    if research_md.exists():
        rep = cite_check.validate_ledger(research_md)
        badge = "PASS" if rep["ok"] else "WARN"
        print(
            f"Research: [{badge}] {research_md} "
            f"(claims={rep['claims_total']}, verified={rep['verified_t1_t2']})"
        )
    else:
        print(f"Research: not initialized ({research_md})")

    print("-" * 52)
    return 0 if overall_ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__.strip())
        return 0

    cmd, rest = args[0], args[1:]
    if cmd == "map":
        return repo_map.main(rest)
    if cmd == "run":
        return trim_run.main(rest)
    if cmd == "ledger":
        return ledger.main(rest)
    if cmd == "cite":
        return cite_check.main(rest)
    if cmd == "audit":
        return token_budget.main(["audit-skills", *rest])
    if cmd == "budget":
        return token_budget.main(rest)
    if cmd == "doctor":
        p = argparse.ArgumentParser(prog="occam.py doctor")
        p.add_argument("--root", default=".", help="Workspace root directory.")
        ns = p.parse_args(rest)
        return run_doctor(Path(ns.root).resolve())

    print(f"Unknown occam subcommand: {cmd!r}\n", file=sys.stderr)
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
