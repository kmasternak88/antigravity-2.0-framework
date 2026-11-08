import unittest
from pathlib import Path
import tempfile
import shutil
from tools.ci_checks import verify_prd_traceability

class TestPRDTraceabilityGate(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.root = Path(self.tmp_dir)
        self.specs_dir = self.root / "specs"
        self.tests_dir = self.root / "tests"
        self.specs_dir.mkdir()
        self.tests_dir.mkdir()

        self.prd_path = self.specs_dir / "00_PRD.md"
        self.prd_path.write_text("Requirements:\n- REQ-001\n- REQ-002\n")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_verify_pass(self):
        matrix_path = self.specs_dir / "05_TRACEABILITY_MATRIX.md"
        matrix_path.write_text("| REQ-001 | \n| REQ-002 |")

        test_file = self.tests_dir / "test_features.py"
        test_file.write_text("def test_req_001():\n    # @test_req(\"REQ-001\")\n    pass\ndef test_req_002():\n    # REQ-002\n    pass")

        passed, errors = verify_prd_traceability(self.prd_path, self.specs_dir, self.tests_dir)
        self.assertTrue(passed)
        self.assertEqual(len(errors), 0)

    def test_verify_missing_in_specs(self):
        test_file = self.tests_dir / "test_features.py"
        test_file.write_text("def test_req_001():\n    # REQ-001\n    pass\ndef test_req_002():\n    # REQ-002\n    pass")

        passed, errors = verify_prd_traceability(self.prd_path, self.specs_dir, self.tests_dir)
        self.assertFalse(passed)
        self.assertTrue(any("REQ-001 missing in specs" in e for e in errors))

    def test_verify_missing_in_tests(self):
        matrix_path = self.specs_dir / "05_TRACEABILITY_MATRIX.md"
        matrix_path.write_text("| REQ-001 | \n| REQ-002 |")

        test_file = self.tests_dir / "test_features.py"
        test_file.write_text("def test_req_001():\n    # @test_req(\"REQ-001\")\n    pass")

        passed, errors = verify_prd_traceability(self.prd_path, self.specs_dir, self.tests_dir)
        self.assertFalse(passed)
        self.assertTrue(any("REQ-002 missing in tests" in e for e in errors))

if __name__ == '__main__':
    unittest.main()
