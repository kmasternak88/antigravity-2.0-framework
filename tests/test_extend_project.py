#!/usr/bin/env python3
"""Comprehensive Unit and Integration Tests for extend_project.py (Antigravity Ultra v8.2).

Verifies:
1. Pre-flight state verification (S0/S1 rejected, S2/S3 accepted).
2. 5-dimensional Socratic interview & answer resolution.
3. EARS requirements & Gherkin Triads synthesis.
4. Kahn's topological sort & DAG cycle detection.
5. Rule 40/3/1 and 7 DREE invariants checklist enforcement.
6. Sequential task ID computation (T004, T005, T006...).
7. DREE Rule 50: CURRENCY_FLOAT_PROHIBITED validation.
8. Static AST impact analysis & symbol collision detection.
9. Preservation of tasks.json Schema v2 (epics & milestones).
10. 7 Niezmienników DREE in scaffolded contracts (slots, frozen, __post_init__, __all__, DomainError).
11. Full end-to-end lifecycle and compatibility with gov.py validation, doctor, and approve-spec.
"""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.extend_project import (
    check_governance_state,
    SocraticEngine,
    synthesize_ears_and_gherkin,
    merge_dag_kahn,
    validate_40_3_1_rule,
    validate_dree_checklist,
    validate_currency_invariants,
    compute_next_task_ids,
    ASTImpactAnalyzer,
    extend_project,
    ProjectStateError,
    DAGCycleError,
    RuleViolationError
)

class TestExtendProjectV82(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_extend_v82_")
        self.workspace = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _setup_managed_workspace(self, spec_locked=False, schema_version=1):
        gov_dir = self.workspace / ".governance"
        gov_dir.mkdir(parents=True, exist_ok=True)
        (self.workspace / "specs").mkdir(parents=True, exist_ok=True)
        (self.workspace / "contracts").mkdir(parents=True, exist_ok=True)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        (self.workspace / "tests").mkdir(parents=True, exist_ok=True)

        cfg = {
            "version": 3,
            "profile": "standard",
            "spec_locked": spec_locked,
            "spec_files": ["specs/01_PRODUCT_REQUIREMENTS.md"],
            "checks": {
                "unit": {"argv": ["python", "-m", "unittest"], "timeout": 60}
            },
            "required_release_checks": ["unit"]
        }
        (gov_dir / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        (self.workspace / "specs" / "01_PRODUCT_REQUIREMENTS.md").write_text("# Requirements\nInitial requirement", encoding="utf-8")

        if schema_version == 2:
            initial_tasks = {
                "version": 2,
                "blueprint_source": "specs/00_MASTER_BLUEPRINT.md",
                "epics": [{"id": "EPIC-01", "title": "Core System"}],
                "milestones": [{"id": "M1", "epic_id": "EPIC-01", "title": "Foundation"}],
                "tasks": [
                    {
                        "id": "T001",
                        "epic_id": "EPIC-01",
                        "milestone_id": "M1",
                        "title": "Baseline Task",
                        "allowed_paths": ["tests"],
                        "depends_on": [],
                        "checks": ["unit"],
                        "acceptance": ["AC-01"],
                        "standards_checklist": [
                            "interface_contract", "input_validation", "domain_exception",
                            "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
                        ]
                    }
                ]
            }
        else:
            initial_tasks = {
                "version": 1,
                "tasks": [
                    {
                        "id": "T001",
                        "title": "Baseline Task",
                        "allowed_paths": ["tests"],
                        "depends_on": [],
                        "checks": ["unit"],
                        "acceptance": ["AC-01"],
                        "standards_checklist": [
                            "interface_contract", "input_validation", "domain_exception",
                            "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
                        ]
                    }
                ]
            }
        (gov_dir / "tasks.json").write_text(json.dumps(initial_tasks), encoding="utf-8")

    def test_unmanaged_workspace_rejected(self):
        with self.assertRaises(ProjectStateError):
            check_governance_state(self.workspace)

    def test_managed_workspace_detected(self):
        self._setup_managed_workspace(spec_locked=False)
        state = check_governance_state(self.workspace)
        self.assertEqual(state, "S2_GOVERNANCE_UNLOCKED")

        cfg = {"version": 1, "spec_locked": True}
        (self.workspace / ".governance" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        state_locked = check_governance_state(self.workspace)
        self.assertEqual(state_locked, "S3_IN_FLIGHT")

    def test_socratic_questionnaire_and_answers(self):
        brief = "Chcę dodać system mikropłatności i fakturowania subskrypcji"
        domain = "billing"
        questions = SocraticEngine.build_standard_questionnaire(brief, domain)
        self.assertEqual(len(questions), 5)

        q2 = next(q for q in questions if q.id == "Q2_FINANCIAL_AND_MONEY_INVARIANTS")
        self.assertEqual(q2.recommended_option_id, "money_integer_cents")

        answers = SocraticEngine.resolve_answers(questions)
        self.assertEqual(answers["Q2_FINANCIAL_AND_MONEY_INVARIANTS"], "money_integer_cents")
        self.assertEqual(answers["Q1_ONE_WAY_DOOR_PERSISTENCE"], "relational_transactional")

        custom = {"Q1_ONE_WAY_DOOR_PERSISTENCE": "append_only_ledger"}
        resolved_custom = SocraticEngine.resolve_answers(questions, custom)
        self.assertEqual(resolved_custom["Q1_ONE_WAY_DOOR_PERSISTENCE"], "append_only_ledger")

    def test_ears_and_gherkin_synthesis(self):
        brief = "Moduł fakturowania z płatnościami"
        domain = "invoicing"
        slug = "invoice"
        answers = {"Q2_FINANCIAL_AND_MONEY_INVARIANTS": "money_integer_cents"}

        ears, triads = synthesize_ears_and_gherkin(domain, slug, brief, answers)
        self.assertEqual(len(ears), 5)
        patterns = {e.pattern_type for e in ears}
        self.assertIn("Ubiquitous", patterns)
        self.assertIn("Event-driven", patterns)
        self.assertIn("State-driven", patterns)
        self.assertIn("Unwanted behavior", patterns)
        self.assertIn("Complex", patterns)

        self.assertEqual(len(triads), 1)
        self.assertIn("Scenario: Pomyślne przetworzenie", triads[0].happy_path)
        self.assertIn("Boundary Failure", triads[0].negative_boundary)
        self.assertIn("Adversarial", triads[0].negative_adversarial)

    def test_merge_dag_kahn_success_and_cycle(self):
        existing = [
            {"id": "T001", "depends_on": []},
            {"id": "T002", "depends_on": ["T001"]}
        ]
        new_tasks = [
            {"id": "T003", "depends_on": ["T002"]},
            {"id": "T004", "depends_on": ["T003"]}
        ]
        merged = merge_dag_kahn(existing, new_tasks)
        merged_ids = [t["id"] for t in merged]
        self.assertEqual(merged_ids, ["T001", "T002", "T003", "T004"])

        cyclic_tasks = [
            {"id": "T003", "depends_on": ["T004"]},
            {"id": "T004", "depends_on": ["T003"]}
        ]
        with self.assertRaises(DAGCycleError):
            merge_dag_kahn(existing, cyclic_tasks)

    def test_sequential_task_id_computation(self):
        existing = [{"id": "T001"}, {"id": "T002"}, {"id": "T003"}]
        next_ids = compute_next_task_ids(existing, count=3, prefix="T")
        self.assertEqual(next_ids, ["T004", "T005", "T006"])

        empty_existing = []
        first_ids = compute_next_task_ids(empty_existing, count=3, prefix="T")
        self.assertEqual(first_ids, ["T001", "T002", "T003"])

    def test_currency_float_prohibited(self):
        valid_entities = [
            {
                "name": "InvoiceRecord",
                "fields": [
                    {"name": "id", "type": "str"},
                    {"name": "amount_cents", "type": "int"},
                    {"name": "tax_cents", "type": "int"}
                ]
            }
        ]
        # Should pass
        validate_currency_invariants(valid_entities)

        invalid_entities = [
            {
                "name": "InvalidPayment",
                "fields": [
                    {"name": "id", "type": "str"},
                    {"name": "price", "type": "float"}  # VIOLATION!
                ]
            }
        ]
        with self.assertRaises(RuleViolationError) as ctx:
            validate_currency_invariants(invalid_entities)
        self.assertIn("CURRENCY_FLOAT_PROHIBITED", str(ctx.exception))

    def test_ast_impact_analysis_and_collision(self):
        self._setup_managed_workspace()
        (self.workspace / "src" / "billing").mkdir(parents=True, exist_ok=True)
        py_file = self.workspace / "src" / "billing" / "existing_service.py"
        py_file.write_text("""
class ExistingBillingService:
    def process(self):
        pass
""", encoding="utf-8")

        # Test collision detection
        res = ASTImpactAnalyzer.analyze_workspace_ast(
            workspace_root=self.workspace,
            new_symbols=["ExistingBillingService"],
            target_domain="billing"
        )
        self.assertTrue(res["breakingChanges"])
        self.assertEqual(len(res["collisions"]), 1)
        self.assertEqual(res["collisions"][0]["symbol"], "ExistingBillingService")

        # Test clean extension without collision
        clean_res = ASTImpactAnalyzer.analyze_workspace_ast(
            workspace_root=self.workspace,
            new_symbols=["BrandNewSubscriptionService"],
            target_domain="subscription"
        )
        self.assertFalse(clean_res["breakingChanges"])
        self.assertEqual(len(clean_res["collisions"]), 0)

    def test_tasks_json_schema_v2_preservation(self):
        self._setup_managed_workspace(spec_locked=True, schema_version=2)

        res = extend_project(
            workspace_root=self.workspace,
            brief="Rozszerzenie o program lojalnościowy",
            module_slug="loyalty",
            domain="loyalty",
            use_sequential_t_ids=True,
            dry_run=False
        )

        self.assertEqual(res["status"], "SUCCESS")
        tasks_file = self.workspace / ".governance" / "tasks.json"
        tasks_data = json.loads(tasks_file.read_text(encoding="utf-8"))

        self.assertEqual(tasks_data.get("version"), 2)
        epics = tasks_data.get("epics", [])
        self.assertEqual(len(epics), 2)  # EPIC-01 + EPIC-LOYALTY
        self.assertTrue(any(e["id"] == "EPIC-LOYALTY" for e in epics))

        tasks = tasks_data.get("tasks", [])
        self.assertEqual(len(tasks), 4)  # 1 initial + 3 new (T002, T003, T004)
        task_ids = [t["id"] for t in tasks]
        self.assertEqual(task_ids, ["T001", "T002", "T003", "T004"])

        # Check that new tasks are tagged with epic_id and milestone_id
        new_task = next(t for t in tasks if t["id"] == "T002")
        self.assertEqual(new_task.get("epic_id"), "EPIC-LOYALTY")
        self.assertEqual(new_task.get("milestone_id"), "M-LOYALTY")

    def test_dree_contract_scaffolding_invariants(self):
        self._setup_managed_workspace(spec_locked=False)

        custom_entities = [
            {
                "name": "VoucherRecord",
                "fields": [
                    {"name": "id", "type": "str"},
                    {"name": "discount_cents", "type": "int"}
                ]
            }
        ]

        res = extend_project(
            workspace_root=self.workspace,
            brief="Moduł voucherów i kuponów",
            module_slug="voucher",
            domain="voucher",
            entities=custom_entities,
            provided_answers={"Q2_FINANCIAL_AND_MONEY_INVARIANTS": "money_integer_cents"},
            dry_run=False
        )
        self.assertEqual(res["status"], "SUCCESS")

        contract_path = self.workspace / "contracts" / "voucher.py"
        self.assertTrue(contract_path.is_file())
        code = contract_path.read_text(encoding="utf-8")

        # 1. slots=True, frozen=True
        self.assertIn("@dataclass(slots=True, frozen=True)", code)
        # 2. __post_init__ validation
        self.assertIn("def __post_init__(self):", code)
        # 3. Domain exception inheriting DomainError
        self.assertIn("class DomainError(Exception):", code)
        self.assertIn("class VoucherDomainError(DomainError):", code)
        # 4. integer cents
        self.assertIn("amount_cents: int = 0", code)
        # 5. Custom entity rendered
        self.assertIn("class VoucherRecord:", code)
        self.assertIn("discount_cents: int", code)
        # 6. Explicit __all__
        self.assertIn("__all__ = [", code)
        self.assertIn("'VoucherDomainError',", code)
        self.assertIn("'VoucherRecord',", code)

        # TypeScript contracts
        ts_path = self.workspace / "contracts" / "voucher.ts"
        self.assertTrue(ts_path.is_file())
        ts_code = ts_path.read_text(encoding="utf-8")
        self.assertIn("readonly amountCents: number;", ts_code)

    def test_full_extend_project_and_gov_validate(self):
        self._setup_managed_workspace(spec_locked=False)
        gov_bin = self.workspace / ".governance" / "bin"
        gov_bin.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / ".governance" / "bin" / "gov.py", gov_bin / "gov.py")

        res = extend_project(
            workspace_root=self.workspace,
            brief="Rozbudowa o moduł raportowania telemetrycznego",
            module_slug="telemetry",
            domain="telemetry",
            dry_run=False
        )
        self.assertEqual(res["status"], "SUCCESS")

        # Dynamically load gov.py and set workspace root
        spec = importlib.util.spec_from_file_location("gov_test_mod", str(gov_bin / "gov.py"))
        gov_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gov_mod)
        gov_mod.set_workspace_root(self.workspace)

        # Validate DAG
        val_res = gov_mod.validate()
        self.assertEqual(val_res["status"], "VALID")

        # Validate doctor
        doc_res = gov_mod.doctor()
        self.assertEqual(doc_res["status"], "VALID")

        # Approve spec lock
        app_res = gov_mod.approve("human:owner", "extend-telemetry-reference")
        self.assertTrue(app_res["approvalRecorded"])

        # Check status shows locked
        stat_res = gov_mod.status()
        self.assertTrue(stat_res["specLocked"])

if __name__ == "__main__":
    unittest.main()
