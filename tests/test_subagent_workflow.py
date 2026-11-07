#!/usr/bin/env python3
"""Tests for Multi-Subagent Dual-Control Workflow and Orchestrator Dispatcher (v8.3 Swarm).

Verifies:
1. Role configuration and skill mappings across agents including task-supervisor.
2. Dual-Control invariant: builder cannot review own task (DualControlViolationError).
3. Independent task-supervisor verification and G5.2 sign-off.
4. Tandem teamwork loop with FEEDBACK_PACKET.json generation.
5. Self-healing budget exhaustion (3-cycle guard) escalating to BLOCKED_ESCALATED.
6. ParallelSwarmOrchestrator topological wave partitioning with zero-overlap resource bounds.
7. Orchestrator gate evaluation, interlock, and final task closure.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import json

# Add repo root to sys.path
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.subagent_workflow import (
    MultiSubagentOrchestrator,
    ParallelSwarmOrchestrator,
    TandemExecutionWorker,
    FeedbackPacket,
    FeedbackFinding,
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
                "unit": {"argv": [sys.executable, "-c", "import sys; sys.exit(0)"], "timeout": 30},
                "failing_check": {"argv": [sys.executable, "-c", "import sys; sys.exit(1)"], "timeout": 30}
            },
            "required_release_checks": ["unit"]
        }
        (gov_dir / "config.json").write_text(json_dumps(cfg), encoding="utf-8")

        # Dummy spec & contract
        (self.workspace / "specs" / "01_CHARTER.md").write_text("# Test Charter", encoding="utf-8")
        (self.workspace / "contracts" / "models.py").write_text("# Models", encoding="utf-8")

        # Basic tasks.json with 2 tasks for parallel wave testing
        tasks = {
            "version": 1,
            "tasks": [
                {
                    "id": "T001",
                    "title": "Subagent Test Task 1",
                    "allowed_paths": ["tests/test_service.py"],
                    "depends_on": [],
                    "risk": "low",
                    "checks": ["unit"],
                    "acceptance": ["Task passes unit test"],
                    "standards_checklist": [
                        "interface_contract", "input_validation", "domain_exception",
                        "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
                    ]
                },
                {
                    "id": "T002",
                    "title": "Subagent Test Task 2",
                    "allowed_paths": ["tests/test_service_2.py"],
                    "depends_on": [],
                    "risk": "low",
                    "checks": ["unit"],
                    "acceptance": ["Task 2 passes unit test"],
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
        self.assertIn("supervisor", roles)
        self.assertIn("builder", roles)
        self.assertIn("auditor", roles)
        self.assertIn("verifier", roles)

        self.assertEqual(roles["supervisor"].name, "task-supervisor")
        self.assertEqual(roles["builder"].skills, ["cl-build", "cl-standards"])
        self.assertEqual(roles["supervisor"].skills, ["cl-review", "cl-audit", "cl-verify"])

    def test_fraudulent_self_review_same_actor_rejected(self):
        with self.assertRaises(DualControlViolationError) as cm:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:builder-1",
                supervisor_actor="agent:builder-1"  # Impersonation attempt
            )
        self.assertIn("FRAUDULENT_SELF_REVIEW_REJECTED", str(cm.exception))

    def test_fraudulent_self_review_same_session_rejected(self):
        with self.assertRaises(DualControlViolationError) as cm:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:builder-1",
                supervisor_actor="agent:task-supervisor-2",
                builder_session="shared-session-xyz",
                supervisor_session="shared-session-xyz"  # Collision
            )
        self.assertIn("DUAL_CONTROL_SESSION_COLLISION", str(cm.exception))

    def test_full_dual_control_lifecycle_success(self):
        res = self.orch.execute_task_lifecycle(
            task_id="T001",
            builder_actor="agent:builder-executor",
            supervisor_actor="agent:task-supervisor",
            orchestrator_actor="agent:project-orchestrator",
            auto_interlock_and_finish=True
        )

        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.gate_status, "PASS")
        self.assertEqual(res.review_status, "APPROVED")
        self.assertEqual(res.iterations_run, 1)
        self.assertTrue(res.interlock_passed)
        self.assertTrue(res.finished)
        self.assertIsNotNone(res.evidence_path)
        self.assertIsNotNone(res.feedback_packet_path)
        self.assertTrue(Path(res.feedback_packet_path).is_file())

    def test_self_healing_budget_exhaustion_escalates_to_blocked(self):
        # We run check_name='failing_check' without modifying tasks.json to preserve spec lock
        res = self.orch.execute_task_lifecycle(
            task_id="T001",
            builder_actor="agent:builder-executor",
            supervisor_actor="agent:task-supervisor",
            orchestrator_actor="agent:project-orchestrator",
            check_name="failing_check",
            max_iterations=3
        )

        self.assertEqual(res.status, "BLOCKED_ESCALATED")
        self.assertEqual(res.iterations_run, 3)
        self.assertFalse(res.finished)
        self.assertIsNotNone(res.feedback_packet_path)

        # Inspect generated FEEDBACK_PACKET
        with open(res.feedback_packet_path, "r", encoding="utf-8") as f:
            packet_data = json.load(f)
        self.assertEqual(packet_data["status"], "BLOCKED_ESCALATED")
        self.assertEqual(packet_data["iteration"], 3)
        self.assertIn("Budget of 3 cycles exceeded", packet_data["required_action"])

    def test_parallel_swarm_execution_waves_computation(self):
        sample_tasks = [
            {"id": "T001", "allowed_paths": ["src/a.py"], "depends_on": []},
            {"id": "T002", "allowed_paths": ["src/b.py"], "depends_on": []},
            {"id": "T003", "allowed_paths": ["src/a.py"], "depends_on": []},  # Overlaps with T001
            {"id": "T004", "allowed_paths": ["src/c.py"], "depends_on": ["T001", "T002"]}
        ]
        waves = ParallelSwarmOrchestrator.compute_execution_waves(sample_tasks)

        # Wave 0 must contain T001 and T002 (disjoint allowed_paths).
        # Wave 1 contains T003 (deferred from wave 0) and T004 (whose deps T001 and T002 were completed in wave 0).
        self.assertEqual(waves[0], ["T001", "T002"])
        self.assertEqual(waves[1], ["T003", "T004"])


def json_dumps(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
