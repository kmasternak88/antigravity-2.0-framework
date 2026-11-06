"""Adversarial Penetration Test Suite for Triple Lock v8.2 Security Hardening.
Tests all 5 Locks against adversarial attacks, bypass attempts, and spoofing:
- Lock 1: Cryptographic Dual-Control & Human Impersonation
- Lock 2: Enforced Worktree Sandboxing
- Lock 3: Mock-Breaker & Gate G4 Cardinal Rule
- Lock 4: Anti-Introspection Guard (native_guard.py & pre_tool_guard.js)
- Lock 5: Task Complexity Limits (Rule 40/3/1) & Clean-Slate Purge
"""
import gc
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from tools.genesis_compiler import (
    is_valid_mutation_target,
    validate_task_complexity_limits,
    validate_gate_g4_cardinal_rule,
)
from tools.init_project import clean_slate_purge_sample_files

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AdversarialPenetrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

        # Copy essential governance and spec structure
        for rel in [
            '.governance/bin/gov.py',
            '.governance/config.json',
            '.governance/tasks.json',
            '.governance/standards.json',
            '.governance/hooks/native_guard.py'
        ]:
            src_file = SOURCE / rel
            if src_file.exists():
                dest = self.root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)

        for rel in [
            '.specify/specs/01_CHARTER.md',
            '.specify/specs/02_ARCHITECTURE.md',
            '.specify/specs/03_ACCEPTANCE.md'
        ]:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('Spec test ' + rel, encoding='utf-8')

        (self.root / 'specs').mkdir(parents=True, exist_ok=True)
        (self.root / 'specs/03_DATA_DICTIONARY.md').write_text('# Data Dictionary\n| SampleModule | core | | | |\n', encoding='utf-8')

        (self.root / 'src').mkdir(parents=True, exist_ok=True)
        (self.root / 'src/sample_module.py').write_text('def sample_module() -> None:\n    pass\n', encoding='utf-8')

        (self.root / 'tests').mkdir(parents=True, exist_ok=True)
        (self.root / 'tests/test_sample_module.py').write_text('import unittest\nfrom src.sample_module import sample_module\nclass T(unittest.TestCase):\n  def test_1(self): pass\n', encoding='utf-8')

        gov_path = self.root / '.governance/bin/gov.py'
        self.g = load_module(gov_path, f"gov_pen_{time.time_ns()}")
        self.g.set_workspace_root(self.root)

        guard_path = self.root / '.governance/hooks/native_guard.py'
        self.h = load_module(guard_path, f"guard_pen_{time.time_ns()}")
        self.h.ROOT = self.root
        self.h.gov = self.g

        # Basic governance config setup
        cfg = self.g.config()
        cfg['checks']['unit'] = {'argv': [sys.executable, '-c', 'print("pass")'], 'timeout': 5}
        cfg['required_release_checks'] = ['unit']
        cfg['max_parallel'] = 2
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')

        tasks = {
            'version': 1,
            'tasks': [{
                'id': 'T001',
                'title': 'Penetration Task',
                'depends_on': [],
                'allowed_paths': ['src/sample_module.py', 'tests/test_sample_module.py'],
                'checks': ['unit'],
                'acceptance': ['AC1'],
                'risk': 'low'
            }]
        }
        (self.root / '.governance/tasks.json').write_text(json.dumps(tasks), encoding='utf-8')

        self.saved_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.saved_env)
        gc.collect()
        self.tmp.cleanup()

    # =========================================================================
    # PRÓBA 1: Atak na Lock 1 - Self-Review & Human Impersonation
    # =========================================================================

    def test_lock1_01_human_impersonation_without_token_rejected(self):
        """Atak 1.1: Próba zatwierdzenia jako human:* bez GOV_HUMAN_TOKEN -> UNAUTHORIZED_HUMAN_IMPERSONATION."""
        os.environ.pop('GOV_HUMAN_TOKEN', None)
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'session-builder-1')
        self.g.run_check('T001', 'unit')

        impersonation_targets = ['human:owner', 'human:techlead', 'human:security_officer', 'human:root']
        for target in impersonation_targets:
            with self.assertRaises(self.g.Rejected) as ctx:
                self.g.review('T001', target, 'APPROVED', 'Forged approval')
            self.assertIn('UNAUTHORIZED_HUMAN_IMPERSONATION', str(ctx.exception))

    def test_lock1_02_self_review_same_agent_session_rejected(self):
        """Atak 1.2: Próba zatwierdzenia w tej samej sesji agenta -> FRAUDULENT_SELF_REVIEW_REJECTED."""
        os.environ['GOV_AUDITOR_TOKEN'] = 'auditor-secret-token-12345'
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'session-shared-xyz')
        self.g.run_check('T001', 'unit')

        with self.assertRaises(self.g.Rejected) as ctx:
            self.g.review('T001', 'agent:reviewer', 'APPROVED', 'Self review attempt',
                          reviewer_session='session-shared-xyz',
                          auditor_token='auditor-secret-token-12345')
        self.assertIn('FRAUDULENT_SELF_REVIEW_REJECTED', str(ctx.exception))

    def test_lock1_03_self_review_same_llm_session_rejected(self):
        """Atak 1.3: Próba zatwierdzenia w tej samej sesji LLM (CONVERSATION_ID/ANTIGRAVITY_SESSION_ID/SESSION_ID) -> FRAUDULENT_SELF_REVIEW_REJECTED."""
        os.environ['GOV_AUDITOR_TOKEN'] = 'auditor-secret-token-12345'
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'shared-llm-conv-99')
        self.g.run_check('T001', 'unit')

        for env_key in ['CONVERSATION_ID', 'ANTIGRAVITY_SESSION_ID', 'SESSION_ID']:
            os.environ[env_key] = 'shared-llm-conv-99'
            with self.assertRaises(self.g.Rejected) as ctx:
                self.g.review('T001', 'agent:reviewer', 'APPROVED', 'Bypass attempt via env',
                              reviewer_session='isolated-different-session',
                              auditor_token='auditor-secret-token-12345')
            self.assertIn('FRAUDULENT_SELF_REVIEW_REJECTED', str(ctx.exception))
            os.environ.pop(env_key, None)

    def test_lock1_04_review_without_auditor_token_rejected(self):
        """Atak 1.4: Próba zatwierdzenia bez tokenu audytora -> FRAUDULENT_SELF_REVIEW_REJECTED."""
        os.environ.pop('GOV_AUDITOR_TOKEN', None)
        os.environ.pop('AUDITOR_TOKEN', None)
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'session-builder-1')
        self.g.run_check('T001', 'unit')

        for invalid_token in [None, '', '   ']:
            with self.assertRaises(self.g.Rejected) as ctx:
                self.g.review('T001', 'agent:reviewer', 'APPROVED', 'Audit without token',
                              reviewer_session='session-auditor-1',
                              auditor_token=invalid_token)
            self.assertIn('FRAUDULENT_SELF_REVIEW_REJECTED', str(ctx.exception))

    def test_lock1_05_review_with_builder_fencing_token_rejected(self):
        """Atak 1.5: Próba zatwierdzenia z tokenem identycznym z tokenem buildera -> FRAUDULENT_SELF_REVIEW_REJECTED."""
        os.environ['GOV_AUDITOR_TOKEN'] = 'auditor-secret-token-12345'
        self.g.approve('human:owner', 'spec approved')
        claim_res = self.g.claim('T001', 'agent:builder', 'session-builder-1')
        self.g.run_check('T001', 'unit')
        builder_token = claim_res['token']

        with self.assertRaises(self.g.Rejected) as ctx:
            self.g.review('T001', 'agent:reviewer', 'APPROVED', 'Forged token',
                          reviewer_session='session-auditor-1',
                          auditor_token=builder_token)
        self.assertIn('FRAUDULENT_SELF_REVIEW_REJECTED', str(ctx.exception))

    def test_lock1_06_gate_rejects_unverified_identity(self):
        """Atak 1.6: Wymuszenie gate() na zadaniu z identity_verified=False -> GATE_FAILED."""
        os.environ['GOV_AUDITOR_TOKEN'] = 'auditor-secret-token-12345'
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'session-builder-1')
        self.g.run_check('T001', 'unit')

        # Wykonaj review
        self.g.review('T001', 'agent:reviewer', 'APPROVED', 'Initial review',
                      reviewer_session='session-auditor-1',
                      auditor_token='auditor-secret-token-12345')

        # Ręcznie zasymuluj wstrzyknięcie/tamper w bazie: ustaw identity_verified = 0
        c = self.g.db()
        try:
            c.execute("UPDATE reviews SET identity_verified = 0 WHERE task='T001'")
            c.commit()
        finally:
            c.close()

        with self.assertRaises(self.g.Rejected) as ctx:
            self.g.gate('T001')
        self.assertIn('GATE_FAILED: Independent review identity unverified', str(ctx.exception))

    # =========================================================================
    # PRÓBA 2: Atak na Lock 2 - Worktree Sandboxing
    # =========================================================================

    def test_lock2_01_worktree_passthrough_completely_eliminated(self):
        """Atak 2.1: Weryfikacja całkowitego usunięcia WORKTREE_PASSTHROUGH z kodu silnika."""
        gov_code = (self.root / '.governance/bin/gov.py').read_text(encoding='utf-8')
        self.assertNotIn('WORKTREE_PASSTHROUGH', gov_code, "WORKTREE_PASSTHROUGH bypass must not exist in gov.py!")

        # Próba obejścia przez zmienne środowiskowe 'share' oraz '1'
        os.environ['ANTIGRAVITY_WORKSPACE_MODE'] = 'share'
        os.environ['GOV_WORKTREE_PASSTHROUGH'] = '1'

        wt_res = self.g.manage_worktree('T001', action='create')
        self.assertEqual(wt_res['status'], 'WORKTREE_READY')
        wt_path = self.root / wt_res['path']
        self.assertTrue(wt_path.is_dir(), "Physical worktree must be created despite pass-through env vars")

    def test_lock2_02_verify_task_missing_physical_worktree_rejected(self):
        """Atak 2.2: Próba weryfikacji zadania bez fizycznego katalogu worktree -> ENFORCED_WORKTREE_REQUIRED."""
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'session-builder-1')
        self.g.manage_worktree('T001', action='create')

        c = self.g.db()
        try:
            wt_row = c.execute('SELECT worktree_path FROM worktrees WHERE task="T001"').fetchone()
            self.assertIsNotNone(wt_row)
            wt_path = self.root / wt_row['worktree_path']

            # Usunięcie fizycznego katalogu worktree z dysku
            if wt_path.exists():
                shutil.rmtree(wt_path)

            with self.assertRaises(self.g.Rejected) as ctx:
                self.g.verify_task(c, 'T001')
            self.assertIn('ENFORCED_WORKTREE_REQUIRED', str(ctx.exception))
        finally:
            c.close()

    # =========================================================================
    # PRÓBA 3: Atak na Lock 4 - Anti-Introspection Guard
    # =========================================================================

    def test_lock4_01_native_guard_blocks_reading_gov_during_active_task(self):
        """Atak 3.1: Hook native_guard.py bezwzględnie blokuje odczyt .governance/bin/gov.py gdy zadanie jest aktywne."""
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'session-builder-1')

        # Narzędzia odczytu do przetestowania
        read_tools = ['view_file', 'read_file', 'grep_search', 'list_dir', 'find_by_name']
        test_targets = [
            str(self.root / '.governance/bin/gov.py'),
            str(self.root / '.governance\\bin\\gov.py'),
            '.governance/bin/gov.py',
            '.governance/hooks',
            str(self.root / '.governance/hooks/native_guard.py')
        ]

        for t_name in read_tools:
            for target in test_targets:
                payload = {
                    'toolCall': {
                        'name': t_name,
                        'args': {'AbsolutePath': target, 'SearchPath': target, 'DirectoryPath': target, 'TargetFile': target}
                    }
                }
                res = self.h.decide(payload)
                self.assertEqual(res['decision'], 'deny', f"Tool {t_name} on {target} must be denied!")
                self.assertIn('ANTI_INTROSPECTION', res['reason'])

        # run_command terminal inspection
        cli_attacks = [
            'cat .governance/bin/gov.py',
            'type .governance\\bin\\gov.py',
            'head -n 20 .governance/bin/gov.py',
            'python -c "open(\'.governance/bin/gov.py\').read()"'
        ]
        for cmd in cli_attacks:
            payload = {'toolCall': {'name': 'run_command', 'args': {'CommandLine': cmd}}}
            res = self.h.decide(payload)
            self.assertEqual(res['decision'], 'deny', f"CLI '{cmd}' must be denied!")
            self.assertIn('ANTI_INTROSPECTION', res['reason'])

    def test_lock4_02_pre_tool_guard_js_blocks_reading_gov_during_active_task(self):
        """Atak 3.2: Hook pre_tool_guard.js (Node.js) bezwzględnie blokuje odczyt .governance/bin/gov.py gdy zadanie jest aktywne."""
        validator_js = Path(r"C:\Users\lpiku\.gemini\config\validators\pre_tool_guard.js")
        if not validator_js.exists():
            self.skipTest("pre_tool_guard.js not found in global config")

        # Utwórz aktywny stan zadania w SQLite
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'session-builder-1')

        env = os.environ.copy()
        env['GOV_WORKSPACE'] = str(self.root)

        # 1. Test view_file
        payload_view = {
            'toolCall': {
                'name': 'view_file',
                'args': {'AbsolutePath': str(self.root / '.governance/bin/gov.py')}
            }
        }
        proc = subprocess.run(['node', str(validator_js)], input=json.dumps(payload_view), text=True, capture_output=True, env=env)
        self.assertEqual(proc.returncode, 0)
        res_view = json.loads(proc.stdout)
        self.assertEqual(res_view.get('decision'), 'deny')
        self.assertIn('ANTI_INTROSPECTION', res_view.get('reason', ''))

        # 2. Test run_command
        payload_cmd = {
            'toolCall': {
                'name': 'run_command',
                'args': {'CommandLine': 'cat .governance/bin/gov.py'}
            }
        }
        proc2 = subprocess.run(['node', str(validator_js)], input=json.dumps(payload_cmd), text=True, capture_output=True, env=env)
        self.assertEqual(proc2.returncode, 0)
        res_cmd = json.loads(proc2.stdout)
        self.assertEqual(res_cmd.get('decision'), 'deny')
        self.assertIn('ANTI_INTROSPECTION', res_cmd.get('reason', ''))

    # =========================================================================
    # PRÓBA 4: Atak na Lock 3 - Mock-Breaker & G4 Cardinal Rule
    # =========================================================================

    def test_lock3_01_mock_breaker_blocks_critical_config_files(self):
        """Atak 4.1: is_valid_mutation_target bezwzględnie blokuje pliki konfiguracyjne."""
        forbidden_configs = [
            "vite.config.ts",
            "vite.config.js",
            "vitest.config.ts",
            "package.json",
            "package-lock.json",
            "tsconfig.json",
            "tsconfig.node.json",
            "Cargo.toml",
            "pyproject.toml",
            ".governance/config.json",
            "./vite.config.ts",
            "sub/../package.json",
            "nested\\tsconfig.json",
        ]
        for f in forbidden_configs:
            self.assertFalse(is_valid_mutation_target(Path(f)), f"Config file '{f}' must be rejected by mock breaker!")

        allowed_domain_files = [
            "src/service.ts",
            "src/ledger.py",
            "app/controller.go",
            "lib/engine.rs"
        ]
        for f in allowed_domain_files:
            self.assertTrue(is_valid_mutation_target(Path(f)), f"Domain file '{f}' should be allowed")

    def test_lock3_02_gate_g4_cardinal_rule_rejects_zero_files_audited(self):
        """Atak 4.2: validate_gate_g4_cardinal_rule rzuca ZERO_FILES_AUDITED gdy auditedFiles == 0 dla kodu w src/."""
        # 1. Direct function validation
        with self.assertRaises(ValueError) as ctx:
            validate_gate_g4_cardinal_rule("T001", ["src/services/billing.ts"], audited_files_count=0)
        self.assertIn("ZERO_FILES_AUDITED", str(ctx.exception))

        # 2. Files outside src/ do not trigger ZERO_FILES_AUDITED
        validate_gate_g4_cardinal_rule("T002", ["specs/01_REQ.md", "docs/ARCH.md"], audited_files_count=0)

        # 3. Valid audited count passes
        validate_gate_g4_cardinal_rule("T003", ["src/services/billing.ts"], audited_files_count=2)

    # =========================================================================
    # PRÓBA 5: Atak na Lock 5 - 40/3/1 Limit & Clean-Slate Purge
    # =========================================================================

    def test_lock5_01_complexity_limits_rejects_more_than_3_files(self):
        """Atak 5.1: validate_task_complexity_limits rzuca ValueError przy >3 plikach w allowed_paths."""
        # 4 files
        with self.assertRaises(ValueError) as ctx:
            validate_task_complexity_limits(["src/a.ts", "src/b.ts", "src/c.ts", "src/d.ts"])
        self.assertIn("TASK_COMPLEXITY_LIMIT_EXCEEDED", str(ctx.exception))
        self.assertIn("Rule 40/3/1", str(ctx.exception))

        # 10 files
        many_files = [f"src/file_{i}.py" for i in range(10)]
        with self.assertRaises(ValueError) as ctx:
            validate_task_complexity_limits(many_files)
        self.assertIn("TASK_COMPLEXITY_LIMIT_EXCEEDED", str(ctx.exception))

        # 1, 2, 3 files must pass
        validate_task_complexity_limits(["src/a.py"])
        validate_task_complexity_limits(["src/a.py", "tests/test_a.py"])
        validate_task_complexity_limits(["src/a.py", "tests/test_a.py", "contracts/a.contract.ts"])

    def test_lock5_02_clean_slate_purge_removes_sample_ecommerce_files(self):
        """Atak 5.2: clean_slate_purge_sample_files usuwa pliki e-commerce/billing dla projektów o innej domenie."""
        with tempfile.TemporaryDirectory() as td:
            p_root = Path(td)
            (p_root / "contracts").mkdir(parents=True, exist_ok=True)
            (p_root / "src" / "billing").mkdir(parents=True, exist_ok=True)
            (p_root / "src" / "telemetry").mkdir(parents=True, exist_ok=True)
            (p_root / "specs" / "blueprints").mkdir(parents=True, exist_ok=True)

            sample_1 = p_root / "contracts" / "billing_payment_processor.contract.ts"
            sample_2 = p_root / "src" / "billing" / "payment_processor.py"
            sample_3 = p_root / "specs" / "blueprints" / "checkout.blueprint.json"
            real_file = p_root / "src" / "telemetry" / "collector.py"

            sample_1.write_text("// sample contract", encoding="utf-8")
            sample_2.write_text("# sample py", encoding="utf-8")
            sample_3.write_text("{}", encoding="utf-8")
            real_file.write_text("# domain telemetry", encoding="utf-8")

            purged = clean_slate_purge_sample_files(p_root)
            self.assertGreaterEqual(len(purged), 3)

            # Assert sample files are erased
            self.assertFalse(sample_1.exists(), "Sample billing contract must be purged!")
            self.assertFalse(sample_2.exists(), "Sample payment processor must be purged!")
            self.assertFalse(sample_3.exists(), "Sample checkout blueprint must be purged!")

            # Assert real domain file is retained
            self.assertTrue(real_file.exists(), "Real telemetry collector must NOT be deleted!")


if __name__ == '__main__':
    unittest.main()
