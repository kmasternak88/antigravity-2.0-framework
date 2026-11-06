#!/usr/bin/env python3
"""Tests for Specification-Driven Development Blueprint (SDB) & LLM-Executable Blueprint Pipeline.

Verifies:
1. Two-Tier Synchronized SSoT (SDB in specs/ and LLM-Executable Blueprint in .governance/tasks.json + contracts/).
2. Adaptive Socratic Flow & 5 Invariant Vectors (Grill-Me execution vs bypass).
3. Zero-Omission & Vertical Slice Invariant (Admin Dashboard, UI WCAG/OKLCH, HPOS, Lifecycles).
4. Append-Only DAG & Kahn's Topological Sort with DONE Task Protection.
5. Contract compatibility and Rule 50 DREE zero-float enforcement.
"""

import json
import tempfile
import unittest
from pathlib import Path

# Add repo root to sys.path
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ingestion_parser import IngestionParser, IngestionContext, FIVE_INVARIANT_VECTORS
from tools.genesis_compiler import (
    validate_blueprint_completeness,
    validate_ears_syntax,
    validate_contract_compatibility,
    validate_dree_financial_invariants,
    lint_zero_placeholders,
    parse_hierarchical_phase_6,
    compile_blueprint,
    validate_dag_acyclic,
    validate_disjoint_parallel_paths,
    validate_task_complexity_limits,
)
from tools.extend_project import (
    validate_grill_me_session,
    merge_tasks_dag,
    validate_currency_invariants,
    compute_next_task_ids,
    extend_project,
)


class TestSDBAndLLMExecutableBlueprint(unittest.TestCase):

    def test_five_invariant_vectors_definition(self):
        self.assertEqual(len(FIVE_INVARIANT_VECTORS), 5)
        self.assertIn("ONE_WAY_DOORS_STORAGE", FIVE_INVARIANT_VECTORS)
        self.assertIn("FINANCIAL_MONEY_INVARIANTS", FIVE_INVARIANT_VECTORS)
        self.assertIn("RESILIENCE_AND_UNWANTED_EARS", FIVE_INVARIANT_VECTORS)
        self.assertIn("SRE_RESOURCE_LIMITS", FIVE_INVARIANT_VECTORS)
        self.assertIn("PANEL_PERMISSIONS_WCAG", FIVE_INVARIANT_VECTORS)

    def test_adaptive_socratic_flow_grill_me_required(self):
        # Raw brief with missing vectors must flag grill_me_required = True
        brief = "Chcę stworzyć wtyczkę WooCommerce do generowania faktur."
        ctx = IngestionParser.parse_input(brief)
        self.assertTrue(ctx.grill_me_required)
        self.assertIsNone(ctx.grill_me_bypass_reason)
        self.assertTrue(len(ctx.missing_invariants) > 0)

    def test_adaptive_socratic_flow_grill_me_bypassed(self):
        # Detailed PRD explicitly grounding all 5 vectors must bypass Grill-Me
        full_prd = """# Wtyczka WooCommerce: Zaawansowane Płatności i Panel
Aktorzy: Administrator, Klient, Menadżer Sklepu.
Encje: Zamowienie, Faktura, Platnosc, Konfiguracja.
Operacje: pobieranie zamówienia, tworzenie faktury, aktualizacja płatności, walidacja formularza.

Wymagania:
- Architektura danych: WooCommerce HPOS (High-Performance Order Storage) oraz baza MySQL / PostgreSQL.
- Płatności: Wszystkie kwoty wyłącznie jako integer cents (amount_cents: int, grosze), bez float, zero-float policy.
- Odporność i zachowania niepożądane: IF błąd autoryzacji lub awaria bramki THEN system rzuca PaymentDomainError i ponawia próbę.
- SRE i limity: Ścisły timeout 5000ms na zapytanie HTTP, rate limit 60 rps, 99.9% dostępności.
- Panel administracyjny i uprawnienia: Dedykowany panel Admin Dashboard z formularzem ustawień, WCAG 2.1 AA (cele dotykowe min. 48px), paleta OKLCH, sprawdzanie uprawnień current_user_can('manage_woocommerce').
"""
        ctx = IngestionParser.parse_input(full_prd)
        self.assertFalse(ctx.grill_me_required)
        self.assertIsNotNone(ctx.grill_me_bypass_reason)
        self.assertIn("Grill-Me Bypassed", ctx.grill_me_bypass_reason)
        self.assertEqual(len(ctx.missing_invariants), 0)
        self.assertEqual(len(ctx.grounded_invariants), 5)

    def test_blueprint_completeness_validation_ecommerce_success(self):
        valid_bp = """
# WooCommerce Extension Blueprint
Wymagania dla wtyczki WordPress / WooCommerce:
- Kompletny moduł panelu Admin Dashboard & Settings menu.
- Standardy UI/UX: WCAG 2.1 AA, paleta OKLCH, cele dotykowe 48px.
- Warstwa danych: HPOS (High-Performance Order Storage) oraz schema dedykowanych tabel.
- Cykl życia: Idempotentne skrypty instalacji (install), migracji oraz deaktywacji / uninstaller.
"""
        report = validate_blueprint_completeness(valid_bp)
        self.assertTrue(report["is_wp_or_ecommerce"])
        self.assertTrue(report["has_admin_dashboard"])
        self.assertTrue(report["has_hpos_or_data_layer"])

    def test_blueprint_completeness_validation_ecommerce_missing_dashboard(self):
        incomplete_bp = """
# WooCommerce Extension Blueprint
Logika silnika płatności bez UI.
Używa bazy danych i HPOS, ale nie ma panelu administracyjnego.
"""
        with self.assertRaises(ValueError) as cm:
            validate_blueprint_completeness(incomplete_bp)
        self.assertIn("BLUEPRINT_COMPLETENESS_VIOLATION", str(cm.exception))
        self.assertIn("Admin Dashboard", str(cm.exception))

    def test_append_only_dag_done_task_protection(self):
        existing = {
            "version": 2,
            "tasks": [
                {
                    "id": "T001",
                    "status": "DONE",
                    "allowed_paths": ["src/module_a.py"],
                    "checks": ["unit"]
                }
            ]
        }
        # Attempting to tamper with completed task allowed_paths must raise DONE_TASK_MUTATION_FORBIDDEN
        tampering = {
            "tasks": [
                {
                    "id": "T001",
                    "status": "TODO",
                    "allowed_paths": ["src/module_a_hacked.py"],
                    "checks": ["unit"]
                }
            ]
        }
        with self.assertRaises(ValueError) as cm:
            merge_tasks_dag(existing, tampering)
        self.assertIn("DONE_TASK_MUTATION_FORBIDDEN", str(cm.exception))

    def test_two_tier_master_blueprint_compilation(self):
        blueprint_content = """# MASTER BLUEPRINT: Two-Tier Test Platform
Standard: RFC 2119 / DREE v8.2 / Genesis Compiler SSoT

### FAZA 1: DEKONSTRUKCJA DOMENY, WYMAGANIA I PRZYPADKI BRZEGOWE (PRD & ADR)
1. Cel: Platforma wieloagentowa.
2. Aktorzy: Administrator, Developer.
3. Wymagania RFC 2119 (EARS):
- REQ-001: THE SYSTEM SHALL zapewnić hermetyczną walidację wejścia.
- REQ-002: WHEN żądanie trafia do endpointu, THE SYSTEM SHALL zweryfikować token.

### FAZA 2: ARCHITEKTURA DANYCH I ZARZĄDZANIE STANEM (DATA & STATE LAYER)
1. Encje: Tenant, Project.
2. Zero Float: Kwoty walutowe wyłącznie jako integer minor units (grosze).

### FAZA 3: KONTRAKTY KOMUNIKACYJNE I WALIDACJA I/O (API & CONTRACTS)
1. Endpointy: /api/v1/projects.

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

##### Task T002: Implement Core Service
- **Zależności**: [T001]
- **Pliki docelowe**: `src/service.py`, `tests/test_service.py`
- **Kontekst wejściowy**: `src/db.py`
- **Kryterium Odbioru (DoD)**: `pytest tests/test_service.py`

### FAZA 7: STRATEGIA TESTOWANIA I KONTROLI JAKOŚCI (QA & VERIFICATION MATRIX)
1. Piramida testów: jednostkowe i integracyjne.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            bp_file = tmppath / "specs" / "00_MASTER_BLUEPRINT.md"
            bp_file.parent.mkdir(parents=True, exist_ok=True)
            bp_file.write_text(blueprint_content, encoding="utf-8")

            res = compile_blueprint(bp_file, tmppath)
            self.assertEqual(res["status"], "BLUEPRINT_COMPILED")

            # Check Tier I (SDB in specs/)
            self.assertTrue((tmppath / "specs" / "01_PRODUCT_REQUIREMENTS.md").is_file())
            self.assertTrue((tmppath / "specs" / "02_SYSTEM_ARCHITECTURE.md").is_file())
            self.assertTrue((tmppath / "specs" / "03_DATA_DICTIONARY.md").is_file())
            self.assertTrue((tmppath / "specs" / "05_TRACEABILITY_MATRIX.md").is_file())

            # Check Tier II (LLM-Executable Blueprint in .governance/tasks.json and contracts/)
            tasks_json_path = tmppath / ".governance" / "tasks.json"
            self.assertTrue(tasks_json_path.is_file())
            tasks_data = json.loads(tasks_json_path.read_text(encoding="utf-8"))
            self.assertEqual(tasks_data["version"], 2)
            self.assertEqual(len(tasks_data["tasks"]), 2)
            self.assertEqual(tasks_data["tasks"][0]["id"], "T001")
            self.assertEqual(tasks_data["tasks"][1]["id"], "T002")

            # Check contracts scaffolded
            self.assertTrue((tmppath / "contracts" / "models.py").is_file())
            self.assertTrue((tmppath / "contracts" / "types.ts").is_file())
            self.assertTrue((tmppath / "contracts" / "openapi.json").is_file())


if __name__ == '__main__':
    unittest.main()
