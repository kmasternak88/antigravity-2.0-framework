"""
Unit tests for Lock 3 and Lock 5 hardening in Antigravity v8.1:
- Dynamic Test Runner & Mock-Breaker Filter
- Task Complexity Limits (Rule 40/3/1)
- Spec-Hash Contracts globbing
- Gate G4 Cardinal Rule (ZERO_FILES_AUDITED)
- Clean-Slate Ingestion & Zero-Contamination Scaffold
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.genesis_compiler import (
    detect_tech_stack,
    is_valid_mutation_target,
    validate_task_complexity_limits,
    validate_gate_g4_cardinal_rule,
    compile_blueprint,
)
from tools.ingestion_parser import IngestionParser, FORBIDDEN_ENTITY_WORDS
from tools.init_project import (
    is_ecommerce_input,
    clean_slate_purge_sample_files,
    generate_clean_contracts_and_specs,
    detect_project_type,
    get_default_check,
)


class TestLock3LanguageAwareTestRunnerAndMockBreaker(unittest.TestCase):
    def test_tech_stack_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Python project
            (tmppath / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            res = detect_tech_stack(tmppath)
            self.assertEqual(res["stack"], "python")
            self.assertEqual(res["gate_cmd"], "pytest")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Node project with vitest
            pkg = {
                "name": "my-ts-app",
                "devDependencies": {"vitest": "^1.0.0"},
                "scripts": {"test": "vitest run"}
            }
            (tmppath / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            (tmppath / "tsconfig.json").write_text("{}", encoding="utf-8")
            res = detect_tech_stack(tmppath)
            self.assertEqual(res["stack"], "typescript")
            self.assertEqual(res["gate_cmd"], "npx vitest run")

    def test_task_complexity_limits_40_3_1(self):
        # 1 to 3 paths allowed
        validate_task_complexity_limits(["src/a.py", "tests/test_a.py", "contracts/a.py"])
        
        # 4 paths must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            validate_task_complexity_limits(["src/a.py", "src/b.py", "tests/test_a.py", "contracts/a.py"])
        self.assertIn("TASK_COMPLEXITY_LIMIT_EXCEEDED", str(ctx.exception))
        self.assertIn("Rule 40/3/1", str(ctx.exception))

    def test_mock_breaker_target_filtering(self):
        # Forbidden configuration files
        forbidden = [
            "vite.config.ts",
            "vite.config.js",
            "tsconfig.json",
            "package.json",
            "package-lock.json",
            "Cargo.toml",
            "pyproject.toml",
            ".governance/config.json",
            "vitest.config.ts",
        ]
        for f in forbidden:
            self.assertFalse(is_valid_mutation_target(Path(f)), f"{f} should be forbidden")

        # Allowed domain and service files
        allowed = [
            "src/services/billing.ts",
            "src/domain/ledger.py",
            "app/controller.go",
            "lib/engine.rs",
            "src/utils.js",
        ]
        for f in allowed:
            self.assertTrue(is_valid_mutation_target(Path(f)), f"{f} should be allowed")

    def test_gate_g4_cardinal_rule(self):
        # Task with src/ and 0 audited files must be rejected
        with self.assertRaises(ValueError) as ctx:
            validate_gate_g4_cardinal_rule("T001", ["src/services/user.py"], audited_files_count=0)
        self.assertIn("ZERO_FILES_AUDITED", str(ctx.exception))

        # Task with src/ and >0 audited files must pass
        validate_gate_g4_cardinal_rule("T001", ["src/services/user.py"], audited_files_count=1)

        # Task with only docs/specs and 0 audited files should pass
        validate_gate_g4_cardinal_rule("T002", ["specs/01_ARCHITECTURE.md", "docs/guide.md"], audited_files_count=0)

    def test_spec_hash_includes_contracts(self):
        import sys
        gov_bin = str(Path(__file__).resolve().parents[1] / ".governance" / "bin")
        if gov_bin not in sys.path:
            sys.path.insert(0, gov_bin)
        import gov
        h = gov.spec_hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)


class TestLock5CleanSlateIngestionAndScaffolding(unittest.TestCase):
    def test_is_ecommerce_detection(self):
        self.assertTrue(is_ecommerce_input(brief="Store checkout cart with payments"))
        self.assertTrue(is_ecommerce_input(prd="E-commerce portal for purchasing products with billing invoice"))
        self.assertFalse(is_ecommerce_input(brief="A high throughput CLI log parsing tool"))
        self.assertFalse(is_ecommerce_input(brief="Real-time telemetry event broker for IoT sensors"))

    def test_ingestion_clean_entities_and_archetype_adr(self):
        cli_brief = "Build a high performance CLI tool to inspect network interfaces and stream packets"
        ctx = IngestionParser.parse_input(cli_brief)
        self.assertEqual(ctx.archetype, "cli_system_tool")
        
        # Ensure domain entities do NOT contain markdown noise or framework stopwords
        for ent in ctx.entities:
            self.assertNotIn(ent.lower(), FORBIDDEN_ENTITY_WORDS)
            self.assertFalse(ent.startswith("FAZA") or ent.startswith("Phase"))

        # Verify ADR-002 is POSIX CLI, NOT monetary zero-float
        adr_titles = [a["title"] for a in ctx.autonomous_adrs]
        self.assertTrue(any("POSIX CLI" in t for t in adr_titles))
        self.assertFalse(any("Zero-Float" in t for t in adr_titles))

    def test_clean_slate_purge_and_dynamic_contracts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Simulate dirty scaffolding with sample ecommerce files
            (tmppath / "contracts").mkdir(parents=True, exist_ok=True)
            (tmppath / "src" / "billing").mkdir(parents=True, exist_ok=True)
            (tmppath / "specs" / "blueprints").mkdir(parents=True, exist_ok=True)
            
            (tmppath / "contracts" / "billing_payment_processor.contract.ts").write_text("// sample", encoding="utf-8")
            (tmppath / "src" / "billing" / "payment_processor.py").write_text("# sample", encoding="utf-8")
            (tmppath / "specs" / "blueprints" / "checkout.blueprint.json").write_text("{}", encoding="utf-8")
            
            # Purge sample files
            purged = clean_slate_purge_sample_files(tmppath)
            self.assertGreater(len(purged), 0)
            self.assertFalse((tmppath / "contracts" / "billing_payment_processor.contract.ts").exists())
            self.assertFalse((tmppath / "specs" / "blueprints" / "checkout.blueprint.json").exists())

            # Generate clean contracts for a CLI tool
            generate_clean_contracts_and_specs(
                tmppath,
                entities=["NetworkInterface", "PacketCapture"],
                archetype="cli_system_tool",
                project_slug="net-inspector",
                ptype="python_pytest"
            )

            # Assert generated contracts conform to DREE invariants
            models_py = tmppath / "contracts" / "models.py"
            types_ts = tmppath / "contracts" / "types.ts"
            data_dict = tmppath / "specs" / "03_DATA_DICTIONARY.md"
            openapi = tmppath / "contracts" / "openapi.json"

            self.assertTrue(models_py.exists())
            self.assertTrue(types_ts.exists())
            self.assertTrue(data_dict.exists())
            self.assertTrue(openapi.exists())

            models_content = models_py.read_text(encoding="utf-8")
            self.assertIn("class NetworkInterfaceError(DomainError):", models_content)
            self.assertIn("@dataclass(frozen=True, slots=True)", models_content)
            self.assertIn("class PacketCapture:", models_content)

            types_content = types_ts.read_text(encoding="utf-8")
            self.assertIn("export interface NetworkInterface extends BaseDomainEntity", types_content)

            data_dict_content = data_dict.read_text(encoding="utf-8")
            self.assertIn("NetworkInterface", data_dict_content)
            self.assertIn("cli_system_tool", data_dict_content)


if __name__ == "__main__":
    unittest.main()
