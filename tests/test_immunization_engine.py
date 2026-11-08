#!/usr/bin/env python3
"""Comprehensive test suite for Antigravity Cross-Task Error Immunization Engine."""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Setup repository root
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.immunization_engine import (
    ImmunizationError,
    InvalidFeedbackPacketError,
    ImmunizationRule,
    ImmunizationState,
    ImmunizationResult,
    ImmunizationEngine,
)


class TestImmunizationEngine(unittest.TestCase):
    """Verifies rule distillation, state persistence, filtering, and prompt injection."""

    def setUp(self) -> None:
        self.sample_packet = {
            "taskId": "TASK-001",
            "cycle": 1,
            "status": "NEEDS_REVISION",
            "findings": [
                {
                    "category": "MOCK_TAUTOLOGY",
                    "file": "src/billing/billing_service.py",
                    "line": 42,
                    "message": "Test asserts against mock return value rather than state change",
                    "remediation": "Assert on state mutation in database fixture"
                },
                {
                    "category": "SRP_VIOLATION",
                    "file": "src/billing/payment_processor.py",
                    "line": 15,
                    "message": "Method process_payment has 55 lines (exceeds limit of 40)",
                    "remediation": "Split into execute_gateway_call and persist_transaction"
                },
                {
                    "category": "TYPE_ERROR",
                    "file": "src/billing/models.py",
                    "line": 8,
                    "message": "Float used for currency amount",
                    "remediation": "Use integer cents"
                }
            ]
        }

    def test_rule_initialization_valid(self) -> None:
        rule = ImmunizationRule(
            rule_id="IMM-TEST01",
            target_module="src/billing/service.py",
            error_category="SRP_VIOLATION",
            negative_constraint="Nigdy nie przekraczaj 40 linii",
            recommended_fix="Dziel na podfunkcje",
            timestamp=time.time(),
        )
        self.assertEqual(rule.rule_id, "IMM-TEST01")
        self.assertFalse(rule.is_expired())

    def test_rule_empty_id_raises(self) -> None:
        with self.assertRaises(InvalidFeedbackPacketError):
            ImmunizationRule(
                rule_id="",
                target_module="service.py",
                error_category="SRP_VIOLATION",
                negative_constraint="Nigdy",
                recommended_fix="Popraw",
                timestamp=time.time(),
            )

    def test_rule_invalid_ttl_raises(self) -> None:
        with self.assertRaises(InvalidFeedbackPacketError):
            ImmunizationRule(
                rule_id="IMM-01",
                target_module="service.py",
                error_category="SRP_VIOLATION",
                negative_constraint="Nigdy",
                recommended_fix="Popraw",
                timestamp=time.time(),
                ttl_seconds=-10,
            )

    def test_rule_is_expired(self) -> None:
        old_time = time.time() - 100000
        rule = ImmunizationRule(
            rule_id="IMM-EXPIRED",
            target_module="service.py",
            error_category="SRP",
            negative_constraint="Rule",
            recommended_fix="Fix",
            timestamp=old_time,
            ttl_seconds=3600,
        )
        self.assertTrue(rule.is_expired())

    def test_distill_from_packet(self) -> None:
        rules = ImmunizationEngine.distill_from_packet(self.sample_packet, project_id="test_proj")
        self.assertEqual(len(rules), 3)
        categories = {r.error_category for r in rules}
        self.assertIn("MOCK_TAUTOLOGY", categories)
        self.assertIn("SRP_VIOLATION", categories)
        self.assertIn("TYPE_ERROR", categories)

    def test_distill_invalid_packet_raises(self) -> None:
        with self.assertRaises(InvalidFeedbackPacketError):
            ImmunizationEngine.distill_from_packet({"findings": "not_a_list"})

    def test_save_and_load_rules_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "immunization.json"
            rules = ImmunizationEngine.distill_from_packet(self.sample_packet)
            res = ImmunizationEngine.save_rules(rules, state_file, project_id="demo_p")
            self.assertEqual(res.status, "SAVED")
            self.assertEqual(res.rules_count, 3)
            self.assertTrue(state_file.is_file())

            loaded = ImmunizationEngine.load_rules(state_file)
            self.assertEqual(len(loaded), 3)
            self.assertEqual(loaded[0].rule_id, rules[0].rule_id)

    def test_filter_rules_for_target(self) -> None:
        rules = ImmunizationEngine.distill_from_packet(self.sample_packet)
        filtered = ImmunizationEngine.filter_rules_for_target(rules, ["src/billing/billing_service.py"])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].error_category, "MOCK_TAUTOLOGY")

    def test_format_prompt_injection(self) -> None:
        rules = ImmunizationEngine.distill_from_packet(self.sample_packet)
        block = ImmunizationEngine.format_prompt_injection(rules)
        self.assertIn("<cross_task_immunization_guardrails>", block)
        self.assertIn("</cross_task_immunization_guardrails>", block)
        self.assertIn("<negative_constraint>", block)
        self.assertIn("<recommended_fix>", block)

    def test_format_prompt_injection_empty(self) -> None:
        block = ImmunizationEngine.format_prompt_injection([])
        self.assertEqual(block, "")


if __name__ == "__main__":
    unittest.main()
