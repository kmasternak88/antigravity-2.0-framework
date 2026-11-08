import sys, pathlib
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
"""
Adversarial SDD & Boundary Test Suite for tools/prd_parser.py and tools/ci_checks.py
Challenger v8.3 — Antigravity Ultra SDD Verification Loop
"""

import sys
import unittest
import tempfile
import shutil
import time
from pathlib import Path

# Resolve framework root

from tools.prd_parser import (
    PRDParser,
    PRDValidationError,
    PRDParseError,
    ParsedPRD,
    Requirement,
    PRDMetadata,
    KPIMetric
)
from tools.ci_checks import verify_prd_traceability, _extract_reqs, _check_single_req


class TestPRDParserMarkdownTables(unittest.TestCase):
    """Adversarial testing of Markdown table parsing in PRDParser."""

    def setUp(self):
        self.parser = PRDParser()

    def test_empty_rows_and_whitespace_handled_gracefully(self):
        """Empty rows or rows with whitespace pipes must not crash parser."""
        content = """
## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | | | |
|   |
||||||||
| **`REQ-001`** | Title 1 | Story 1 | `PER-01` | **MUST HAVE** | Given When Then | `EVT-01` | High |

## 4. Przepływy Użytkownika
"""
        prd = self.parser.parse_markdown(content)
        self.assertEqual(len(prd.requirements), 1)
        self.assertEqual(prd.requirements[0].id, "REQ-001")

    def test_missing_columns_row_handling(self):
        """Rows with fewer than 7 columns are dropped gracefully without crashing."""
        content = """
## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW |
| :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Title 1 | Story 1 | `PER-01` | **MUST HAVE** |
| **`REQ-002`** | Title 2 | Story 2 | `PER-01` | **SHOULD HAVE** |

## 4. Przepływy Użytkownika
"""
        prd = self.parser.parse_markdown(content)
        self.assertEqual(len(prd.requirements), 0)

    def test_kpi_separator_row_rejected(self):
        """VULNERABILITY: Standard markdown separator |---|---| must not be parsed as a real KPIMetric."""
        content = """
### 6.1. Hierarchia Metryk
| ID | Nazwa | Baseline | Target |
|---|---|---|---|
| `KPI-01` | MTTR | 48h | 2h |
### 6.2. Specyfikacja Zdarzeń
"""
        prd = self.parser.parse_markdown(content)
        # Should only parse the real KPI, not the separator row '---'
        self.assertEqual(len(prd.kpis), 1, f"Expected 1 KPI metric, but found {len(prd.kpis)}: {[k.id for k in prd.kpis]}")
        self.assertEqual(prd.kpis[0].id, "KPI-01")

    def test_row_containing_word_with_uppercase_id_not_dropped(self):
        """VULNERABILITY: Rows containing words with 'ID' (e.g. EVIDENCE, VALIDATION) must not be silently dropped."""
        content = """
## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Title | Automated EVIDENCE Collection | `PER-01` | **MUST HAVE** | Given When Then | `EVT-01` | High |

## 4. Przepływy Użytkownika
"""
        prd = self.parser.parse_markdown(content)
        self.assertEqual(len(prd.requirements), 1, "Requirement containing 'EVIDENCE' was erroneously dropped due to 'ID' in line check")

    def test_unescaped_pipe_in_text_does_not_corrupt_columns(self):
        """VULNERABILITY: Pipe inside text column must not cause column shift corruption."""
        content = """
## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Title | Story with | pipe | `PER-01` | **MUST HAVE** | Given When Then | `EVT-01` | High |

## 4. Przepływy Użytkownika
"""
        prd = self.parser.parse_markdown(content)
        self.assertEqual(len(prd.requirements), 1)
        self.assertEqual(prd.requirements[0].persona_id, "PER-01", f"Persona corrupted to '{prd.requirements[0].persona_id}' due to column shift")

    def test_missing_subsequent_section_does_not_wipe_preceding_section(self):
        """VULNERABILITY: Missing Section 4 must not wipe Section 3 requirements due to regex lookahead."""
        content = """
## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Title 1 | Story 1 | `PER-01` | **MUST HAVE** | Given-When-Then 1 | `EVT-01` | High |

## 5. Wymagania Niefunkcjonalne
"""
        prd = self.parser.parse_markdown(content)
        self.assertEqual(len(prd.requirements), 1, "Lookahead (?=## 4\\.) caused Section 3 requirements to be completely wiped")

    def test_section_headers_case_insensitivity(self):
        """VULNERABILITY: Section header with lowercase letters must be recognized."""
        content = """
## 3. Zakres funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Title 1 | Story 1 | `PER-01` | **MUST HAVE** | Given-When-Then 1 | `EVT-01` | High |

## 4. Przepływy Użytkownika
"""
        prd = self.parser.parse_markdown(content)
        self.assertEqual(len(prd.requirements), 1, "Case-sensitive regex missed 'Zakres funkcjonalny'")


class TestPRDParserMoSCoWCompliance(unittest.TestCase):
    """Adversarial testing of MoSCoW limit enforcement (<= 40% MUST HAVE rule)."""

    def setUp(self):
        self.parser = PRDParser()
        self.dummy_metadata = PRDMetadata("ID", "v1", "APPROVED", "A", "L", True, False, False, "today")

    def test_moscow_limit_fails_when_must_have_exceeds_40_percent(self):
        """PRD with > 40% MUST HAVE requirements strictly raises PRDValidationError."""
        prd = ParsedPRD(
            metadata=self.dummy_metadata,
            requirements=[
                Requirement("REQ-001", "T1", "S1", "P1", "MUST HAVE", "AC", "E1", "L"),
                Requirement("REQ-002", "T2", "S2", "P1", "MUST HAVE", "AC", "E2", "L"),
                Requirement("REQ-003", "T3", "S3", "P1", "MUST HAVE", "AC", "E3", "L"),
                Requirement("REQ-004", "T4", "S4", "P1", "SHOULD HAVE", "AC", "E4", "L"),
                Requirement("REQ-005", "T5", "S5", "P1", "COULD HAVE", "AC", "E5", "L"),
            ]
        )
        with self.assertRaises(PRDValidationError) as ctx:
            self.parser.validate_moscow_limit(prd)
        self.assertIn("MUST HAVE requirements exceed 40%", str(ctx.exception))
        self.assertIn("60.0%", str(ctx.exception))

    def test_moscow_limit_passes_at_exact_40_percent(self):
        """PRD with exactly 40% MUST HAVE requirements (2 of 5) passes cleanly."""
        prd = ParsedPRD(
            metadata=self.dummy_metadata,
            requirements=[
                Requirement("REQ-001", "T1", "S1", "P1", "MUST HAVE", "AC", "E1", "L"),
                Requirement("REQ-002", "T2", "S2", "P1", "MUST HAVE", "AC", "E2", "L"),
                Requirement("REQ-003", "T3", "S3", "P1", "SHOULD HAVE", "AC", "E3", "L"),
                Requirement("REQ-004", "T4", "S4", "P1", "COULD HAVE", "AC", "E4", "L"),
                Requirement("REQ-005", "T5", "S5", "P1", "WON'T HAVE", "AC", "E5", "L"),
            ]
        )
        self.assertTrue(self.parser.validate_moscow_limit(prd))

    def test_moscow_limit_fails_single_must_have_100_percent(self):
        """PRD with 1 requirement that is MUST HAVE (100%) must fail."""
        prd = ParsedPRD(
            metadata=self.dummy_metadata,
            requirements=[
                Requirement("REQ-001", "T1", "S1", "P1", "MUST HAVE", "AC", "E1", "L"),
            ]
        )
        with self.assertRaises(PRDValidationError):
            self.parser.validate_moscow_limit(prd)

    def test_moscow_limit_zero_requirements_no_zero_division(self):
        """PRD with 0 requirements returns True gracefully without ZeroDivisionError."""
        prd = ParsedPRD(metadata=self.dummy_metadata, requirements=[])
        self.assertTrue(self.parser.validate_moscow_limit(prd))

    def test_moscow_case_insensitivity_and_markdown_bold(self):
        """MoSCoW matching handles lowercase and markdown bold formatting."""
        prd = ParsedPRD(
            metadata=self.dummy_metadata,
            requirements=[
                Requirement("REQ-001", "T1", "S1", "P1", "must have", "AC", "E1", "L"),
                Requirement("REQ-002", "T2", "S2", "P1", "**MUST HAVE**", "AC", "E2", "L"),
                Requirement("REQ-003", "T3", "S3", "P1", "could have", "AC", "E3", "L"),
            ]
        )
        with self.assertRaises(PRDValidationError):
            self.parser.validate_moscow_limit(prd)

    def test_moscow_negation_not_must_have_rejected(self):
        """VULNERABILITY: 'NOT MUST HAVE' should NOT be counted as MUST HAVE."""
        prd = ParsedPRD(
            metadata=self.dummy_metadata,
            requirements=[
                Requirement("REQ-001", "T1", "S1", "P1", "NOT MUST HAVE", "AC", "E1", "L"),
                Requirement("REQ-002", "T2", "S2", "P1", "COULD HAVE", "AC", "E2", "L"),
            ]
        )
        # Should NOT fail MoSCoW limit because there are 0 MUST HAVEs (0 <= 40%)
        # But 'MUST HAVE' in 'NOT MUST HAVE' causes false positive failure!
        try:
            self.parser.validate_moscow_limit(prd)
        except PRDValidationError:
            self.fail("VULNERABILITY: 'NOT MUST HAVE' was falsely classified as MUST HAVE")


class TestPRDParserInputBoundaries(unittest.TestCase):
    """Adversarial testing of empty, missing, or malformed document structures."""

    def setUp(self):
        self.parser = PRDParser()

    def test_completely_empty_document_does_not_crash(self):
        """Empty string must return ParsedPRD with fallback metadata and empty lists."""
        prd = self.parser.parse_markdown("")
        self.assertIsInstance(prd, ParsedPRD)
        self.assertEqual(prd.metadata.doc_id, "UNKNOWN")
        self.assertEqual(len(prd.requirements), 0)
        self.assertEqual(len(prd.personas), 0)
        self.assertEqual(len(prd.nfrs), 0)
        self.assertEqual(len(prd.kpis), 0)

    def test_whitespace_only_document_does_not_crash(self):
        """Whitespace-only document returns empty parsed entities."""
        prd = self.parser.parse_markdown("   \n\n\t  \r\n  ")
        self.assertIsInstance(prd, ParsedPRD)
        self.assertEqual(len(prd.requirements), 0)

    def test_none_input_raises_prd_parse_error_not_unhandled_type_error(self):
        """VULNERABILITY: None input should raise PRDParseError, not unhandled TypeError."""
        try:
            self.parser.parse_markdown(None)
        except PRDParseError:
            pass  # Expected safe domain error
        except TypeError as e:
            self.fail(f"VULNERABILITY: parse_markdown(None) crashed with unhandled TypeError: {e}")

    def test_massive_payload_stress_performance(self):
        """Stress test: 1000 requirements parsed in < 1.0 second."""
        header = """
> - **ID Dokumentu:** `PRD-PERF-001`
## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        rows = [
            f"| `REQ-{i:03d}` | Title {i} | Story {i} | `PER-01` | {'MUST HAVE' if i < 300 else 'SHOULD HAVE'} | Given When Then | `EVT-01` | Low |"
            for i in range(1000)
        ]
        footer = "\n## 4. Przepływy Użytkownika\n"

        content = header + "\n".join(rows) + footer
        start_time = time.perf_counter()
        prd = self.parser.parse_markdown(content)
        duration = time.perf_counter() - start_time

        self.assertEqual(len(prd.requirements), 1000)
        self.assertLess(duration, 1.0)
        self.assertTrue(self.parser.validate_moscow_limit(prd))


class TestPRDParserGivenWhenThenValidation(unittest.TestCase):
    """Adversarial analysis of Given-When-Then acceptance criteria."""

    def setUp(self):
        self.parser = PRDParser()

    def test_invalid_given_when_then_format_raises_validation_error(self):
        """BDD GAP: Parser should reject or flag non-Given-When-Then junk in acceptance criteria."""
        content = """
## 3. Zakres Funkcjonalny i Specyfikacja MVP (MoSCoW Matrix)
| ID Wymagania | Tytuł | Historia Użytkownika | Persona | MoSCoW | Kryteria | Event | Dodatek |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-001`** | Title | Story | `PER-01` | **MUST HAVE** | JUNK_NO_GHERKIN_CRITERIA | `EVT-01` | Low |

## 4. Przepływy Użytkownika
"""
        prd = self.parser.parse_markdown(content)
        # Verify if acceptance criteria enforces Gherkin keywords
        ac = prd.requirements[0].acceptance_criteria
        has_gherkin = any(kw in ac.lower() for kw in ["given", "when", "then"])
        self.assertTrue(has_gherkin, f"VULNERABILITY: Acceptance criteria accepted invalid non-Gherkin string: '{ac}'")


class TestCITraceabilityGateAdversarial(unittest.TestCase):
    """Adversarial testing of G6 PRD Traceability Gate in tools/ci_checks.py."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.specs_dir = self.tmp_dir / "specs"
        self.tests_dir = self.tmp_dir / "tests"
        self.specs_dir.mkdir()
        self.tests_dir.mkdir()
        self.prd_path = self.specs_dir / "00_PRD.md"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_simulation_req_missing_in_specs_returns_false_with_error(self):
        """Simulation: REQ-999 in PRD missing in specs & tests returns is_traceable=False."""
        self.prd_path.write_text("Requirements:\n- REQ-999\n", encoding="utf-8")
        is_traceable, errors = verify_prd_traceability(self.prd_path, self.specs_dir, self.tests_dir)

        self.assertFalse(is_traceable)
        self.assertEqual(len(errors), 1)
        self.assertIn("UNCOVERED_PRD_REQUIREMENTS: REQ-999 missing in specs.", errors[0])

    def test_simulation_req_missing_in_tests_returns_false_with_error(self):
        """Simulation: REQ-999 present in specs but missing in tests returns is_traceable=False."""
        self.prd_path.write_text("Requirements:\n- REQ-999\n", encoding="utf-8")
        (self.specs_dir / "05_TRACEABILITY_MATRIX.md").write_text("| REQ-999 |", encoding="utf-8")

        is_traceable, errors = verify_prd_traceability(self.prd_path, self.specs_dir, self.tests_dir)
        self.assertFalse(is_traceable)
        self.assertEqual(len(errors), 1)
        self.assertIn("UNCOVERED_PRD_REQUIREMENTS: REQ-999 missing in tests.", errors[0])

    def test_simulation_empty_prd_or_missing_file_default_behavior(self):
        """Simulation: Empty PRD or non-existent file returns (True, []) default bypass."""
        non_existent_prd = self.specs_dir / "NON_EXISTENT_PRD.md"
        is_traceable, errors = verify_prd_traceability(non_existent_prd, self.specs_dir, self.tests_dir)
        self.assertTrue(is_traceable)
        self.assertEqual(errors, [])

        empty_prd = self.specs_dir / "EMPTY_PRD.md"
        empty_prd.write_text("", encoding="utf-8")
        is_traceable, errors = verify_prd_traceability(empty_prd, self.specs_dir, self.tests_dir)
        self.assertTrue(is_traceable)
        self.assertEqual(errors, [])

    def test_substring_matching_in_tests_rejected(self):
        """CRITICAL VULNERABILITY: Test for REQ-0010 must not falsely satisfy REQ-001."""
        self.prd_path.write_text("Requirements:\n- REQ-001\n", encoding="utf-8")
        (self.specs_dir / "05_TRACEABILITY_MATRIX.md").write_text("| REQ-001 |", encoding="utf-8")

        # Test suite only tests REQ-0010, NOT REQ-001
        test_file = self.tests_dir / "test_other.py"
        test_file.write_text("def test_req_0010():\n    # REQ-0010 only\n    pass\n", encoding="utf-8")

        is_traceable, errors = verify_prd_traceability(self.prd_path, self.specs_dir, self.tests_dir)
        self.assertFalse(is_traceable, "VULNERABILITY: 'REQ-0010' in tests was falsely accepted as covering 'REQ-001'")

    def test_four_digit_req_id_extracted_accurately(self):
        """VULNERABILITY: 4-digit requirement REQ-1000 must not be truncated to REQ-100."""
        self.prd_path.write_text("Requirements:\n- REQ-1000\n", encoding="utf-8")
        reqs = _extract_reqs(self.prd_path)
        self.assertIn("REQ-1000", reqs, f"VULNERABILITY: REQ-1000 was truncated to {reqs}")

    def test_traceability_pass_with_proper_decorator(self):
        """Valid path: Requirement covered with explicit @test_req decorator passes cleanly."""
        self.prd_path.write_text("Requirements:\n- REQ-001\n", encoding="utf-8")
        (self.specs_dir / "05_TRACEABILITY_MATRIX.md").write_text("| REQ-001 |", encoding="utf-8")
        test_file = self.tests_dir / "test_suite.py"
        test_file.write_text("@test_req(\"REQ-001\")\ndef test_feature():\n    pass\n", encoding="utf-8")

        is_traceable, errors = verify_prd_traceability(self.prd_path, self.specs_dir, self.tests_dir)
        self.assertTrue(is_traceable)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()