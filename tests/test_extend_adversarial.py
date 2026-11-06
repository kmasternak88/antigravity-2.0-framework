"""Adversarial Penetration Test Suite for /extend and grill-me Architecture (Antigravity v8.2).
Validates EARS syntax, Grill-Me interlocks, DAG immutability, backward compatibility, and DREE Rule 50.
"""
import unittest, json, tempfile, shutil, sys, types, importlib.util
from pathlib import Path

# Setup path and module mapping
_repo_root = Path(__file__).resolve().parent.parent
_guard_file = _repo_root / ".governance" / "hooks" / "native_guard.py"
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

if _guard_file.is_file():
    _spec = importlib.util.spec_from_file_location(".governance.hooks.native_guard", _guard_file)
    if _spec and _spec.loader:
        _native_guard = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_native_guard)
        sys.modules[".governance.hooks.native_guard"] = _native_guard
        _pkg_name = "tests"
        sys.modules[f"{_pkg_name}.governance"] = types.ModuleType(f"{_pkg_name}.governance")
        sys.modules[f"{_pkg_name}.governance.hooks"] = types.ModuleType(f"{_pkg_name}.governance.hooks")
        sys.modules[f"{_pkg_name}.governance.hooks.native_guard"] = _native_guard

class TestExtendAdversarialPenetration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".governance").mkdir(parents=True)
        (self.root / "specs").mkdir(parents=True)
        (self.root / "contracts").mkdir(parents=True)
        (self.root / "src").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    # --- TEST 1: Grill-Me Interlock Bypass ---
    def test_extend_rejects_missing_or_forged_grill_me_answers(self):
        """Atak: Próba rozbudowy projektu bez udokumentowanej sesji grill-me."""
        from tools.extend_project import validate_grill_me_session
        
        # 1. Brak pliku sesji
        with self.assertRaises(ValueError) as ctx:
            validate_grill_me_session(self.root)
        self.assertIn("GRILL_ME_SESSION_MISSING", str(ctx.exception))

        # 2. Pusta sesja / mniej niż 3 pytania
        session_file = self.root / ".governance/state/grill_me_session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({"questions": [{"q": "Styl?", "a": "Ładny"}]}), encoding="utf-8")
        
        with self.assertRaises(ValueError) as ctx:
            validate_grill_me_session(self.root)
        self.assertIn("INSUFFICIENT_GRILL_ME_DEPTH", str(ctx.exception))

    # --- TEST 2: EARS Syntax Enforcement ---
    def test_extend_rejects_non_ears_requirements(self):
        """Atak: Próba dodania wymagań PRD ze składnią życzeniową zamiast EARS."""
        from tools.genesis_compiler import validate_ears_syntax

        malicious_spec = """
        ## 3. Wymagania Funkcjonalne
        - REQ-01: System powinien działać szybko i bezawaryjnie.
        - REQ-02: Użytkownik może w razie potrzeby zresetować hasło.
        """
        with self.assertRaises(ValueError) as ctx:
            validate_ears_syntax(malicious_spec)
        self.assertIn("NON_EARS_REQUIREMENT_DETECTED", str(ctx.exception))

        valid_ears_spec = """
        ## 3. Wymagania Funkcjonalne
        - REQ-01: THE SYSTEM SHALL authenticate users within 200ms.
        - REQ-02: WHEN user clicks reset password THE SYSTEM SHALL send a one-time token.
        - REQ-03: IF database connection fails THEN THE SYSTEM SHALL return HTTP 503.
        """
        self.assertTrue(validate_ears_syntax(valid_ears_spec))

    # --- TEST 3: DAG Immutability & Anti-Stomping ---
    def test_extend_prevents_mutating_done_tasks(self):
        """Atak: Próba zresetowania lub nadpisania zadań DONE w tasks.json."""
        from tools.extend_project import merge_tasks_dag

        existing_tasks = {
            "tasks": [
                {"id": "T001", "status": "DONE", "allowed_paths": ["src/auth.py"], "checks": ["test"]}
            ]
        }
        tampered_extension = {
            "tasks": [
                {"id": "T001", "status": "TODO", "allowed_paths": ["src/tampered.py"]} # Atak!
            ]
        }
        with self.assertRaises(ValueError) as ctx:
            merge_tasks_dag(existing_tasks, tampered_extension)
        self.assertIn("DONE_TASK_MUTATION_FORBIDDEN", str(ctx.exception))

    # --- TEST 4: DAG Cycle Detection on Merge ---
    def test_extend_detects_circular_dependencies_across_generations(self):
        """Atak: Wprowadzenie cyklu między starymi a nowymi zadaniami."""
        from tools.genesis_compiler import validate_dag_acyclic

        cyclic_tasks = [
            {"id": "T001", "depends_on": []},
            {"id": "T002", "depends_on": ["T001"]},
            {"id": "T_EXT_01", "depends_on": ["T002"]},
            {"id": "T_EXT_02", "depends_on": ["T_EXT_01"]},
            {"id": "T001", "depends_on": ["T_EXT_02"]} # Cykl!
        ]
        with self.assertRaises(ValueError) as ctx:
            validate_dag_acyclic(cyclic_tasks)
        self.assertIn("CYCLIC_DAG_DETECTED", str(ctx.exception))

    # --- TEST 5: Contract Backward Compatibility (Breaking Change Detection) ---
    def test_extend_rejects_contract_breaking_changes(self):
        """Atak: Niewersjonowana zmiana typu pola w istniejącym kontrakcie DTO."""
        from tools.genesis_compiler import validate_contract_compatibility

        old_contract = "class UserDTO:\n    id: str\n    tier: str\n"
        breaking_contract = "class UserDTO:\n    id: int\n    tier: str\n" # Zmiana str -> int

        with self.assertRaises(ValueError) as ctx:
            validate_contract_compatibility(old_contract, breaking_contract)
        self.assertIn("BREAKING_CONTRACT_CHANGE_DETECTED", str(ctx.exception))

    # --- TEST 6: DREE Rule 50 Financial Float Rejection ---
    def test_extend_rejects_float_in_financial_models(self):
        """Atak: Wprowadzenie typu float do nowego modelu billingowego."""
        from tools.genesis_compiler import validate_dree_financial_invariants

        malicious_dto = """
        @dataclass(frozen=True)
        class DiscountPolicy:
            discount_percentage: float  # ZŁAMANIE REGUŁY 50!
            min_order_amount_cents: int
        """
        with self.assertRaises(ValueError) as ctx:
            validate_dree_financial_invariants(malicious_dto)
        self.assertIn("DREE_RULE_50_FLOAT_FORBIDDEN", str(ctx.exception))

    # --- TEST 7: Spec Lock Stale Guard ---
    def test_native_guard_blocks_src_write_on_stale_spec_lock(self):
        """Atak: Próba zapisu do src/ gdy specyfikacja została zmieniona bez approve-spec."""
        if _native_guard and hasattr(_native_guard, "verify_spec_lock_freshness"):
            verify_spec_lock_freshness = _native_guard.verify_spec_lock_freshness
        else:
            spec = importlib.util.spec_from_file_location("native_guard", _guard_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            verify_spec_lock_freshness = mod.verify_spec_lock_freshness
        
        # Zapisz specyfikację
        spec_path = self.root / "specs/01_PRODUCT_REQUIREMENTS.md"
        spec_path.write_text("# Updated PRD", encoding="utf-8")
        
        # Baza ma stary digest
        db_digest = "old_sha256_hash_12345"
        with self.assertRaises(PermissionError) as ctx:
            verify_spec_lock_freshness(self.root, db_digest)
        self.assertIn("SPEC_LOCK_STALE_OR_MISSING", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
