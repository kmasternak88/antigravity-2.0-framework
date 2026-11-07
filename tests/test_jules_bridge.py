#!/usr/bin/env python3
"""Comprehensive Unit and Governance Tests for Jules MCP Bridge & Orchestration."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.jules_bridge import (
    JulesBridgeError,
    JulesPlanAuditError,
    JulesConfig,
    JulesPlanAuditResult,
    JulesSessionRequest,
    MockJulesMCPClient,
    JulesBridgeClient,
    audit_jules_plan,
    format_feedback_packet_to_prompt
)


class TestJulesMCPBridge(unittest.TestCase):
    """Test suite for Jules MCP server communication, plan auditing, and feedback mapping."""

    def test_config_from_env(self):
        env = {
            "JULES_API_KEY": "secret_key_12345",
            "JULES_DEFAULT_SOURCE": "sources/github/owner/repo"
        }
        cfg = JulesConfig.from_env(env)
        self.assertEqual(cfg.api_key, "secret_key_12345")
        self.assertEqual(cfg.default_source, "sources/github/owner/repo")

    def test_mock_mcp_client_tools(self):
        client = MockJulesMCPClient()
        # list_sources
        sources = client.call_tool("list_sources", {})
        self.assertIn("sources", sources)
        self.assertTrue(len(sources["sources"]) >= 1)

        # create_session
        sess = client.call_tool("create_session", {
            "prompt": "Build vertical slice",
            "source": "sources/github/owner/repo",
            "require_plan_approval": True
        })
        sess_id = sess["name"]
        self.assertEqual(sess["state"], "AWAITING_PLAN_APPROVAL")

        # get_session
        fetched = client.call_tool("get_session", {"session_id": sess_id})
        self.assertEqual(fetched["id"], sess_id)

        # approve_session_plan
        app_res = client.call_tool("approve_session_plan", {"session_id": sess_id})
        self.assertEqual(app_res["status"], "SUCCESS")
        self.assertEqual(client.sessions[sess_id]["state"], "IN_PROGRESS")

        # send_session_message
        msg_res = client.call_tool("send_session_message", {
            "session_id": sess_id,
            "prompt": "Fix test assertions"
        })
        self.assertEqual(msg_res["status"], "SENT")
        self.assertEqual(len(client.messages_sent), 1)

        # wait_for_session_completion
        comp_res = client.call_tool("wait_for_session_completion", {"session_id": sess_id})
        self.assertEqual(comp_res["state"], "COMPLETED")

    def test_audit_jules_plan_approved(self):
        plan = (
            "1. Implement UserAuthService in src/auth_service.py according to contract.\n"
            "2. Add unit tests with boundary assertions in tests/test_auth.py.\n"
            "3. Verify all assertions pass."
        )
        allowed = ["src/auth_service.py", "tests/test_auth.py"]
        res = audit_jules_plan(plan, allowed)
        self.assertTrue(res.approved)
        self.assertEqual(res.status, "APPROVED")
        self.assertEqual(len(res.violations), 0)

    def test_audit_jules_plan_rejects_unauthorized_paths(self):
        plan = (
            "1. Modify backend core in src/unauthorized_core.py.\n"
            "2. Add unit tests in tests/test_auth.py."
        )
        allowed = ["src/auth_service.py", "tests/test_auth.py"]
        res = audit_jules_plan(plan, allowed)
        self.assertFalse(res.approved)
        self.assertEqual(res.status, "REJECTED_PLAN")
        self.assertTrue(any("PATH_CONFINEMENT_VIOLATION" in v for v in res.violations))
        self.assertIn("src/unauthorized_core.py", res.remediation_prompt)

    def test_audit_jules_plan_rejects_contract_tampering(self):
        plan = (
            "1. Update interface definition in contracts/user.contract.py.\n"
            "2. Implement tests in tests/test_auth.py."
        )
        allowed = ["contracts/user.contract.py", "tests/test_auth.py"]
        res = audit_jules_plan(plan, allowed, contract_paths=["contracts/user.contract.py"])
        self.assertFalse(res.approved)
        self.assertEqual(res.status, "REJECTED_PLAN")
        self.assertTrue(any("CONTRACT_TAMPERING_FORBIDDEN" in v for v in res.violations))

    def test_audit_jules_plan_rejects_missing_tests(self):
        plan = "1. Write user service code without any automated verification."
        allowed = ["src/service.py"]
        res = audit_jules_plan(plan, allowed)
        self.assertFalse(res.approved)
        self.assertTrue(any("DREE_DUAL_TEST_OMISSION" in v for v in res.violations))

    def test_format_feedback_packet_to_prompt(self):
        packet = {
            "task_id": "T004",
            "iteration": 2,
            "max_iterations": 3,
            "status": "REJECTED_NEEDS_REVISION",
            "findings": [
                {
                    "type": "DREE_SRP_VIOLATION",
                    "file": "src/auth.py",
                    "details": "Function verify_login exceeds 40 lines.",
                    "actionable_remediation": "Extract password hashing to separate helper.",
                    "line_range": "20-65"
                }
            ],
            "required_action": "Decompose function to comply with SRP <= 40 lines."
        }
        prompt = format_feedback_packet_to_prompt(packet)
        self.assertIn("ITERATION 2/3", prompt)
        self.assertIn("DREE_SRP_VIOLATION", prompt)
        self.assertIn("src/auth.py (lines: 20-65)", prompt)
        self.assertIn("Extract password hashing to separate helper", prompt)
        self.assertIn("Decompose function to comply with SRP <= 40 lines", prompt)

    def test_jules_bridge_client_ping(self):
        client = JulesBridgeClient()
        ping_res = client.ping()
        self.assertEqual(ping_res["status"], "OK")
        self.assertEqual(ping_res["mcp_server"], "jules")
        self.assertEqual(ping_res["sources_count"], 1)

    def test_jules_bridge_dispatch_and_supervise(self):
        client = JulesBridgeClient()
        req = JulesSessionRequest(
            task_id="T001",
            prompt="Implement order service",
            source="sources/github/owner/repo",
            starting_branch="task/T001",
            require_plan_approval=True,
            allowed_paths=["src/order.py", "tests/test_order.py"]
        )
        res = client.dispatch_and_supervise_task(req)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("sessions/", res["session_id"])
        self.assertIn(res["session_id"], client.mcp.plans_approved)


if __name__ == "__main__":
    unittest.main()
