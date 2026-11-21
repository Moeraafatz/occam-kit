#!/usr/bin/env python3
"""Tier 0 zero-token repository symbol map generator.

Extracts compact file + symbol skeletons (classes, structs, functions, headings)
using Python's AST for .py files and targeted regex extractors for JS/TS, Swift,
Go, Rust, Java/Kotlin, C/C++, Shell, and Markdown.

Stdlib-only (Python 3.9+). Cuts initial repo exploration context by 70-95%.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from token_budget import estimate_tokens  # noqa: E402

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".occam",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".build",
    ".next",
    ".nuxt",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
    "DerivedData",
    "Pods",
    "coverage",
    ".idea",
    ".vscode",
    "vendor",
}

IGNORE_FILE_GLOBS = {
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.lock",
    "poetry.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.pyc",
    "*.pyo",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.dmg",
    "*.wasm",
    "*.sqlite",
    "*.db",
}

SUPPORTED_EXTS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".swift",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".sh",
    ".bash",
    ".zsh",
    ".md",
}

MAX_FILE_BYTES = 512 * 1024

RE_JS_TS = [
    re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_]\w*)\s*="),
    re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([A-Za-z_]\w*\s*\([^)]*\))"),
    re.compile(
        r"^\s*export\s+(?:const|let)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>"
    ),
]

RE_SWIFT = [
    re.compile(r"^\s*(?:(?:public|internal|private|fileprivate|open|final|indirect)\s+)*(?:class|struct|enum|protocol|actor)\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*extension\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:(?:public|internal|private|fileprivate|open|static|class|mutating|override|nonisolated)\s+)*func\s+([A-Za-z_]\w*\s*\([^)]*\))"),
]

RE_GO = [
    re.compile(r"^type\s+([A-Za-z_]\w*\s+(?:struct|interface))"),
    re.compile(r"^func\s+((?:\([^)]+\)\s*)?[A-Za-z_]\w*\s*\([^)]*\))"),
]

RE_RUST = [
    re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*impl(?:<[^>]+>)?\s+([A-Za-z_][\w:<>\s]+?)(?:\s+where|\s*\{)"),
    re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*\s*\([^)]*\))"),
]

RE_JAVA_KT = [
    re.compile(r"^\s*(?:(?:public|private|protected|internal|abstract|final|sealed|data|open)\s+)*(?:class|interface|enum|object|record)\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:(?:public|private|protected|internal|override|suspend|inline)\s+)*fun\s+([A-Za-z_]\w*\s*\([^)]*\))"),
]

RE_C_CPP = [
    re.compile(r"^\s*(?:typedef\s+)?(?:struct|class|enum)\s+([A-Za-z_]\w*)"),
    re.compile(r"^(?:[A-Za-z_][\w:*&<>\s]+?)\s+([A-Za-z_]\w*\s*\([^;)]*\))\s*(?:const\s*)?\{"),
]

RE_SHELL = [
    re.compile(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{"),
]

RE_MD = [
    re.compile(r"^(#{1,2}\s+.+)$"),
]


def load_gitignore_patterns(root: Path) -> List[str]:
    gitignore = root / ".gitignore"
    patterns: List[str] = []
    if not gitignore.exists():
        return patterns
    for raw in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def is_ignored(rel_path: str, name: str, gitignore_patterns: Sequence[str]) -> bool:
    for glob_pat in IGNORE_FILE_GLOBS:
        if fnmatch.fnmatch(name, glob_pat):
            return True
    for pat in gitignore_patterns:
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(name, pat):
            return True
        if "/" not in pat and any(fnmatch.fnmatch(part, pat) for part in rel_path.split("/")):
            return True
    return False


def extract_python_symbols(text: str, max_symbols: int) -> List[str]:
    symbols: List[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for idx, line in enumerate(text.splitlines(), 1):
            m = re.match(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*(?:\([^)]*\))?)", line)
            if m:
                symbols.append(f"L{idx}: {m.group(0).strip().rstrip(':')}")
        return symbols[:max_symbols]

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
            base_str = f"({', '.join(bases)})" if bases else ""
            methods: List[str] = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not child.name.startswith("__") or child.name == "__init__":
                        methods.append(child.name)
            meth_str = f" [{', '.join(methods[:6])}{'...' if len(methods) > 6 else ''}]" if methods else ""
            symbols.append(f"L{node.lineno}: class {node.name}{base_str}{meth_str}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arg_names = [a.arg for a in node.args.args]
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            symbols.append(f"L{node.lineno}: {prefix} {node.name}({', '.join(arg_names[:5])})")
        if len(symbols) >= max_symbols:
            break
    return symbols


def extract_regex_symbols(text: str, patterns: Sequence[re.Pattern], max_symbols: int) -> List[str]:
    symbols: List[str] = []
    for idx, line in enumerate(text.splitlines(), 1):
        for pat in patterns:
            m = pat.search(line)
            if m:
                sig = " ".join(m.group(1).strip().split())
                if len(sig) > 84:
                    sig = sig[:81] + "..."
                symbols.append(f"L{idx}: {sig}")
                break
        if len(symbols) >= max_symbols:
            break
    return symbols


def extract_markdown_headings(text: str, max_symbols: int) -> List[str]:
    symbols: List[str] = []
    in_fence = False
    for idx, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = RE_MD[0].match(line)
        if m:
            sig = " ".join(m.group(1).strip().split())
            if len(sig) > 84:
                sig = sig[:81] + "..."
            symbols.append(f"L{idx}: {sig}")
            if len(symbols) >= max_symbols:
                break
    return symbols


def extract_symbols(path: Path, text: str, max_symbols: int) -> List[str]:
    ext = path.suffix.lower()
    if ext == ".py":
        return extract_python_symbols(text, max_symbols)
    if ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return extract_regex_symbols(text, RE_JS_TS, max_symbols)
    if ext == ".swift":
        return extract_regex_symbols(text, RE_SWIFT, max_symbols)
    if ext == ".go":
        return extract_regex_symbols(text, RE_GO, max_symbols)
    if ext == ".rs":
        return extract_regex_symbols(text, RE_RUST, max_symbols)
    if ext in {".java", ".kt", ".kts"}:
        return extract_regex_symbols(text, RE_JAVA_KT, max_symbols)
    if ext in {".c", ".h", ".cpp", ".hpp", ".cc"}:
        return extract_regex_symbols(text, RE_C_CPP, max_symbols)
    if ext in {".sh", ".bash", ".zsh"}:
        return extract_regex_symbols(text, RE_SHELL, max_symbols)
    if ext == ".md":
        return extract_markdown_headings(text, min(max_symbols, 6))
    return []


def generate_repo_map(
    root: Path,
    focus: Optional[str] = None,
    max_tokens: int = 1800,
    max_symbols: int = 12,
) -> Tuple[str, Dict[str, int]]:
    root = root.resolve()
    scan_root = (root / focus).resolve() if focus else root
    if not scan_root.exists():
        raise FileNotFoundError(f"Path not found: {scan_root}")

    gitignore_patterns = load_gitignore_patterns(root)
    entries: List[Tuple[str, int, List[str]]] = []
    raw_total_tokens = 0
    total_files_scanned = 0

    for dirpath, dirnames, filenames in os.walk(scan_root):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in IGNORE_DIRS and not is_ignored(
                str(Path(dirpath, d).relative_to(root)).replace(os.sep, "/"),
                d,
                gitignore_patterns,
            )
        )
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            rel = str(fpath.relative_to(root)).replace(os.sep, "/")
            if is_ignored(rel, fname, gitignore_patterns):
                continue
            if fpath.suffix.lower() not in SUPPORTED_EXTS:
                continue
            try:
                if fpath.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            total_files_scanned += 1
            raw_total_tokens += estimate_tokens(text)
            line_count = len(text.splitlines())
            symbols = extract_symbols(fpath, text, max_symbols=max_symbols)
            entries.append((rel, line_count, symbols))

    # Prioritize code files over Markdown when budget is tight
    entries.sort(key=lambda item: (1 if item[0].endswith(".md") else 0, item[0]))

    header = f"# Repo Map: {root.name}" + (f" ({focus})" if focus else "")
    lines: List[str] = [header, ""]
    used_tokens = estimate_tokens("\n".join(lines))
    included_files = 0
    omitted_files = 0

    for rel, line_count, symbols in entries:
        block_lines = [f"- `{rel}` ({line_count}L)"]
        for sym in symbols:
            block_lines.append(f"  - {sym}")
        block = "\n".join(block_lines) + "\n"
        block_tok = estimate_tokens(block)

        if used_tokens + block_tok > max_tokens and included_files > 0:
            omitted_files += 1
            continue
        lines.extend(block_lines)
        used_tokens += block_tok
        included_files += 1

    if omitted_files > 0:
        lines.append("")
        lines.append(
            f"... ({omitted_files} more files omitted to stay within --max-tokens {max_tokens}; "
            "pass --focus <dir> to inspect a subdirectory.)"
        )

    output = "\n".join(lines).rstrip() + "\n"
    map_tokens = estimate_tokens(output)
    stats = {
        "files_scanned": total_files_scanned,
        "files_included": included_files,
        "files_omitted": omitted_files,
        "raw_tokens": raw_total_tokens,
        "map_tokens": map_tokens,
        "tokens_saved": max(0, raw_total_tokens - map_tokens),
    }
    return output, stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a compact symbol skeleton of a repository to avoid reading whole files."
    )
    parser.add_argument("--root", default=".", help="Repository root directory (default: .).")
    parser.add_argument("--focus", default=None, help="Optional subdirectory to focus on.")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1800,
        help="Hard output token budget cap (default: 1800).",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=12,
        help="Maximum symbols listed per file (default: 12).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print token-savings summary footer.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output, stats = generate_repo_map(
            root=Path(args.root),
            focus=args.focus,
            max_tokens=args.max_tokens,
            max_symbols=args.max_symbols,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(output)
    if args.stats:
        pct = (
            (stats["tokens_saved"] / stats["raw_tokens"] * 100.0)
            if stats["raw_tokens"] > 0
            else 0.0
        )
        print(
            f"\n[occam map] scanned={stats['files_scanned']} files | "
            f"raw={stats['raw_tokens']} tok -> map={stats['map_tokens']} tok "
            f"(saved {stats['tokens_saved']} tok / {pct:.1f}%)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
