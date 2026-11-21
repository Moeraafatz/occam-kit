#!/usr/bin/env python3
"""Deterministic token estimator and agentskills.io compliance auditor.

Stdlib-only (Python 3.9+). Uses the standard ~4 characters/token BPE heuristic
so token budgets and startup context tax can be measured offline at zero cost.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def estimate_tokens(text: str) -> int:
    """Estimate BPE token count deterministically (~4 chars/token heuristic)."""
    if not text:
        return 0
    return max(1, int(math.ceil(len(text) / 4.0)))


def parse_frontmatter(markdown_text: str) -> Tuple[Optional[Dict[str, object]], str, List[str]]:
    """Parse minimal YAML frontmatter from a SKILL.md or .mdc file."""
    errors: List[str] = []
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, markdown_text, ["Missing opening '---' YAML frontmatter delimiter."]

    end_idx: Optional[int] = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        return None, markdown_text, ["Missing closing '---' YAML frontmatter delimiter."]

    front_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")

    data: Dict[str, object] = {}
    current_map_key: Optional[str] = None
    current_multiline_key: Optional[str] = None
    multiline_buf: List[str] = []

    def flush_multiline() -> None:
        nonlocal current_multiline_key, multiline_buf
        if current_multiline_key is not None:
            data[current_multiline_key] = " ".join(
                part.strip() for part in multiline_buf if part.strip()
            )
            current_multiline_key = None
            multiline_buf = []

    for raw_line in front_lines:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if current_multiline_key is not None:
            if raw_line.startswith(" ") or raw_line.startswith("\t"):
                multiline_buf.append(raw_line.strip())
                continue
            flush_multiline()

        if current_map_key is not None and (raw_line.startswith("  ") or raw_line.startswith("\t")):
            stripped = raw_line.strip()
            if ":" in stripped:
                sub_k, sub_v = stripped.split(":", 1)
                sub_dict = data.setdefault(current_map_key, {})
                if isinstance(sub_dict, dict):
                    sub_dict[sub_k.strip()] = sub_v.strip().strip('"').strip("'")
                continue

        current_map_key = None
        if ":" not in raw_line:
            errors.append(f"Malformed frontmatter line: {raw_line!r}")
            continue

        key, val = raw_line.split(":", 1)
        key = key.strip()
        val = val.strip()

        if val in (">", "|", ">-", "|-"):
            current_multiline_key = key
            multiline_buf = []
        elif val == "":
            current_map_key = key
            data[key] = {}
        else:
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            data[key] = val

    flush_multiline()
    return data, body, errors


def audit_skills_dir(skills_dir: Path, max_startup_tokens: int = 400) -> Dict[str, object]:
    """Validate all SKILL.md files under skills_dir and compute startup context tax."""
    results: List[Dict[str, object]] = []
    total_startup_tokens = 0
    total_body_tokens = 0
    all_ok = True

    if not skills_dir.exists():
        return {
            "ok": False,
            "error": f"Skills directory not found: {skills_dir}",
            "skills": [],
            "total_startup_tokens": 0,
            "total_body_tokens": 0,
            "max_startup_tokens": max_startup_tokens,
        }

    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not skill_dirs:
        return {
            "ok": False,
            "error": f"No skill subdirectories found under: {skills_dir}",
            "skills": [],
            "total_startup_tokens": 0,
            "total_body_tokens": 0,
            "max_startup_tokens": max_startup_tokens,
        }

    for folder in skill_dirs:
        skill_md = folder / "SKILL.md"
        issues: List[str] = []
        if not skill_md.exists():
            all_ok = False
            results.append(
                {
                    "folder": folder.name,
                    "ok": False,
                    "startup_tokens": 0,
                    "body_tokens": 0,
                    "issues": ["Missing required SKILL.md file."],
                }
            )
            continue

        raw_text = skill_md.read_text(encoding="utf-8")
        fm, body, parse_errors = parse_frontmatter(raw_text)
        issues.extend(parse_errors)

        name = str(fm.get("name", "")) if fm else ""
        description = str(fm.get("description", "")) if fm else ""

        if not name:
            issues.append("Missing required 'name' field in frontmatter.")
        else:
            if len(name) > 64:
                issues.append(f"'name' exceeds 64 characters ({len(name)}).")
            if not SKILL_NAME_RE.match(name):
                issues.append(
                    f"'name' must be lowercase alphanumeric with single hyphens: {name!r}"
                )
            if name != folder.name:
                issues.append(
                    f"'name' ({name!r}) does not match folder name ({folder.name!r})."
                )

        if not description:
            issues.append("Missing required 'description' field in frontmatter.")
        elif len(description) > 1024:
            issues.append(f"'description' exceeds 1024 characters ({len(description)}).")

        if not body.strip():
            issues.append("SKILL.md instruction body is empty.")

        startup_payload = f"{name}: {description}"
        startup_tokens = estimate_tokens(startup_payload)
        body_tokens = estimate_tokens(body)
        total_startup_tokens += startup_tokens
        total_body_tokens += body_tokens

        skill_ok = len(issues) == 0
        if not skill_ok:
            all_ok = False

        results.append(
            {
                "folder": folder.name,
                "name": name,
                "ok": skill_ok,
                "startup_tokens": startup_tokens,
                "body_tokens": body_tokens,
                "issues": issues,
            }
        )

    budget_ok = total_startup_tokens <= max_startup_tokens
    if not budget_ok:
        all_ok = False

    return {
        "ok": all_ok,
        "budget_ok": budget_ok,
        "skills": results,
        "total_startup_tokens": total_startup_tokens,
        "total_body_tokens": total_body_tokens,
        "max_startup_tokens": max_startup_tokens,
    }


def cmd_estimate(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    stats = {
        "file": str(path),
        "chars": len(text),
        "lines": len(text.splitlines()),
        "words": len(text.split()),
        "est_tokens": estimate_tokens(text),
    }
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print(
            f"{path}: {stats['est_tokens']} est. tokens "
            f"({stats['lines']} lines, {stats['words']} words, {stats['chars']} chars)"
        )
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    raw_path = Path(args.raw)
    compact_path = Path(args.compact)
    for p in (raw_path, compact_path):
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            return 1

    raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
    compact_text = compact_path.read_text(encoding="utf-8", errors="replace")
    raw_tok = estimate_tokens(raw_text)
    compact_tok = estimate_tokens(compact_text)
    saved = raw_tok - compact_tok
    pct = (saved / raw_tok * 100.0) if raw_tok > 0 else 0.0

    payload = {
        "raw_tokens": raw_tok,
        "compact_tokens": compact_tok,
        "tokens_saved": saved,
        "reduction_pct": round(pct, 1),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Raw: {raw_tok} tok -> Compact: {compact_tok} tok "
            f"(saved {saved} tok / {pct:.1f}%)"
        )
    return 0


def cmd_audit_skills(args: argparse.Namespace) -> int:
    report = audit_skills_dir(Path(args.dir), max_startup_tokens=args.max_startup_tokens)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if "error" in report:
            print(f"FAIL: {report['error']}", file=sys.stderr)
            return 1
        print("Occam-Kit Skill Audit (agentskills.io compliance + startup tax)")
        print("-" * 68)
        for item in report["skills"]:
            status = "PASS" if item["ok"] else "FAIL"
            print(
                f"[{status}] {item['folder']:<24} "
                f"startup={item['startup_tokens']:>4} tok  body={item['body_tokens']:>5} tok"
            )
            for issue in item["issues"]:
                print(f"       - {issue}")
        print("-" * 68)
        budget_status = "PASS" if report["budget_ok"] else "OVER BUDGET"
        print(
            f"Total startup discovery tax: {report['total_startup_tokens']} / "
            f"{report['max_startup_tokens']} tok [{budget_status}]"
        )
        print(
            f"Deferred on-demand body total: {report['total_body_tokens']} tok "
            "(loaded only when a skill triggers)"
        )
    return 0 if report["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic token budget estimator and SKILL.md compliance auditor."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_est = sub.add_parser("estimate", help="Estimate tokens for a file.")
    p_est.add_argument("file", help="Path to text file.")
    p_est.add_argument("--json", action="store_true", help="Output JSON.")
    p_est.set_defaults(func=cmd_estimate)

    p_cmp = sub.add_parser("compare", help="Compare raw vs. compact token counts.")
    p_cmp.add_argument("raw", help="Raw text file path.")
    p_cmp.add_argument("compact", help="Compact text file path.")
    p_cmp.add_argument("--json", action="store_true", help="Output JSON.")
    p_cmp.set_defaults(func=cmd_compare)

    p_aud = sub.add_parser("audit-skills", help="Validate SKILL.md files and startup tax.")
    p_aud.add_argument("dir", nargs="?", default="skills", help="Directory containing skill folders.")
    p_aud.add_argument(
        "--max-startup-tokens",
        type=int,
        default=400,
        help="Maximum allowed combined startup metadata tokens (default: 400).",
    )
    p_aud.add_argument("--json", action="store_true", help="Output JSON.")
    p_aud.set_defaults(func=cmd_audit_skills)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
