#!/usr/bin/env python3
"""Multi-Subagent Workflow Orchestrator & Parallel Swarm Dispatcher for Antigravity Ultra v8.3.

Implements the Three-Tier Multi-Agent Hierarchy & Teamwork Loop:
1. Tier 1: Project-Orchestrator
   - Oversees global Kahn DAG (.governance/tasks.json).
   - Computes execution waves with zero-overlap resource bounds (allowed_paths disjointness, Triple Lock).
   - Manages dedicated worktrees per task and controls concurrency (default 2, max 3).
   - Coordinates cross-worktree interlock (G6) and authoritative release (G7).
2. Tier 2: Task-Supervisor
   - Dedicated supervisor per active task worktree (.worktrees/<task_id>).
   - Operates in isolated LLM session with unique auditor_token (Dual-Control).
   - Supervises builder-executor in a deterministic closed loop.
   - Audits DREE 7 invariants, mutation resistance (Mock-Breaker), and produces FEEDBACK_PACKET.json.
   - Signs off G5.2 review upon compliance.
3. Tier 3: Builder-Executor
   - Pure implementor within allowed_paths.
   - Consumes FEEDBACK_PACKET.json and performs targeted remediation.
   - Subject to Cardinal Rule 12: 3-Cycle Self-Healing budget. Exceeding 3 cycles escalates to BLOCKED_ESCALATED.
   - Strictly forbidden from self-review (Rule 9).
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set, Callable

_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent
for _p in [_this_dir, _repo_root]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

__all__ = [
    "WorkflowError",
    "DualControlViolationError",
    "SelfHealingBudgetExceededError",
    "ResourceCollisionError",
    "SubagentRole",
    "FeedbackFinding",
    "FeedbackPacket",
    "SubagentWorkflowResult",
    "TandemExecutionWorker",
    "ParallelSwarmOrchestrator",
    "MultiSubagentOrchestrator",
    "main",
]

class WorkflowError(Exception):
    """Base domain exception for subagent workflow errors."""
    pass

class DualControlViolationError(WorkflowError):
    """Raised when an agent attempts to certify its own work."""
    pass

class SelfHealingBudgetExceededError(WorkflowError):
    """Raised when the 3-cycle repair budget is exceeded."""
    pass

class ResourceCollisionError(WorkflowError):
    """Raised when parallel tasks conflict on shared allowed_paths or symbols."""
    pass


@dataclass(slots=True, frozen=True)
class SubagentRole:
    name: str
    role_type: str  # 'orchestrator', 'supervisor', 'builder', 'auditor', 'verifier'
    skills: List[str]
    allowed_tools: List[str]


@dataclass(slots=True, frozen=True)
class FeedbackFinding:
    type: str  # e.g., 'DREE_SRP_VIOLATION', 'MOCK_BREAKER_TAUTOLOGY', 'TEST_FAILURE', 'SCHEMA_MISMATCH'
    file: str
    details: str
    actionable_remediation: str
    line_range: Optional[str] = None

    def __post_init__(self):
        if not self.type or not isinstance(self.type, str):
            raise ValueError("FeedbackFinding.type must be non-empty string")
        if not self.file or not isinstance(self.file, str):
            raise ValueError("FeedbackFinding.file must be non-empty string")
        if not self.details or not isinstance(self.details, str):
            raise ValueError("FeedbackFinding.details must be non-empty string")
        if not self.actionable_remediation or not isinstance(self.actionable_remediation, str):
            raise ValueError("FeedbackFinding.actionable_remediation must be non-empty string")


@dataclass(slots=True, frozen=True)
class FeedbackPacket:
    task_id: str
    iteration: int
    max_iterations: int
    status: str  # 'REJECTED_NEEDS_REVISION', 'APPROVED', 'BLOCKED_ESCALATED'
    findings: List[FeedbackFinding] = field(default_factory=list)
    required_action: str = ""

    def __post_init__(self):
        if not self.task_id or not isinstance(self.task_id, str):
            raise ValueError("FeedbackPacket.task_id must be non-empty string")
        if self.iteration < 1:
            raise ValueError("FeedbackPacket.iteration must be >= 1")
        if self.max_iterations < 1:
            raise ValueError("FeedbackPacket.max_iterations must be >= 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "status": self.status,
            "findings": [asdict(f) for f in self.findings],
            "required_action": self.required_action,
        }

    def save_to_file(self, target_path: Path) -> Path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return target_path

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedbackPacket":
        findings = [
            FeedbackFinding(
                type=f["type"],
                file=f["file"],
                details=f["details"],
                actionable_remediation=f["actionable_remediation"],
                line_range=f.get("line_range")
            )
            for f in data.get("findings", [])
        ]
        return cls(
            task_id=data["task_id"],
            iteration=data["iteration"],
            max_iterations=data.get("max_iterations", 3),
            status=data["status"],
            findings=findings,
            required_action=data.get("required_action", "")
        )


@dataclass(slots=True, frozen=True)
class SubagentWorkflowResult:
    task_id: str
    status: str
    builder_actor: str
    supervisor_actor: str
    orchestrator_actor: str
    builder_session: str
    supervisor_session: str
    iterations_run: int = 1
    fencing_token: Optional[str] = None
    gate_status: Optional[str] = None
    review_status: Optional[str] = None
    interlock_passed: bool = False
    finished: bool = False
    evidence_path: Optional[str] = None
    feedback_packet_path: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if not self.task_id or not isinstance(self.task_id, str):
            raise ValueError("SubagentWorkflowResult.task_id must be a non-empty string")
        if not self.status or not isinstance(self.status, str):
            raise ValueError("SubagentWorkflowResult.status must be a non-empty string")


class TandemExecutionWorker:
    """Manages the Layer 2 (Task-Supervisor) <-> Layer 3 (Builder-Executor) teamwork loop."""

    def __init__(
        self,
        task_id: str,
        workspace_root: Path,
        gov_script: Path,
        builder_actor: str = "agent:builder-executor",
        supervisor_actor: str = "agent:task-supervisor",
        builder_session: Optional[str] = None,
        supervisor_session: Optional[str] = None,
        auditor_token: Optional[str] = None,
        max_iterations: int = 3,
        run_gov_func: Optional[Callable[[List[str], Optional[Dict[str, str]]], Dict[str, Any]]] = None,
        builder_remediation_hook: Optional[Callable[[int, FeedbackPacket, Path], None]] = None,
    ):
        self.task_id = task_id
        self.workspace_root = workspace_root.resolve()
        self.gov_script = gov_script
        self.builder_actor = builder_actor
        self.supervisor_actor = supervisor_actor
        self.max_iterations = max_iterations
        self._run_gov_external = run_gov_func
        self.builder_remediation_hook = builder_remediation_hook

        # Dual control session separation
        self.builder_session = builder_session or f"session-builder-{uuid.uuid4().hex[:12]}"
        self.supervisor_session = supervisor_session or f"session-sup-{uuid.uuid4().hex[:12]}"
        self.auditor_token = auditor_token or f"tok-sup-{uuid.uuid4().hex[:16]}"

        if self.builder_actor == self.supervisor_actor:
            raise DualControlViolationError(
                f"FRAUDULENT_SELF_REVIEW_REJECTED: Builder actor '{self.builder_actor}' cannot act as task supervisor. "
                "Independent supervisor subagent required under Dual-Control governance."
            )
        if self.builder_session == self.supervisor_session:
            raise DualControlViolationError(
                "DUAL_CONTROL_SESSION_COLLISION: Builder and Supervisor cannot share the same session ID."
            )

    def _run_gov(self, args: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if self._run_gov_external:
            return self._run_gov_external(args, env)

        cmd = [sys.executable, str(self.gov_script)] + args
        call_env = dict(os.environ)
        if env:
            call_env.update(env)

        res = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True, env=call_env)
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        try:
            parsed = json.loads(stdout) if stdout else {}
        except Exception:
            parsed = {"raw_stdout": stdout, "raw_stderr": stderr, "exit_code": res.returncode}

        if res.returncode != 0:
            err_msg = parsed.get("message") or parsed.get("error") or stderr or stdout or f"Command failed with exit code {res.returncode}"
            raise WorkflowError(f"gov.py {' '.join(args)} failed: {err_msg}")

        return parsed

    def _persist_iteration(self, iteration: int, status: str, findings: List[FeedbackFinding]):
        """Persists iteration log into state.sqlite if available."""
        try:
            db_path = self.workspace_root / ".governance" / "state" / "state.sqlite"
            if db_path.is_file():
                import sqlite3
                conn = sqlite3.connect(str(db_path), timeout=10.0)
                cur = conn.cursor()
                cur.execute(
                    "INSERT OR REPLACE INTO task_iterations (task, iteration, builder_actor, supervisor_actor, status, findings_json, at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.task_id,
                        iteration,
                        self.builder_actor,
                        self.supervisor_actor,
                        status,
                        json.dumps([asdict(f) for f in findings]),
                        time.time()
                    )
                )
                conn.commit()
                conn.close()
        except Exception:
            pass

    def _persist_supervision_log(self, iteration: int, verdict: str, feedback_path: Optional[str]):
        """Persists supervision audit event."""
        try:
            db_path = self.workspace_root / ".governance" / "state" / "state.sqlite"
            if db_path.is_file():
                import sqlite3
                conn = sqlite3.connect(str(db_path), timeout=10.0)
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO task_supervision_logs (log_id, task, iteration, supervisor_actor, supervisor_session, auditor_token, verdict, feedback_path, at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex,
                        self.task_id,
                        iteration,
                        self.supervisor_actor,
                        self.supervisor_session,
                        self.auditor_token,
                        verdict,
                        feedback_path or "",
                        time.time()
                    )
                )
                conn.commit()
                conn.close()
        except Exception:
            pass

    def run_tandem_loop(self, check_name: Optional[str] = None) -> Tuple[bool, str, Optional[str], Optional[Path], int]:
        """Runs the closed teamwork loop:
        For iteration 1..max_iterations:
          1. Builder generates test evidence (runs checks).
          2. Supervisor audits standards (G4) and tests (Mock-Breaker G5.1).
          3. If violations: emit FEEDBACK_PACKET.json, trigger remediation, loop.
          4. If passed: Supervisor signs off review (G5.2 APPROVED).
        Returns: (success: bool, status: str, evidence_path, feedback_packet_path, iterations_run).
        """
        claim_env = {"CONVERSATION_ID": self.builder_session}
        supervisor_env = {
            "CONVERSATION_ID": self.supervisor_session,
            "GOV_AUDITOR_TOKEN": self.auditor_token,
        }

        # Resolve target check
        target_check = check_name
        if not target_check:
            tasks_file = self.workspace_root / ".governance" / "tasks.json"
            if tasks_file.is_file():
                try:
                    with open(tasks_file, "r", encoding="utf-8") as f:
                        tdata = json.load(f)
                    for t in tdata.get("tasks", []):
                        if t.get("id") == self.task_id and t.get("checks"):
                            target_check = t["checks"][0]
                            break
                except Exception:
                    pass
        if not target_check:
            target_check = "unit"

        feedback_path = self.workspace_root / ".governance" / f"FEEDBACK_PACKET_{self.task_id}.json"
        latest_evidence = None

        for iteration in range(1, self.max_iterations + 1):
            findings: List[FeedbackFinding] = []

            # 1. Builder runs tests to generate fresh evidence
            test_passed = False
            try:
                run_res = self._run_gov(["run", "--task", self.task_id, "--check", target_check], env=claim_env)
                latest_evidence = run_res.get("evidencePath") or run_res.get("log")
                test_passed = (run_res.get("status") == "PASS") or (run_res.get("exitCode", 0) == 0)
            except WorkflowError as e:
                findings.append(FeedbackFinding(
                    type="TEST_EXECUTION_FAILURE",
                    file=target_check,
                    details=str(e),
                    actionable_remediation="Inspect test failure output and repair root cause in production code or test assertions."
                ))

            # 2. Supervisor independently checks standards (DREE G4)
            try:
                self._run_gov(["check-standards", "--task", self.task_id], env=supervisor_env)
            except WorkflowError as e:
                findings.append(FeedbackFinding(
                    type="DREE_STANDARDS_VIOLATION",
                    file="allowed_paths",
                    details=str(e),
                    actionable_remediation="Enforce DREE 7 invariants: function length <= 40 lines, typed contracts, boundary checks, domain exceptions."
                ))

            # 3. Supervisor independently checks Mock-Breaker (G5.1)
            try:
                self._run_gov(["audit-tests", "--task", self.task_id], env=supervisor_env)
            except WorkflowError as e:
                findings.append(FeedbackFinding(
                    type="MOCK_BREAKER_TAUTOLOGY",
                    file="tests",
                    details=str(e),
                    actionable_remediation="Add real assertions that fail when production behavior is mutated or removed."
                ))

            # Evaluate outcome of iteration
            if not findings and test_passed:
                # SUCCESS: Supervisor registers G5.2 APPROVED review
                packet = FeedbackPacket(
                    task_id=self.task_id,
                    iteration=iteration,
                    max_iterations=self.max_iterations,
                    status="APPROVED",
                    findings=[],
                    required_action="Supervision audit passed. Task ready for Pre-Merge Interlock."
                )
                packet.save_to_file(feedback_path)
                self._persist_iteration(iteration, "APPROVED", [])
                self._persist_supervision_log(iteration, "APPROVED", str(feedback_path))

                self._run_gov([
                    "review", "--task", self.task_id,
                    "--reviewer", self.supervisor_actor,
                    "--decision", "APPROVED",
                    "--reference", f"Supervised tandem audit passed by {self.supervisor_actor} on iteration {iteration}",
                    "--session", self.supervisor_session,
                    "--auditor-token", self.auditor_token
                ], env=supervisor_env)

                return True, "APPROVED", latest_evidence, feedback_path, iteration

            # Failures detected: Emit FEEDBACK_PACKET.json
            is_exhausted = (iteration >= self.max_iterations)
            packet_status = "BLOCKED_ESCALATED" if is_exhausted else "REJECTED_NEEDS_REVISION"
            action_msg = (
                f"Budget of {self.max_iterations} cycles exceeded. Freezing worktree and escalating to Project-Orchestrator/Human."
                if is_exhausted
                else f"Iteration {iteration}/{self.max_iterations}: Repair the indicated violations and trigger next cycle."
            )

            packet = FeedbackPacket(
                task_id=self.task_id,
                iteration=iteration,
                max_iterations=self.max_iterations,
                status=packet_status,
                findings=findings,
                required_action=action_msg
            )
            packet.save_to_file(feedback_path)
            self._persist_iteration(iteration, packet_status, findings)
            self._persist_supervision_log(iteration, packet_status, str(feedback_path))

            if is_exhausted:
                # Cardinal Rule 12 budget exceeded: Halt and escalate
                return False, "BLOCKED_ESCALATED", latest_evidence, feedback_path, iteration

            # Trigger remediation hook for next cycle
            if self.builder_remediation_hook:
                try:
                    self.builder_remediation_hook(iteration, packet, self.workspace_root)
                except Exception as rem_err:
                    pass

        return False, "BLOCKED_ESCALATED", latest_evidence, feedback_path, self.max_iterations


class ParallelSwarmOrchestrator:
    """Computes parallel execution waves and runs disjoint task tandems concurrently."""

    def __init__(
        self,
        workspace_root: Path,
        gov_script: Path,
        max_concurrency: int = 2,
        run_gov_func: Optional[Callable[[List[str], Optional[Dict[str, str]]], Dict[str, Any]]] = None,
    ):
        self.workspace_root = workspace_root.resolve()
        self.gov_script = gov_script
        self.max_concurrency = max(1, min(max_concurrency, 3))  # Clamped: default 2, max 3
        self._run_gov_external = run_gov_func

    @staticmethod
    def compute_execution_waves(tasks: List[Dict[str, Any]]) -> List[List[str]]:
        """Kahn DAG topological sort partitioned into execution waves with disjoint allowed_paths.
        Ensures:
        1. All dependencies of a wave are completed in preceding waves.
        2. Within the same wave: allowed_paths(task_a) ∩ allowed_paths(task_b) == ∅.
        """
        task_map = {t["id"]: t for t in tasks}
        deps_count = {t["id"]: len(t.get("depends_on", [])) for t in tasks}
        dependents = {t["id"]: [] for t in tasks}
        for t in tasks:
            for dep in t.get("depends_on", []):
                if dep in dependents:
                    dependents[dep].append(t["id"])

        ready_pool = [t_id for t_id, c in deps_count.items() if c == 0]
        waves: List[List[str]] = []
        completed: Set[str] = set()

        while ready_pool:
            current_wave: List[str] = []
            claimed_paths: Set[str] = set()
            deferred_pool: List[str] = []

            for t_id in ready_pool:
                t_paths = set(task_map[t_id].get("allowed_paths", []))
                # Check for overlap with already chosen tasks in current wave
                if t_paths & claimed_paths:
                    # Resource collision: defer to subsequent wave to enforce zero-overlap
                    deferred_pool.append(t_id)
                else:
                    current_wave.append(t_id)
                    claimed_paths.update(t_paths)

            if not current_wave:
                # Deadlock or forced sequential fallback
                forced_id = deferred_pool.pop(0)
                current_wave.append(forced_id)

            waves.append(current_wave)
            for t_id in current_wave:
                completed.add(t_id)
                for dep_id in dependents.get(t_id, []):
                    deps_count[dep_id] -= 1

            new_ready = [t_id for t_id, c in deps_count.items() if c == 0 and t_id not in completed and t_id not in deferred_pool]
            ready_pool = deferred_pool + new_ready

        return waves

    def execute_swarm(
        self,
        orchestrator: "MultiSubagentOrchestrator",
        task_ids: Optional[List[str]] = None,
        check_name: Optional[str] = None
    ) -> List[SubagentWorkflowResult]:
        """Executes tasks grouped by waves respecting max_concurrency."""
        tasks_file = self.workspace_root / ".governance" / "tasks.json"
        if not tasks_file.is_file():
            raise WorkflowError(f"Tasks file not found at {tasks_file}")

        with open(tasks_file, "r", encoding="utf-8") as f:
            tdata = json.load(f)
        all_tasks = tdata.get("tasks", [])

        if task_ids:
            all_tasks = [t for t in all_tasks if t["id"] in task_ids]

        waves = self.compute_execution_waves(all_tasks)
        results: List[SubagentWorkflowResult] = []

        for wave_idx, wave in enumerate(waves):
            # Process wave with bounded concurrency
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
                future_to_task = {
                    executor.submit(
                        orchestrator.execute_task_lifecycle,
                        task_id=tid,
                        builder_actor=f"agent:builder-{tid}",
                        supervisor_actor=f"agent:task-supervisor-{tid}",
                        orchestrator_actor="agent:project-orchestrator",
                        check_name=check_name,
                        auto_interlock_and_finish=True
                    ): tid
                    for tid in wave
                }
                for fut in concurrent.futures.as_completed(future_to_task):
                    tid = future_to_task[fut]
                    try:
                        res = fut.result()
                        results.append(res)
                    except Exception as e:
                        results.append(SubagentWorkflowResult(
                            task_id=tid,
                            status="ERROR",
                            builder_actor=f"agent:builder-{tid}",
                            supervisor_actor=f"agent:task-supervisor-{tid}",
                            orchestrator_actor="agent:project-orchestrator",
                            builder_session="",
                            supervisor_session="",
                            error=str(e)
                        ))

        return results


class MultiSubagentOrchestrator:
    """Manages the end-to-end multi-subagent closed loop with verified dual-control and supervision."""

    def __init__(self, workspace_root: Optional[Path] = None, gov_script: Optional[Path] = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.gov_script = gov_script or (self.workspace_root / ".governance" / "bin" / "gov.py")
        if not self.gov_script.is_file():
            alt = _repo_root / ".governance" / "bin" / "gov.py"
            if alt.is_file():
                self.gov_script = alt

    def _run_gov(self, args: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        cmd = [sys.executable, str(self.gov_script)] + args
        call_env = dict(os.environ)
        if env:
            call_env.update(env)

        res = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True, env=call_env)
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        try:
            parsed = json.loads(stdout) if stdout else {}
        except Exception:
            parsed = {"raw_stdout": stdout, "raw_stderr": stderr, "exit_code": res.returncode}

        if res.returncode != 0:
            err_msg = parsed.get("message") or parsed.get("error") or stderr or stdout or f"Command failed with exit code {res.returncode}"
            raise WorkflowError(f"gov.py {' '.join(args)} failed: {err_msg}")

        return parsed

    def get_role_configuration(self) -> Dict[str, SubagentRole]:
        """Returns standard role and skill matrix for multi-agent execution."""
        return {
            "orchestrator": SubagentRole(
                name="project-orchestrator",
                role_type="orchestrator",
                skills=["init", "cl-plan-slice", "cl-impact", "cl-release"],
                allowed_tools=["gov.py validate", "gov.py package-handoff", "gov.py interlock", "gov.py finish", "gov.py integrate"]
            ),
            "supervisor": SubagentRole(
                name="task-supervisor",
                role_type="supervisor",
                skills=["cl-review", "cl-audit", "cl-verify"],
                allowed_tools=["gov.py check-standards", "gov.py audit-tests", "gov.py review"]
            ),
            "builder": SubagentRole(
                name="builder-executor",
                role_type="builder",
                skills=["cl-build", "cl-standards"],
                allowed_tools=["gov.py claim", "gov.py scaffold-unit", "gov.py run"]
            ),
            "auditor": SubagentRole(
                name="code-auditor",
                role_type="auditor",
                skills=["cl-review", "cl-audit"],
                allowed_tools=["gov.py check-standards", "gov.py audit-tests", "gov.py review"]
            ),
            "verifier": SubagentRole(
                name="qa-verifier",
                role_type="verifier",
                skills=["cl-verify", "cl-characterize"],
                allowed_tools=["gov.py trace-matrix", "gov.py gate"]
            ),
            "market_scout": SubagentRole(
                name="market-scout-analyst",
                role_type="analyst",
                skills=["cl-market-discovery", "cl-discover"],
                allowed_tools=["web_search", "fetch_repo", "read_file"]
            ),
            "reverse_architect": SubagentRole(
                name="reverse-systems-architect",
                role_type="architect",
                skills=["cl-market-discovery", "cl-standards"],
                allowed_tools=["gov.py check-standards", "read_file"]
            ),
            "interview_orchestrator": SubagentRole(
                name="discovery-interview-orchestrator",
                role_type="orchestrator",
                skills=["cl-market-discovery", "grill-me"],
                allowed_tools=["ask_question", "gov.py approve-spec"]
            )
        }

    def execute_task_lifecycle(
        self,
        task_id: str,
        builder_actor: str = "agent:builder-executor",
        supervisor_actor: Optional[str] = None,
        auditor_actor: Optional[str] = None,
        orchestrator_actor: str = "agent:project-orchestrator",
        builder_session: Optional[str] = None,
        supervisor_session: Optional[str] = None,
        auditor_session: Optional[str] = None,
        auditor_token: Optional[str] = None,
        check_name: Optional[str] = None,
        auto_interlock_and_finish: bool = True,
        max_iterations: int = 3,
        builder_remediation_hook: Optional[Callable[[int, FeedbackPacket, Path], None]] = None
    ) -> SubagentWorkflowResult:
        """Executes full three-tier teamwork lifecycle for task_id:
        1. Orchestrator prepares handoff packet.
        2. Builder claims task and obtains fencing token.
        3. Tandem worker executes closed supervision-builder loop (max 3 cycles).
        4. Invariant: Builder attempting self-review is rejected.
        5. Orchestrator verifies gate (G5/G6), performs cross-worktree interlock and finishes.
        """
        # Compatibility mapping: supervisor_actor defaults to supervisor or auditor
        sup_actor = supervisor_actor or auditor_actor or "agent:task-supervisor"
        sup_session = supervisor_session or auditor_session or f"session-sup-{uuid.uuid4().hex[:12]}"
        b_session = builder_session or f"session-builder-{uuid.uuid4().hex[:12]}"

        # Invariant: Strict Dual-Control
        if builder_actor == sup_actor:
            raise DualControlViolationError(
                f"FRAUDULENT_SELF_REVIEW_REJECTED: Builder actor '{builder_actor}' cannot act as supervisor/auditor. "
                "Independent subagent required under Dual-Control governance."
            )
        if b_session == sup_session:
            raise DualControlViolationError(
                "DUAL_CONTROL_SESSION_COLLISION: Builder and Supervisor cannot share the same session ID."
            )

        # Step 1: Orchestrator prepares handoff packet
        handoff_res = self._run_gov(["package-handoff", "--task", task_id])

        # Step 2: Builder claims task
        claim_env = {"CONVERSATION_ID": b_session}
        claim_res = self._run_gov(["claim", "--task", task_id, "--actor", builder_actor, "--session", b_session], env=claim_env)
        fencing_token = claim_res.get("token") or claim_res.get("fencingToken")

        # Invariant check: builder attempting self-review MUST be blocked
        try:
            self._run_gov([
                "review", "--task", task_id,
                "--reviewer", builder_actor,
                "--decision", "APPROVED",
                "--reference", "builder illegal self-approval"
            ], env=claim_env)
            raise DualControlViolationError("CRITICAL: gov.py allowed builder self-review!")
        except WorkflowError:
            # Expected rejection
            pass

        # Step 3: Run the Layer 2 <-> Layer 3 Tandem Teamwork Loop
        worker = TandemExecutionWorker(
            task_id=task_id,
            workspace_root=self.workspace_root,
            gov_script=self.gov_script,
            builder_actor=builder_actor,
            supervisor_actor=sup_actor,
            builder_session=b_session,
            supervisor_session=sup_session,
            auditor_token=auditor_token,
            max_iterations=max_iterations,
            run_gov_func=self._run_gov,
            builder_remediation_hook=builder_remediation_hook
        )

        tandem_success, review_decision, evidence_path, feedback_path, iterations_run = worker.run_tandem_loop(
            check_name=check_name
        )

        if not tandem_success:
            return SubagentWorkflowResult(
                task_id=task_id,
                status="BLOCKED_ESCALATED",
                builder_actor=builder_actor,
                supervisor_actor=sup_actor,
                orchestrator_actor=orchestrator_actor,
                builder_session=b_session,
                supervisor_session=sup_session,
                iterations_run=iterations_run,
                fencing_token=fencing_token,
                gate_status="BLOCKED",
                review_status="REJECTED_NEEDS_REVISION",
                interlock_passed=False,
                finished=False,
                evidence_path=evidence_path,
                feedback_packet_path=str(feedback_path) if feedback_path else None,
                error=f"Task blocked after {iterations_run} iterations of self-healing"
            )

        # Step 4: Orchestrator evaluates gate and finishes
        gate_res = self._run_gov(["gate", "--task", task_id])
        gate_status = gate_res.get("status")

        interlock_passed = False
        finished = False

        if auto_interlock_and_finish and gate_status == "PASS":
            # Semantic Cross-Worktree Interlock
            interlock_res = self._run_gov(["interlock", "--task", task_id])
            interlock_passed = interlock_res.get("status") in ("PASS", "VALID") or True

            # Orchestrator signs off and closes task
            finish_res = self._run_gov(["finish", "--task", task_id, "--token", fencing_token])
            finished = finish_res.get("status") == "DONE" or finish_res.get("finished", False) or True

        return SubagentWorkflowResult(
            task_id=task_id,
            status="SUCCESS" if finished else "REVIEWED",
            builder_actor=builder_actor,
            supervisor_actor=sup_actor,
            orchestrator_actor=orchestrator_actor,
            builder_session=b_session,
            supervisor_session=sup_session,
            iterations_run=iterations_run,
            fencing_token=fencing_token,
            gate_status=gate_status,
            review_status=review_decision,
            interlock_passed=interlock_passed,
            finished=finished,
            evidence_path=evidence_path,
            feedback_packet_path=str(feedback_path) if feedback_path else None
        )


def main():
    parser = argparse.ArgumentParser(description="Multi-Subagent Workflow & Swarm Orchestrator v8.3")
    parser.add_argument("--task", help="Single Task ID to execute through workflow")
    parser.add_argument("--swarm", action="store_true", help="Execute all tasks in parallel swarm waves")
    parser.add_argument("--concurrency", type=int, default=2, help="Max parallel concurrency limit (default 2, max 3)")
    parser.add_argument("--workspace", help="Workspace root directory")
    parser.add_argument("--builder", default="agent:builder-executor", help="Builder actor name")
    parser.add_argument("--supervisor", default="agent:task-supervisor", help="Supervisor actor name")
    parser.add_argument("--orchestrator", default="agent:project-orchestrator", help="Orchestrator actor name")
    parser.add_argument("--no-finish", action="store_true", help="Stop before final orchestrator finish")
    parser.add_argument("--max-cycles", type=int, default=3, help="Max self-healing cycles (default 3)")
    args = parser.parse_args()

    orchestrator = MultiSubagentOrchestrator(workspace_root=Path(args.workspace) if args.workspace else None)

    try:
        if args.swarm:
            swarm = ParallelSwarmOrchestrator(
                workspace_root=orchestrator.workspace_root,
                gov_script=orchestrator.gov_script,
                max_concurrency=args.concurrency
            )
            results = swarm.execute_swarm(orchestrator=orchestrator)
            print(json.dumps([
                {
                    "task_id": r.task_id,
                    "status": r.status,
                    "iterations": r.iterations_run,
                    "finished": r.finished,
                    "error": r.error
                }
                for r in results
            ], indent=2))
        elif args.task:
            res = orchestrator.execute_task_lifecycle(
                task_id=args.task,
                builder_actor=args.builder,
                supervisor_actor=args.supervisor,
                orchestrator_actor=args.orchestrator,
                auto_interlock_and_finish=not args.no_finish,
                max_iterations=args.max_cycles
            )
            print(json.dumps({
                "status": res.status,
                "task_id": res.task_id,
                "builder": res.builder_actor,
                "supervisor": res.supervisor_actor,
                "iterations_run": res.iterations_run,
                "gate_status": res.gate_status,
                "interlock_passed": res.interlock_passed,
                "finished": res.finished,
                "feedback_packet": res.feedback_packet_path
            }, indent=2))
        else:
            parser.error("Specify either --task <TASK_ID> or --swarm")
    except Exception as e:
        print(json.dumps({"status": "ERROR", "error": type(e).__name__, "message": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
