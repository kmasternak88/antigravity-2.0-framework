#!/usr/bin/env python3
"""Comprehensive test suite for Antigravity Zero-Guess Contract Generator."""

import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Setup repository root
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.contract_generator import (
    ContractGenerationError,
    SchemaParseError,
    FieldDefinition,
    EntityDefinition,
    GeneratedContract,
    ContractGenerationResult,
    ContractGenerator,
)


class TestContractGenerator(unittest.TestCase):
    """Verifies contract extraction, code generation, and boundary validation."""

    def setUp(self) -> None:
        self.sample_prd = """
# Sample PRD
## 6.2. Specyfikacja Implementacji Zdarzeń Analitycznych
| ID Zdarzenia | Nazwa Techniczna Zdarzenia (`event_name`) | Powiązane Wymaganie | Wyzwalacz | Struktura Ładunku (JSON Properties / Payload Schema) | Punkt Emisji |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`EVT-001`** | `critical_anomaly_displayed` | `REQ-001` | Trigger | `{"anomaly_id": "UUID", "tenant_id": "UUID", "estimated_loss_eur": "Float", "delivery_latency_ms": "Integer", "filter_preset": "String"}` | Frontend Web |
| **`EVT-002`** | `offline_inspection_synced` | `REQ-002` | Trigger | `{"inspection_id": "UUID", "device_model": "String", "photos_count": "Integer"}` | Mobile Client |
"""

    def test_field_definition_valid(self) -> None:
        field = FieldDefinition(name="tenant_id", field_type="str")
        self.assertEqual(field.name, "tenant_id")
        self.assertEqual(field.field_type, "str")

    def test_field_definition_empty_name_raises(self) -> None:
        with self.assertRaises(SchemaParseError):
            FieldDefinition(name="", field_type="str")

    def test_field_definition_empty_type_raises(self) -> None:
        with self.assertRaises(SchemaParseError):
            FieldDefinition(name="field_a", field_type="")

    def test_entity_definition_empty_fields_raises(self) -> None:
        with self.assertRaises(SchemaParseError):
            EntityDefinition(name="EmptyEntity", fields=())

    def test_parse_payload_schema_json(self) -> None:
        raw = '{"id": "UUID", "cost": "Float", "active": "Boolean"}'
        fields = ContractGenerator.parse_payload_schema(raw)
        self.assertEqual(len(fields), 3)
        names = [f.name for f in fields]
        self.assertIn("id", names)
        self.assertIn("cost", names)
        self.assertIn("active", names)

    def test_parse_payload_schema_loose(self) -> None:
        raw = '{user_id: UUID, role: Enum(admin|user)}'
        fields = ContractGenerator.parse_payload_schema(raw)
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0].name, "user_id")

    def test_extract_entities_from_prd(self) -> None:
        entities = ContractGenerator.extract_entities_from_prd(self.sample_prd)
        self.assertEqual(len(entities), 2)
        names = [e.name for e in entities]
        self.assertIn("CriticalAnomalyDisplayedPayload", names)
        self.assertIn("OfflineInspectionSyncedPayload", names)

    def test_generate_python_code_valid_ast(self) -> None:
        entities = ContractGenerator.extract_entities_from_prd(self.sample_prd)
        code = ContractGenerator.generate_python(entities)
        self.assertIn("@dataclass(frozen=True)", code)
        self.assertIn("class CriticalAnomalyDisplayedPayload:", code)
        self.assertIn("anomaly_id: str", code)
        # Verify syntax compiles cleanly
        parsed = ast.parse(code)
        self.assertIsNotNone(parsed)

    def test_generate_typescript_code(self) -> None:
        entities = ContractGenerator.extract_entities_from_prd(self.sample_prd)
        code = ContractGenerator.generate_typescript(entities)
        self.assertIn("export interface CriticalAnomalyDisplayedPayload", code)
        self.assertIn("readonly anomaly_id: string;", code)
        self.assertIn("readonly estimated_loss_eur: number;", code)

    def test_generate_php_code(self) -> None:
        entities = ContractGenerator.extract_entities_from_prd(self.sample_prd)
        code = ContractGenerator.generate_php(entities)
        self.assertIn("final readonly class CriticalAnomalyDisplayedPayload", code)
        self.assertIn("public string $anomaly_id,", code)
        self.assertIn("public float $estimated_loss_eur,", code)

    def test_generate_contracts_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            prd_file = tmp_path / "00_PRD.md"
            prd_file.write_text(self.sample_prd, encoding="utf-8")
            out_dir = tmp_path / "contracts"

            res = ContractGenerator.generate_contracts(prd_file, out_dir)
            self.assertEqual(res.status, "SUCCESS")
            self.assertEqual(res.entities_count, 2)
            self.assertTrue((out_dir / "models.py").is_file())
            self.assertTrue((out_dir / "types.ts").is_file())
            self.assertTrue((out_dir / "Contracts.php").is_file())

    def test_generate_contracts_missing_prd_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_file = Path(tmp_dir) / "non_existent.md"
            out_dir = Path(tmp_dir) / "contracts"
            with self.assertRaises(SchemaParseError):
                ContractGenerator.generate_contracts(missing_file, out_dir)


if __name__ == "__main__":
    unittest.main()
