#!/usr/bin/env python3
"""Tier 0 zero-token command runner & log reducer.

Runs a shell command (test suite, linter, compiler), preserves full raw output in
.occam/last_run.log, and emits a surgically compressed summary keeping only errors,
failure blocks, stack heads, and final pass/fail counts.

Stdlib-only (Python 3.9+). Prevents verbose build/test logs from poisoning context.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from token_budget import estimate_tokens  # noqa: E402

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

ERROR_PATTERNS = [
    re.compile(r"\b(FAIL|FAILED|ERROR|FATAL|PANIC|EXCEPTION)\b"),
    re.compile(r"\b(AssertionError|TypeError|ValueError|KeyError|AttributeError|ImportError|SyntaxError|RuntimeError|NameError|ZeroDivisionError)\b"),
    re.compile(r"^Traceback \(most recent call last\):"),
    re.compile(r"^\s*E\s{3,}"),
    re.compile(r":\d+(?::\d+)?:\s*(?:error|fatal error):"),
    re.compile(r"^--- FAIL:"),
    re.compile(r"^error\[E\d+\]:"),
    re.compile(r"^\s*✖|^\s*✗|^\s*×"),
]

SUMMARY_PATTERNS = [
    re.compile(r"\b\d+\s+(?:passed|failed|skipped|errors?|warnings?)\b", re.IGNORECASE),
    re.compile(r"^(?:Ran \d+ tests?|OK|FAILED \(|Test Suites:|Tests:|PASS\b|FAIL\b)"),
    re.compile(r"^test result:"),
    re.compile(r"^Build (?:complete|failed)", re.IGNORECASE),
]

WARNING_PATTERN = re.compile(r"\bwarning(?:\[[^\]]+\])?:", re.IGNORECASE)


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def reduce_log(
    raw_output: str,
    exit_code: int,
    max_lines: int = 80,
    context_lines: int = 2,
    duration_sec: Optional[float] = None,
    log_path: Optional[str] = None,
) -> Tuple[str, int, int]:
    """Compress raw command output while preserving all failure evidence."""
    cleaned = strip_ansi(raw_output)
    lines = cleaned.splitlines()
    raw_tokens = estimate_tokens(cleaned)

    selected_indices = set()
    summary_lines: List[str] = []
    warning_lines: List[str] = []

    for idx, line in enumerate(lines):
        if any(pat.search(line) for pat in SUMMARY_PATTERNS):
            summary_lines.append(line.rstrip())
        if WARNING_PATTERN.search(line):
            warning_lines.append(line.rstrip())
        if exit_code != 0 and any(pat.search(line) for pat in ERROR_PATTERNS):
            start = max(0, idx - context_lines)
            end = min(len(lines), idx + context_lines + 1)
            for j in range(start, end):
                selected_indices.add(j)

    out_lines: List[str] = []
    status = "OK" if exit_code == 0 else "FAIL"
    dur_str = f" | {duration_sec:.2f}s" if duration_sec is not None else ""
    out_lines.append(f"[occam run] {status} (exit={exit_code}{dur_str} | raw={len(lines)} lines)")

    if exit_code == 0:
        # Keep only summary lines + last few non-empty lines + capped unique warnings
        dedup_summary: List[str] = []
        for s in summary_lines[-8:]:
            if s not in dedup_summary:
                dedup_summary.append(s)
        if dedup_summary:
            out_lines.append("Summary:")
            out_lines.extend(f"  {s}" for s in dedup_summary)
        else:
            tail = [ln.rstrip() for ln in lines if ln.strip()][-6:]
            if tail:
                out_lines.append("Tail:")
                out_lines.extend(f"  {ln}" for ln in tail)

        if warning_lines:
            uniq_warn = list(dict.fromkeys(warning_lines))
            out_lines.append(f"Warnings ({len(uniq_warn)} unique, showing up to 5):")
            out_lines.extend(f"  {w}" for w in uniq_warn[:5])
    else:
        # Failure path: preserve diagnostic blocks with deduplication
        if selected_indices:
            out_lines.append("Errors & Failures:")
            prev_idx: Optional[int] = None
            seen_error_lines = set()
            emitted = 0
            for idx in sorted(selected_indices):
                line = lines[idx].rstrip()
                if not line.strip():
                    continue
                if prev_idx is not None and idx > prev_idx + 1:
                    out_lines.append("  ---")
                norm = line.strip()
                if norm in seen_error_lines and len(norm) > 20:
                    prev_idx = idx
                    continue
                seen_error_lines.add(norm)
                out_lines.append(f"  L{idx + 1}: {line}")
                emitted += 1
                prev_idx = idx
                if emitted >= max(10, max_lines - 14):
                    out_lines.append(
                        f"  ... (truncated at {max_lines} lines; inspect full log if needed)"
                    )
                    break
        else:
            # Fallback if tool didn't match known error patterns: keep last 25 non-empty lines
            tail = [ln.rstrip() for ln in lines if ln.strip()][-min(25, max_lines - 6) :]
            out_lines.append("Last output lines:")
            out_lines.extend(f"  {ln}" for ln in tail)

        if summary_lines:
            dedup_summary = list(dict.fromkeys(summary_lines[-5:]))
            out_lines.append("Summary:")
            out_lines.extend(f"  {s}" for s in dedup_summary)

    if log_path:
        out_lines.append(f"Full raw log saved: {log_path}")

    body_preview = "\n".join(out_lines) + "\n"
    compact_tokens = estimate_tokens(body_preview)
    saved = max(0, raw_tokens - compact_tokens)
    pct = (saved / raw_tokens * 100.0) if raw_tokens > 0 else 0.0
    out_lines.append(
        f"Tokens: {raw_tokens} -> {compact_tokens} (saved {saved} tok / {pct:.1f}%)"
    )

    final_text = "\n".join(out_lines) + "\n"
    return final_text, raw_tokens, estimate_tokens(final_text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a command and return failure-focused compressed output to save tokens."
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=80,
        help="Maximum emitted lines (default: 80).",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=2,
        help="Context lines around each error line (default: 2).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Command timeout in seconds (default: 300).",
    )
    parser.add_argument(
        "--log",
        default=".occam/last_run.log",
        help="Path to save full raw output (default: .occam/last_run.log).",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Do not write full raw output to disk.",
    )
    parser.add_argument(
        "--from-file",
        default=None,
        help="Reduce an existing log file instead of executing a command.",
    )
    parser.add_argument(
        "--exit-code",
        type=int,
        default=1,
        help="Simulated exit code when using --from-file (default: 1).",
    )
    parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Command to execute (prefix with -- if passing flags).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.from_file:
        src = Path(args.from_file)
        if not src.exists():
            print(f"Error: file not found: {src}", file=sys.stderr)
            return 1
        raw = src.read_text(encoding="utf-8", errors="replace")
        reduced, _, _ = reduce_log(
            raw_output=raw,
            exit_code=args.exit_code,
            max_lines=args.max_lines,
            context_lines=args.context,
            log_path=str(src),
        )
        sys.stdout.write(reduced)
        return args.exit_code

    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("Provide a command to run (e.g., trim_run.py -- pytest) or --from-file.")

    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=args.timeout,
        )
        raw_output = proc.stdout or ""
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        raw_output = (exc.stdout or "") + f"\nERROR: Command timed out after {args.timeout}s."
        exit_code = 124
    except FileNotFoundError:
        print(f"Error: executable not found: {cmd[0]}", file=sys.stderr)
        return 127

    duration = time.monotonic() - start
    saved_log_path: Optional[str] = None
    if not args.no_log and args.log:
        log_file = Path(args.log)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(raw_output, encoding="utf-8")
        saved_log_path = str(log_file)

    reduced, _, _ = reduce_log(
        raw_output=raw_output,
        exit_code=exit_code,
        max_lines=args.max_lines,
        context_lines=args.context,
        duration_sec=duration,
        log_path=saved_log_path,
    )
    sys.stdout.write(reduced)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
