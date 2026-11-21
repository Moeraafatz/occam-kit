#!/usr/bin/env python3
"""Tier 0 persistent state ledger & anti-context-poisoning handoff generator.

Stores compact project state in .occam/state.json and mirrors a clean human-readable
.occam/state.md so agents can resume across sessions or switch to cheaper models
without replaying bloated chat history or repeating failed debugging loops.

Stdlib-only (Python 3.9+).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from token_budget import estimate_tokens  # noqa: E402

DEFAULT_DIR = Path(".occam")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_paths(ledger_dir: Path) -> tuple[Path, Path]:
    return ledger_dir / "state.json", ledger_dir / "state.md"


def load_state(ledger_dir: Path) -> Dict[str, object]:
    json_path, _ = state_paths(ledger_dir)
    if not json_path.exists():
        raise FileNotFoundError(
            f"Ledger not initialized at {json_path}. Run: ledger.py init --goal '...'"
        )
    return json.loads(json_path.read_text(encoding="utf-8"))


def render_markdown(state: Dict[str, object]) -> str:
    lines: List[str] = [
        "# Occam State Ledger",
        "",
        f"- **Updated:** {state.get('updated_at', '')}",
        f"- **Goal:** {state.get('goal', '')}",
    ]
    constraints = state.get("constraints", [])
    if constraints:
        lines.append(f"- **Constraints:** {'; '.join(constraints)}")
    non_goals = state.get("non_goals", [])
    if non_goals:
        lines.append(f"- **Non-Goals:** {'; '.join(non_goals)}")

    lines.extend(["", "## Locked Decisions"])
    decisions = state.get("decisions", [])
    if decisions:
        for dec in decisions:
            src = f" *(source: {dec['source']})*" if dec.get("source") else ""
            lines.append(f"- **{dec['id']}:** {dec['decision']} — {dec['reason']}{src}")
    else:
        lines.append("- *(none yet)*")

    lines.extend(["", "## Plan Steps"])
    steps = state.get("steps", [])
    if steps:
        for idx, step in enumerate(steps, 1):
            marker = {"done": "x", "active": ">", "todo": " "}.get(step.get("status", "todo"), " ")
            tier = f" [{step['tier']}]" if step.get("tier") else ""
            lines.append(f"- [{marker}] {idx}. {step['title']}{tier}")
    else:
        lines.append("- *(none yet)*")

    lines.extend(["", "## Dead Ends (Do Not Repeat)"])
    deadends = state.get("deadends", [])
    if deadends:
        for de in deadends:
            lines.append(f"- Tried: {de['tried']} -> Failed: {de['why']}")
    else:
        lines.append("- *(none)*")

    cp = state.get("checkpoint") or {}
    lines.extend(["", "## Current Checkpoint"])
    if cp:
        lines.append(f"- **Done so far:** {cp.get('summary', '')}")
        lines.append(f"- **Next action:** {cp.get('next', '')}")
        if cp.get("tier"):
            lines.append(f"- **Recommended model tier:** {cp['tier']}")
    else:
        lines.append("- *(no checkpoint yet)*")

    return "\n".join(lines).rstrip() + "\n"


def save_state(ledger_dir: Path, state: Dict[str, object]) -> None:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now()
    json_path, md_path = state_paths(ledger_dir)
    json_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(state), encoding="utf-8")


def build_handoff(state: Dict[str, object], max_tokens: int = 350) -> str:
    """Emit a token-capped resume brief dropping completed history."""
    lines: List[str] = [
        "# Occam Handoff Brief",
        f"Goal: {state.get('goal', '')}",
    ]
    constraints = state.get("constraints", [])
    if constraints:
        lines.append(f"Constraints: {'; '.join(constraints)}")
    non_goals = state.get("non_goals", [])
    if non_goals:
        lines.append(f"Non-Goals: {'; '.join(non_goals)}")

    decisions = state.get("decisions", [])
    if decisions:
        dec_str = " | ".join(f"{d['id']}: {d['decision']}" for d in decisions[-6:])
        lines.append(f"Locked: {dec_str}")

    steps = state.get("steps", [])
    open_steps = [
        f"{idx}. [{s.get('tier', 'T2')}] {s['title']}"
        for idx, s in enumerate(steps, 1)
        if s.get("status") != "done"
    ]
    done_count = sum(1 for s in steps if s.get("status") == "done")
    if steps:
        lines.append(f"Progress: {done_count}/{len(steps)} done")
    if open_steps:
        lines.append("Remaining:")
        lines.extend(f"  - {s}" for s in open_steps[:5])

    deadends = state.get("deadends", [])
    if deadends:
        lines.append("Do NOT retry:")
        for de in deadends[-4:]:
            lines.append(f"  - {de['tried']} ({de['why']})")

    cp = state.get("checkpoint") or {}
    if cp.get("next"):
        tier_note = f" [Use {cp['tier']}]" if cp.get("tier") else ""
        lines.append(f"Next{tier_note}: {cp['next']}")

    text = "\n".join(lines).rstrip() + "\n"
    while estimate_tokens(text) > max_tokens and len(lines) > 4:
        lines.pop(-2)
        text = "\n".join(lines).rstrip() + "\n"
    return text


def cmd_init(args: argparse.Namespace) -> int:
    state: Dict[str, object] = {
        "goal": args.goal.strip(),
        "constraints": [c.strip() for c in args.constraint if c.strip()],
        "non_goals": [n.strip() for n in args.non_goal if n.strip()],
        "decisions": [],
        "steps": [],
        "deadends": [],
        "checkpoint": {},
    }
    save_state(Path(args.dir), state)
    print(f"Initialized ledger at {Path(args.dir) / 'state.md'}")
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    ledger_dir = Path(args.dir)
    state = load_state(ledger_dir)
    decisions = list(state.get("decisions", []))
    dec_id = args.id or f"D{len(decisions) + 1}"
    decisions = [d for d in decisions if d.get("id") != dec_id]
    decisions.append(
        {
            "id": dec_id,
            "decision": args.decision.strip(),
            "reason": args.reason.strip(),
            "source": (args.source or "").strip(),
        }
    )
    state["decisions"] = decisions
    save_state(ledger_dir, state)
    print(f"Recorded decision {dec_id}.")
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    ledger_dir = Path(args.dir)
    state = load_state(ledger_dir)
    steps = list(state.get("steps", []))

    if args.action == "add":
        if not args.title:
            print("Error: --title is required for 'step add'.", file=sys.stderr)
            return 1
        steps.append({"title": args.title.strip(), "status": "todo", "tier": args.tier})
        state["steps"] = steps
        save_state(ledger_dir, state)
        print(f"Added step {len(steps)} [{args.tier}]: {args.title.strip()}")
        return 0

    if args.index is None or args.index < 1 or args.index > len(steps):
        print(f"Error: step index out of range (1..{len(steps)}).", file=sys.stderr)
        return 1

    if args.action == "active":
        for i, s in enumerate(steps):
            if s.get("status") == "active" and i != args.index - 1:
                s["status"] = "todo"
        steps[args.index - 1]["status"] = "active"
    elif args.action == "done":
        steps[args.index - 1]["status"] = "done"

    state["steps"] = steps
    save_state(ledger_dir, state)
    print(f"Marked step {args.index} as {args.action}.")
    return 0


def cmd_deadend(args: argparse.Namespace) -> int:
    ledger_dir = Path(args.dir)
    state = load_state(ledger_dir)
    deadends = list(state.get("deadends", []))
    deadends.append({"tried": args.tried.strip(), "why": args.why.strip()})
    state["deadends"] = deadends
    save_state(ledger_dir, state)
    print(f"Recorded dead end #{len(deadends)}.")
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    ledger_dir = Path(args.dir)
    state = load_state(ledger_dir)
    state["checkpoint"] = {
        "summary": args.summary.strip(),
        "next": args.next.strip(),
        "tier": args.tier,
    }
    save_state(ledger_dir, state)
    print("Updated checkpoint.")
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    state = load_state(Path(args.dir))
    brief = build_handoff(state, max_tokens=args.max_tokens)
    sys.stdout.write(brief)
    if args.stats:
        print(f"[occam handoff] {estimate_tokens(brief)} est. tokens (cap={args.max_tokens})")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    _, md_path = state_paths(Path(args.dir))
    if not md_path.exists():
        print(f"Error: ledger not found at {md_path}", file=sys.stderr)
        return 1
    sys.stdout.write(md_path.read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Maintain compact persistent state to prevent context poisoning."
    )
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="Ledger directory (default: .occam).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a new project state ledger.")
    p_init.add_argument("--goal", required=True, help="Single-sentence project or task goal.")
    p_init.add_argument("--constraint", action="append", default=[], help="Hard constraint (repeatable).")
    p_init.add_argument("--non-goal", action="append", default=[], help="Explicit non-goal (repeatable).")
    p_init.set_defaults(func=cmd_init)

    p_dec = sub.add_parser("decide", help="Lock an architectural or product decision.")
    p_dec.add_argument("--id", default=None, help="Decision ID (e.g., D1). Auto-increments if omitted.")
    p_dec.add_argument("--decision", required=True, help="The chosen approach.")
    p_dec.add_argument("--reason", required=True, help="Concise rationale.")
    p_dec.add_argument("--source", default="", help="Verified source URL/path (optional).")
    p_dec.set_defaults(func=cmd_decide)

    p_step = sub.add_parser("step", help="Manage ordered execution steps.")
    p_step.add_argument("action", choices=["add", "active", "done"])
    p_step.add_argument("--title", default=None, help="Step description (for 'add').")
    p_step.add_argument("--index", type=int, default=None, help="1-based step number (for active/done).")
    p_step.add_argument("--tier", choices=["T0", "T1", "T2", "T3"], default="T2", help="Minimum model tier.")
    p_step.set_defaults(func=cmd_step)

    p_de = sub.add_parser("deadend", help="Record a failed hypothesis so agents never repeat it.")
    p_de.add_argument("--tried", required=True, help="What was attempted.")
    p_de.add_argument("--why", required=True, help="Why it failed.")
    p_de.set_defaults(func=cmd_deadend)

    p_cp = sub.add_parser("checkpoint", help="Record a compact session checkpoint.")
    p_cp.add_argument("--summary", required=True, help="What is verified done.")
    p_cp.add_argument("--next", required=True, help="Exact next atomic action.")
    p_cp.add_argument("--tier", choices=["T0", "T1", "T2", "T3"], default="T1", help="Recommended next tier.")
    p_cp.set_defaults(func=cmd_checkpoint)

    p_ho = sub.add_parser("handoff", help="Print token-capped resume brief for fresh context.")
    p_ho.add_argument("--max-tokens", type=int, default=350, help="Token cap (default: 350).")
    p_ho.add_argument("--stats", action="store_true", help="Print estimated token footer.")
    p_ho.set_defaults(func=cmd_handoff)

    p_sh = sub.add_parser("show", help="Print full .occam/state.md.")
    p_sh.set_defaults(func=cmd_show)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
