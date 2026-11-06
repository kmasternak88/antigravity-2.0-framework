#!/usr/bin/env python3
"""Project State & Maturity Probe for Antigravity Closed Loop Framework 3.0."""
import json, os, subprocess, sys
from pathlib import Path

def detect_stack(cwd: Path):
    if (cwd / 'package.json').exists(): return 'node'
    if any((cwd / f).exists() for f in ['pytest.ini', 'pyproject.toml', 'requirements.txt']): return 'python'
    if (cwd / 'Cargo.toml').exists(): return 'rust'
    if (cwd / 'go.mod').exists(): return 'go'
    if any((cwd / d).is_dir() for d in ['src', 'app', 'lib', 'tests', 'test']): return 'generic_code'
    return 'empty'

def probe(target_path: str = '.'):
    cwd = Path(target_path).resolve()
    has_git = (cwd / '.git').is_dir()
    stack = detect_stack(cwd)
    gov_bin = cwd / '.governance' / 'bin' / 'gov.py'
    has_gov = gov_bin.is_file()
    
    # Check Mem0 project config
    mem0_file = cwd / '.agents' / 'project.json'
    mem0_id = None
    if mem0_file.is_file():
        try:
            mem0_data = json.loads(mem0_file.read_text(encoding='utf-8'))
            mem0_id = mem0_data.get('id') or mem0_data.get('tenant')
        except Exception:
            pass

    # Check state if gov.py is present
    gov_status = None
    py_bin = 'python' if os.name == 'nt' else 'python3'
    if has_gov:
        try:
            p = subprocess.run([py_bin, str(gov_bin), 'status'], cwd=cwd, capture_output=True, text=True, timeout=10)
            if p.returncode == 0:
                gov_status = json.loads(p.stdout)
        except Exception as e:
            gov_status = {'error': str(e)}

    # Classification
    state = 'UNKNOWN'
    recommendation = ''
    action = ''

    if not has_gov:
        if stack == 'empty':
            state = 'S0_GREENFIELD'
            recommendation = 'Czysty nowy projekt. Wymaga wygenerowania struktury bazowej, frameworka v3, specyfikacji i początkowego zadania T001.'
            action = 'bootstrap_new'
        else:
            state = 'S1_BROWNFIELD_UNMANAGED'
            recommendation = f'Aktywny projekt bez governance (wykryty stack: {stack}). Wymaga bezpiecznego nałożenia frameworka z zachowaniem istniejącego kodu i reguł oraz wpięcia testów projektu.'
            action = 'bootstrap_extend'
    else:
        if not gov_status or not gov_status.get('specLocked', False):
            state = 'S2_GOVERNANCE_UNLOCKED'
            recommendation = 'Framework zainstalowany, ale specyfikacja nie jest zablokowana (lub została zmieniona). Wymagany audyt specyfikacji i zatwierdzenie Spec Lock przez człowieka.'
            action = 'spec_audit_and_lock'
        else:
            tasks = gov_status.get('tasks', [])
            active_tasks = [t for t in tasks if t.get('state') == 'ACTIVE']
            done_tasks = [t for t in tasks if t.get('state') == 'DONE']
            
            # Check tasks.json for pending tasks
            tasks_file = cwd / '.governance' / 'tasks.json'
            all_defs = []
            if tasks_file.is_file():
                try:
                    all_defs = json.loads(tasks_file.read_text(encoding='utf-8')).get('tasks', [])
                except Exception:
                    pass
            pending_ids = [t['id'] for t in all_defs if t['id'] not in [x['id'] for x in done_tasks] and t['id'] not in [x['id'] for x in active_tasks]]

            if active_tasks:
                state = 'S3_IN_FLIGHT_ACTIVE'
                recommendation = f'Trwa aktywne zadanie {active_tasks[0]["id"]}. Kontynuuj implementację, weryfikację i niezależny audyt.'
                action = 'resume_active_task'
            elif pending_ids:
                state = 'S3_IN_FLIGHT_READY'
                recommendation = f'Specyfikacja zablokowana. Kolejne zadanie do podjęcia: {pending_ids[0]}.'
                action = 'claim_next_task'
            else:
                state = 'S3_ALL_TASKS_DONE'
                recommendation = 'Wszystkie zdefiniowane zadania w stanie DONE. Gotowość do weryfikacji CI kandydata wydania lub zaplanowania nowego slice.'
                action = 'release_or_next_slice'

    output = {
        'state': state,
        'action': action,
        'recommendation': recommendation,
        'cwd': str(cwd),
        'has_git': has_git,
        'tech_stack': stack,
        'has_governance': has_gov,
        'mem0_tenant': mem0_id,
        'gov_status': gov_status
    }
    return output

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    print(json.dumps(probe(target), indent=2, ensure_ascii=False))
