#!/usr/bin/env python3
"""Comprehensive test suite for Antigravity Anticipatory Archetype Expander."""

import os
import sys
import unittest
from pathlib import Path

# Setup repository root
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.anticipatory_expander import (
    AnticipatoryExpansionError,
    UnknownArchetypeError,
    AnticipatedRequirement,
    ArchetypeDefinition,
    ExpansionResult,
    AnticipatoryExpander,
)


class TestAnticipatoryExpander(unittest.TestCase):
    """Verifies archetypal detection, hidden requirement anticipation, and tool/skill binding."""

    def test_archetype_initialization_valid(self) -> None:
        arch = AnticipatoryExpander.ARCHETYPES["BILLING_CHECKOUT"]
        self.assertEqual(arch.name, "Billing & Checkout")
        self.assertTrue(len(arch.requirements) >= 2)
        self.assertTrue(all(r.vector for r in arch.requirements))

    def test_requirement_empty_code_raises(self) -> None:
        with self.assertRaises(AnticipatoryExpansionError):
            AnticipatedRequirement(
                code="",
                title="Title",
                description="Desc",
                vector="SECURITY",
                required_skills=("clean-code",),
                required_tools=("gov.py check-standards",),
                acceptance_criteria="Given When Then",
            )

    def test_detect_billing_archetype(self) -> None:
        text = "Zbuduj bramkę płatności Stripe dla koszyka zamówień i checkout"
        detected = AnticipatoryExpander.detect_archetypes(text)
        names = [a.name for a in detected]
        self.assertIn("Billing & Checkout", names)

    def test_detect_auth_archetype(self) -> None:
        text = "Moduł logowania użytkowników z tokenami JWT i sesjami"
        detected = AnticipatoryExpander.detect_archetypes(text)
        names = [a.name for a in detected]
        self.assertIn("Authentication & Identity", names)

    def test_detect_multiple_archetypes(self) -> None:
        text = "Stwórz dashboard analityczny w React z autoryzacją użytkowników i endpointem REST API"
        detected = AnticipatoryExpander.detect_archetypes(text)
        names = [a.name for a in detected]
        self.assertIn("Frontend UI & Dashboard", names)
        self.assertIn("Authentication & Identity", names)
        self.assertIn("API & Microservice Router", names)

    def test_expand_requirements_production_profile(self) -> None:
        text = "Implementacja płatności checkout dla klientów"
        res = AnticipatoryExpander.expand_requirements(text, profile="production")
        self.assertGreater(res.total_added, 0)
        codes = [r.code for r in res.added_requirements]
        self.assertIn("REQ-IDEMP-01", codes)
        self.assertIn("REQ-CURR-01", codes)

    def test_expand_requirements_lean_profile_skips(self) -> None:
        text = "Implementacja płatności checkout dla klientów"
        res = AnticipatoryExpander.expand_requirements(text, profile="lean")
        self.assertEqual(res.total_added, 0)
        self.assertEqual(len(res.added_requirements), 0)

    def test_expand_requirements_empty_raises(self) -> None:
        with self.assertRaises(AnticipatoryExpansionError):
            AnticipatoryExpander.expand_requirements("")

    def test_expand_requirements_deduplication(self) -> None:
        text = "Implementacja płatności checkout dla klientów"
        existing = {"REQ-IDEMP-01"}
        res = AnticipatoryExpander.expand_requirements(text, existing_codes=existing)
        codes = [r.code for r in res.added_requirements]
        self.assertNotIn("REQ-IDEMP-01", codes)
        self.assertIn("REQ-CURR-01", codes)

    def test_enrich_tasks_with_skills_and_tools_ui(self) -> None:
        raw_tasks = [
            {
                "id": "T-UI-01",
                "title": "Build responsive React checkout screen component",
                "allowed_paths": ["src/ui/Checkout.tsx"],
            }
        ]
        enriched = AnticipatoryExpander.enrich_tasks_with_skills_and_tools(raw_tasks)
        task = enriched[0]
        self.assertIn("better-interface", task["required_skills"])
        self.assertIn("a11y-audit", task["required_skills"])
        self.assertIn("clean-code", task["required_skills"])
        self.assertIn("gov.py check-standards", task["required_tools"])

    def test_enrich_tasks_with_skills_and_tools_security(self) -> None:
        raw_tasks = [
            {
                "id": "T-AUTH-01",
                "title": "Implement password verification and token auth",
                "allowed_paths": ["src/auth/service.py"],
            }
        ]
        enriched = AnticipatoryExpander.enrich_tasks_with_skills_and_tools(raw_tasks)
        task = enriched[0]
        self.assertIn("wp-security-guardrails", task["required_skills"])
        self.assertIn("adversarial-resilience", task["required_skills"])
        self.assertIn("clean-code", task["required_skills"])


if __name__ == "__main__":
    unittest.main()
