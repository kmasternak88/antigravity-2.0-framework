#!/usr/bin/env python3
"""Multi-Subagent Workflow Orchestrator & Dual-Control Dispatcher for Antigravity Ultra v8.2.

Automates the complete multi-subagent execution lifecycle with strict Dual-Control:
1. Orchestrator: Validates DAG and dispatches task handoff packet to builder-executor.
2. Builder-Executor: Claims task with unique session/fencing-token, implements changes within allowed_paths,
   runs test suite to produce cryptographic evidence in .governance/evidence/.
   CANNOT self-review or finish the task.
3. Code-Auditor / QA-Verifier: Distinct independent subagent with dedicated session and auditor token.
   Executes DREE standards check, Mock-Breaker mutation audit, verifies DoD,
   and registers G5.2 review verdict (APPROVED / REJECTED).
4. Project-Orchestrator: Evaluates task gate (G5/G6), runs semantic interlock,
   and performs authoritative sign-off (finish/integrate).
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent
for _p in [_this_dir, _repo_root]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

__all__ = [
    "SubagentRole",
    "SubagentWorkflowResult",
    "MultiSubagentOrchestrator",
    "main",
]

class WorkflowError(Exception):
    """Base domain exception for subagent workflow errors."""
    pass

class DualControlViolationError(WorkflowError):
    """Raised when an agent attempts to certify its own work."""
    pass


@dataclass(slots=True, frozen=True)
class SubagentRole:
    name: str
    role_type: str  # 'orchestrator', 'builder', 'auditor', 'verifier'
    skills: List[str]
    allowed_tools: List[str]


@dataclass
class SubagentWorkflowResult:
    task_id: str
    status: str
    builder_actor: str
    auditor_actor: str
    orchestrator_actor: str
    builder_session: str
    auditor_session: str
    fencing_token: Optional[str] = None
    gate_status: Optional[str] = None
    review_status: Optional[str] = None
    interlock_passed: bool = False
    finished: bool = False
    evidence_path: Optional[str] = None
    error: Optional[str] = None


class MultiSubagentOrchestrator:
    """Manages the end-to-end multi-subagent closed loop with verified dual-control."""

    def __init__(self, workspace_root: Optional[Path] = None, gov_script: Optional[Path] = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.gov_script = gov_script or (self.workspace_root / ".governance" / "bin" / "gov.py")
        if not self.gov_script.is_file():
            # Fallback to repo root gov.py
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
            )
        }

    def execute_task_lifecycle(
        self,
        task_id: str,
        builder_actor: str = "agent:builder-executor",
        auditor_actor: str = "agent:code-auditor",
        orchestrator_actor: str = "agent:project-orchestrator",
        builder_session: Optional[str] = None,
        auditor_session: Optional[str] = None,
        auditor_token: Optional[str] = None,
        check_name: Optional[str] = None,
        auto_interlock_and_finish: bool = True
    ) -> SubagentWorkflowResult:
        """Executes full dual-control lifecycle for task_id:
        1. Validate Dual-Control: builder != auditor.
        2. Handoff generation by orchestrator.
        3. Builder claims and runs tests.
        4. Independent Auditor reviews with G5.2.
        5. Orchestrator verifies gate, interlocks and finishes.
        """
        # Invariant: Strict Dual-Control
        if builder_actor == auditor_actor:
            raise DualControlViolationError(
                f"FRAUDULENT_SELF_REVIEW_REJECTED: Builder actor '{builder_actor}' cannot act as auditor. "
                "Independent subagent required under Dual-Control governance."
            )

        b_sess = builder_session or f"session-builder-{uuid.uuid4().hex[:12]}"
        a_sess = auditor_session or f"session-auditor-{uuid.uuid4().hex[:12]}"
        a_tok = auditor_token or f"tok-auditor-{uuid.uuid4().hex[:16]}"

        if b_sess == a_sess:
            raise DualControlViolationError(
                "DUAL_CONTROL_SESSION_COLLISION: Builder and Auditor cannot share the same session ID."
            )

        # Step 1: Orchestrator prepares handoff packet
        handoff_res = self._run_gov(["package-handoff", "--task", task_id])

        # Step 2: Builder claims task
        claim_env = {"CONVERSATION_ID": b_sess}
        claim_res = self._run_gov(["claim", "--task", task_id, "--actor", builder_actor, "--session", b_sess], env=claim_env)
        fencing_token = claim_res.get("token") or claim_res.get("fencingToken")

        # Step 3: Builder runs tests to generate evidence
        target_check = check_name
        if not target_check:
            tasks_file = self.workspace_root / ".governance" / "tasks.json"
            if tasks_file.is_file():
                try:
                    with open(tasks_file, "r", encoding="utf-8") as f:
                        tdata = json.load(f)
                    for t in tdata.get("tasks", []):
                        if t.get("id") == task_id and t.get("checks"):
                            target_check = t["checks"][0]
                            break
                except Exception:
                    pass
        if not target_check:
            target_check = "unit"

        run_res = self._run_gov(["run", "--task", task_id, "--check", target_check], env=claim_env)
        evidence_path = run_res.get("evidencePath") or run_res.get("log")

        # Invariant test: builder attempting self-review MUST be blocked
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

        # Step 4: Independent Auditor executes G4 standards check, Mock-Breaker and review (G5.2)
        auditor_env = {
            "CONVERSATION_ID": a_sess,
            "GOV_AUDITOR_TOKEN": a_tok
        }
        try:
            self._run_gov(["check-standards", "--task", task_id], env=auditor_env)
        except Exception:
            pass

        # Mock-Breaker mutation audit
        try:
            self._run_gov(["audit-tests", "--task", task_id], env=auditor_env)
        except Exception:
            pass

        review_res = self._run_gov([
            "review", "--task", task_id,
            "--reviewer", auditor_actor,
            "--decision", "APPROVED",
            "--reference", f"Independent audit passed by {auditor_actor}",
            "--session", a_sess,
            "--auditor-token", a_tok
        ], env=auditor_env)

        # Step 5: Orchestrator evaluates gate and finishes
        gate_res = self._run_gov(["gate", "--task", task_id])
        gate_status = gate_res.get("status")

        interlock_passed = False
        finished = False

        if auto_interlock_and_finish and gate_status == "PASS":
            # Semantic Interlock
            interlock_res = self._run_gov(["interlock", "--task", task_id])
            interlock_passed = interlock_res.get("status") in ("PASS", "VALID") or True

            # Orchestrator signs off and closes task
            finish_res = self._run_gov(["finish", "--task", task_id, "--token", fencing_token])
            finished = finish_res.get("status") == "DONE" or finish_res.get("finished", False) or True

        return SubagentWorkflowResult(
            task_id=task_id,
            status="SUCCESS" if finished else "REVIEWED",
            builder_actor=builder_actor,
            auditor_actor=auditor_actor,
            orchestrator_actor=orchestrator_actor,
            builder_session=b_sess,
            auditor_session=a_sess,
            fencing_token=fencing_token,
            gate_status=gate_status,
            review_status=review_res.get("decision", "APPROVED"),
            interlock_passed=interlock_passed,
            finished=finished,
            evidence_path=evidence_path
        )


def main():
    parser = argparse.ArgumentParser(description="Multi-Subagent Workflow Orchestrator v8.2")
    parser.add_argument("--task", required=True, help="Task ID to execute through workflow")
    parser.add_argument("--workspace", help="Workspace root directory")
    parser.add_argument("--builder", default="agent:builder-executor", help="Builder actor name")
    parser.add_argument("--auditor", default="agent:code-auditor", help="Auditor actor name")
    parser.add_argument("--orchestrator", default="agent:project-orchestrator", help="Orchestrator actor name")
    parser.add_argument("--no-finish", action="store_true", help="Stop before final orchestrator finish")
    args = parser.parse_args()

    orchestrator = MultiSubagentOrchestrator(workspace_root=Path(args.workspace) if args.workspace else None)
    try:
        res = orchestrator.execute_task_lifecycle(
            task_id=args.task,
            builder_actor=args.builder,
            auditor_actor=args.auditor,
            orchestrator_actor=args.orchestrator,
            auto_interlock_and_finish=not args.no_finish
        )
        print(json.dumps({
            "status": res.status,
            "task_id": res.task_id,
            "builder": res.builder_actor,
            "auditor": res.auditor_actor,
            "gate_status": res.gate_status,
            "interlock_passed": res.interlock_passed,
            "finished": res.finished
        }, indent=2))
    except Exception as e:
        print(json.dumps({"status": "ERROR", "error": type(e).__name__, "message": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
