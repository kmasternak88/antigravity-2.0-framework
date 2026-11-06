#!/usr/bin/env python3
"""Unit tests for Genesis Pipeline v8.1 (IngestionParser, Hierarchical DAG, Disjoint Write-Sets)."""
import json, tempfile, unittest
from pathlib import Path

# Add repo root to sys.path
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ingestion_parser import IngestionParser, IngestionContext
from tools.genesis_compiler import (
    lint_zero_placeholders,
    parse_hierarchical_phase_6,
    validate_dag_acyclic,
    validate_disjoint_parallel_paths,
    validate_task_complexity_limits,
    compile_blueprint,
    scaffold_baseline_contracts
)

SAMPLE_RAW_BRIEF = "Chcę stworzyć serwis subskrypcyjny z płatnościami Stripe, fakturami PDF i powiadomieniami email."

SAMPLE_HIERARCHICAL_BLUEPRINT = """# MASTER BLUEPRINT: Test Platform

### FAZA 1: DEKONSTRUKCJA DOMENY, WYMAGANIA I PRZYPADKI BRZEGOWE (PRD & ADR)
1. Cel: Test platform.
2. Aktorzy: User, Admin.
3. Wymagania RFC 2119:
- REQ-001: System MUST zapewniać spójność transakcyjną.

### FAZA 2: ARCHITEKTURA DANYCH I ZARZĄDZANIE STANEM (DATA & STATE LAYER)
1. Encje: Account, Invoice.
2. Zero Float: Kwoty w integer minor.

### FAZA 3: KONTRAKTY KOMUNIKACYJNE I WALIDACJA I/O (API & CONTRACTS)
1. Endpointy: /api/v1/invoices.

### FAZA 4: BEZPIECZEŃSTWO, ODPORNOŚĆ I OBSERWOWALNOŚĆ (SECURITY & SRE)
1. Autoryzacja: Bearer JWT.

### FAZA 5: STOS TECHNOLOGICZNY, KONFIGURACJA I DRZEWO PLIKÓW (TOPOLOGY)
1. Stos: Python 3.12.

### FAZA 6: ATOMOWY PLAN IMPLEMENTACJI (TOPOLOGICAL EXECUTION DAG)
### Epic EPIC-01: Foundation
#### Milestone M1: Core Schema
##### Task T001: Setup database schema
- **Zależności**: []
- **Pliki docelowe**: `src/db.py`, `tests/test_db.py`
- **Kontekst wejściowy**: `specs/02_DATA_AND_STATE.md`
- **Kryterium Odbioru (DoD)**: `pytest tests/test_db.py`

##### Task T002: Implement User Entity
- **Zależności**: [T001]
- **Pliki docelowe**: `src/user.py`, `tests/test_user.py`
- **Kontekst wejściowy**: `src/db.py`
- **Kryterium Odbioru (DoD)**: `pytest tests/test_user.py`

### Epic EPIC-02: Business Services
#### Milestone M2: Invoicing Service
##### Task T003: Implement Invoice Service
- **Zależności**: [T002]
- **Pliki docelowe**: `src/invoice.py`, `tests/test_invoice.py`
- **Kontekst wejściowy**: `src/user.py`
- **Kryterium Odbioru (DoD)**: `pytest tests/test_invoice.py`

### FAZA 7: STRATEGIA TESTOWANIA I KONTROLI JAKOŚCI (QA & VERIFICATION MATRIX)
1. Testy jednostkowe i integracyjne.
"""

class TestGenesisPipelineV81(unittest.TestCase):
    def test_ingestion_parser_raw_brief(self):
        ctx = IngestionParser.parse_input(SAMPLE_RAW_BRIEF)
        self.assertEqual(ctx.classification, "RAW_SEED")
        self.assertGreater(ctx.ims_score, 0.0)
        self.assertEqual(ctx.archetype, "fintech_transaction_ledger")
        self.assertGreater(len(ctx.autonomous_adrs), 0)

    def test_zero_placeholder_linter(self):
        valid = "Wymaganie: System MUST weryfikować nagłówek X-Token."
        self.assertEqual(len(lint_zero_placeholders(valid)), 0)

        invalid = "Zabezpiecz odpowiednio endpoint, reszta do ustalenia // TODO"
        violations = lint_zero_placeholders(invalid)
        self.assertGreater(len(violations), 0)

    def test_hierarchical_phase_6_parsing(self):
        epics, milestones, tasks = parse_hierarchical_phase_6(SAMPLE_HIERARCHICAL_BLUEPRINT)
        self.assertEqual(len(epics), 2)
        self.assertEqual(len(milestones), 2)
        self.assertEqual(len(tasks), 3)

        self.assertEqual(tasks[0]["id"], "T001")
        self.assertEqual(tasks[0]["epic_id"], "EPIC-01")
        self.assertEqual(tasks[0]["milestone_id"], "M1")
        self.assertEqual(tasks[2]["epic_id"], "EPIC-02")
        self.assertEqual(tasks[2]["milestone_id"], "M2")

    def test_dag_acyclic_and_topological_sort(self):
        _, _, tasks = parse_hierarchical_phase_6(SAMPLE_HIERARCHICAL_BLUEPRINT)
        # Should pass without exception
        validate_dag_acyclic(tasks)

        # Introduce circular dependency
        tasks[0]["depends_on"] = ["T003"]
        with self.assertRaises(ValueError):
            validate_dag_acyclic(tasks)

    def test_disjoint_parallel_paths_validation(self):
        # T001 -> T002 and T001 -> T003 (T002 and T003 are parallel)
        tasks = [
            {"id": "T001", "depends_on": [], "allowed_paths": ["src/base.py"]},
            {"id": "T002", "depends_on": ["T001"], "allowed_paths": ["src/service_a.py"]},
            {"id": "T003", "depends_on": ["T001"], "allowed_paths": ["src/service_b.py"]},
        ]
        # Disjoint: should pass
        validate_disjoint_parallel_paths(tasks)

        # Collision: T002 and T003 share src/shared.py
        tasks[1]["allowed_paths"].append("src/shared.py")
        tasks[2]["allowed_paths"].append("src/shared.py")
        with self.assertRaises(ValueError) as cm:
            validate_disjoint_parallel_paths(tasks)
        self.assertIn("DAG_CONCURRENT_COLLISION", str(cm.exception))

    def test_compile_blueprint_full_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            bp_path = ws / "specs" / "00_MASTER_BLUEPRINT.md"
            bp_path.parent.mkdir(parents=True, exist_ok=True)
            bp_path.write_text(SAMPLE_HIERARCHICAL_BLUEPRINT, encoding="utf-8")

            res = compile_blueprint(bp_path, ws)
            self.assertEqual(res["status"], "BLUEPRINT_COMPILED")
            self.assertEqual(res["hierarchy"]["tasksExtracted"], 3)

            # Check generated files
            self.assertTrue((ws / "specs" / "01_PRD_AND_ADR.md").is_file())
            self.assertTrue((ws / "specs" / "01_PRODUCT_REQUIREMENTS.md").is_file())
            self.assertTrue((ws / "specs" / "02_SYSTEM_ARCHITECTURE.md").is_file())
            self.assertTrue((ws / "specs" / "03_DATA_DICTIONARY.md").is_file())
            self.assertTrue((ws / "specs" / "05_TRACEABILITY_MATRIX.md").is_file())
            self.assertTrue((ws / "contracts" / "models.py").is_file())
            self.assertTrue((ws / "contracts" / "types.ts").is_file())
            self.assertTrue((ws / "contracts" / "openapi.json").is_file())
            self.assertTrue((ws / ".governance" / "tasks.json").is_file())

            # Verify tasks.json v2 structure
            tasks_data = json.loads((ws / ".governance" / "tasks.json").read_text(encoding="utf-8"))
            self.assertEqual(tasks_data.get("version"), 2)
            self.assertEqual(len(tasks_data.get("epics", [])), 2)
            self.assertEqual(len(tasks_data.get("milestones", [])), 2)
            self.assertEqual(len(tasks_data.get("tasks", [])), 3)

if __name__ == "__main__":
    unittest.main()
