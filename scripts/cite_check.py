#!/usr/bin/env python3
"""Tier 0 verified-source research ledger gate.

Validates Markdown research ledgers (.occam/research.md) against an explicit
evidence hierarchy:
  T1 = Primary artifact (official docs, source code, RFC/spec, peer-reviewed paper, local benchmark)
  T2 = Reputable benchmark, maintainer issue/PR, engineering post with reproducible code
  T3 = Secondary blog, forum, or model memory (CANNOT back a 'Verified' claim alone)

Stdlib-only (Python 3.9+).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

VALID_TIERS = {"T1", "T2", "T3"}
VALID_STATUSES = {"Verified", "Provisional", "Contradicted", "Rejected"}

SOURCE_RE = re.compile(
    r"(https?://\S+|doi:\S+|arXiv:\S+|file://\S+|[\w./-]+\.(?:py|ts|tsx|js|swift|go|rs|md|json|yaml|yml|toml)(?:#L\d+)?)",
    re.IGNORECASE,
)
VERSION_OR_DATE_RE = re.compile(
    r"(\b20\d{2}-\d{2}-\d{2}\b|\b20\d{2}\b|\bv?\d+\.\d+(?:\.\d+)?\b|\bcommit:[0-9a-f]{6,40}\b)",
    re.IGNORECASE,
)


def parse_research_table(text: str) -> List[Dict[str, str]]:
    """Extract evidence rows from Markdown tables with 5 columns."""
    rows: List[Dict[str, str]] = []
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or not line.endswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        lower_first = cells[0].lower()
        if lower_first == "claim" and cells[1].lower() == "tier":
            in_table = True
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if not in_table:
            continue
        rows.append(
            {
                "claim": cells[0],
                "tier": cells[1].upper(),
                "source": cells[2],
                "version_date": cells[3],
                "status": cells[4],
            }
        )
    return rows


def validate_ledger(path: Path, strict: bool = False) -> Dict[str, object]:
    if not path.exists():
        return {
            "ok": False,
            "file": str(path),
            "claims_total": 0,
            "verified_t1_t2": 0,
            "provisional": 0,
            "errors": [f"Research ledger not found: {path}"],
            "warnings": [],
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    rows = parse_research_table(text)
    errors: List[str] = []
    warnings: List[str] = []
    verified_strong = 0
    provisional_count = 0

    if not rows:
        errors.append(
            "No valid 5-column evidence table found "
            "(expected headers: | Claim | Tier | Source | Version/Date | Status |)."
        )

    for idx, row in enumerate(rows, 1):
        label = f"Row {idx} ({row['claim'][:40]})"
        tier = row["tier"]
        status = row["status"]
        source = row["source"]
        ver_date = row["version_date"]

        if tier not in VALID_TIERS:
            errors.append(f"{label}: invalid Tier {tier!r} (must be T1, T2, or T3).")

        if status not in VALID_STATUSES:
            errors.append(
                f"{label}: invalid Status {status!r} "
                f"(must be one of {', '.join(sorted(VALID_STATUSES))})."
            )

        if not SOURCE_RE.search(source):
            errors.append(
                f"{label}: missing verifiable Source URL, DOI/arXiv ID, or repo file path ({source!r})."
            )

        if not VERSION_OR_DATE_RE.search(ver_date):
            errors.append(
                f"{label}: missing Version or Date (e.g., 2026-11-21, v3.12, commit:abc1234)."
            )

        if status == "Verified":
            if tier == "T3":
                errors.append(
                    f"{label}: 'Verified' claim cannot rely solely on T3 secondary source; "
                    "confirm with a T1/T2 source or downgrade to 'Provisional'."
                )
            elif tier in {"T1", "T2"}:
                verified_strong += 1
        elif status == "Provisional":
            provisional_count += 1
            msg = f"{label}: still Provisional — confirm with T1 source before locking core architecture."
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)

    ok = len(errors) == 0 and len(rows) > 0
    return {
        "ok": ok,
        "file": str(path),
        "claims_total": len(rows),
        "verified_t1_t2": verified_strong,
        "provisional": provisional_count,
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a research evidence ledger against Occam-Kit source-tier rules."
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=".occam/research.md",
        help="Path to research ledger Markdown file (default: .occam/research.md).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail gate if any Provisional claims remain unresolved.",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = validate_ledger(Path(args.file), strict=args.strict)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = "PASS" if report["ok"] else "FAIL"
        print(
            f"[occam cite] {status} | {report['file']} | "
            f"claims={report['claims_total']} verified(T1/T2)={report['verified_t1_t2']} "
            f"provisional={report['provisional']}"
        )
        for err in report["errors"]:
            print(f"  ERROR: {err}")
        for warn in report["warnings"]:
            print(f"  WARN:  {warn}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
