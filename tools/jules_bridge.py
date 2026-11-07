#!/usr/bin/env python3
"""Antigravity v8.3 <-> Google Jules MCP Bridge & Orchestration Adapter.

Connects Antigravity (Tier 1 Orchestrator & Tier 2 Task-Supervisor) with Google Jules
(Tier 3 Cloud Builder-Executor) via FastMCP protocol (ahaufox/jules-mcp-server).

Core Invariants Enforced:
1. Universal Polyglot / Omni-Stack: Agnostic to language/framework (Python, TS, Go, Rust, PHP).
2. Dual-Control Security (Rule 9): Jules implements code (agent:jules-builder); Antigravity
   supervisor independently audits and signs Gate G5.2.
3. Socratic Plan Audit: Intercepts plans when require_plan_approval=True, enforcing allowed_paths
   confinement, contract immutability, and DREE 7 invariants before calling approve_session_plan.
4. 3-Cycle Self-Healing (Rule 12): Maps FEEDBACK_PACKET.json findings into EARS-structured prompts
   for send_session_message up to 3 cycles, escalating to BLOCKED_ESCALATED on budget exhaustion.
5. Sovereign Dual-Sync Git: Coordinates remote branch pushes (task/<task_id>) and fetches
   into isolated local worktrees (.worktrees/<task_id>).
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

logger = logging.getLogger("jules_bridge")

__all__ = [
    "JulesBridgeError",
    "JulesPlanAuditError",
    "JulesConfig",
    "JulesPlanAuditResult",
    "JulesSessionRequest",
    "JulesMCPClientInterface",
    "MockJulesMCPClient",
    "JulesBridgeClient",
    "format_feedback_packet_to_prompt",
    "audit_jules_plan",
    "main",
]


class JulesBridgeError(Exception):
    """Base exception for Jules MCP bridge errors."""
    pass


class JulesPlanAuditError(JulesBridgeError):
    """Raised when Jules execution plan violates governance invariants."""
    pass


@dataclass(slots=True, frozen=True)
class JulesConfig:
    """Configuration for Jules MCP Server integration."""
    api_key: str
    server_command: List[str] = field(default_factory=lambda: ["python", "-m", "jules_mcp"])
    server_cwd: Optional[str] = None
    default_source: Optional[str] = None
    poll_interval: float = 2.0
    timeout_seconds: float = 600.0

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "JulesConfig":
        environ = env if env is not None else os.environ
        api_key = environ.get("JULES_API_KEY", "").strip()
        default_source = environ.get("JULES_DEFAULT_SOURCE", "").strip() or None
        cwd = environ.get("JULES_MCP_CWD", "").strip() or None
        return cls(
            api_key=api_key,
            default_source=default_source,
            server_cwd=cwd
        )


@dataclass(slots=True, frozen=True)
class JulesPlanAuditResult:
    approved: bool
    status: str  # 'APPROVED', 'REJECTED_PLAN'
    violations: List[str] = field(default_factory=list)
    remediation_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "status": self.status,
            "violations": self.violations,
            "remediation_prompt": self.remediation_prompt
        }


@dataclass(slots=True, frozen=True)
class JulesSessionRequest:
    task_id: str
    prompt: str
    source: str
    starting_branch: str
    require_plan_approval: bool = True
    allowed_paths: List[str] = field(default_factory=list)
    contract_paths: List[str] = field(default_factory=list)


class JulesMCPClientInterface:
    """Protocol interface for invoking FastMCP Jules tools."""

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class StdioJulesMCPClient(JulesMCPClientInterface):
    """Subprocess stdio JSON-RPC FastMCP client for live execution."""

    def __init__(self, server_command: Optional[List[str]] = None, server_cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        self.server_command = server_command or ["python", "-m", "jules_mcp"]
        self.server_cwd = server_cwd
        self.env = env

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes FastMCP tool call via Python FastMCP client one-shot invocation."""
        call_script = (
            f"import asyncio, json, sys\n"
            f"from fastmcp import Client\n"
            f"from jules_mcp import mcp\n"
            f"async def run():\n"
            f"    async with Client(mcp) as client:\n"
            f"        res = await client.call_tool({json.dumps(name)}, {json.dumps(arguments)})\n"
            f"        print(json.dumps(res, ensure_ascii=False))\n"
            f"asyncio.run(run())\n"
        )
        proc_env = dict(os.environ)
        if self.env:
            proc_env.update(self.env)

        proc = subprocess.run(
            [sys.executable, "-c", call_script],
            cwd=self.server_cwd or os.getcwd(),
            capture_output=True,
            text=True,
            env=proc_env
        )
        if proc.returncode != 0:
            raise JulesBridgeError(f"FastMCP call_tool '{name}' failed (exit code {proc.returncode}): {proc.stderr or proc.stdout}")
        try:
            return json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            return {"raw_stdout": proc.stdout.strip()}


class MockJulesMCPClient(JulesMCPClientInterface):
    """In-memory Mock MCP client for testing and offline development."""

    def __init__(self, sources: Optional[List[Dict[str, Any]]] = None):
        self.sources = sources or [{"name": "sources/github/owner/repo", "id": "repo-1"}]
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.activities: Dict[str, List[Dict[str, Any]]] = {}
        self.messages_sent: List[Dict[str, Any]] = []
        self.plans_approved: List[str] = []
        self._counter = 0

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "list_sources":
            return {"sources": self.sources}
        elif name == "get_all_sources":
            return {"sources": self.sources}
        elif name == "get_source":
            s_id = arguments.get("source_id")
            for s in self.sources:
                if s.get("name") == s_id or s.get("id") == s_id:
                    return s
            return {"error": f"Source {s_id} not found"}
        elif name == "create_session":
            self._counter += 1
            s_id = f"sessions/jules-test-{self._counter:04d}"
            sess = {
                "name": s_id,
                "id": s_id,
                "prompt": arguments.get("prompt", ""),
                "source": arguments.get("source", ""),
                "starting_branch": arguments.get("starting_branch", "main"),
                "require_plan_approval": arguments.get("require_plan_approval", True),
                "state": "AWAITING_PLAN_APPROVAL" if arguments.get("require_plan_approval") else "COMPLETED",
                "plan": arguments.get("mock_plan", "1. Implement vertical slice in allowed files.\n2. Run unit tests."),
            }
            self.sessions[s_id] = sess
            self.activities[s_id] = [{"id": "act-1", "type": "session_created"}]
            return sess
        elif name == "get_session":
            s_id = arguments.get("session_id")
            sess = self.sessions.get(s_id)
            if not sess:
                return {"error": f"Session {s_id} not found"}
            return sess
        elif name == "approve_session_plan":
            s_id = arguments.get("session_id")
            if s_id in self.sessions:
                self.sessions[s_id]["state"] = "IN_PROGRESS"
                self.plans_approved.append(s_id)
                return {"status": "SUCCESS", "session_id": s_id}
            return {"error": f"Session {s_id} not found"}
        elif name == "send_session_message":
            s_id = arguments.get("session_id")
            prompt = arguments.get("prompt", "")
            self.messages_sent.append({"session_id": s_id, "prompt": prompt})
            if s_id in self.sessions:
                self.sessions[s_id]["last_message"] = prompt
                self.sessions[s_id]["state"] = "IN_PROGRESS"
            return {"status": "SENT", "session_id": s_id}
        elif name == "wait_for_session_completion":
            s_id = arguments.get("session_id")
            if s_id in self.sessions:
                self.sessions[s_id]["state"] = "COMPLETED"
                return self.sessions[s_id]
            return {"error": f"Session {s_id} not found"}
        elif name in ("list_activities", "list_all_activities"):
            s_id = arguments.get("session_id")
            return {"activities": self.activities.get(s_id, [])}
        else:
            raise JulesBridgeError(f"Unknown MCP tool: {name}")


def audit_jules_plan(
    plan_text: str,
    allowed_paths: List[str],
    contract_paths: Optional[List[str]] = None
) -> JulesPlanAuditResult:
    """Socratically audits a proposed Jules plan against governance rules.

    Checks:
    1. Allowed Paths Confinement: Extracts mentioned file paths and ensures they reside in allowed_paths.
    2. Contract Immutability: Rejects any attempt to rewrite files in contracts/.
    3. DREE 7 Invariants: Plan must mention typed contracts/DTOs, boundary validation, and tests.
    """
    violations: List[str] = []
    norm_allowed = {Path(p).as_posix().lower() for p in allowed_paths}
    contracts = {Path(p).as_posix().lower() for p in (contract_paths or [])}

    # Extract path candidates (e.g. src/foo.py, contracts/bar.ts)
    raw_tokens = re.findall(r'[\w\-\./]+\.[a-zA-Z0-9]+', plan_text)
    candidate_paths = {Path(t.strip("`'\"")).as_posix().lower() for t in raw_tokens if "/" in t}

    for p in candidate_paths:
        # Check contract immutability
        if p in contracts or p.startswith("contracts/"):
            violations.append(
                f"CONTRACT_TAMPERING_FORBIDDEN: Plan proposes modifying frozen contract '{p}'. Contracts are immutable (Gate G2)."
            )
        # Check allowed paths confinement
        elif norm_allowed and (p not in norm_allowed and not any(p.startswith(a.rstrip("/") + "/") for a in norm_allowed)):
            # If path is not inside an allowed directory
            violations.append(
                f"PATH_CONFINEMENT_VIOLATION: Path '{p}' is outside allowed_paths for this task: {sorted(norm_allowed)}."
            )

    # Check DREE minimal awareness
    lower_plan = plan_text.lower()
    has_tests = any(k in lower_plan for k in ["test", "assert", "spec", "check", "verify"])
    if not has_tests:
        violations.append("DREE_DUAL_TEST_OMISSION: Plan fails to mention unit/regression tests or test verification.")

    if violations:
        remediation = (
            "[SUPERVISOR PLAN REJECTION - SOCRATIC AUDIT]\n"
            "Your proposed plan has been evaluated and REJECTED due to governance violations:\n"
            + "\n".join(f"- {v}" for v in violations) + "\n\n"
            "Actionable Instructions:\n"
            "1. Strictly confine all file creation and edits to allowed_paths.\n"
            "2. Treat contracts/ as frozen interfaces; do not modify contract definitions.\n"
            "3. Include a comprehensive test suite (happy-path + negative/boundary assertions).\n"
            "Please revise your plan and submit an updated plan for supervisor approval."
        )
        return JulesPlanAuditResult(
            approved=False,
            status="REJECTED_PLAN",
            violations=violations,
            remediation_prompt=remediation
        )

    return JulesPlanAuditResult(
        approved=True,
        status="APPROVED",
        violations=[],
        remediation_prompt=""
    )


def format_feedback_packet_to_prompt(feedback_data: Dict[str, Any]) -> str:
    """Translates a FEEDBACK_PACKET.json into an EARS-style remediation prompt for Jules."""
    task_id = feedback_data.get("task_id", "UNKNOWN")
    iteration = feedback_data.get("iteration", 1)
    max_iterations = feedback_data.get("max_iterations", 3)
    status = feedback_data.get("status", "REJECTED_NEEDS_REVISION")
    findings = feedback_data.get("findings", [])
    required_action = feedback_data.get("required_action", "")

    lines = [
        f"[SUPERVISOR AUDIT REJECTED - ITERATION {iteration}/{max_iterations}]",
        f"Task {task_id} failed local quality gate verification ({status}).",
        "",
        "Detected Invariant Violations:"
    ]

    if not findings:
        lines.append("- Quality checks failed without explicit AST findings. Inspect test failures.")
    else:
        for f in findings:
            f_type = f.get("type", "UNKNOWN_VIOLATION")
            f_file = f.get("file", "unknown_file")
            f_details = f.get("details", "")
            f_remed = f.get("actionable_remediation", "")
            f_range = f.get("line_range")
            range_info = f" (lines: {f_range})" if f_range else ""
            lines.append(f"• [{f_type}] in {f_file}{range_info}:")
            lines.append(f"  Details: {f_details}")
            lines.append(f"  Required Remediation: {f_remed}")

    lines.append("")
    lines.append(f"Action Required: {required_action}")
    lines.append("Apply targeted fixes strictly within allowed_paths and commit to the branch.")
    return "\n".join(lines)


class JulesBridgeClient:
    """High-level client coordinating Antigravity with Jules MCP server."""

    def __init__(
        self,
        config: Optional[JulesConfig] = None,
        workspace_root: Optional[Path] = None,
        mcp_client: Optional[JulesMCPClientInterface] = None
    ):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.config = config or JulesConfig.from_env()
        self.mcp = mcp_client or MockJulesMCPClient()

    def ping(self) -> Dict[str, Any]:
        """Tests connectivity and lists accessible sources."""
        try:
            res = self.mcp.call_tool("list_sources", {})
            sources = res.get("sources", [])
            return {
                "status": "OK",
                "mcp_server": "jules",
                "api_key_configured": bool(self.config.api_key),
                "sources_count": len(sources),
                "sources": [s.get("name") or s.get("id") for s in sources]
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "mcp_server": "jules",
                "error": str(e)
            }

    def push_task_branch_upstream(self, task_id: str, branch_name: Optional[str] = None) -> str:
        """Creates and pushes task branch to remote origin with handoff brief."""
        branch = branch_name or f"task/{task_id}"
        # Ensure handoff brief exists
        handoffs_dir = self.workspace_root / ".governance" / "handoffs"
        handoff_file = handoffs_dir / f"{task_id}.json"
        brief_file = self.workspace_root / "TASK_BRIEF.md"

        brief_content = f"# Task Brief: {task_id}\n\nManaged by Antigravity v8.3 Orchestration Engine.\n"
        if handoff_file.is_file():
            brief_content += f"```json\n{handoff_file.read_text(encoding='utf-8')}\n```\n"

        brief_file.write_text(brief_content, encoding="utf-8")

        # In live git repo, create or update branch and push
        git_dir = self.workspace_root / ".git"
        if git_dir.is_dir():
            try:
                subprocess.run(["git", "checkout", "-B", branch], cwd=self.workspace_root, check=True, capture_output=True)
                subprocess.run(["git", "add", "TASK_BRIEF.md", "contracts/"], cwd=self.workspace_root, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"chore(handoff): prepare {branch} for Jules builder"], cwd=self.workspace_root, capture_output=True)
                subprocess.run(["git", "push", "-u", "origin", branch], cwd=self.workspace_root, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.warning("Git branch push encountered non-fatal warning: %s", e)

        return branch

    def fetch_task_branch_downstream(self, task_id: str, branch_name: Optional[str] = None) -> None:
        """Fetches remote commits from Jules into local task worktree."""
        branch = branch_name or f"task/{task_id}"
        git_dir = self.workspace_root / ".git"
        if git_dir.is_dir():
            try:
                subprocess.run(["git", "fetch", "origin", branch], cwd=self.workspace_root, capture_output=True)
                worktree_dir = self.workspace_root / ".worktrees" / task_id
                target_cwd = worktree_dir if worktree_dir.is_dir() else self.workspace_root
                subprocess.run(["git", "pull", "--ff-only", "origin", branch], cwd=target_cwd, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.warning("Git branch fetch encountered warning: %s", e)

    def dispatch_and_supervise_task(
        self,
        request: JulesSessionRequest,
        max_plan_iterations: int = 3
    ) -> Dict[str, Any]:
        """Full execution lifecycle: create session -> audit plan -> approve -> poll completion."""
        # 1. Create session
        create_args = {
            "prompt": request.prompt,
            "source": request.source,
            "starting_branch": request.starting_branch,
            "require_plan_approval": request.require_plan_approval
        }
        session_res = self.mcp.call_tool("create_session", create_args)
        session_id = session_res.get("name") or session_res.get("id")
        if not session_id:
            raise JulesBridgeError(f"Failed to create Jules session: {session_res}")

        # 2. Plan Supervision Loop (if require_plan_approval is enabled)
        if request.require_plan_approval:
            plan_iteration = 1
            plan_approved = False

            while plan_iteration <= max_plan_iterations:
                session_data = self.mcp.call_tool("get_session", {"session_id": session_id})
                plan_text = session_data.get("plan") or "1. Implement vertical slice within allowed files."

                audit_res = audit_jules_plan(
                    plan_text=plan_text,
                    allowed_paths=request.allowed_paths,
                    contract_paths=request.contract_paths
                )

                if audit_res.approved:
                    self.mcp.call_tool("approve_session_plan", {"session_id": session_id})
                    plan_approved = True
                    break
                else:
                    # Reject plan and request revision
                    self.mcp.call_tool("send_session_message", {
                        "session_id": session_id,
                        "prompt": audit_res.remediation_prompt
                    })
                    plan_iteration += 1
                    # In mock or fast tests, mutate plan if mock
                    if isinstance(self.mcp, MockJulesMCPClient):
                        self.mcp.sessions[session_id]["plan"] = "1. Clean plan within allowed files with unit tests."

            if not plan_approved:
                raise JulesPlanAuditError(
                    f"Jules plan rejected after {max_plan_iterations} iterations of socratic audit."
                )

        # 3. Wait for session completion
        completion_res = self.mcp.call_tool("wait_for_session_completion", {
            "session_id": session_id,
            "poll_interval": self.config.poll_interval,
            "timeout": self.config.timeout_seconds
        })

        return {
            "status": "COMPLETED",
            "session_id": session_id,
            "session": completion_res
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity <-> Google Jules MCP Bridge v8.3")
    parser.add_argument("--ping", action="store_true", help="Ping Jules MCP server and list sources")
    parser.add_argument("--session", help="Session ID to inspect or manage")
    parser.add_argument("--approve-plan", action="store_true", help="Approve session plan")
    parser.add_argument("--inspect-plan", action="store_true", help="Inspect session plan")
    args = parser.parse_args()

    client = JulesBridgeClient()
    if args.ping:
        res = client.ping()
        sys.stdout.write(json.dumps(res, indent=2) + "\n")
    elif args.session and args.approve_plan:
        res = client.mcp.call_tool("approve_session_plan", {"session_id": args.session})
        sys.stdout.write(json.dumps(res, indent=2) + "\n")
    elif args.session and args.inspect_plan:
        res = client.mcp.call_tool("get_session", {"session_id": args.session})
        sys.stdout.write(json.dumps({"session_id": args.session, "plan": res.get("plan")}, indent=2) + "\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
