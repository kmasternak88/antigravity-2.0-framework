#!/usr/bin/env python3
"""Tests for Multi-Subagent Dual-Control Workflow and Orchestrator Dispatcher.

Verifies:
1. Role configuration and skill mappings across agents.
2. Dual-Control invariant: builder cannot review own task (DualControlViolationError).
3. Independent auditor verification and G5.2 sign-off.
4. Orchestrator gate evaluation, interlock, and final task closure.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Add repo root to sys.path
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.subagent_workflow import (
    MultiSubagentOrchestrator,
    DualControlViolationError,
    WorkflowError
)


class TestSubagentWorkflowDualControl(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir)

        # Initialize basic governance in temporary workspace
        gov_dir = self.workspace / ".governance"
        bin_dir = gov_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (gov_dir / "state").mkdir(parents=True, exist_ok=True)
        (gov_dir / "evidence").mkdir(parents=True, exist_ok=True)
        (gov_dir / "handoffs").mkdir(parents=True, exist_ok=True)
        (self.workspace / "contracts").mkdir(parents=True, exist_ok=True)
        (self.workspace / "specs").mkdir(parents=True, exist_ok=True)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        (self.workspace / "tests").mkdir(parents=True, exist_ok=True)

        # Copy gov.py and hooks
        shutil.copy2(REPO_ROOT / ".governance" / "bin" / "gov.py", bin_dir / "gov.py")
        (gov_dir / "hooks").mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / ".governance" / "hooks" / "native_guard.py", gov_dir / "hooks" / "native_guard.py")

        # Basic config.json
        cfg = {
            "profile": "standard",
            "max_parallel": 2,
            "lease_seconds": 1800,
            "spec_files": ["specs/**/*", "contracts/**/*"],
            "checks": {
                "unit": {"argv": [sys.executable, "-c", "import sys; sys.exit(0)"], "timeout": 30}
            },
            "required_release_checks": ["unit"]
        }
        (gov_dir / "config.json").write_text(json_dumps(cfg), encoding="utf-8")

        # Dummy spec & contract
        (self.workspace / "specs" / "01_CHARTER.md").write_text("# Test Charter", encoding="utf-8")
        (self.workspace / "contracts" / "models.py").write_text("# Models", encoding="utf-8")

        # Basic tasks.json with 1 task (low risk to skip mock_breaker in synthetic unit test)
        tasks = {
            "version": 1,
            "tasks": [
                {
                    "id": "T001",
                    "title": "Subagent Test Task",
                    "allowed_paths": ["tests/test_service.py"],
                    "depends_on": [],
                    "risk": "low",
                    "checks": ["unit"],
                    "acceptance": ["Task passes unit test"],
                    "standards_checklist": [
                        "interface_contract", "input_validation", "domain_exception",
                        "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
                    ]
                }
            ]
        }
        (gov_dir / "tasks.json").write_text(json_dumps(tasks), encoding="utf-8")

        # Initialize git repo and approve spec
        import subprocess
        subprocess.run(["git", "init"], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "TestAgent"], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "agent@test.local"], cwd=self.workspace, capture_output=True, check=True)

        self.orch = MultiSubagentOrchestrator(workspace_root=self.workspace)
        # Approve spec to satisfy G2
        self.orch._run_gov(["approve-spec", "--actor", "human:owner", "--reference", "initial test approval"])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_role_matrix_loaded(self):
        roles = self.orch.get_role_configuration()
        self.assertIn("orchestrator", roles)
        self.assertIn("builder", roles)
        self.assertIn("auditor", roles)
        self.assertIn("verifier", roles)

        self.assertEqual(roles["builder"].skills, ["cl-build", "cl-standards"])
        self.assertEqual(roles["auditor"].skills, ["cl-review", "cl-audit"])
        self.assertEqual(roles["verifier"].skills, ["cl-verify", "cl-characterize"])

    def test_fraudulent_self_review_same_actor_rejected(self):
        with self.assertRaises(DualControlViolationError) as cm:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:builder-1",
                auditor_actor="agent:builder-1"  # Impersonation attempt
            )
        self.assertIn("FRAUDULENT_SELF_REVIEW_REJECTED", str(cm.exception))

    def test_fraudulent_self_review_same_session_rejected(self):
        with self.assertRaises(DualControlViolationError) as cm:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:builder-1",
                auditor_actor="agent:auditor-2",
                builder_session="shared-session-xyz",
                auditor_session="shared-session-xyz"  # Collision
            )
        self.assertIn("DUAL_CONTROL_SESSION_COLLISION", str(cm.exception))

    def test_full_dual_control_lifecycle_success(self):
        res = self.orch.execute_task_lifecycle(
            task_id="T001",
            builder_actor="agent:builder-executor",
            auditor_actor="agent:code-auditor",
            orchestrator_actor="agent:project-orchestrator",
            auto_interlock_and_finish=True
        )

        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.gate_status, "PASS")
        self.assertEqual(res.review_status, "APPROVED")
        self.assertTrue(res.interlock_passed)
        self.assertTrue(res.finished)
        self.assertIsNotNone(res.evidence_path)


def json_dumps(data):
    import json
    return json.dumps(data, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
