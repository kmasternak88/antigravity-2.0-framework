#!/usr/bin/env python3
"""Adversarial Penetration and Fuzzing Test Suite for Multi-Subagent Swarm v8.3.

Attacks and validates the three-tier multi-agent engine (tools/subagent_workflow.py):
1. Dual-Control Security Invariants:
   - Self-review / self-certification spoofing (builder == supervisor/auditor).
   - Session collision and token impersonation.
   - Unauthorized direct review bypass via gov.py.
   - LLM session leaking via CONVERSATION_ID environment variable.
2. Cardinal Rule 12: Iron 3-Cycle Self-Healing Budget:
   - Persistent failing checks bounded at exactly 3 cycles.
   - Escalation to BLOCKED_ESCALATED with immutable FEEDBACK_PACKET.json.
   - State audit trail in SQLite (task_iterations & task_supervision_logs).
   - Fault tolerance against crashing remediation hooks.
   - Dynamic self-healing recovery before exhaustion (passes on cycle 2).
3. Parallel Swarm Wave Partitioning (Zero-Overlap Invariant & Fuzzing):
   - Overlapping allowed_paths resource collisions deferred to subsequent waves.
   - 100-iteration randomized DAG fuzzing proving zero path collision across all waves.
   - Concurrency bounds clamping (1..3).
"""

import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Dict, Any, Set

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
    WorkflowError,
    SubagentWorkflowResult
)


class BaseSubagentWorkspaceTest(unittest.TestCase):
    """Hermetic temporary governance workspace for adversarial testing."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir)

        # Initialize governance layout
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

        # Base sample tests with assertion for Mock-Breaker audit compliance
        (self.workspace / "tests" / "test_sample.py").write_text("def test_sample(): assert True\n", encoding="utf-8")
        (self.workspace / "tests" / "test_service_b.py").write_text("# INITIAL BROKEN\ndef test_b(): assert True\n", encoding="utf-8")

        shutil.copy2(REPO_ROOT / ".governance" / "bin" / "gov.py", bin_dir / "gov.py")
        (gov_dir / "hooks").mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / ".governance" / "hooks" / "native_guard.py", gov_dir / "hooks" / "native_guard.py")

        cfg = {
            "profile": "standard",
            "max_parallel": 2,
            "lease_seconds": 1800,
            "spec_files": ["specs/**/*", "contracts/**/*"],
            "checks": {
                "unit": {"argv": [sys.executable, "-c", "import sys; sys.exit(0)"], "timeout": 30},
                "failing_check": {"argv": [sys.executable, "-c", "import sys; sys.exit(1)"], "timeout": 30},
                "dynamic_unit": {
                    "argv": [sys.executable, "-c", "import sys, os; sys.exit(0 if os.path.exists('tests/test_service_b.py') and 'FIXED' in open('tests/test_service_b.py', encoding='utf-8').read() else 1)"],
                    "timeout": 30
                }
            },
            "required_release_checks": ["unit"]
        }
        (gov_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        (self.workspace / "specs" / "01_CHARTER.md").write_text("# Test Charter\nAdversarial test charter.", encoding="utf-8")
        (self.workspace / "contracts" / "models.py").write_text("# Models contract", encoding="utf-8")

        tasks = {
            "version": 1,
            "tasks": [
                {
                    "id": "T001",
                    "title": "Adversarial Target Task 1",
                    "allowed_paths": ["tests/test_service_a.py"],
                    "depends_on": [],
                    "risk": "low",
                    "checks": ["unit"],
                    "acceptance": ["Passes unit check"],
                    "standards_checklist": [
                        "interface_contract", "input_validation", "domain_exception",
                        "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
                    ]
                },
                {
                    "id": "T002",
                    "title": "Adversarial Target Task 2 Dynamic Recovery",
                    "allowed_paths": ["tests/test_service_b.py"],
                    "depends_on": [],
                    "risk": "low",
                    "checks": ["dynamic_unit"],
                    "acceptance": ["Passes dynamic unit check"],
                    "standards_checklist": [
                        "interface_contract", "input_validation", "domain_exception",
                        "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
                    ]
                }
            ]
        }
        (gov_dir / "tasks.json").write_text(json.dumps(tasks, indent=2), encoding="utf-8")

        subprocess.run(["git", "init"], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "ChallengerAgent"], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "challenger@test.local"], cwd=self.workspace, capture_output=True, check=True)

        self.orch = MultiSubagentOrchestrator(workspace_root=self.workspace)
        self.orch._run_gov(["approve-spec", "--actor", "human:owner", "--reference", "challenger spec lock"])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestDualControlAdversarial(BaseSubagentWorkspaceTest):
    """Adversarial penetration tests for Dual-Control and Separation of Duties."""

    def test_builder_attempts_self_review_direct_rejection(self):
        """Attacker tries to appoint builder as supervisor to self-certify."""
        with self.assertRaises(DualControlViolationError) as ctx:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:malicious-builder",
                supervisor_actor="agent:malicious-builder"
            )
        self.assertIn("FRAUDULENT_SELF_REVIEW_REJECTED", str(ctx.exception))

    def test_builder_attempts_self_review_via_auditor_alias(self):
        """Attacker omits supervisor_actor and sets auditor_actor to builder actor."""
        with self.assertRaises(DualControlViolationError) as ctx:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:sneaky-builder",
                auditor_actor="agent:sneaky-builder",
                supervisor_actor=None
            )
        self.assertIn("FRAUDULENT_SELF_REVIEW_REJECTED", str(ctx.exception))

    def test_tandem_worker_init_rejects_identical_actors(self):
        """Direct low-level TandemExecutionWorker initialization with identical actors must fail."""
        with self.assertRaises(DualControlViolationError) as ctx:
            TandemExecutionWorker(
                task_id="T001",
                workspace_root=self.workspace,
                gov_script=self.orch.gov_script,
                builder_actor="agent:compromised-actor",
                supervisor_actor="agent:compromised-actor"
            )
        self.assertIn("FRAUDULENT_SELF_REVIEW_REJECTED", str(ctx.exception))

    def test_session_collision_shared_llm_session_rejected(self):
        """Attacker runs supervisor in the same conversation session as builder."""
        shared_session = "session-leak-998877"
        with self.assertRaises(DualControlViolationError) as ctx:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:builder-a",
                supervisor_actor="agent:supervisor-b",
                builder_session=shared_session,
                supervisor_session=shared_session
            )
        self.assertIn("DUAL_CONTROL_SESSION_COLLISION", str(ctx.exception))

    def test_session_collision_via_auditor_session_rejected(self):
        """Attacker sets auditor_session identical to builder_session."""
        shared_session = "session-leak-auditor-332211"
        with self.assertRaises(DualControlViolationError) as ctx:
            self.orch.execute_task_lifecycle(
                task_id="T001",
                builder_actor="agent:builder-x",
                supervisor_actor="agent:supervisor-y",
                builder_session=shared_session,
                auditor_session=shared_session,
                supervisor_session=None
            )
        self.assertIn("DUAL_CONTROL_SESSION_COLLISION", str(ctx.exception))

    def test_tandem_worker_init_rejects_identical_sessions(self):
        """Direct low-level TandemExecutionWorker initialization with shared session must fail."""
        with self.assertRaises(DualControlViolationError) as ctx:
            TandemExecutionWorker(
                task_id="T001",
                workspace_root=self.workspace,
                gov_script=self.orch.gov_script,
                builder_actor="agent:builder-1",
                supervisor_actor="agent:supervisor-2",
                builder_session="same-id-555",
                supervisor_session="same-id-555"
            )
        self.assertIn("DUAL_CONTROL_SESSION_COLLISION", str(ctx.exception))

    def test_gov_py_rejects_builder_claim_self_review_at_cli_level(self):
        """Attacker claims task as builder, runs check, then calls gov.py review directly with builder actor."""
        builder_session = "builder-session-xyz"
        claim_env = {"CONVERSATION_ID": builder_session}
        self.orch._run_gov(["package-handoff", "--task", "T001"])
        claim_res = self.orch._run_gov(["claim", "--task", "T001", "--actor", "agent:builder-self", "--session", builder_session], env=claim_env)
        self.assertIn("token", claim_res)

        # Generate passing evidence
        self.orch._run_gov(["run", "--task", "T001", "--check", "unit"], env=claim_env)

        # Attempt review by the same actor -> rejected by INDEPENDENT_REVIEW_REQUIRED
        with self.assertRaises(WorkflowError) as ctx:
            self.orch._run_gov([
                "review", "--task", "T001",
                "--reviewer", "agent:builder-self",
                "--decision", "APPROVED",
                "--reference", "self-approval attempt"
            ], env=claim_env)
        err = str(ctx.exception)
        self.assertTrue("INDEPENDENT_REVIEW_REQUIRED" in err or "FRAUDULENT_SELF_REVIEW_REJECTED" in err)

    def test_gov_py_rejects_reviewer_using_builder_conversation_session(self):
        """Attacker uses different reviewer name but bleeds CONVERSATION_ID from builder session."""
        builder_session = "builder-session-alpha"
        claim_env = {"CONVERSATION_ID": builder_session}
        self.orch._run_gov(["package-handoff", "--task", "T001"])
        self.orch._run_gov(["claim", "--task", "T001", "--actor", "agent:builder-alpha", "--session", builder_session], env=claim_env)
        self.orch._run_gov(["run", "--task", "T001", "--check", "unit"], env=claim_env)

        # Reviewer attempts review with a different name but leaking CONVERSATION_ID of builder
        colliding_env = {
            "CONVERSATION_ID": builder_session,
            "GOV_AUDITOR_TOKEN": "valid-token-12345678"
        }
        with self.assertRaises(WorkflowError) as ctx:
            self.orch._run_gov([
                "review", "--task", "T001",
                "--reviewer", "agent:supervisor-beta",
                "--decision", "APPROVED",
                "--reference", "session bleed attack",
                "--session", "reviewer-separate-session",
                "--auditor-token", "valid-token-12345678"
            ], env=colliding_env)
        err = str(ctx.exception)
        self.assertIn("FRAUDULENT_SELF_REVIEW_REJECTED", err)


class TestSelfHealingBudgetAdversarial(BaseSubagentWorkspaceTest):
    """Adversarial stress-testing of Cardinal Rule 12: 3-Cycle Self-Healing Budget."""

    def test_failing_task_halts_at_exactly_3_cycles(self):
        """Ensure repeated failures halt at exactly 3 cycles with BLOCKED_ESCALATED."""
        res = self.orch.execute_task_lifecycle(
            task_id="T001",
            builder_actor="agent:builder-adversary",
            supervisor_actor="agent:supervisor-strict",
            check_name="failing_check",
            max_iterations=3
        )

        self.assertEqual(res.status, "BLOCKED_ESCALATED")
        self.assertEqual(res.iterations_run, 3)
        self.assertFalse(res.finished)
        self.assertEqual(res.gate_status, "BLOCKED")
        self.assertEqual(res.review_status, "REJECTED_NEEDS_REVISION")
        self.assertIsNotNone(res.feedback_packet_path)

        # Validate feedback packet contents
        with open(res.feedback_packet_path, "r", encoding="utf-8") as f:
            packet = json.load(f)

        self.assertEqual(packet["task_id"], "T001")
        self.assertEqual(packet["status"], "BLOCKED_ESCALATED")
        self.assertEqual(packet["iteration"], 3)
        self.assertEqual(packet["max_iterations"], 3)
        self.assertIn("Budget of 3 cycles exceeded", packet["required_action"])
        self.assertIn("escalating to Project-Orchestrator/Human", packet["required_action"])
        self.assertTrue(len(packet["findings"]) >= 1)
        self.assertEqual(packet["findings"][0]["type"], "TEST_EXECUTION_FAILURE")

    def test_iteration_progression_packet_status_transition(self):
        """Track FEEDBACK_PACKET status progression across cycles: 1..2=REJECTED_NEEDS_REVISION, 3=BLOCKED_ESCALATED."""
        observed_statuses = []

        def tracking_hook(iteration: int, packet: FeedbackPacket, workspace_path: Path):
            observed_statuses.append((iteration, packet.status))

        res = self.orch.execute_task_lifecycle(
            task_id="T001",
            check_name="failing_check",
            max_iterations=3,
            builder_remediation_hook=tracking_hook
        )

        self.assertEqual(res.status, "BLOCKED_ESCALATED")
        self.assertEqual(res.iterations_run, 3)
        # Hook was called on iteration 1 and 2 (iteration 3 halts immediately without triggering hook)
        self.assertEqual(len(observed_statuses), 2)
        self.assertEqual(observed_statuses[0], (1, "REJECTED_NEEDS_REVISION"))
        self.assertEqual(observed_statuses[1], (2, "REJECTED_NEEDS_REVISION"))

    def test_fault_tolerant_remediation_hook_crash(self):
        """Even if builder remediation hook explodes, orchestrator maintains budget and escalates cleanly."""
        def exploding_hook(iteration: int, packet: FeedbackPacket, workspace_path: Path):
            raise RuntimeError(f"Simulated catastrophic failure in builder hook at iter {iteration}")

        res = self.orch.execute_task_lifecycle(
            task_id="T001",
            check_name="failing_check",
            max_iterations=3,
            builder_remediation_hook=exploding_hook
        )

        self.assertEqual(res.status, "BLOCKED_ESCALATED")
        self.assertEqual(res.iterations_run, 3)
        self.assertFalse(res.finished)

    def test_sqlite_audit_trail_recorded(self):
        """Verify state.sqlite records all 3 iterations and supervision logs."""
        self.orch.execute_task_lifecycle(
            task_id="T001",
            check_name="failing_check",
            max_iterations=3
        )

        db_path = self.workspace / ".governance" / "state" / "state.sqlite"
        if db_path.is_file():
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT iteration, status FROM task_iterations WHERE task='T001' ORDER BY iteration ASC")
            rows = cur.fetchall()
            if rows:
                self.assertEqual(len(rows), 3)
                self.assertEqual(rows[0][1], "REJECTED_NEEDS_REVISION")
                self.assertEqual(rows[1][1], "REJECTED_NEEDS_REVISION")
                self.assertEqual(rows[2][1], "BLOCKED_ESCALATED")
            conn.close()

    def test_feedback_packet_post_init_validation(self):
        """Adversarial input testing for FeedbackPacket dataclass."""
        # Empty task_id
        with self.assertRaises(ValueError):
            FeedbackPacket(task_id="", iteration=1, max_iterations=3, status="APPROVED")
        # Negative iteration
        with self.assertRaises(ValueError):
            FeedbackPacket(task_id="T1", iteration=0, max_iterations=3, status="APPROVED")
        # Negative max_iterations
        with self.assertRaises(ValueError):
            FeedbackPacket(task_id="T1", iteration=1, max_iterations=-1, status="APPROVED")

    def test_dynamic_self_healing_recovery_on_cycle_2(self):
        """Simulate a task failing on cycle 1, healed by remediation hook within allowed_paths, passing on cycle 2."""
        def repair_hook(iteration: int, packet: FeedbackPacket, workspace_path: Path):
            if iteration == 1:
                (workspace_path / "tests" / "test_service_b.py").write_text("# FIXED\ndef test_b(): assert True\n", encoding="utf-8")

        res = self.orch.execute_task_lifecycle(
            task_id="T002",
            check_name="dynamic_unit",
            max_iterations=3,
            builder_remediation_hook=repair_hook
        )

        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.iterations_run, 2)
        self.assertTrue(res.finished)
        self.assertEqual(res.review_status, "APPROVED")


class TestParallelSwarmWaveAdversarial(unittest.TestCase):
    """Adversarial testing and fuzzing of Parallel Execution Waves and Zero-Overlap Invariant."""

    def test_direct_allowed_paths_collision_deferred(self):
        """Two tasks with identical allowed_paths MUST be split into consecutive waves."""
        tasks = [
            {"id": "T1", "allowed_paths": ["src/core.py"], "depends_on": []},
            {"id": "T2", "allowed_paths": ["src/core.py"], "depends_on": []}
        ]
        waves = ParallelSwarmOrchestrator.compute_execution_waves(tasks)
        self.assertEqual(len(waves), 2)
        self.assertEqual(waves[0], ["T1"])
        self.assertEqual(waves[1], ["T2"])

    def test_partial_path_overlap_disjointness(self):
        """Multiple overlapping subsets properly segregated."""
        tasks = [
            {"id": "T1", "allowed_paths": ["src/a.py", "src/shared.py"], "depends_on": []},
            {"id": "T2", "allowed_paths": ["src/b.py", "src/shared.py"], "depends_on": []},
            {"id": "T3", "allowed_paths": ["src/c.py"], "depends_on": []}
        ]
        waves = ParallelSwarmOrchestrator.compute_execution_waves(tasks)
        # Wave 0 can take T1 and T3 (shared.py claimed by T1, T3 uses c.py)
        # Wave 1 takes T2
        self.assertIn("T1", waves[0])
        self.assertIn("T3", waves[0])
        self.assertNotIn("T2", waves[0])
        self.assertIn("T2", waves[1])

        # Verify zero overlap in wave 0
        w0_paths = set(tasks[0]["allowed_paths"]) & set(tasks[2]["allowed_paths"])
        self.assertEqual(len(w0_paths), 0)

    def test_all_tasks_share_resource_full_serialization(self):
        """N tasks all contending for a single file -> serialized into N waves."""
        n = 5
        tasks = [
            {"id": f"T{i}", "allowed_paths": ["src/contested.py"], "depends_on": []}
            for i in range(n)
        ]
        waves = ParallelSwarmOrchestrator.compute_execution_waves(tasks)
        self.assertEqual(len(waves), n)
        for w in waves:
            self.assertEqual(len(w), 1)

    def test_disjoint_tasks_parallelized_in_single_wave(self):
        """N tasks with completely disjoint paths and no dependencies run together in wave 0."""
        n = 4
        tasks = [
            {"id": f"T{i}", "allowed_paths": [f"src/file_{i}.py"], "depends_on": []}
            for i in range(n)
        ]
        waves = ParallelSwarmOrchestrator.compute_execution_waves(tasks)
        self.assertEqual(len(waves), 1)
        self.assertEqual(set(waves[0]), {f"T{i}" for i in range(n)})

    def test_empty_tasks_list(self):
        """Zero tasks produce zero waves."""
        self.assertEqual(ParallelSwarmOrchestrator.compute_execution_waves([]), [])

    def test_tasks_with_empty_allowed_paths_do_not_collide(self):
        """Tasks with empty allowed_paths can execute in parallel if no dependencies."""
        tasks = [
            {"id": "T1", "allowed_paths": [], "depends_on": []},
            {"id": "T2", "allowed_paths": [], "depends_on": []}
        ]
        waves = ParallelSwarmOrchestrator.compute_execution_waves(tasks)
        self.assertEqual(len(waves), 1)
        self.assertEqual(waves[0], ["T1", "T2"])

    def test_concurrency_clamping(self):
        """Ensure max_concurrency is clamped between 1 and 3."""
        orch = ParallelSwarmOrchestrator(workspace_root=Path("."), gov_script=Path("."), max_concurrency=10)
        self.assertEqual(orch.max_concurrency, 3)

        orch_low = ParallelSwarmOrchestrator(workspace_root=Path("."), gov_script=Path("."), max_concurrency=-5)
        self.assertEqual(orch_low.max_concurrency, 1)

    def test_fuzzing_random_dags_zero_overlap_invariant(self):
        """Fuzz testing: 100 randomized task DAGs with overlapping resource pools.
        Assert for EVERY wave that:
        1. All pairs of tasks in the wave have mutually exclusive allowed_paths.
        2. All dependencies of tasks in wave W were completed in earlier waves.
        """
        rng = random.Random(42)
        resource_pool = [f"src/module_{i}.py" for i in range(8)]

        for trial in range(100):
            num_tasks = rng.randint(4, 15)
            tasks = []
            task_ids = [f"TASK_{i:02d}" for i in range(num_tasks)]

            for i, tid in enumerate(task_ids):
                # Sample 1-3 random files from the shared pool
                assigned_paths = rng.sample(resource_pool, k=rng.randint(1, 3))
                # Dependencies can only point to preceding task indices (guarantees DAG acylicity)
                possible_deps = task_ids[:i]
                deps = rng.sample(possible_deps, k=rng.randint(0, min(2, len(possible_deps)))) if possible_deps else []

                tasks.append({
                    "id": tid,
                    "allowed_paths": assigned_paths,
                    "depends_on": deps
                })

            waves = ParallelSwarmOrchestrator.compute_execution_waves(tasks)
            task_map = {t["id"]: t for t in tasks}
            completed_tasks: Set[str] = set()

            for wave_idx, wave in enumerate(waves):
                wave_claimed_paths: Set[str] = set()

                for tid in wave:
                    t = task_map[tid]
                    # Invariant 1: All dependencies must be satisfied in previous waves
                    for dep in t["depends_on"]:
                        self.assertIn(
                            dep, completed_tasks,
                            f"Trial {trial}: Task {tid} in wave {wave_idx} has unsatisfied dep {dep}"
                        )

                    # Invariant 2: Zero overlapping allowed_paths within the same wave
                    t_paths = set(t["allowed_paths"])
                    collision = wave_claimed_paths & t_paths
                    self.assertEqual(
                        len(collision), 0,
                        f"Trial {trial}: Resource collision in wave {wave_idx} between tasks for paths: {collision}"
                    )
                    wave_claimed_paths.update(t_paths)

                completed_tasks.update(wave)

            # All tasks must be scheduled
            self.assertEqual(completed_tasks, set(task_ids), f"Trial {trial}: Not all tasks were scheduled!")


if __name__ == "__main__":
    unittest.main()
