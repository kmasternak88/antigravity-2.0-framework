#!/usr/bin/env python3
"""Comprehensive test suite for Gate G1.5 Production Completeness Linter."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Setup repository root
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
gov_bin = REPO_ROOT / ".governance" / "bin"
if str(gov_bin) not in sys.path:
    sys.path.insert(0, str(gov_bin))

from gov import lint_completeness, Rejected


class TestCompletenessLinter(unittest.TestCase):
    """Verifies Gate G1.5 8-vector production completeness evaluation."""

    def setUp(self) -> None:
        self.lean_tasks = {
            "version": 2,
            "tasks": [
                {
                    "id": "T-01",
                    "title": "Basic helper with resilience error handling",
                    "checks": ["unit", "dual_test_suite"],
                    "acceptance": ["handle domain_exception"],
                }
            ]
        }
        self.production_tasks = {
            "version": 2,
            "tasks": [
                {
                    "id": "T-01",
                    "title": "Idempotency key and transaction atomic lock",
                    "checks": ["unit", "dual_test_suite"],
                    "acceptance": ["prevent replay attack"],
                    "required_skills": ["clean-code"],
                },
                {
                    "id": "T-02",
                    "title": "Auth rate limit security token validation",
                    "checks": ["security"],
                    "acceptance": ["sanitize inputs"],
                    "required_skills": ["wp-security-guardrails"],
                },
                {
                    "id": "T-03",
                    "title": "Database schema migration and foreign key constraint",
                    "checks": ["db"],
                    "acceptance": ["sqlite table model"],
                    "required_skills": ["database-design"],
                },
                {
                    "id": "T-04",
                    "title": "Healthcheck endpoint and telemetry correlation logging",
                    "checks": ["sre"],
                    "acceptance": ["structured audit log"],
                },
                {
                    "id": "T-05",
                    "title": "Frontend UI empty and loading state with WCAG a11y 48px touch",
                    "checks": ["ui"],
                    "acceptance": ["skeleton loading"],
                    "required_skills": ["better-interface", "a11y-audit"],
                }
            ]
        }

    def test_completeness_production_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "tasks.json"
            p.write_text(json.dumps(self.production_tasks), encoding="utf-8")
            res = lint_completeness(tasks_file=str(p), profile="production")
            self.assertEqual(res["status"], "PASS")
            self.assertEqual(res["exitCode"], 0)
            self.assertGreaterEqual(res["coveredCount"], 5)

    def test_completeness_production_blocked_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "tasks.json"
            p.write_text(json.dumps(self.lean_tasks), encoding="utf-8")
            res = lint_completeness(tasks_file=str(p), profile="production")
            self.assertEqual(res["status"], "BLOCKED_INCOMPLETE")
            self.assertEqual(res["exitCode"], 1)
            self.assertLess(res["coveredCount"], 5)

    def test_completeness_lean_profile_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "tasks.json"
            p.write_text(json.dumps(self.lean_tasks), encoding="utf-8")
            res = lint_completeness(tasks_file=str(p), profile="lean")
            self.assertEqual(res["status"], "PASS")
            self.assertEqual(res["exitCode"], 0)

    def test_missing_tasks_file_raises_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "non_existent.json"
            with self.assertRaises(Rejected):
                lint_completeness(tasks_file=str(missing_path))


if __name__ == "__main__":
    unittest.main()
