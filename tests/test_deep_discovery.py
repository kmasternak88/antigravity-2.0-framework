"""Comprehensive Unit and Integration Tests for Autonomous Deep Discovery Engine v8.2+."""

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.discovery_engine import DiscoveryEngine, validate_blueprint_schema
from tools.init_project import bootstrap
from tools.subagent_workflow import MultiSubagentOrchestrator


class TestDeepDiscoveryEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_discovery_")
        self.workspace = Path(self.test_dir)

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_schema_validator_success_and_failures(self):
        schema_file = Path("specs/blueprints/system.blueprint.schema.json")
        if not schema_file.is_file():
            schema_file = Path(__file__).resolve().parents[1] / "specs/blueprints/system.blueprint.schema.json"
        self.assertTrue(schema_file.is_file(), "Schema file must exist in repo")
        schema = json.loads(schema_file.read_text(encoding="utf-8"))

        valid_blueprint = {
            "metadata": {
                "name": "Test SEO Plugin",
                "slug": "test-seo-plugin",
                "target_archetype": "wordpress_woocommerce_seo",
                "target_stack": "php_wordpress",
                "version": "1.0.0",
                "blueprint_hash": "a" * 64
            },
            "competitive_advantages": [
                {
                    "id": "ADV-01",
                    "advantage": "Zero Autoload",
                    "competitor_pain_point_solved": "Eliminates 100KB options bloat",
                    "evidence_reference": "COMPETITIVE_MATRIX.json"
                }
            ],
            "architecture_topology": {
                "layers": ["Core", "Data Engine"],
                "components": [
                    {
                        "id": "COMP-01",
                        "name": "Bootloader",
                        "layer": "Core",
                        "allowed_paths": ["src/Core"],
                        "srp_max_lines": 35,
                        "checksum": "b" * 64
                    }
                ]
            },
            "ast_processing_pipeline": {
                "parser": "AstParser",
                "transformers": ["JsonLdTransformer"],
                "caching_strategy": "RedisCache"
            },
            "data_dictionary": {
                "entities": ["SeoRecord"],
                "tables": [
                    {
                        "name": "ag_seo_index",
                        "primary_key": "id",
                        "indexes": ["idx_lookup"]
                    }
                ]
            },
            "governance_criteria": {
                "max_query_time_ms": 3.5,
                "max_memory_mb": 16.0,
                "standards_checklist": ["CONTRACT_DEFINED", "INPUT_VALIDATED"]
            }
        }

        # 1. Valid test
        is_valid, errors = validate_blueprint_schema(valid_blueprint, schema)
        self.assertTrue(is_valid, f"Expected valid blueprint, got errors: {errors}")

        # 2. Invalid test: SRP limit violation (>40 lines)
        invalid_srp = dict(valid_blueprint)
        invalid_srp["architecture_topology"] = {
            "layers": ["Core"],
            "components": [
                {
                    "id": "COMP-01",
                    "name": "Bootloader",
                    "layer": "Core",
                    "allowed_paths": ["src/Core"],
                    "srp_max_lines": 45,
                    "checksum": "c" * 64
                }
            ]
        }
        is_valid, errors = validate_blueprint_schema(invalid_srp, schema)
        self.assertFalse(is_valid)
        self.assertTrue(any("SRP limit violated" in e for e in errors))

    def test_full_discovery_pipeline_wordpress_seo(self):
        """DoD Validation: /init 'Stwórz najlepszy plugin SEO dla wp/woo' with deep discovery."""
        res = bootstrap(
            target_dir=str(self.workspace),
            brief="Stwórz najlepszy plugin SEO dla wp/woo",
            deep_discovery=True,
            non_interactive=True,
            auto_genesis=True
        )

        self.assertEqual(res["status"], "INITIALIZED")
        self.assertIsNotNone(res["discovery"])
        self.assertEqual(res["discovery"]["status"], "BLUEPRINT_COMPILED")
        self.assertGreaterEqual(res["discovery"]["competitors_analyzed"], 3)

        # Check Step 0: Raw Competitor Dumps
        dumps_file = self.workspace / ".governance" / "discovery" / "raw_competitor_dumps.json"
        self.assertTrue(dumps_file.is_file())
        dumps_data = json.loads(dumps_file.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(dumps_data["competitors"]), 3)

        # Check Step 1: Competitive Matrix
        matrix_file = self.workspace / ".governance" / "discovery" / "COMPETITIVE_MATRIX.json"
        self.assertTrue(matrix_file.is_file())
        matrix_data = json.loads(matrix_file.read_text(encoding="utf-8"))
        self.assertTrue("extracted_architectural_tradeoffs" in matrix_data)

        # Check Step 2: User Decisions
        decisions_file = self.workspace / ".governance" / "discovery" / "USER_DECISIONS.json"
        self.assertTrue(decisions_file.is_file())

        # Check Step 3: Master Blueprint JSON
        bp_file = self.workspace / "specs" / "blueprints" / "system.blueprint.json"
        self.assertTrue(bp_file.is_file())
        bp_data = json.loads(bp_file.read_text(encoding="utf-8"))
        self.assertTrue(len(bp_data["metadata"]["blueprint_hash"]) == 64)

        # Check Specs Generation (01 to 05)
        for snum in ["01_PRODUCT_REQUIREMENTS.md", "02_SYSTEM_ARCHITECTURE.md", "03_DATA_DICTIONARY.md", "05_TRACEABILITY_MATRIX.md"]:
            self.assertTrue((self.workspace / "specs" / snum).is_file(), f"Missing spec: {snum}")

        # Check Contracts Generation (PHP, TS, OpenAPI)
        contracts_dir = self.workspace / "contracts"
        self.assertTrue((contracts_dir / "PluginContracts.php").is_file(), "Missing contracts/PluginContracts.php")
        self.assertTrue((contracts_dir / "types.ts").is_file(), "Missing contracts/types.ts")
        self.assertTrue((contracts_dir / "openapi.json").is_file(), "Missing contracts/openapi.json")

        # Check Checkpoints in state.sqlite
        sqlite_file = self.workspace / ".governance" / "state" / "state.sqlite"
        self.assertTrue(sqlite_file.is_file())
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM discovery_runs")
        run_count = c.fetchone()[0]
        self.assertGreaterEqual(run_count, 1)

        c.execute("SELECT count(*) FROM discovery_checkpoints")
        chk_count = c.fetchone()[0]
        self.assertGreaterEqual(chk_count, 4)  # 4 checkpoints: SWEEP, MATRIX, INTERVIEW, BLUEPRINT
        conn.close()

    def test_subagent_role_matrix_includes_discovery_agents(self):
        orchestrator = MultiSubagentOrchestrator()
        roles = orchestrator.get_role_configuration()
        self.assertIn("market_scout", roles)
        self.assertIn("reverse_architect", roles)
        self.assertIn("interview_orchestrator", roles)
        self.assertEqual(roles["market_scout"].name, "market-scout-analyst")
        self.assertEqual(roles["reverse_architect"].name, "reverse-systems-architect")
        self.assertEqual(roles["interview_orchestrator"].name, "discovery-interview-orchestrator")


if __name__ == "__main__":
    unittest.main()
