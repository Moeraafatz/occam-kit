#!/usr/bin/env bash
set -euo pipefail

# Occam-Kit Universal Installer
# Installs portable SKILL.md packages, IDE rules, and Tier 0 zero-token Python scripts
# across Claude Code, OpenAI Codex CLI, Cursor, Gemini CLI, Antigravity, and GitHub Copilot.

REPO_URL="${OCCAM_KIT_REPO:-https://github.com/Moeraafatz/occam-kit.git}"
TARGETS="all"
SCOPE="project"
SCOPE_EXPLICIT=0
PROJECT_DIR="$(pwd)"
DRY_RUN=0
UNINSTALL=0
TEMP_CLONE=""
AGENTS_SKILLS_INSTALLED=0

usage() {
  cat <<'EOF'
Occam-Kit Installer

Usage:
  ./install.sh [options]

Options:
  --target <list>    Comma-separated targets: claude,codex,cursor,gemini,antigravity,copilot,all (default: all)
  --scope <mode>     Install scope: project | global (default: project)
  --dir <path>       Target project root when --scope project (default: current directory)
  --dry-run          Print actions without modifying files
  --uninstall        Remove Occam-Kit skills, rules, and scripts from the target scope
  -h, --help         Show this help message

Examples:
  ./install.sh --target claude,cursor --scope project --dir /path/to/repo
  ./install.sh --target all --scope global
  curl -fsSL https://raw.githubusercontent.com/Moeraafatz/occam-kit/main/install.sh | bash -s -- --target all
EOF
}

cleanup() {
  if [ -n "$TEMP_CLONE" ] && [ -d "$TEMP_CLONE" ]; then
    rm -rf "$TEMP_CLONE"
  fi
}
trap cleanup EXIT

while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      TARGETS="${2:-}"
      shift 2
      ;;
    --scope)
      SCOPE="${2:-}"
      SCOPE_EXPLICIT=1
      shift 2
      ;;
    --dir)
      PROJECT_DIR="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$SCOPE" != "project" ] && [ "$SCOPE" != "global" ]; then
  echo "Error: --scope must be 'project' or 'global' (got '$SCOPE')" >&2
  exit 2
fi

SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
if [ -n "$SCRIPT_SOURCE" ] && [ -f "$SCRIPT_SOURCE" ]; then
  SRC_ROOT="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
else
  SRC_ROOT=""
fi

if [ "$UNINSTALL" -eq 0 ]; then
  if [ -z "$SRC_ROOT" ] || [ ! -d "$SRC_ROOT/skills/occam-harness" ]; then
    TEMP_CLONE="$(mktemp -d)"
    echo "[occam-kit] Fetching occam-kit into temporary staging directory..."
    git clone --depth 1 --quiet "$REPO_URL" "$TEMP_CLONE"
    SRC_ROOT="$TEMP_CLONE"
  fi
fi

if [ "$SCOPE" = "project" ]; then
  BASE_DIR="$(cd "$PROJECT_DIR" && pwd)"
  RESOLVED_HOME="$(cd "$HOME" && pwd)"
  if [ "$SCOPE_EXPLICIT" -eq 0 ] && [ "$BASE_DIR" = "$RESOLVED_HOME" ]; then
    echo "[occam-kit] Detected home directory ($RESOLVED_HOME) — switching to --scope global to keep ~ clean."
    SCOPE="global"
  fi
else
  BASE_DIR="$(cd "$HOME" && pwd)"
fi

run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  [dry-run] $*"
  else
    "$@"
  fi
}

install_skills_into() {
  local dest="$1"
  echo "[occam-kit] Installing SKILL.md pack -> $dest"
  run_cmd mkdir -p "$dest"
  for skill_dir in "$SRC_ROOT"/skills/occam-*; do
    local name
    name="$(basename "$skill_dir")"
    run_cmd rm -rf "$dest/$name"
    run_cmd cp -R "$skill_dir" "$dest/$name"
  done
}

remove_skills_from() {
  local dest="$1"
  if [ -d "$dest" ]; then
    echo "[occam-kit] Removing occam-* skills from $dest"
    for name in occam-harness occam-brainstorm occam-research-gate occam-frugal-router; do
      if [ -e "$dest/$name" ]; then
        run_cmd rm -rf "$dest/$name"
      fi
    done
  fi
}

install_scripts() {
  local dest="$BASE_DIR/.occam/scripts"
  echo "[occam-kit] Installing Tier 0 Python scripts -> $dest"
  run_cmd mkdir -p "$dest"
  run_cmd cp "$SRC_ROOT"/scripts/*.py "$dest/"
  if [ "$DRY_RUN" -eq 0 ]; then
    chmod +x "$dest"/*.py
  fi
}

remove_scripts() {
  local dest="$BASE_DIR/.occam/scripts"
  if [ -d "$dest" ]; then
    echo "[occam-kit] Removing Tier 0 scripts -> $dest"
    run_cmd rm -rf "$dest"
  fi
}

should_run_target() {
  local wanted="$1"
  if [ "$TARGETS" = "all" ]; then
    return 0
  fi
  IFS=',' read -r -a list <<< "$TARGETS"
  for item in "${list[@]}"; do
    if [ "$item" = "$wanted" ]; then
      return 0
    fi
  done
  return 1
}

echo "[occam-kit] Mode: $( [ "$UNINSTALL" -eq 1 ] && echo "uninstall" || echo "install" ) | Scope: $SCOPE | Base: $BASE_DIR | Targets: $TARGETS"

if [ "$UNINSTALL" -eq 1 ]; then
  should_run_target claude && remove_skills_from "$BASE_DIR/.claude/skills"
  should_run_target codex && remove_skills_from "$BASE_DIR/.agents/skills"
  should_run_target gemini && remove_skills_from "$BASE_DIR/.gemini/skills"
  should_run_target antigravity && remove_skills_from "$BASE_DIR/.gemini/antigravity/skills"
  if should_run_target cursor && [ "$SCOPE" = "project" ]; then
    for rule in occam-core.mdc occam-brainstorm.mdc occam-research.mdc occam-routing.mdc; do
      [ -e "$BASE_DIR/.cursor/rules/$rule" ] && run_cmd rm -f "$BASE_DIR/.cursor/rules/$rule"
    done
  fi
  remove_scripts
  echo "[occam-kit] Uninstall complete."
  exit 0
fi

install_scripts

install_shared_agents_skills() {
  if [ "$AGENTS_SKILLS_INSTALLED" -eq 1 ]; then
    return 0
  fi
  install_skills_into "$BASE_DIR/.agents/skills"
  AGENTS_SKILLS_INSTALLED=1
}

if should_run_target claude; then
  install_skills_into "$BASE_DIR/.claude/skills"
fi

if should_run_target codex; then
  install_shared_agents_skills
fi

if should_run_target cursor; then
  if [ "$SCOPE" = "project" ]; then
    echo "[occam-kit] Installing Cursor .mdc rules -> $BASE_DIR/.cursor/rules"
    run_cmd mkdir -p "$BASE_DIR/.cursor/rules"
    run_cmd cp "$SRC_ROOT"/adapters/cursor/rules/*.mdc "$BASE_DIR/.cursor/rules/"
    install_shared_agents_skills
  else
    echo "[occam-kit] Cursor global skills -> $BASE_DIR/.agents/skills (use --scope project for .cursor/rules/*.mdc)"
    install_shared_agents_skills
  fi
fi

if should_run_target gemini; then
  install_skills_into "$BASE_DIR/.gemini/skills"
fi

if should_run_target antigravity; then
  if [ "$SCOPE" = "global" ]; then
    install_skills_into "$BASE_DIR/.gemini/antigravity/skills"
  else
    install_shared_agents_skills
  fi
fi

if should_run_target copilot && [ "$SCOPE" = "project" ]; then
  if [ ! -e "$BASE_DIR/.github/copilot-instructions.md" ]; then
    echo "[occam-kit] Installing GitHub Copilot adapter -> $BASE_DIR/.github/copilot-instructions.md"
    run_cmd mkdir -p "$BASE_DIR/.github"
    run_cmd cp "$SRC_ROOT/adapters/copilot/copilot-instructions.md" "$BASE_DIR/.github/copilot-instructions.md"
  else
    echo "[occam-kit] Skipping existing $BASE_DIR/.github/copilot-instructions.md (will not overwrite user rules)."
  fi
fi

if [ "$SCOPE" = "project" ]; then
  if [ ! -e "$BASE_DIR/AGENTS.md" ]; then
    echo "[occam-kit] Installing root AGENTS.md -> $BASE_DIR/AGENTS.md"
    run_cmd cp "$SRC_ROOT/AGENTS.md" "$BASE_DIR/AGENTS.md"
  else
    echo "[occam-kit] Existing AGENTS.md preserved (merge occam-kit rules manually if desired)."
  fi
fi

echo ""
echo "[occam-kit] Done! Verify installation with:"
echo "  python3 $BASE_DIR/.occam/scripts/occam.py doctor --root $BASE_DIR"
