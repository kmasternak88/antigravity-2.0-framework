import gc, importlib.util,json,os,shutil,sqlite3,sys,tempfile,time,unittest
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h = load(SOURCE / '.governance/hooks/native_guard.py', 'guard')
guard = h
class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for rel in ['.governance/bin/gov.py','.governance/config.json','.governance/tasks.json', '.governance/hooks/native_guard.py']:
            dest=self.root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/rel,dest)
        for rel in ['.specify/specs/01_CHARTER.md','.specify/specs/02_ARCHITECTURE.md','.specify/specs/03_ACCEPTANCE.md']:
            p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('Spec test '+rel)
        (self.root/'src').mkdir();(self.root/'src/code.py').write_text('value=1\n')
        self.g=load(self.root/'.governance/bin/gov.py','gov_'+str(time.time_ns()))
        self.g.set_workspace_root(self.root)
        self.h = load(self.root / '.governance/hooks/native_guard.py', 'guard_' + str(time.time_ns()))
        self.h.ROOT = self.root
        self.h.gov = self.g
        os.environ['GOV_REVIEWER_SESSION'] = 'test-auditor-session'
        os.environ['GOV_AUDITOR_TOKEN'] = 'test-auditor-token-secret'
        os.environ['GOV_HUMAN_TOKEN'] = 'test-human-token-secret'
        cfg=self.g.config();cfg['checks']={'unit':{'argv':[sys.executable,'-c','print("actual test")'],'timeout':3}};cfg['required_release_checks']=['unit'];cfg['max_parallel']=2
        self.write('.governance/config.json',cfg)
        self.write('.governance/tasks.json',{'version':1,'tasks':[self.task('T001')]})
    def tearDown(self):
        os.environ['GOV_REVIEWER_SESSION'] = 'test-auditor-session'
        os.environ['GOV_AUDITOR_TOKEN'] = 'test-auditor-token-secret'
        os.environ['GOV_HUMAN_TOKEN'] = 'test-human-token-secret'
        import gc; gc.collect()
        self.tmp.cleanup()
    def task(self,id,deps=None,paths=None):return {'id':id,'depends_on':deps or [],'allowed_paths':paths or ['src'],'checks':['unit'],'acceptance':['AC1'],'risk':'low'}
    def write(self,path,obj):(self.root/path).write_text(json.dumps(obj),encoding='utf-8')
    def start(self):
        self.g.approve('human:owner','reviewed test spec');return self.g.claim('T001','agent:builder','session1')
    def verified(self):
        self.start();self.g.run_check('T001','unit')
    def test_valid_dag(self):self.assertEqual(self.g.validate()['status'],'VALID')
    def test_cycle_rejected(self):
        self.write('.governance/tasks.json',{'tasks':[self.task('T001',['T002']),self.task('T002',['T001'])]})
        with self.assertRaisesRegex(self.g.Rejected,'DAG_CYCLE'):self.g.validate()
    def test_unknown_dependency(self):
        self.write('.governance/tasks.json',{'tasks':[self.task('T001',['missing'])]})
        with self.assertRaisesRegex(self.g.Rejected,'Unknown dependency'):self.g.validate()
    def test_path_traversal(self):
        with self.assertRaises(self.g.Rejected):self.g.safe_path('../outside')
    def test_unbounded_path(self):
        with self.assertRaises(self.g.Rejected):self.g.safe_path('.')
    def test_claim_requires_spec_lock(self):
        with self.assertRaisesRegex(self.g.Rejected,'SPEC_LOCK'):self.g.claim('T001','a','s')
    def test_spec_edit_invalidates_lock(self):
        self.start();(self.root/'.specify/specs/01_CHARTER.md').write_text('changed')
        self.assertFalse(self.g.status()['specLocked'])
    def test_task_edit_invalidates_lock(self):
        self.start();tasks=self.g.definitions();tasks[0]['allowed_paths']=['src','other'];self.write('.governance/tasks.json',{'tasks':tasks})
        self.assertFalse(self.g.status()['specLocked'])
    def test_config_edit_invalidates_lock(self):
        self.start();cfg=self.g.config();cfg['max_parallel']=3;self.write('.governance/config.json',cfg)
        self.assertFalse(self.g.status()['specLocked'])
    def test_dependency_not_done(self):
        self.write('.governance/tasks.json',{'tasks':[self.task('T001'),self.task('T002',['T001'],['other'])]})
        self.g.approve('human:o','r')
        with self.assertRaisesRegex(self.g.Rejected,'DEPENDENCY_NOT_DONE'):self.g.claim('T002','b','s')
    def test_overlapping_claims(self):
        self.write('.governance/tasks.json',{'tasks':[self.task('T001'),self.task('T002',paths=['src/deep'])]})
        self.start()
        with self.assertRaisesRegex(self.g.Rejected,'WRITE_SCOPE_CONFLICT'):self.g.claim('T002','b','s2')
    def test_stale_fencing_token(self):
        self.start()
        with self.assertRaisesRegex(self.g.Rejected,'STALE_FENCING'):self.g.heartbeat('T001','wrong')
    def test_expired_lease_takeover(self):
        first=self.start();c=self.g.db();c.execute('UPDATE tasks SET expires=0');c.commit();c.close()
        second=self.g.claim('T001','agent:new','session2');self.assertNotEqual(first['token'],second['token'])
        with self.assertRaisesRegex(self.g.Rejected,'STALE_FENCING'):self.g.heartbeat('T001',first['token'])
    def test_real_process_evidence(self):
        self.start();r=self.g.run_check('T001','unit');self.assertEqual(r['exitCode'],0);self.assertTrue((self.root/r['log']).exists())
    def test_failing_process_blocks_gate(self):
        cfg=self.g.config();cfg['checks']['unit']['argv']=[sys.executable,'-c','raise SystemExit(7)'];self.write('.governance/config.json',cfg)
        self.start();self.assertEqual(self.g.run_check('T001','unit')['exitCode'],7)
        with self.assertRaisesRegex(self.g.Rejected,'CURRENT_PASS_REQUIRED'):self.g.gate('T001')
    def test_timeout_records_124(self):
        cfg=self.g.config();cfg['checks']['unit']={'argv':[sys.executable,'-c','import time;time.sleep(5)'],'timeout':1};self.write('.governance/config.json',cfg)
        self.start();self.assertEqual(self.g.run_check('T001','unit')['exitCode'],124)
    def test_source_mutating_test_invalid(self):
        cfg=self.g.config();cfg['checks']['unit']['argv']=[sys.executable,'-c','from pathlib import Path;Path("src/code.py").write_text("changed")'];self.write('.governance/config.json',cfg)
        self.start();self.assertEqual(self.g.run_check('T001','unit')['exitCode'],125)
    def test_stale_evidence_after_edit(self):
        self.verified();(self.root/'src/code.py').write_text('value=2')
        with self.assertRaisesRegex(self.g.Rejected,'CURRENT_PASS_REQUIRED'):self.g.gate('T001')
    def test_self_review_rejected(self):
        self.verified()
        with self.assertRaisesRegex(self.g.Rejected,'INDEPENDENT_REVIEW'):self.g.review('T001','agent:builder','APPROVED','review1')
    def test_no_review_no_gate(self):
        self.verified()
        with self.assertRaisesRegex(self.g.Rejected,'CURRENT_INDEPENDENT_REVIEW'):self.g.gate('T001')
    def test_valid_review_finish(self):
        claim=self.start();self.g.run_check('T001','unit');self.g.review('T001','agent:reviewer','APPROVED','report1')
        self.assertEqual(self.g.gate('T001')['status'],'PASS');self.assertEqual(self.g.finish('T001',claim['token'])['state'],'DONE')
    def test_rejected_review_blocks(self):
        self.verified();self.g.review('T001','other','REJECTED','issues')
        with self.assertRaises(self.g.Rejected):self.g.gate('T001')
    def test_tampered_log_blocks(self):
        self.start();r=self.g.run_check('T001','unit');(self.root/r['log']).write_text('fake pass')
        with self.assertRaisesRegex(self.g.Rejected,'EVIDENCE_TAMPERED'):self.g.review('T001','other','APPROVED','x')
    def test_out_of_scope(self):
        self.start();(self.root/'unassigned.txt').write_text('bad')
        with self.assertRaisesRegex(self.g.Rejected,'OUT_OF_SCOPE'):self.g.run_check('T001','unit')
    def test_native_hook_denies_unclaimed_write(self):
        decision=self.h.decide({'conversationId':'s','toolCall':{'name':'write_to_file','args':{'TargetFile':str(self.root/'src/new.py')}}})
        self.assertEqual(decision['decision'],'deny')
    def test_native_hook_allows_scoped_claim(self):
        self.start()
        self.assertEqual(self.h.decide({'conversationId':'session1','toolCall':{'name':'write_to_file','args':{'TargetFile':str(self.root/'src/new.py')}}})['decision'],'allow')
    def test_native_hook_terminal_not_autoapproved(self):
        self.assertEqual(self.h.decide({'toolCall':{'name':'run_command','args':{'CommandLine':'python3 -c "print(1)"'}}})['decision'],'force_ask')
    def test_native_hook_control_change_review(self):
        self.assertEqual(self.h.decide({'toolCall':{'name':'write_to_file','args':{'TargetFile':str(self.root/'.agents/hooks.json')}}})['decision'],'force_ask')
    def test_redaction_known_secret(self):
        os.environ['TEST_SECRET']='some-long-private-value'
        try:self.assertNotIn('some-long-private-value',self.g.redact('some-long-private-value'))
        finally:del os.environ['TEST_SECRET']

    def test_review_stales_after_source_rerun(self):
        self.verified();self.g.review('T001','other','APPROVED','report')
        (self.root/'src/code.py').write_text('value=99')
        self.g.run_check('T001','unit')
        with self.assertRaisesRegex(self.g.Rejected,'CURRENT_INDEPENDENT_REVIEW'):self.g.gate('T001')
    def test_simultaneous_claim_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        self.g.approve('human:o','review')
        def attempt(i):
            try:self.g.claim('T001','agent:'+str(i),'s'+str(i));return 'won'
            except self.g.Rejected:return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(attempt,[1,2]))
        self.assertEqual(outcomes.count('won'),1)
    def test_hook_shell_chain_requires_review(self):
        self.assertEqual(h.decide({'toolCall':{'name':'run_command','args':{'CommandLine':'git status --short; python3 x.py'}}})['decision'],'force_ask')
    def test_hook_outside_workspace_denied(self):
        self.assertEqual(h.decide({'toolCall':{'name':'write_to_file','args':{'TargetFile':'/tmp/outside.py'}}})['decision'],'deny')
    def test_governance_files_validate_frontmatter(self):
        for path in (SOURCE/'.agents/rules').glob('*.md'):
            text=path.read_text();self.assertTrue(text.startswith('---\n'));self.assertIn('trigger:',text)
        hooks=json.loads((SOURCE/'.agents/hooks.json').read_text())
        self.assertIn('PreToolUse',hooks['closed-loop-write-guard'])

class InstallerTests(unittest.TestCase):
    def test_dry_run_and_collision(self):
        m=load(SOURCE/'tools/install.py','installer')
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a';b=Path(t)/'b';a.mkdir();b.mkdir();(a/'AGENTS.md').write_text('new')
            self.assertEqual(m.install(a,b)['written'],0);self.assertFalse((b/'AGENTS.md').exists())
            (b/'AGENTS.md').write_text('old');self.assertEqual(m.install(a,b,True)['status'],'CONFLICT');self.assertEqual((b/'AGENTS.md').read_text(),'old')

class V4UltraTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        SOURCE = Path(__file__).resolve().parents[1]
        for rel in ['.governance/bin/gov.py', '.governance/config.json', '.governance/tasks.json', '.governance/hooks/native_guard.py']:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / rel, dest)
        for rel in ['.specify/specs/01_CHARTER.md', '.specify/specs/02_ARCHITECTURE.md', '.specify/specs/03_ACCEPTANCE.md']:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('Spec test ' + rel)
        (self.root / 'src').mkdir()
        (self.root / 'src/code.py').write_text('value = 1\n')
        self.g = load(self.root / '.governance/bin/gov.py', 'gov_' + str(time.time_ns()))
        self.guard = load(self.root / '.governance/hooks/native_guard.py', 'guard_v4_' + str(time.time_ns()))
        self.guard.ROOT = self.root
        self.guard.gov = self.g
        cfg = self.g.config()
        cfg['checks'] = {'unit': {'argv': [sys.executable, '-c', 'print("actual test")'], 'timeout': 3}}
        cfg['required_release_checks'] = ['unit']
        cfg['max_parallel'] = 2
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': [{'id': 'T001', 'title': 'Task One', 'depends_on': [], 'allowed_paths': ['src'], 'checks': ['unit'], 'acceptance': ['AC1'], 'risk': 'low'}]}), encoding='utf-8')

    def tearDown(self):
        import gc
        gc.collect()
        self.tmp.cleanup()

    def test_discover_deep_and_reconstructed_spec(self):
        (self.root / 'src/app.py').write_text('@app.get("/api/v1/users")\ndef get_users(): pass\nclass User(BaseModel): pass\n')
        topo = self.g.discover(deep=True, write_files=True)
        self.assertIn('fragilityScore', topo)
        self.assertTrue((self.root / '.governance/inventory.json').is_file())
        self.assertTrue((self.root / '.governance/topology.json').is_file())
        self.assertTrue((self.root / 'specs/RECONSTRUCTED_SPEC.md').is_file())
        spec_text = (self.root / 'specs/RECONSTRUCTED_SPEC.md').read_text(encoding='utf-8')
        self.assertIn('RECONSTRUCTED SPECIFICATION', spec_text)
        self.assertIn('/api/v1/users', spec_text)

    def test_scaffold_contracts(self):
        (self.root / 'src/models.py').write_text('class Customer(BaseModel): pass\n')
        self.g.discover(deep=True, write_files=True)
        res = self.g.scaffold_contracts()
        self.assertEqual(res['status'], 'SCAFFOLDED')
        self.assertTrue((self.root / 'contracts/types.ts').is_file())
        self.assertTrue((self.root / 'contracts/models.py').is_file())
        self.assertTrue((self.root / 'contracts/openapi.json').is_file())

    def test_package_handoff_structure(self):
        self.g.approve('human:owner', 'test spec')
        packet = self.g.package_handoff('T001')
        self.assertEqual(packet['taskId'], 'T001')
        self.assertIn('allowedToWrite', packet['targetFiles'])
        self.assertTrue((self.root / '.governance/handoffs/T001.json').is_file())

    def test_golden_record_and_assert_masking(self):
        cmd1 = [sys.executable, '-c', 'print("UUID: 11111111-2222-3333-4444-555555555555 Date: 2026-11-02T10:00:00Z Status: PASS")']
        cmd2 = [sys.executable, '-c', 'print("UUID: 99999999-8888-7777-6666-000000000000 Date: 2026-11-03T18:30:15Z Status: PASS")']
        rec = self.g.golden_record('test_suite', cmd1)
        self.assertEqual(rec['status'], 'RECORDED')
        self.assertEqual(rec['exitCode'], 0)
        
        # Comparison with dynamic masked content must PASS
        assertion = self.g.golden_assert('test_suite', cmd2)
        self.assertEqual(assertion['status'], 'PASS')
        
        # Real behavioral difference must be caught
        cmd_diff = [sys.executable, '-c', 'print("UUID: 99999999-8888-7777-6666-000000000000 Date: 2026-11-03T18:30:15Z Status: FAIL")']
        assertion_fail = self.g.golden_assert('test_suite', cmd_diff)
        self.assertEqual(assertion_fail['status'], 'REGRESSION_DETECTED')
        self.assertIn('diff', assertion_fail)

    def test_auto_heal_cycles_and_rollback(self):
        self.g.approve('human:owner', 'test spec')
        self.g.claim('T001', 'agent:tester', 'sess1')
        
        # Modify file
        (self.root / 'src/code.py').write_text('value = 999\n')
        
        c1 = self.g.auto_heal('T001', 1, 'Hypothesis 1')
        self.assertEqual(c1['status'], 'IN_PROGRESS')
        self.assertEqual(c1['remainingCycles'], 2)
        
        c2 = self.g.auto_heal('T001', 2, 'Hypothesis 2')
        self.assertEqual(c2['remainingCycles'], 1)
        
        c3 = self.g.auto_heal('T001', 3, 'Hypothesis 3')
        self.assertEqual(c3['remainingCycles'], 0)
        
        # Cycle 4 -> Escalation & Rollback
        esc = self.g.auto_heal('T001', 4, 'Failed 3 times')
        self.assertEqual(esc['status'], 'ESCALATED')
        self.assertEqual(esc['action'], 'ROLLED_BACK')
        self.assertTrue((self.root / 'ESC_T001.md').is_file())
        
        # Verify rollback restored original code
        self.assertEqual((self.root / 'src/code.py').read_text(), 'value = 1\n')

    def test_integrate_and_release_gates(self):
        self.g.approve('human:owner', 'test spec')
        claim_res = self.g.claim('T001', 'agent:builder', 'sess1')
        self.g.run_check('T001', 'unit')
        self.g.review('T001', 'agent:reviewer', 'APPROVED', 'Audit passed')
        self.g.finish('T001', claim_res['token'])
        
        res_int = self.g.integrate('T001')
        self.assertEqual(res_int['status'], 'INTEGRATED')
        
        res_rel = self.g.release()
        self.assertEqual(res_rel['gateStatus'], 'G7_PASS_OPERATIONAL_RELEASE')
        self.assertTrue((self.root / '.governance/RELEASE_MANIFEST.json').is_file())

    def test_native_guard_handoff_isolation(self):
        self.g.approve('human:owner', 'test spec')
        self.g.claim('T001', 'agent:builder', 'sess1')
        
        # Package handoff restricting write to src/code.py
        h_packet = {
            'taskId': 'T001',
            'targetFiles': {
                'readOnly': ['contracts/types.ts'],
                'allowedToWrite': ['src/code.py']
            }
        }
        h_dir = self.root / '.governance/handoffs'
        h_dir.mkdir(parents=True, exist_ok=True)
        (h_dir / 'T001.json').write_text(json.dumps(h_packet), encoding='utf-8')
        
        
        # Write to src/code.py should be allowed
        res_ok = self.guard.decide({'conversationId': 'sess1', 'toolCall': {'name': 'write_to_file', 'args': {'TargetFile': str(self.root / 'src/code.py')}}})
        self.assertEqual(res_ok['decision'], 'allow')
        
        # Write to src/unauthorized.py should be denied by handoff scope
        res_denied = self.guard.decide({'conversationId': 'sess1', 'toolCall': {'name': 'write_to_file', 'args': {'TargetFile': str(self.root / 'src/unauthorized.py')}}})
        self.assertEqual(res_denied['decision'], 'deny')
        self.assertIn('Outside task handoff scope', res_denied['reason'])

class V5UltraOmniTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        SOURCE = Path(__file__).resolve().parents[1]
        for rel in ['.governance/bin/gov.py', '.governance/config.json', '.governance/tasks.json']:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / rel, dest)
        for rel in ['.specify/specs/01_CHARTER.md', '.specify/specs/02_ARCHITECTURE.md', '.specify/specs/03_ACCEPTANCE.md']:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('Spec test ' + rel)
        (self.root / 'src').mkdir()
        (self.root / 'src/service.py').write_text('class AuthService:\n    def authenticate(self, u, p):\n        return True\n')
        (self.root / 'src/controller.py').write_text('from service import AuthService\ndef login():\n    return AuthService().authenticate("u", "p")\n')
        (self.root / 'tests').mkdir(exist_ok=True)
        (self.root / 'tests/test_auth.py').write_text('import unittest\nfrom src.service import AuthService\nclass TestAuth(unittest.TestCase):\n    def test_auth(self):\n        self.assertTrue(AuthService().authenticate("a", "b"))\nif __name__ == "__main__": unittest.main()\n')
        
        self.g = load(self.root / '.governance/bin/gov.py', 'gov_' + str(time.time_ns()))
        cfg = self.g.config()
        cfg['checks'] = {'unit': {'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], 'timeout': 10}}
        cfg['required_release_checks'] = ['unit']
        cfg['max_parallel'] = 2
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': [{'id': 'T001', 'title': 'Auth Task', 'depends_on': [], 'allowed_paths': ['src/service.py'], 'checks': ['unit'], 'acceptance': ['AC-AUTH-01'], 'risk': 'low'}]}), encoding='utf-8')

    def tearDown(self):
        import gc
        gc.collect()
        self.tmp.cleanup()

    def test_index_symbols_and_calculate_impact(self):
        idx = self.g.index_symbols(write_db=True)
        self.assertGreater(idx['totalSymbols'], 0)
        
        impact = self.g.calculate_impact(target_file='src/service.py')
        self.assertEqual(impact['target'], 'src/service.py')
        self.assertIn('AuthService', impact['directSymbols'])
        self.assertIn('riskRating', impact)

    def test_package_handoff_includes_blast_radius(self):
        self.g.approve('human:owner', 'test spec')
        packet = self.g.package_handoff('T001')
        self.assertEqual(packet['taskId'], 'T001')
        self.assertIn('blastRadius', packet)
        self.assertIn('riskRating', packet['blastRadius'])

    def test_manage_worktree_lifecycle(self):
        self.g.approve('human:owner', 'test spec')
        self.g.package_handoff('T001')
        
        # 1. Create worktree
        wt = self.g.manage_worktree('T001', action='create')
        self.assertEqual(wt['status'], 'WORKTREE_READY')
        wt_path = self.root / wt['path']
        self.assertTrue(wt_path.is_dir())
        
        # 2. Modify file inside worktree
        target_in_wt = wt_path / 'src/service.py'
        if target_in_wt.is_file():
            target_in_wt.write_text('class AuthService:\n    def authenticate(self, u, p):\n        return "NEW_VAL"\n')
            
        # 3. Merge worktree
        merge_res = self.g.manage_worktree('T001', action='merge')
        self.assertEqual(merge_res['status'], 'WORKTREE_MERGED')
        self.assertIn('NEW_VAL', (self.root / 'src/service.py').read_text())

    def test_audit_tests_mutation_detection(self):
        self.g.approve('human:owner', 'test spec')
        
        # Real test should pass mutation audit
        audit = self.g.audit_tests('T001')
        self.assertEqual(audit['status'], 'AUDIT_PASS')
        self.assertEqual(audit['mutationsCaught'], 1)

    def test_generate_charter_and_trace_matrix(self):
        self.g.approve('human:owner', 'test spec')
        charter = self.g.generate_charter(out_dir='specs')
        self.assertEqual(charter['status'], 'CHARTER_GENERATED')
        for f in ['01_PRODUCT_REQUIREMENTS.md', '02_SYSTEM_ARCHITECTURE.md', '03_DATA_DICTIONARY.md', '04_DEPENDENCY_AND_IMPACT.md', '05_TRACEABILITY_MATRIX.md']:
            self.assertTrue((self.root / 'specs' / f).is_file())
            
        tm = self.g.trace_matrix(export_format='markdown')
        self.assertIn('TRACEABILITY MATRIX', tm['matrix'])
        self.assertIn('REQ-T001', tm['matrix'])

    def test_interlock_semantic_gate(self):
        self.g.approve('human:owner', 'test spec')
        il = self.g.interlock('T001')
        self.assertEqual(il['status'], 'INTERLOCK_PASS')
        self.assertEqual(il['task'], 'T001')


class V51StandardsEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        SOURCE = Path(__file__).resolve().parents[1]
        for rel in ['.governance/bin/gov.py', '.governance/config.json', '.governance/tasks.json']:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if (SOURCE / rel).is_file():
                shutil.copy2(SOURCE / rel, dest)
        for rel in ['.specify/specs/01_CHARTER.md', '.specify/specs/02_ARCHITECTURE.md', '.specify/specs/03_ACCEPTANCE.md']:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('Spec test ' + rel)
        (self.root / 'src').mkdir()
        (self.root / 'src/service.py').write_text('from dataclasses import dataclass\n\n@dataclass\nclass AuthReq:\n    u: str\n\ndef authenticate(req: AuthReq) -> bool:\n    return True\n')
        (self.root / 'tests').mkdir(exist_ok=True)
        (self.root / 'tests/test_service.py').write_text('import unittest\nfrom src.service import AuthReq, authenticate\nclass TestService(unittest.TestCase):\n    def test_auth(self) -> None:\n        self.assertTrue(authenticate(AuthReq("u")))\nif __name__ == "__main__": unittest.main()\n')
        
        self.g = load(self.root / '.governance/bin/gov.py', 'gov_' + str(time.time_ns()))
        cfg = self.g.config()
        cfg['checks'] = {'unit': {'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], 'timeout': 10}}
        cfg['required_release_checks'] = ['unit']
        cfg['max_parallel'] = 2
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': [{'id': 'T001', 'title': 'Auth Task', 'depends_on': [], 'allowed_paths': ['src/service.py'], 'checks': ['unit'], 'acceptance': ['AC-AUTH-01'], 'risk': 'low'}]}), encoding='utf-8')

    def tearDown(self):
        import gc
        gc.collect()
        self.tmp.cleanup()

    def test_naming_converters(self):
        self.assertEqual(self.g.to_pascal_case('process_payment'), 'ProcessPayment')
        self.assertEqual(self.g.to_pascal_case('ProcessPayment'), 'ProcessPayment')
        self.assertEqual(self.g.to_pascal_case('process-payment'), 'ProcessPayment')
        self.assertEqual(self.g.to_snake_case('ProcessPayment'), 'process_payment')
        self.assertEqual(self.g.to_snake_case('process_payment'), 'process_payment')

    def test_scaffold_unit_generates_7_invariants(self):
        res = self.g.scaffold_unit(name='PaymentProcessor', domain='billing', unit_type='service')
        self.assertEqual(res['status'], 'UNIT_SCAFFOLDED')
        self.assertEqual(res['unitName'], 'PaymentProcessor')
        
        impl_path = self.root / 'src/billing/payment_processor.py'
        test_path = self.root / 'tests/test_payment_processor.py'
        dict_path = self.root / 'specs/03_DATA_DICTIONARY.md'
        
        self.assertTrue(impl_path.is_file())
        self.assertTrue(test_path.is_file())
        self.assertTrue(dict_path.is_file())
        
        # Verify 7 invariants in implementation
        impl_text = impl_path.read_text(encoding='utf-8')
        self.assertIn('class PaymentProcessorError(Exception):', impl_text)
        self.assertIn('class PaymentProcessorRequest:', impl_text)
        self.assertIn('class PaymentProcessorResult:', impl_text)
        self.assertIn('def payment_processor(req: PaymentProcessorRequest) -> PaymentProcessorResult:', impl_text)
        self.assertIn('__all__', impl_text)
        
        # Verify dual test suite
        test_text = test_path.read_text(encoding='utf-8')
        self.assertIn('test_payment_processor_happy_path', test_text)
        self.assertIn('test_payment_processor_validation_failure', test_text)
        self.assertIn('assertRaises', test_text)
        
        # Verify data dictionary sync
        dict_text = dict_path.read_text(encoding='utf-8')
        self.assertIn('PaymentProcessor', dict_text)

    def test_check_standards_complies_clean_code(self):
        self.g.scaffold_unit(name='BillingService', domain='billing', unit_type='service')
        report = self.g.check_standards(file_path=str(self.root / 'src/billing/billing_service.py'))
        self.assertEqual(report['status'], 'STANDARDS_COMPLIANT')
        self.assertEqual(report['totalViolations'], 0)

    def test_check_standards_detects_violations(self):
        bad_code = """
def bad_func(a, b):
    try:
        res = a / b
    except:
        pass
    print("bad print debugging")
    return res
"""
        bad_path = self.root / 'src/bad.py'
        bad_path.write_text(bad_code, encoding='utf-8')
        
        report = self.g.check_standards(file_path=str(bad_path))
        self.assertEqual(report['status'], 'VIOLATIONS_FOUND')
        rules_triggered = {v['rule'] for v in report['violations']}
        self.assertIn('MISSING_RETURN_TYPE', rules_triggered)
        self.assertIn('MISSING_ARG_TYPE', rules_triggered)
        self.assertIn('BARE_EXCEPT_FORBIDDEN', rules_triggered)
        self.assertIn('FORBIDDEN_PATTERN', rules_triggered)

    def test_gate_rejects_standards_violations(self):
        self.g.approve('human:owner', 'test spec')
        claim = self.g.claim('T001', 'agent:builder', 'sess1')
        
        # Inject substandard function into allowed path src/service.py
        bad_service = """from dataclasses import dataclass

@dataclass
class AuthReq:
    u: str

def authenticate(req: AuthReq) -> bool:
    print("unauthorized debug log")
    return True
"""
        (self.root / 'src/service.py').write_text(bad_service, encoding='utf-8')
        self.g.run_check('T001', 'unit')
        self.g.review('T001', 'agent:reviewer', 'APPROVED', 'lgtm')
        
        # Gate must reject due to standards violation
        with self.assertRaisesRegex(self.g.Rejected, 'STANDARDS_VIOLATION'):
            self.g.gate('T001')

    def test_validate_rejects_empty_standards_checklist(self):
        tasks = self.g.definitions()
        tasks[0]['standards_checklist'] = []
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')
        
        with self.assertRaisesRegex(self.g.Rejected, 'STANDARDS_CHECKLIST_EMPTY'):
            self.g.validate()


class V6CadreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in ['.governance/bin/gov.py', '.governance/config.json', '.governance/tasks.json']:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / rel, dest)
        if (SOURCE / '.governance/registry').is_dir():
            shutil.copytree(SOURCE / '.governance/registry', self.root / '.governance/registry')

        (self.root / '.specify/specs').mkdir(parents=True, exist_ok=True)
        for sf in ['01_CHARTER.md', '02_ARCHITECTURE.md', '03_ACCEPTANCE.md']:
            (self.root / '.specify/specs' / sf).write_text('spec content', encoding='utf-8')
        (self.root / 'specs/blueprints').mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / 'specs/blueprints/checkout.blueprint.json', self.root / 'specs/blueprints/checkout.blueprint.json')
        (self.root / 'src').mkdir(parents=True, exist_ok=True)
        (self.root / 'tests').mkdir(parents=True, exist_ok=True)

        gov_path = self.root / '.governance/bin/gov.py'
        spec = importlib.util.spec_from_file_location(f"gov_v6_{time.time_ns()}", str(gov_path))
        self.g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.g)

        cfg = self.g.config()
        cfg['checks']['unit'] = {'argv': [sys.executable, '-c', 'print("ok")'], 'timeout': 5}
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')

    def tearDown(self):
        del self.g
        gc.collect()
        self.tmp.cleanup()

    def test_cadre_registry_loading(self):
        reg = self.g.registry_data()
        self.assertIn('OrderSummary', reg['components'])
        self.assertIn('PaymentForm', reg['components'])
        self.assertIn('vendor.stripe-js', reg['assets'])
        self.assertEqual(reg['taxonomy']['default_css_prefix'], 'cw-')

    def test_cadre_scaffold_page(self):
        res = self.g.scaffold_page('checkout')
        self.assertEqual(res['status'], 'PAGE_SCAFFOLDED')
        target = self.root / res['filePath']
        self.assertTrue(target.is_file())
        content = target.read_text(encoding='utf-8')
        self.assertIn('OrderSummary', content)
        self.assertIn('PaymentForm', content)
        self.assertIn('useCheckoutStore', content)
        self.assertIn('cw-checkout-container', content)

    def test_cadre_check_templates_clean(self):
        self.g.scaffold_page('checkout')
        audit = self.g.check_templates(file_path=str(self.root / 'src/pages/CheckoutPage.tsx'))
        self.assertEqual(audit['status'], 'TEMPLATES_COMPLIANT')
        self.assertEqual(audit['totalViolations'], 0)

    def test_cadre_check_templates_detects_violations(self):
        dirty_code = """import React, { FC } from 'react';

export const CheckoutPage: FC = () => {
  return (
    <div className="bad_container">
      <OrderSummary items={[]} currency="PLN" totalAmount={100} />
    </div>
  );
};
"""
        dirty_path = self.root / 'src/pages/CheckoutPage.tsx'
        dirty_path.parent.mkdir(parents=True, exist_ok=True)
        dirty_path.write_text(dirty_code, encoding='utf-8')

        audit = self.g.check_templates(file_path=str(dirty_path))
        self.assertEqual(audit['status'], 'VIOLATIONS_FOUND')
        rules = {v['rule'] for v in audit['violations']}
        self.assertIn('MISSING_COMPONENT_IMPORT', rules)
        self.assertIn('TAXONOMY_CSS_VIOLATION', rules)

    def test_cadre_wire_template(self):
        dirty_code = """import React, { FC } from 'react';

export const CheckoutPage: FC = () => {
  return (
    <div className="cw-container">
      <OrderSummary items={[]} currency="PLN" totalAmount={100} />
    </div>
  );
};
"""
        dirty_path = self.root / 'src/pages/CheckoutPage.tsx'
        dirty_path.parent.mkdir(parents=True, exist_ok=True)
        dirty_path.write_text(dirty_code, encoding='utf-8')

        wire_res = self.g.wire_template(str(dirty_path))
        self.assertEqual(wire_res['status'], 'TEMPLATE_WIRED')
        self.assertGreaterEqual(wire_res['injectedCount'], 1)

        # Re-check should now be clean
        audit = self.g.check_templates(file_path=str(dirty_path))
        self.assertEqual(audit['status'], 'TEMPLATES_COMPLIANT')

    def test_cadre_scaffold_woocommerce_php(self):
        # Create a woocommerce blueprint
        woo_bp = {
            "$schema": "./page.blueprint.schema.json",
            "pageId": "pages.cart",
            "title": "Koszyk WooCommerce",
            "targetFile": "templates/page-cart.php",
            "adapter": "woocommerce",
            "taxonomy": {
                "cssPrefix": "cw-woo-"
            },
            "slots": {
                "cart_items": {
                    "order": 1,
                    "components": [
                        { "component": "CartTable", "templatePart": "template-parts/cart-table" }
                    ]
                }
            }
        }
        bp_path = self.root / 'specs/blueprints/cart.blueprint.json'
        bp_path.write_text(json.dumps(woo_bp), encoding='utf-8')

        # Test scaffolding with positional blueprint argument
        res = self.g.scaffold_page('cart')
        self.assertEqual(res['status'], 'PAGE_SCAFFOLDED')
        self.assertEqual(res['adapter'], 'woocommerce')
        self.assertEqual(res['filePath'], 'templates/page-cart.php')

        target = self.root / res['filePath']
        self.assertTrue(target.is_file())
        content = target.read_text(encoding='utf-8')
        self.assertIn("defined('ABSPATH') || exit;", content)
        self.assertIn("get_header();", content)
        self.assertIn("get_footer();", content)
        self.assertIn("cw-woo-container", content)
        self.assertIn("get_template_part('template-parts/cart-table')", content)

        # Audit PHP template: static and dynamic classes shouldn't trigger false positives
        audit = self.g.check_templates(file_path=str(target))
        self.assertEqual(audit['status'], 'TEMPLATES_COMPLIANT')
        self.assertEqual(audit['totalViolations'], 0)

    def test_cadre_check_templates_php_sanitization(self):
        # PHP file with dynamic tags in class attributes
        php_content = """<?php
defined('ABSPATH') || exit;
?>
<div class="<?php echo esc_attr('cw-container'); ?> <?= 'cw-active' ?>">
  <section class="cw-content">
    <p>Content</p>
  </section>
</div>
"""
        tpl_dir = self.root / 'templates'
        tpl_dir.mkdir(parents=True, exist_ok=True)
        php_file = tpl_dir / 'page-custom.php'
        php_file.write_text(php_content, encoding='utf-8')

        audit = self.g.check_templates(file_path=str(php_file))
        self.assertEqual(audit['status'], 'TEMPLATES_COMPLIANT')
        self.assertEqual(audit['totalViolations'], 0)

    def test_cadre_scaffold_direct_path_and_case_insensitivity(self):
        # Resolve via direct path
        res1 = self.g.scaffold_page('specs/blueprints/checkout.blueprint.json')
        self.assertEqual(res1['status'], 'PAGE_SCAFFOLDED')

        # Resolve case-insensitively
        res2 = self.g.scaffold_page('CHECKOUT')
        self.assertEqual(res2['status'], 'PAGE_SCAFFOLDED')

    def test_gate_rejects_template_violations(self):
        # Configure task allowed paths to include src/pages
        tasks = self.g.definitions()
        tasks[0]['allowed_paths'] = ['src/pages', 'tests']
        tasks[0]['checks'] = ['unit']
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')

        self.g.approve('human:owner', 'test spec')
        claim = self.g.claim('T001', 'agent:builder', 'sess1')

        # Inject dirty template into allowed path
        dirty_page = """import React, { FC } from 'react';

export const CheckoutPage: FC = () => {
  return <OrderSummary />;
};
"""
        (self.root / 'src/pages/CheckoutPage.tsx').parent.mkdir(parents=True, exist_ok=True)
        (self.root / 'src/pages/CheckoutPage.tsx').write_text(dirty_page, encoding='utf-8')

        self.g.run_check('T001', 'unit')
        self.g.review('T001', 'agent:reviewer', 'APPROVED', 'lgtm')

        with self.assertRaisesRegex(self.g.Rejected, 'TEMPLATE_VIOLATION'):
            self.g.gate('T001')

class V65SynapseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in ['.governance/bin/gov.py', '.governance/config.json', '.governance/tasks.json']:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / rel, dest)
        if (SOURCE / '.governance/registry').is_dir():
            shutil.copytree(SOURCE / '.governance/registry', self.root / '.governance/registry')

        (self.root / '.specify/specs').mkdir(parents=True, exist_ok=True)
        for sf in ['01_CHARTER.md', '02_ARCHITECTURE.md', '03_ACCEPTANCE.md']:
            (self.root / '.specify/specs' / sf).write_text('spec content', encoding='utf-8')
        (self.root / 'specs').mkdir(parents=True, exist_ok=True)
        (self.root / 'specs/03_DATA_DICTIONARY.md').write_text('# Data Dictionary\n', encoding='utf-8')
        (self.root / 'src').mkdir(parents=True, exist_ok=True)
        (self.root / 'tests').mkdir(parents=True, exist_ok=True)

        gov_path = self.root / '.governance/bin/gov.py'
        spec = importlib.util.spec_from_file_location(f"gov_v65_{time.time_ns()}", str(gov_path))
        self.g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.g)
        self.g.set_workspace_root(self.root)

        cfg = self.g.config()
        cfg['max_parallel'] = 4
        cfg['checks']['unit'] = {'argv': [sys.executable, '-c', 'print("ok")'], 'timeout': 5}
        cfg['checks']['framework-selftests'] = {'argv': [sys.executable, '-c', 'print("ok")'], 'timeout': 5}
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')

    def tearDown(self):
        del self.g
        gc.collect()
        self.tmp.cleanup()

    def test_synapse_tables_and_wal(self):
        c = self.g.db()
        try:
            mode = c.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), 'wal')
            tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            self.assertIn('symbol_leases', tables)
            self.assertIn('decision_mesh', tables)
            self.assertIn('contract_manifests', tables)
        finally:
            c.close()
            gc.collect()

    def test_synapse_triple_lock_symbol_collision(self):
        tasks = self.g.definitions()
        tasks[0]['symbols'] = ['AuthTokenValidator']
        tasks[0]['allowed_paths'] = ['src/auth_one.py']
        import copy
        task2 = copy.deepcopy(tasks[0])
        task2['id'] = 'T002'
        task2['depends_on'] = []
        task2['symbols'] = ['AuthTokenValidator']
        task2['allowed_paths'] = ['src/auth_two.py']
        tasks.append(task2)
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')

        self.g.approve('human:owner', 'test spec')
        c1 = self.g.claim(tasks[0]['id'], 'agent:builder-1', 'sess-1')
        self.assertIn('token', c1)

        with self.assertRaisesRegex(self.g.Rejected, 'RESOURCE_COLLISION: AST Symbol'):
            self.g.claim(task2['id'], 'agent:builder-2', 'sess-2')

    def test_synapse_triple_lock_route_collision(self):
        tasks = self.g.definitions()
        tasks[0]['routes'] = ['/api/v1/billing/charge']
        tasks[0]['allowed_paths'] = ['src/bill1.py']
        import copy
        task2 = copy.deepcopy(tasks[0])
        task2['id'] = 'T002'
        task2['depends_on'] = []
        task2['routes'] = ['/api/v1/billing/charge']
        task2['allowed_paths'] = ['src/bill2.py']
        tasks.append(task2)
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')

        self.g.approve('human:owner', 'test spec')
        self.g.claim(tasks[0]['id'], 'agent:builder-1', 'sess-1')

        with self.assertRaisesRegex(self.g.Rejected, 'RESOURCE_COLLISION: Route'):
            self.g.claim(task2['id'], 'agent:builder-2', 'sess-2')

    def test_synapse_scaffold_module(self):
        res = self.g.scaffold_module(name='payment_processor', domain='billing')
        self.assertEqual(res['status'], 'MODULE_SCAFFOLDED')
        self.assertEqual(res['domain'], 'billing')
        self.assertTrue((self.root / res['contractPath']).is_file())
        
        c = self.g.db()
        try:
            m = c.execute("SELECT * FROM contract_manifests WHERE contract_id=?", ('billing:payment_processor',)).fetchone()
            self.assertIsNotNone(m)
        finally:
            c.close()
            gc.collect()

        tasks = self.g.definitions()
        mod_task = next((t for t in tasks if t['id'] == res['taskId']), None)
        self.assertIsNotNone(mod_task)
        self.assertIn('/api/v1/billing/payment-processor', mod_task['routes'])

    def test_synapse_decision_mesh_and_context_slicing(self):
        adr_res = self.g.approve_decision(
            adr_id='ADR-0099',
            domain='billing',
            assertion='All monetary amounts must be stored as integers in minor currency units (cents).',
            scope='domain'
        )
        self.assertEqual(adr_res['status'], 'DECISION_APPROVED')
        self.assertTrue((self.root / 'docs/decisions/ADR-0099.md').is_file())

        tasks = self.g.definitions()
        tasks[0]['domain'] = 'billing'
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')
        self.g.approve('human:owner', 'test spec')

        handoff = self.g.package_handoff(tasks[0]['id'])
        self.assertEqual(handoff['status'], 'HANDOFF_GENERATED')
        self.assertIn('activeDecisions', handoff)
        adr_ids = [d['adrId'] for d in handoff['activeDecisions']]
        self.assertIn('ADR-0099', adr_ids)

    def test_synapse_cross_worktrees_interlock(self):
        tasks = self.g.definitions()
        tasks[0]['symbols'] = ['SharedEngine']
        tasks[0]['allowed_paths'] = ['src/shared.py']
        import copy
        task2 = copy.deepcopy(tasks[0])
        task2['id'] = 'T002'
        task2['depends_on'] = []
        task2['symbols'] = ['SharedEngine']
        task2['allowed_paths'] = ['src/other.py']
        tasks.append(task2)
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')
        self.g.approve('human:owner', 'test spec')

        c1 = self.g.claim(tasks[0]['id'], 'agent:builder-1', 'sess-1')
        
        with self.assertRaisesRegex(self.g.Rejected, 'CROSS_WORKTREE_SYMBOL_COLLISION'):
            self.g.interlock(task2['id'], cross_worktrees=True)

class V7EvidenceAndGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in ['.governance/bin/gov.py', '.governance/config.json', '.governance/tasks.json']:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / rel, dest)
        if (SOURCE / '.governance/registry').is_dir():
            shutil.copytree(SOURCE / '.governance/registry', self.root / '.governance/registry')

        (self.root / '.specify/specs').mkdir(parents=True, exist_ok=True)
        for sf in ['01_CHARTER.md', '02_ARCHITECTURE.md', '03_ACCEPTANCE.md']:
            (self.root / '.specify/specs' / sf).write_text('spec content', encoding='utf-8')
        (self.root / 'specs').mkdir(parents=True, exist_ok=True)
        (self.root / 'specs/03_DATA_DICTIONARY.md').write_text('# Data Dictionary\n| BillingModule | core | | | |\n', encoding='utf-8')
        (self.root / 'src').mkdir(parents=True, exist_ok=True)
        (self.root / 'tests').mkdir(parents=True, exist_ok=True)
        (self.root / 'src/billing_module.py').write_text('def process() -> None:\n    pass\n', encoding='utf-8')
        (self.root / 'tests/test_billing_module.py').write_text('import unittest\nclass T(unittest.TestCase):\n  def test_1(self): pass\n', encoding='utf-8')

        gov_path = self.root / '.governance/bin/gov.py'
        spec = importlib.util.spec_from_file_location(f"gov_v7_{time.time_ns()}", str(gov_path))
        self.g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.g)

        cfg = self.g.config()
        cfg['checks']['unit'] = {'argv': [sys.executable, '-c', 'print("ok")'], 'timeout': 5}
        cfg['checks']['framework-selftests'] = {'argv': [sys.executable, '-c', 'print("ok")'], 'timeout': 5}
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')

    def tearDown(self):
        del self.g
        gc.collect()
        self.tmp.cleanup()

    def test_g4_standards_evidence_emission(self):
        # Create valid python unit
        (self.root / 'src/billing_module.py').write_text('def process() -> None:\n    pass\n', encoding='utf-8')
        (self.root / 'tests/test_billing_module.py').write_text('import unittest\nclass T(unittest.TestCase):\n  def test_1(self): pass\n', encoding='utf-8')

        tasks = self.g.definitions()
        tasks[0]['allowed_paths'] = ['src/billing_module.py', 'tests/test_billing_module.py']
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')

        rep = self.g.check_standards(task_id=tasks[0]['id'])
        self.assertIn('evidence', rep)
        ev_p = self.root / rep['evidence']
        self.assertTrue(ev_p.is_file())
        self.assertIn('G4_STANDARDS', ev_p.read_text(encoding='utf-8'))

    def test_g5_review_evidence_emission_and_gate_pass(self):
        tasks = self.g.definitions()
        tasks[0]['allowed_paths'] = ['src', 'tests']
        tasks[0]['checks'] = ['unit']
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')

        self.g.approve('human:owner', 'test spec')
        claim = self.g.claim(tasks[0]['id'], 'agent:builder', 'sess1')
        self.g.run_check(tasks[0]['id'], 'unit')

        rev_res = self.g.review(tasks[0]['id'], 'agent:reviewer', 'APPROVED', 'lgtm')
        self.assertIn('evidence', rev_res)
        self.assertTrue((self.root / rev_res['evidence']).is_file())

        gate_res = self.g.gate(tasks[0]['id'])
        self.assertEqual(gate_res['status'], 'PASS')
        self.assertIn('gateCertificate', gate_res)
        cert_p = self.root / gate_res['gateCertificate']
        self.assertTrue(cert_p.is_file())
        self.assertIn('GATE_PASS_CERTIFICATE', cert_p.read_text(encoding='utf-8'))

    def test_prune_evidence_retention(self):
        tasks = self.g.definitions()
        tasks[0]['allowed_paths'] = ['src', 'tests']
        tasks[0]['checks'] = ['unit']
        (self.root / '.governance/tasks.json').write_text(json.dumps({'version': 1, 'tasks': tasks}), encoding='utf-8')

        self.g.approve('human:owner', 'test spec')
        self.g.claim(tasks[0]['id'], 'agent:builder', 'sess1')

        # Run check 6 times
        for _ in range(6):
            self.g.run_check(tasks[0]['id'], 'unit')

        prune_res = self.g.prune_evidence(keep_last=3)
        self.assertEqual(prune_res['status'], 'PRUNED')
        self.assertGreaterEqual(prune_res['removedFiles'], 3)
        self.assertEqual(prune_res['retainedRecords'], 3)

    def test_data_dictionary_unsynchronized_detection(self):
        # Module defines __all__ with unknown symbol missing in specs/03_DATA_DICTIONARY.md
        dirty_code = '__all__ = ["GhostPaymentService"]\n'
        (self.root / 'src/ghost_module.py').write_text(dirty_code, encoding='utf-8')
        rep = self.g.check_standards(file_path=str(self.root / 'src/ghost_module.py'))
        self.assertEqual(rep['status'], 'VIOLATIONS_FOUND')
        rules = [v['rule'] for v in rep['violations']]
        self.assertIn('UNSYNCHRONIZED_DATA_DICTIONARY', rules)


class V75NativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / '.governance/bin').mkdir(parents=True, exist_ok=True)
        (self.root / '.governance/hooks').mkdir(parents=True, exist_ok=True)
        (self.root / '.agents/rules').mkdir(parents=True, exist_ok=True)
        (self.root / '.agents/learning_inbox').mkdir(parents=True, exist_ok=True)
        (self.root / '.agents/skills').mkdir(parents=True, exist_ok=True)

        shutil.copy2(SOURCE / '.governance/bin/gov.py', self.root / '.governance/bin/gov.py')
        shutil.copy2(SOURCE / '.governance/config.json', self.root / '.governance/config.json')
        shutil.copy2(SOURCE / '.governance/tasks.json', self.root / '.governance/tasks.json')
        shutil.copy2(SOURCE / '.governance/standards.json', self.root / '.governance/standards.json')
        (self.root / '.specify/specs').mkdir(parents=True, exist_ok=True)
        for sf in ['01_CHARTER.md', '02_ARCHITECTURE.md', '03_ACCEPTANCE.md']:
            (self.root / '.specify/specs' / sf).write_text('spec content', encoding='utf-8')

        gov_path = self.root / '.governance/bin/gov.py'
        spec = importlib.util.spec_from_file_location(f"gov_v75_{time.time_ns()}", str(gov_path))
        self.g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.g)

    def tearDown(self):
        del self.g
        gc.collect()
        self.tmp.cleanup()

    def test_check_rules_no_candidates(self):
        res = self.g.check_rules()
        self.assertEqual(res['status'], 'NO_CANDIDATES')
        self.assertEqual(res['count'], 0)

    def test_check_rules_validation_and_rejection(self):
        inbox = self.root / '.agents/learning_inbox'
        good = inbox / 'good.candidate.md'
        good.write_text('---\ntrigger: model_decision\ndescription: "Good rule description"\n---\n# Rule\nDo proper checks.\n', encoding='utf-8')
        bad = inbox / 'bad.candidate.md'
        bad.write_text('---\ntrigger: model_decision\ndescription: "Bad rule description"\n---\n# Bad Rule\nAlways bypass_review.\n', encoding='utf-8')

        res = self.g.check_rules()
        self.assertEqual(res['status'], 'VIOLATIONS_FOUND')
        self.assertEqual(res['count'], 2)
        statuses = {r['file']: r['status'] for r in res['results']}
        self.assertEqual(statuses['good.candidate.md'], 'APPROVED_FOR_PROMOTION')
        self.assertEqual(statuses['bad.candidate.md'], 'REJECTED')

    def test_approve_rule_promotes_and_creates_evidence(self):
        inbox = self.root / '.agents/learning_inbox'
        cand = inbox / 'performance-cache.candidate.md'
        cand.write_text('---\ntrigger: model_decision\ndescription: "Cache rule description"\n---\n# Cache Rule\nUse Redis caching.\n', encoding='utf-8')

        res = self.g.approve_rule('performance-cache.candidate.md')
        self.assertEqual(res['status'], 'RULE_PROMOTED')
        dest_rule = self.root / '.agents/rules/performance-cache.md'
        self.assertTrue(dest_rule.is_file())
        self.assertFalse(cand.exists())

        ev_file = self.root / res['evidence']
        self.assertTrue(ev_file.is_file())
        self.assertIn('G_LEARN_RULE_PROMOTION', ev_file.read_text(encoding='utf-8'))

    def test_worktree_passthrough_mode(self):
        # Lock 2: Enforced Worktree Sandboxing - passthrough bypass eliminated; physical worktree required
        old_val = os.environ.get('ANTIGRAVITY_WORKSPACE_MODE')
        os.environ['ANTIGRAVITY_WORKSPACE_MODE'] = 'share'
        try:
            res = self.g.manage_worktree('T001', action='create')
            self.assertEqual(res['status'], 'WORKTREE_READY')
            self.assertTrue((self.root / res['path']).is_dir())
        finally:
            if old_val is None:
                os.environ.pop('ANTIGRAVITY_WORKSPACE_MODE', None)
            else:
                os.environ['ANTIGRAVITY_WORKSPACE_MODE'] = old_val

    def test_db_gov_state_path_env(self):
        custom_db_dir = self.root / 'custom_state'
        custom_db = custom_db_dir / 'my_state.sqlite'
        old_env = os.environ.get('GOV_STATE_PATH')
        os.environ['GOV_STATE_PATH'] = str(custom_db)
        try:
            c = self.g.db()
            self.assertTrue(custom_db.is_file())
            c.close()
        finally:
            if old_env is None:
                os.environ.pop('GOV_STATE_PATH', None)
            else:
                os.environ['GOV_STATE_PATH'] = old_env

class V8MultiWorkspaceAndPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Create minimal framework repo structure
        (self.root / '.governance/bin').mkdir(parents=True, exist_ok=True)
        (self.root / '.governance/state').mkdir(parents=True, exist_ok=True)
        (self.root / '.governance/evidence').mkdir(parents=True, exist_ok=True)
        (self.root / '.governance/handoffs').mkdir(parents=True, exist_ok=True)
        (self.root / '.agents/hooks').mkdir(parents=True, exist_ok=True)
        (self.root / '.agents/rules').mkdir(parents=True, exist_ok=True)
        (self.root / 'tools').mkdir(parents=True, exist_ok=True)
        (self.root / 'specs').mkdir(parents=True, exist_ok=True)
        (self.root / 'specs/01_CHARTER.md').write_text('# Charter\n', encoding='utf-8')
        (self.root / 'specs/02_ARCHITECTURE.md').write_text('# Arch\n', encoding='utf-8')
        (self.root / 'specs/03_ACCEPTANCE.md').write_text('# Acc\n', encoding='utf-8')
        (self.root / 'AGENTS.md').write_text('# AGENTS\n', encoding='utf-8')

        cfg = {
            'profile': 'standard',
            'spec_files': ['specs/01_CHARTER.md', 'specs/02_ARCHITECTURE.md', 'specs/03_ACCEPTANCE.md'],
            'max_parallel': 2,
            'lease_seconds': 1800,
            'protected_paths': ['.governance', '.agents', 'specs'],
            'checks': {'unit': {'argv': ['python', '-c', 'import sys; sys.exit(0)'], 'timeout': 30}},
            'required_release_checks': ['unit']
        }
        (self.root / '.governance/config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        tasks = {
            'version': 1,
            'tasks': [
                {'id': 'T001', 'title': 'Test task', 'depends_on': [], 'allowed_paths': ['src/app.py'], 'checks': ['unit'], 'acceptance': ['works']}
            ]
        }
        (self.root / '.governance/tasks.json').write_text(json.dumps(tasks, indent=2), encoding='utf-8')
        (self.root / 'src').mkdir(exist_ok=True)
        (self.root / 'src/app.py').write_text('print("hello")\n', encoding='utf-8')

        # Load gov.py
        gov_src = SOURCE / '.governance/bin/gov.py'
        (self.root / '.governance/bin/gov.py').write_text(gov_src.read_text(encoding='utf-8'), encoding='utf-8')
        spec = importlib.util.spec_from_file_location('gov', self.root / '.governance/bin/gov.py')
        self.g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.g)
        self.g.set_workspace_root(self.root)

    def tearDown(self):
        import gc
        gc.collect()
        self.tmp.cleanup()

    def test_file_stat_cache_sub_second_performance(self):
        # Generate 100 test files
        for i in range(100):
            (self.root / f'src/module_{i}.py').write_text(f'def func_{i}(): pass\n', encoding='utf-8')

        t0 = time.time()
        snap1 = self.g.snapshot()
        t_first = time.time() - t0

        t1 = time.time()
        snap2 = self.g.snapshot()
        t_cached = time.time() - t1

        self.assertEqual(snap1, snap2)
        # Cached snapshot should be lightning fast (< 200 ms)
        self.assertLess(t_cached, 0.5)

        # Modify one file and check that snapshot changes
        (self.root / 'src/module_42.py').write_text('def func_42_modified(): pass\n', encoding='utf-8')
        snap3 = self.g.snapshot()
        self.assertNotEqual(snap1, snap3)

    def test_package_handoff_includes_workspace_context(self):
        self.g.validate()
        h = self.g.package_handoff('T001')
        self.assertEqual(h['status'], 'HANDOFF_GENERATED')
        self.assertIn('workspaceContext', h)
        self.assertEqual(h['workspaceContext']['boundaryPolicy'], 'STRICT_HERMETIC')
        self.assertIn(str(self.root).replace('\\', '/'), h['workspaceContext']['workspaceRoot'])

    def test_workspace_resolver_get_and_boundary(self):
        ws_tool = Path(__file__).resolve().parents[1] / 'tools' / 'workspace_resolver.py'
        spec = importlib.util.spec_from_file_location('ws_res', ws_tool)
        res_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(res_mod)

        # Create multi-project workspace subdirs
        ws_dir = self.root / 'workspace'
        p1 = ws_dir / 'subproject_alpha'
        p2 = ws_dir / 'subproject_beta'
        p1.mkdir(parents=True)
        p2.mkdir(parents=True)
        (p1 / 'package.json').write_text('{}', encoding='utf-8')
        (p2 / 'package.json').write_text('{}', encoding='utf-8')

        # Test set and get active workspace
        res_mod.set_active_workspace('subproject_alpha', repo_root=self.root)
        active = res_mod.get_active_workspace(repo_root=self.root)
        self.assertEqual(active, p1.resolve())

        # Test boundary enforcement inside workspace
        valid_path = str(p1 / 'src/index.ts')
        self.assertEqual(res_mod.enforce_boundary(valid_path, active), Path(valid_path).resolve())

        # Test boundary violation escaping workspace
        invalid_path = str(p2 / 'src/index.ts')
        with self.assertRaises(RuntimeError) as ctx:
            res_mod.enforce_boundary(invalid_path, active)
        self.assertIn('HERMETIC_BOUNDARY_VIOLATION', str(ctx.exception))

    def test_native_guard_rejects_boundary_escapes(self):
        ng_src = Path(__file__).resolve().parents[1] / '.governance' / 'hooks' / 'native_guard.py'
        spec_ng = importlib.util.spec_from_file_location('ng_test', ng_src)
        ng = importlib.util.module_from_spec(spec_ng)
        spec_ng.loader.exec_module(ng)

        # Set ROOT in guard to subproject
        p1 = self.root / 'workspace/subproject_alpha'
        p1.mkdir(parents=True, exist_ok=True)
        ng.ROOT = p1

        # Attempt to write outside active workspace
        payload_escaping = {
            'toolCall': {
                'name': 'write_file',
                'args': {'Path': str(self.root / 'workspace/subproject_beta/leak.ts'), 'Content': 'exploit'}
            }
        }
        res = ng.decide(payload_escaping)
        self.assertEqual(res['decision'], 'deny')
        self.assertIn('HERMETIC_BOUNDARY_VIOLATION', res['reason'])

class SecurityLocksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / '.governance/bin').mkdir(parents=True, exist_ok=True)
        (self.root / '.governance/hooks').mkdir(parents=True, exist_ok=True)
        (self.root / '.governance/state').mkdir(parents=True, exist_ok=True)
        (self.root / '.governance/evidence').mkdir(parents=True, exist_ok=True)
        (self.root / '.specify/specs').mkdir(parents=True, exist_ok=True)
        (self.root / 'src').mkdir(parents=True, exist_ok=True)
        (self.root / 'tests').mkdir(parents=True, exist_ok=True)

        for rel in ['.governance/bin/gov.py', '.governance/config.json', '.governance/tasks.json', '.governance/hooks/native_guard.py']:
            shutil.copy2(SOURCE / rel, self.root / rel)
        for rel in ['.specify/specs/01_CHARTER.md', '.specify/specs/02_ARCHITECTURE.md', '.specify/specs/03_ACCEPTANCE.md']:
            (self.root / rel).write_text('Spec test ' + rel, encoding='utf-8')
        (self.root / 'specs').mkdir(parents=True, exist_ok=True)
        (self.root / 'specs/03_DATA_DICTIONARY.md').write_text('# Data Dictionary\n| SampleModule | core | | | |\n', encoding='utf-8')
        (self.root / 'src/sample_module.py').write_text('def sample_module() -> None:\n    pass\n', encoding='utf-8')
        (self.root / 'tests/test_sample_module.py').write_text('import unittest\nfrom src.sample_module import sample_module\nclass T(unittest.TestCase):\n  def test_1(self): pass\n', encoding='utf-8')

        gov_path = self.root / '.governance/bin/gov.py'
        self.g = load(gov_path, f"gov_sec_{time.time_ns()}")
        self.g.set_workspace_root(self.root)

        ng_path = self.root / '.governance/hooks/native_guard.py'
        self.h = load(ng_path, f"guard_sec_{time.time_ns()}")
        self.h.ROOT = self.root
        self.h.gov = self.g

        cfg = self.g.config()
        cfg['checks']['unit'] = {'argv': [sys.executable, '-c', 'print("ok")'], 'timeout': 5}
        cfg['required_release_checks'] = ['unit']
        cfg['max_parallel'] = 2
        (self.root / '.governance/config.json').write_text(json.dumps(cfg), encoding='utf-8')

        tasks = {'version': 1, 'tasks': [{'id': 'T001', 'title': 'Sec Task', 'depends_on': [], 'allowed_paths': ['src/sample_module.py', 'tests/test_sample_module.py'], 'checks': ['unit'], 'acceptance': ['AC1'], 'risk': 'low'}]}
        (self.root / '.governance/tasks.json').write_text(json.dumps(tasks), encoding='utf-8')

        self.saved_env = {
            'GOV_REVIEWER_SESSION': os.environ.get('GOV_REVIEWER_SESSION'),
            'GOV_AUDITOR_TOKEN': os.environ.get('GOV_AUDITOR_TOKEN'),
            'GOV_HUMAN_TOKEN': os.environ.get('GOV_HUMAN_TOKEN'),
            'CONVERSATION_ID': os.environ.get('CONVERSATION_ID'),
            'ANTIGRAVITY_SESSION_ID': os.environ.get('ANTIGRAVITY_SESSION_ID'),
            'SESSION_ID': os.environ.get('SESSION_ID'),
            'ANTIGRAVITY_WORKSPACE_MODE': os.environ.get('ANTIGRAVITY_WORKSPACE_MODE'),
            'GOV_WORKTREE_PASSTHROUGH': os.environ.get('GOV_WORKTREE_PASSTHROUGH'),
        }

    def tearDown(self):
        for k, v in self.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import gc
        gc.collect()
        self.tmp.cleanup()

    # --- Lock 1: Cryptographic Dual-Control & Session Binding ---
    def test_lock1_fraudulent_self_review_same_session_rejected(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'builder-session-alpha')
        self.g.run_check('T001', 'unit')

        with self.assertRaisesRegex(self.g.Rejected, 'FRAUDULENT_SELF_REVIEW_REJECTED'):
            self.g.review('T001', 'agent:reviewer', 'APPROVED', 'lgtm',
                          reviewer_session='builder-session-alpha',
                          auditor_token='secret-token-xyz')

    def test_lock1_fraudulent_self_review_same_llm_session_rejected(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'shared-llm-session-99')
        self.g.run_check('T001', 'unit')

        os.environ['CONVERSATION_ID'] = 'shared-llm-session-99'
        with self.assertRaisesRegex(self.g.Rejected, 'FRAUDULENT_SELF_REVIEW_REJECTED'):
            self.g.review('T001', 'agent:reviewer', 'APPROVED', 'lgtm',
                          reviewer_session='different-session',
                          auditor_token='secret-token-xyz')

    def test_lock1_fraudulent_self_review_missing_auditor_token_rejected(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'builder-session-alpha')
        self.g.run_check('T001', 'unit')

        os.environ.pop('GOV_AUDITOR_TOKEN', None)
        with self.assertRaisesRegex(self.g.Rejected, 'FRAUDULENT_SELF_REVIEW_REJECTED'):
            self.g.review('T001', 'agent:reviewer', 'APPROVED', 'lgtm',
                          reviewer_session='independent-auditor-session',
                          auditor_token='')

    def test_lock1_unauthorized_human_impersonation_rejected(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'builder-session-alpha')
        self.g.run_check('T001', 'unit')

        os.environ.pop('GOV_HUMAN_TOKEN', None)
        with self.assertRaisesRegex(self.g.Rejected, 'UNAUTHORIZED_HUMAN_IMPERSONATION'):
            self.g.review('T001', 'human:impostor', 'APPROVED', 'human approval')

    def test_lock1_authorized_independent_agent_and_human_review(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'builder-session-alpha')
        self.g.run_check('T001', 'unit')

        rev = self.g.review('T001', 'agent:auditor-lead', 'APPROVED', 'independent audit passed',
                            reviewer_session='independent-auditor-sess-1',
                            auditor_token='test-auditor-token-secret')
        self.assertTrue(rev['identityVerified'])

        c = self.g.db()
        try:
            r = c.execute("SELECT identity_verified, reviewer_session FROM reviews WHERE task='T001'").fetchone()
            self.assertEqual(r['identity_verified'], 1)
            self.assertEqual(r['reviewer_session'], 'independent-auditor-sess-1')
        finally:
            c.close()

        gate_res = self.g.gate('T001')
        self.assertEqual(gate_res['status'], 'PASS')

        os.environ['GOV_HUMAN_TOKEN'] = 'secret-human-authorized-token'
        rev_human = self.g.review('T001', 'human:tech-lead', 'APPROVED', 'verified by tech lead')
        self.assertTrue(rev_human['identityVerified'])

    def test_lock1_gate_failed_when_identity_unverified(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'builder-session-alpha')
        self.g.run_check('T001', 'unit')

        self.g.review('T001', 'agent:reviewer', 'APPROVED', 'audit passed',
                      reviewer_session='independent-auditor-sess',
                      auditor_token='test-auditor-token-secret')

        c = self.g.db()
        try:
            c.execute("UPDATE reviews SET identity_verified = 0 WHERE task='T001'")
            c.commit()
        finally:
            c.close()

        with self.assertRaisesRegex(self.g.Rejected, 'GATE_FAILED: Independent review identity unverified'):
            self.g.gate('T001')

    # --- Lock 2: Enforced Worktree Sandboxing ---
    def test_lock2_enforced_worktree_physical_isolation(self):
        os.environ['ANTIGRAVITY_WORKSPACE_MODE'] = 'share'
        os.environ['GOV_WORKTREE_PASSTHROUGH'] = '1'

        wt_res = self.g.manage_worktree('T001', action='create')
        self.assertEqual(wt_res['status'], 'WORKTREE_READY')
        wt_dir = self.root / wt_res['path']
        self.assertTrue(wt_dir.is_dir())
        self.assertTrue('.worktrees' in wt_res['path'] or '.shadow_worktrees' in wt_res['path'])

    def test_lock2_verify_task_requires_physical_worktree(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'builder-session-alpha')
        self.g.manage_worktree('T001', action='create')

        c = self.g.db()
        try:
            wt_row = c.execute('SELECT worktree_path FROM worktrees WHERE task="T001"').fetchone()
            self.assertIsNotNone(wt_row)
            wt_path = self.root / wt_row['worktree_path']
            if wt_path.exists():
                shutil.rmtree(wt_path)

            with self.assertRaisesRegex(self.g.Rejected, 'ENFORCED_WORKTREE_REQUIRED'):
                self.g.verify_task(c, 'T001')
        finally:
            c.close()

    # --- Lock 4: Anti-Introspection Guard ---
    def test_lock4_anti_introspection_blocks_governance_inspection_while_active(self):
        self.g.approve('human:owner', 'spec approved')
        self.g.claim('T001', 'agent:builder', 'builder-session-alpha')

        payload_view_gov = {
            'toolCall': {
                'name': 'view_file',
                'args': {'AbsolutePath': str(self.root / '.governance/bin/gov.py')}
            }
        }
        res1 = self.h.decide(payload_view_gov)
        self.assertEqual(res1['decision'], 'deny')
        self.assertIn('ANTI_INTROSPECTION', res1['reason'])

        payload_grep_hooks = {
            'toolCall': {
                'name': 'grep_search',
                'args': {'SearchPath': str(self.root / '.governance/hooks'), 'Query': 'def decide'}
            }
        }
        res2 = self.h.decide(payload_grep_hooks)
        self.assertEqual(res2['decision'], 'deny')
        self.assertIn('ANTI_INTROSPECTION', res2['reason'])

        payload_cmd = {
            'toolCall': {
                'name': 'run_command',
                'args': {'CommandLine': 'cat .governance/bin/gov.py'}
            }
        }
        res3 = self.h.decide(payload_cmd)
        self.assertEqual(res3['decision'], 'deny')
        self.assertIn('ANTI_INTROSPECTION', res3['reason'])

        payload_src = {
            'toolCall': {
                'name': 'view_file',
                'args': {'AbsolutePath': str(self.root / 'src/sample_module.py')}
            }
        }
        res4 = self.h.decide(payload_src)
        self.assertEqual(res4['decision'], 'allow')

    def test_lock4_anti_introspection_allows_read_when_no_active_task(self):
        payload_view_gov = {
            'toolCall': {
                'name': 'view_file',
                'args': {'AbsolutePath': str(self.root / '.governance/bin/gov.py')}
            }
        }
        res = self.h.decide(payload_view_gov)
        self.assertEqual(res['decision'], 'allow')

if __name__ == '__main__':
    unittest.main()



