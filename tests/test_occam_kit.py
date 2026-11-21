#!/usr/bin/env python3
"""Unit and integration tests for Occam-Kit (stdlib unittest, Python 3.9+)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cite_check  # noqa: E402
import ledger  # noqa: E402
import repo_map  # noqa: E402
import token_budget  # noqa: E402
import trim_run  # noqa: E402


class TestTokenBudgetAndSkills(unittest.TestCase):
    def test_own_skills_pass_agentskills_audit(self) -> None:
        report = token_budget.audit_skills_dir(REPO_ROOT / "skills", max_startup_tokens=400)
        self.assertTrue(report["ok"], f"Skill audit failed: {report}")
        self.assertEqual(len(report["skills"]), 4)
        self.assertLessEqual(report["total_startup_tokens"], 350)

    def test_invalid_skill_folder_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sdir = Path(tmp) / "bad-folder"
            sdir.mkdir()
            (sdir / "SKILL.md").write_text(
                "---\nname: other-name\ndescription: Valid desc.\n---\nBody\n",
                encoding="utf-8",
            )
            report = token_budget.audit_skills_dir(Path(tmp))
            self.assertFalse(report["ok"])

    def test_yaml_list_frontmatter_parses_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sdir = Path(tmp) / "list-skill"
            sdir.mkdir()
            (sdir / "SKILL.md").write_text(
                '---\nname: list-skill\ndescription: Supports YAML list tools.\nallowed-tools:\n  - "Bash"\n  - "Read"\n---\nBody text\n',
                encoding="utf-8",
            )
            report = token_budget.audit_skills_dir(Path(tmp))
            self.assertTrue(report["ok"], f"YAML list skill failed audit: {report}")


class TestRepoMap(unittest.TestCase):
    def test_extracts_python_and_ts_symbols_under_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "class Engine:\n    def start(self):\n        return 1\n\ndef main(x, y):\n    return x + y\n",
                encoding="utf-8",
            )
            (root / "ui.ts").write_text(
                "export interface Config { debug: boolean }\nexport function renderView(id: string) { return id; }\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "# Title\n```bash\n# shell comment not heading\n```\n## Real Section\n",
                encoding="utf-8",
            )
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.js").write_text("function nope() {}", encoding="utf-8")

            output, stats = repo_map.generate_repo_map(root, max_tokens=600)
            self.assertIn("class Engine [start]", output)
            self.assertIn("def main(x, y)", output)
            self.assertIn("Config", output)
            self.assertIn("renderView(id: string)", output)
            self.assertIn("## Real Section", output)
            self.assertNotIn("shell comment not heading", output)
            self.assertNotIn("node_modules", output)
            self.assertEqual(stats["files_scanned"], 3)


class TestTrimRun(unittest.TestCase):
    def test_compresses_passing_log_and_keeps_summary(self) -> None:
        raw = "\n".join(f"tests/test_a.py::test_{i} PASSED" for i in range(120))
        raw += "\n=== 120 passed in 1.23s ===\n"
        reduced, raw_tok, cmp_tok = trim_run.reduce_log(raw, exit_code=0)
        self.assertIn("120 passed", reduced)
        self.assertLess(cmp_tok, raw_tok)

    def test_keeps_failing_errors_and_tracebacks(self) -> None:
        raw = "\n".join(f"tests/test_a.py::test_{i} PASSED" for i in range(80))
        raw += "\nFAILED tests/test_a.py::test_boom - AssertionError: expected 4 == 5\n"
        raw += "=== 1 failed, 80 passed in 0.8s ===\n"
        reduced, raw_tok, cmp_tok = trim_run.reduce_log(raw, exit_code=1)
        self.assertIn("test_boom", reduced)
        self.assertIn("AssertionError", reduced)
        self.assertLess(cmp_tok, raw_tok)

    def test_live_command_execution_and_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "run.log"
            rc = trim_run.main(
                [
                    "--log",
                    str(log_path),
                    "--",
                    sys.executable,
                    "-c",
                    "print('OK 10 passed in 0.01s')",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(log_path.exists())
            self.assertIn("10 passed", log_path.read_text(encoding="utf-8"))


class TestLedger(unittest.TestCase):
    def test_full_ledger_lifecycle_and_handoff_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ldir = Path(tmp) / ".occam"
            self.assertEqual(
                ledger.main(
                    [
                        "--dir",
                        str(ldir),
                        "init",
                        "--goal",
                        "Build zero-cost offline CLI",
                        "--constraint",
                        "Python 3.9+ stdlib",
                        "--non-goal",
                        "Cloud dashboard",
                    ]
                ),
                0,
            )
            self.assertEqual(
                ledger.main(
                    [
                        "--dir",
                        str(ldir),
                        "decide",
                        "--id",
                        "D1",
                        "--decision",
                        "Use sqlite3",
                        "--reason",
                        "Built into Python stdlib",
                        "--source",
                        "https://docs.python.org/3/library/sqlite3.html",
                    ]
                ),
                0,
            )
            self.assertEqual(
                ledger.main(["--dir", str(ldir), "step", "add", "--title", "Create schema", "--tier", "T1"]),
                0,
            )
            self.assertEqual(
                ledger.main(["--dir", str(ldir), "step", "done", "--index", "1"]),
                0,
            )
            self.assertEqual(
                ledger.main(
                    [
                        "--dir",
                        str(ldir),
                        "deadend",
                        "--tried",
                        "Flat CSV store",
                        "--why",
                        "Slow concurrent writes",
                    ]
                ),
                0,
            )
            self.assertEqual(
                ledger.main(
                    [
                        "--dir",
                        str(ldir),
                        "checkpoint",
                        "--summary",
                        "Schema done",
                        "--next",
                        "Write query CLI",
                        "--tier",
                        "T1",
                    ]
                ),
                0,
            )
            state = ledger.load_state(ldir)
            brief = ledger.build_handoff(state, max_tokens=200)
            self.assertLessEqual(token_budget.estimate_tokens(brief), 200)
            self.assertIn("Flat CSV store", brief)
            self.assertIn("Write query CLI", brief)


class TestCiteCheck(unittest.TestCase):
    def test_accepts_t1_verified_and_rejects_t3_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.md"
            good.write_text(
                "| Claim | Tier | Source | Version/Date | Status |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| SKILL.md requires lowercase hyphenated names | T1 | https://agentskills.io/specification | 2026-11-21 | Verified |\n",
                encoding="utf-8",
            )
            self.assertTrue(cite_check.validate_ledger(good, strict=True)["ok"])

            bad = Path(tmp) / "bad.md"
            bad.write_text(
                "| Claim | Tier | Source | Version/Date | Status |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| Random blog claim | T3 | https://example.com/blog | 2026-11-21 | Verified |\n",
                encoding="utf-8",
            )
            rep = cite_check.validate_ledger(bad)
            self.assertFalse(rep["ok"])
            self.assertTrue(any("T3" in e for e in rep["errors"]))


class TestInstallerAndCLI(unittest.TestCase):
    def test_installer_project_install_doctor_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            res = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--target",
                    "all",
                    "--scope",
                    "project",
                    "--dir",
                    str(project),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(res.stdout.count(".agents/skills"), 1, res.stdout)
            self.assertTrue((project / ".claude" / "skills" / "occam-harness" / "SKILL.md").exists())
            self.assertTrue((project / ".agents" / "skills" / "occam-frugal-router" / "SKILL.md").exists())
            self.assertTrue((project / ".cursor" / "rules" / "occam-core.mdc").exists())
            self.assertTrue((project / ".github" / "copilot-instructions.md").exists())
            self.assertTrue((project / "AGENTS.md").exists())
            self.assertTrue((project / ".occam" / "scripts" / "occam.py").exists())

            doc = subprocess.run(
                [sys.executable, str(project / ".occam" / "scripts" / "occam.py"), "doctor", "--root", str(project)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(doc.returncode, 0, doc.stdout + doc.stderr)

            uninst = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--target",
                    "all",
                    "--scope",
                    "project",
                    "--dir",
                    str(project),
                    "--uninstall",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(uninst.returncode, 0, uninst.stderr)
            self.assertFalse((project / ".claude" / "skills" / "occam-harness").exists())
            self.assertFalse((project / ".cursor" / "rules" / "occam-core.mdc").exists())
            self.assertFalse((project / ".occam" / "scripts").exists())

    def test_installer_auto_global_in_home_and_doctor_separates_third_party_tax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp)
            # Pre-populate a heavy third-party skill in fake_home/.agents/skills
            heavy = fake_home / ".agents" / "skills" / "heavy-third-party"
            heavy.mkdir(parents=True)
            (heavy / "SKILL.md").write_text(
                "---\nname: heavy-third-party\ndescription: " + ("word " * 180) + "\n---\nBody\n",
                encoding="utf-8",
            )

            env = dict(**__import__("os").environ)
            env["HOME"] = str(fake_home)
            res = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--target",
                    "all",
                    "--dir",
                    str(fake_home),
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("switching to --scope global", res.stdout)
            self.assertFalse((fake_home / "AGENTS.md").exists())
            self.assertFalse((fake_home / ".cursor" / "rules" / "occam-core.mdc").exists())
            self.assertTrue((fake_home / ".gemini" / "antigravity" / "skills" / "occam-harness" / "SKILL.md").exists())

            doc = subprocess.run(
                [sys.executable, str(fake_home / ".occam" / "scripts" / "occam.py"), "doctor", "--root", str(fake_home)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(doc.returncode, 0, doc.stdout + doc.stderr)
            self.assertIn("[PASS]", doc.stdout)
            self.assertIn("WARN: high context tax", doc.stdout)
            self.assertIn(".gemini/antigravity/skills", doc.stdout)


if __name__ == "__main__":
    unittest.main()
