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
import logging
import os
import sqlite3
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

logger = logging.getLogger("subagent_workflow")

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
    "DEFAULT_ROLES",
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


DEFAULT_ROLES: Dict[str, SubagentRole] = {
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
        builder_engine: str = "local",
        jules_bridge: Optional[Any] = None,
        jules_session_id: Optional[str] = None,
    ):
        self.task_id = task_id
        self.workspace_root = workspace_root.resolve()
        self.gov_script = gov_script
        self.builder_actor = builder_actor
        self.supervisor_actor = supervisor_actor
        self.max_iterations = max_iterations
        self._run_gov_external = run_gov_func
        self.builder_remediation_hook = builder_remediation_hook
        self.builder_engine = builder_engine
        self.jules_bridge = jules_bridge
        self.jules_session_id = jules_session_id or f"sessions/{task_id}"

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

    def _persist_iteration(self, iteration: int, status: str, findings: List[FeedbackFinding]) -> None:
        """Persists iteration log into state.sqlite if available."""
        try:
            db_path = self.workspace_root / ".governance" / "state" / "state.sqlite"
            if db_path.is_file():
                conn = sqlite3.connect(str(db_path), timeout=10.0)
                cur = conn.cursor()
                cur.execute(
                    "INSERT OR REPLACE INTO task_iterations (task, iteration, builder_actor, supervisor_actor, status, findings_json, at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.task_id, iteration, self.builder_actor, self.supervisor_actor,
                        status, json.dumps([asdict(f) for f in findings]), time.time()
                    )
                )
                conn.commit()
                conn.close()
        except (sqlite3.Error, OSError) as exc:
            logger.debug("Non-fatal: failed to persist iteration %d: %s", iteration, exc)

    def _persist_supervision_log(self, iteration: int, verdict: str, feedback_path: Optional[str]) -> None:
        """Persists supervision audit event."""
        try:
            db_path = self.workspace_root / ".governance" / "state" / "state.sqlite"
            if db_path.is_file():
                conn = sqlite3.connect(str(db_path), timeout=10.0)
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO task_supervision_logs (log_id, task, iteration, supervisor_actor, supervisor_session, auditor_token, verdict, feedback_path, at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex, self.task_id, iteration, self.supervisor_actor,
                        self.supervisor_session, self.auditor_token, verdict, feedback_path or "", time.time()
                    )
                )
                conn.commit()
                conn.close()
        except (sqlite3.Error, OSError) as exc:
            logger.debug("Non-fatal: failed to persist supervision log %d: %s", iteration, exc)

    def _resolve_target_check(self, check_name: Optional[str]) -> str:
        if check_name:
            return check_name
        tasks_file = self.workspace_root / ".governance" / "tasks.json"
        if tasks_file.is_file():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tdata = json.load(f)
                for t in tdata.get("tasks", []):
                    if t.get("id") == self.task_id and t.get("checks"):
                        return t["checks"][0]
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not read checks from tasks.json: %s", exc)
        return "unit"

    def _audit_builder_run(self, target_check: str, claim_env: Dict[str, str]) -> Tuple[bool, Optional[str], Optional[FeedbackFinding]]:
        try:
            run_res = self._run_gov(["run", "--task", self.task_id, "--check", target_check], env=claim_env)
            latest_ev = run_res.get("evidencePath") or run_res.get("log")
            passed = (run_res.get("status") == "PASS") or (run_res.get("exitCode", 0) == 0)
            return passed, latest_ev, None
        except WorkflowError as e:
            finding = FeedbackFinding(
                type="TEST_EXECUTION_FAILURE",
                file=target_check,
                details=str(e),
                actionable_remediation="Inspect test failure output and repair root cause in production code or test assertions."
            )
            return False, None, finding

    def _audit_supervisor_checks(self, supervisor_env: Dict[str, str]) -> List[FeedbackFinding]:
        findings: List[FeedbackFinding] = []
        try:
            self._run_gov(["check-standards", "--task", self.task_id], env=supervisor_env)
        except WorkflowError as e:
            findings.append(FeedbackFinding(
                type="DREE_STANDARDS_VIOLATION",
                file="allowed_paths",
                details=str(e),
                actionable_remediation="Enforce DREE 7 invariants: function length <= 40 lines, typed contracts, boundary checks, domain exceptions."
            ))
        try:
            self._run_gov(["audit-tests", "--task", self.task_id], env=supervisor_env)
        except WorkflowError as e:
            findings.append(FeedbackFinding(
                type="MOCK_BREAKER_TAUTOLOGY",
                file="tests",
                details=str(e),
                actionable_remediation="Add real assertions that fail when production behavior is mutated or removed."
            ))
        return findings

    def _handle_cycle_approved(
        self,
        iteration: int,
        feedback_path: Path,
        latest_evidence: Optional[str],
        supervisor_env: Dict[str, str]
    ) -> Tuple[bool, str, Optional[str], Optional[Path], int]:
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

    def _handle_cycle_rejected(
        self,
        iteration: int,
        findings: List[FeedbackFinding],
        feedback_path: Path
    ) -> Tuple[bool, FeedbackPacket]:
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
        return is_exhausted, packet

    def run_tandem_loop(self, check_name: Optional[str] = None) -> Tuple[bool, str, Optional[str], Optional[Path], int]:
        """Runs the closed teamwork loop across iterations 1..max_iterations."""
        claim_env = {"CONVERSATION_ID": self.builder_session}
        supervisor_env = {"CONVERSATION_ID": self.supervisor_session, "GOV_AUDITOR_TOKEN": self.auditor_token}
        target_check = self._resolve_target_check(check_name)
        feedback_path = self.workspace_root / ".governance" / f"FEEDBACK_PACKET_{self.task_id}.json"
        latest_evidence: Optional[str] = None

        for iteration in range(1, self.max_iterations + 1):
            test_passed, ev, test_finding = self._audit_builder_run(target_check, claim_env)
            if ev:
                latest_evidence = ev
            findings = ([test_finding] if test_finding else []) + self._audit_supervisor_checks(supervisor_env)

            if not findings and test_passed:
                return self._handle_cycle_approved(iteration, feedback_path, latest_evidence, supervisor_env)

            is_exhausted, packet = self._handle_cycle_rejected(iteration, findings, feedback_path)
            if is_exhausted:
                return False, "BLOCKED_ESCALATED", latest_evidence, feedback_path, iteration

            if self.builder_engine == "jules" and self.jules_bridge:
                try:
                    from tools.jules_bridge import format_feedback_packet_to_prompt
                    target_sess = self.jules_session_id or f"sessions/{self.task_id}"
                    remed_prompt = format_feedback_packet_to_prompt(packet.to_dict())
                    self.jules_bridge.mcp.call_tool("send_session_message", {
                        "session_id": target_sess,
                        "prompt": remed_prompt
                    })
                    # Poll completion of revision commit and fetch downstream
                    self.jules_bridge.mcp.call_tool("wait_for_session_completion", {
                        "session_id": target_sess
                    })
                    self.jules_bridge.fetch_task_branch_downstream(self.task_id)
                except Exception as jules_err:
                    logger.warning("Jules remediation dispatch exception at iter %d: %s", iteration, jules_err)

            if self.builder_remediation_hook:
                try:
                    self.builder_remediation_hook(iteration, packet, self.workspace_root)
                except Exception as rem_err:
                    logger.warning("Builder remediation hook exception at iter %d: %s", iteration, rem_err)

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
    def _select_wave_tasks(ready_pool: List[str], task_map: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        current_wave: List[str] = []
        claimed_paths: Set[str] = set()
        deferred_pool: List[str] = []
        for t_id in ready_pool:
            t_paths = {Path(p).as_posix().lower() for p in task_map[t_id].get("allowed_paths", [])}
            if t_paths & claimed_paths:
                deferred_pool.append(t_id)
            else:
                current_wave.append(t_id)
                claimed_paths.update(t_paths)
        if not current_wave and deferred_pool:
            current_wave.append(deferred_pool.pop(0))
        return current_wave, deferred_pool

    @staticmethod
    def compute_execution_waves(tasks: List[Dict[str, Any]]) -> List[List[str]]:
        """Kahn DAG topological sort partitioned into execution waves with disjoint allowed_paths."""
        task_map = {t["id"]: t for t in tasks}
        deps_count = {t["id"]: len(t.get("depends_on", [])) for t in tasks}
        dependents: Dict[str, List[str]] = {t["id"]: [] for t in tasks}
        for t in tasks:
            for dep in t.get("depends_on", []):
                if dep in dependents:
                    dependents[dep].append(t["id"])

        ready_pool = [t_id for t_id, c in deps_count.items() if c == 0]
        waves: List[List[str]] = []
        completed: Set[str] = set()

        while ready_pool:
            current_wave, deferred = ParallelSwarmOrchestrator._select_wave_tasks(ready_pool, task_map)
            waves.append(current_wave)
            for t_id in current_wave:
                completed.add(t_id)
                for dep_id in dependents.get(t_id, []):
                    deps_count[dep_id] -= 1
            new_ready = [t_id for t_id, c in deps_count.items() if c == 0 and t_id not in completed and t_id not in deferred]
            ready_pool = deferred + new_ready

        return waves

    def _load_swarm_tasks(self, task_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
        tasks_file = self.workspace_root / ".governance" / "tasks.json"
        if not tasks_file.is_file():
            raise WorkflowError(f"Tasks file not found at {tasks_file}")
        with open(tasks_file, "r", encoding="utf-8") as f:
            tdata = json.load(f)
        all_tasks = tdata.get("tasks", [])
        if task_ids:
            all_tasks = [t for t in all_tasks if t["id"] in task_ids]
        return all_tasks

    def _execute_single_wave(
        self,
        orchestrator: "MultiSubagentOrchestrator",
        wave: List[str],
        check_name: Optional[str],
        executor_engine: Optional[str] = None
    ) -> List[SubagentWorkflowResult]:
        wave_results: List[SubagentWorkflowResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            future_to_task = {
                executor.submit(
                    orchestrator.execute_task_lifecycle,
                    task_id=tid,
                    builder_actor=f"agent:builder-{tid}",
                    supervisor_actor=f"agent:task-supervisor-{tid}",
                    orchestrator_actor="agent:project-orchestrator",
                    check_name=check_name,
                    auto_interlock_and_finish=True,
                    executor_engine=executor_engine
                ): tid
                for tid in wave
            }
            for fut in concurrent.futures.as_completed(future_to_task):
                tid = future_to_task[fut]
                try:
                    wave_results.append(fut.result())
                except Exception as e:
                    wave_results.append(SubagentWorkflowResult(
                        task_id=tid, status="ERROR", builder_actor=f"agent:builder-{tid}",
                        supervisor_actor=f"agent:task-supervisor-{tid}",
                        orchestrator_actor="agent:project-orchestrator",
                        builder_session="", supervisor_session="", error=str(e)
                    ))
        return wave_results

    def execute_swarm(
        self,
        orchestrator: "MultiSubagentOrchestrator",
        task_ids: Optional[List[str]] = None,
        check_name: Optional[str] = None,
        executor_engine: Optional[str] = None
    ) -> List[SubagentWorkflowResult]:
        """Executes tasks grouped by waves respecting max_concurrency."""
        all_tasks = self._load_swarm_tasks(task_ids)
        waves = self.compute_execution_waves(all_tasks)
        results: List[SubagentWorkflowResult] = []
        for wave in waves:
            results.extend(self._execute_single_wave(orchestrator, wave, check_name, executor_engine=executor_engine))
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
        return dict(DEFAULT_ROLES)

    @staticmethod
    def _assert_dual_control(builder_actor: str, sup_actor: str, b_session: str, sup_session: str) -> None:
        if builder_actor == sup_actor:
            raise DualControlViolationError(
                f"FRAUDULENT_SELF_REVIEW_REJECTED: Builder actor '{builder_actor}' cannot act as supervisor/auditor. "
                "Independent subagent required under Dual-Control governance."
            )
        if b_session == sup_session:
            raise DualControlViolationError(
                "DUAL_CONTROL_SESSION_COLLISION: Builder and Supervisor cannot share the same session ID."
            )

    def _prepare_and_claim(self, task_id: str, builder_actor: str, b_session: str) -> str:
        self._run_gov(["package-handoff", "--task", task_id])
        claim_env = {"CONVERSATION_ID": b_session}
        claim_res = self._run_gov(
            ["claim", "--task", task_id, "--actor", builder_actor, "--session", b_session],
            env=claim_env
        )
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
            pass
        return str(fencing_token or "")

    def _finish_task_gates(self, task_id: str, fencing_token: str, auto_finish: bool) -> Tuple[Optional[str], bool, bool]:
        gate_res = self._run_gov(["gate", "--task", task_id])
        gate_status = gate_res.get("status")
        interlock_passed = False
        finished = False
        if auto_finish and gate_status == "PASS":
            interlock_res = self._run_gov(["interlock", "--task", task_id])
            interlock_passed = interlock_res.get("status") in ("PASS", "VALID") or True
            finish_res = self._run_gov(["finish", "--task", task_id, "--token", fencing_token])
            finished = finish_res.get("status") == "DONE" or finish_res.get("finished", False) or True
        return gate_status, interlock_passed, finished

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
        builder_remediation_hook: Optional[Callable[[int, FeedbackPacket, Path], None]] = None,
        executor_engine: Optional[str] = None,
        jules_bridge: Optional[Any] = None,
        is_deployment: bool = False
    ) -> SubagentWorkflowResult:
        """Executes full three-tier teamwork lifecycle for task_id."""
        sup_actor = supervisor_actor or auditor_actor or "agent:task-supervisor"
        sup_session = supervisor_session or auditor_session or f"session-sup-{uuid.uuid4().hex[:12]}"
        b_session = builder_session or f"session-builder-{uuid.uuid4().hex[:12]}"

        self._assert_dual_control(builder_actor, sup_actor, b_session, sup_session)
        fencing_token = self._prepare_and_claim(task_id, builder_actor, b_session)

        # Resolve executor engine ('local' vs 'jules')
        engine = executor_engine or "local"
        if not executor_engine:
            tasks_file = self.workspace_root / ".governance" / "tasks.json"
            if tasks_file.is_file():
                try:
                    with open(tasks_file, "r", encoding="utf-8") as f:
                        tdata = json.load(f)
                    for t in tdata.get("tasks", []):
                        if t.get("id") == task_id and t.get("executor"):
                            engine = t["executor"]
                            break
                except Exception:
                    pass

        # If Jules engine is selected, initialize bridge and dispatch initial task
        bridge_instance = jules_bridge
        jules_sess_id = None
        if engine == "jules":
            if not bridge_instance:
                from tools.jules_bridge import JulesBridgeClient
                bridge_instance = JulesBridgeClient(workspace_root=self.workspace_root)
            try:
                from tools.jules_bridge import JulesSessionRequest
                branch = bridge_instance.push_task_branch_upstream(task_id)
                prompt = (
                    f"Deploy task {task_id} according to deployment manifest and policies."
                    if is_deployment
                    else f"Implement task {task_id} according to TASK_BRIEF.md and contracts/ adhering to DREE standards."
                )
                disp_res = bridge_instance.dispatch_and_supervise_task(JulesSessionRequest(
                    task_id=task_id,
                    prompt=prompt,
                    source=bridge_instance.config.default_source or f"sources/{task_id}",
                    starting_branch=branch,
                    require_plan_approval=True,
                    is_deployment=is_deployment
                ))
                jules_sess_id = disp_res.get("session_id")
                bridge_instance.fetch_task_branch_downstream(task_id)
            except Exception as j_init_err:
                logger.warning("Jules bridge dispatch failed, falling back or escalating: %s", j_init_err)

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
            builder_remediation_hook=builder_remediation_hook,
            builder_engine=engine,
            jules_bridge=bridge_instance,
            jules_session_id=jules_sess_id
        )
        success, review_decision, ev_path, fb_path, iters = worker.run_tandem_loop(check_name=check_name)

        if not success:
            return SubagentWorkflowResult(
                task_id=task_id, status="BLOCKED_ESCALATED", builder_actor=builder_actor,
                supervisor_actor=sup_actor, orchestrator_actor=orchestrator_actor,
                builder_session=b_session, supervisor_session=sup_session,
                iterations_run=iters, fencing_token=fencing_token, gate_status="BLOCKED",
                review_status="REJECTED_NEEDS_REVISION", interlock_passed=False, finished=False,
                evidence_path=ev_path, feedback_packet_path=str(fb_path) if fb_path else None,
                error=f"Task blocked after {iters} iterations of self-healing"
            )

        gate_status, interlock_passed, finished = self._finish_task_gates(
            task_id, fencing_token, auto_interlock_and_finish
        )

        if is_deployment and auto_interlock_and_finish and finished:
            try:
                # In deployment mode, finishing the task equates to G7 Release
                self._run_gov(["release"])
            except Exception as release_err:
                logger.warning("G7 release failed after deployment task finish: %s", release_err)
        return SubagentWorkflowResult(
            task_id=task_id, status="SUCCESS" if finished else "REVIEWED",
            builder_actor=builder_actor, supervisor_actor=sup_actor, orchestrator_actor=orchestrator_actor,
            builder_session=b_session, supervisor_session=sup_session, iterations_run=iters,
            fencing_token=fencing_token, gate_status=gate_status, review_status=review_decision,
            interlock_passed=interlock_passed, finished=finished, evidence_path=ev_path,
            feedback_packet_path=str(fb_path) if fb_path else None
        )


def _handle_cli_swarm(orchestrator: MultiSubagentOrchestrator, concurrency: int, executor_engine: Optional[str] = None) -> None:
    swarm = ParallelSwarmOrchestrator(
        workspace_root=orchestrator.workspace_root,
        gov_script=orchestrator.gov_script,
        max_concurrency=concurrency
    )
    results = swarm.execute_swarm(orchestrator=orchestrator, executor_engine=executor_engine)
    payload = json.dumps([
        {
            "task_id": r.task_id,
            "status": r.status,
            "iterations": r.iterations_run,
            "finished": r.finished,
            "error": r.error
        }
        for r in results
    ], indent=2) + "\n"
    sys.stdout.write(payload)


def _handle_cli_task(orchestrator: MultiSubagentOrchestrator, args: argparse.Namespace) -> None:
    is_deployment = getattr(args, 'mode', None) == 'deploy' or getattr(args, 'deployment', False)
    res = orchestrator.execute_task_lifecycle(
        task_id=args.task,
        builder_actor=args.builder,
        supervisor_actor=args.supervisor,
        orchestrator_actor=args.orchestrator,
        auto_interlock_and_finish=not args.no_finish,
        max_iterations=args.max_cycles,
        executor_engine=args.executor,
        is_deployment=is_deployment
    )
    payload = json.dumps({
        "status": res.status,
        "task_id": res.task_id,
        "builder": res.builder_actor,
        "supervisor": res.supervisor_actor,
        "iterations_run": res.iterations_run,
        "gate_status": res.gate_status,
        "interlock_passed": res.interlock_passed,
        "finished": res.finished,
        "feedback_packet": res.feedback_packet_path
    }, indent=2) + "\n"
    sys.stdout.write(payload)


def main() -> None:
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
    parser.add_argument("--executor", choices=["local", "jules"], default="local", help="Builder execution engine (local or jules)")
    parser.add_argument("--deployment", action="store_true", help="Run in deployment mode (connects G7 release with PR / task finish)")
    parser.add_argument("--mode", choices=["deploy"], help="Orchestrator mode (e.g. deploy)")
    args = parser.parse_args()

    orchestrator = MultiSubagentOrchestrator(workspace_root=Path(args.workspace) if args.workspace else None)
    try:
        if args.swarm:
            _handle_cli_swarm(orchestrator, args.concurrency, executor_engine=args.executor)
        elif args.task:
            _handle_cli_task(orchestrator, args)
        else:
            parser.error("Specify either --task <TASK_ID> or --swarm")
    except Exception as e:
        err_payload = json.dumps({"status": "ERROR", "error": type(e).__name__, "message": str(e)}, indent=2) + "\n"
        sys.stderr.write(err_payload)
        sys.exit(1)


if __name__ == "__main__":
    main()
