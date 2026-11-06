#!/usr/bin/env python3
"""Project State & Maturity Probe for Antigravity Closed Loop Framework 3.0.

Includes self-healing immunization for Windows python3.exe and dual hook paths.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

def immunize_environment(cwd: Path):
    healed = []
    # 1. Automatyczne zapewnienie python3.exe na Windows
    if os.name == 'nt':
        py_exe = Path(sys.executable)
        py3_exe = py_exe.parent / 'python3.exe'
        if not py3_exe.is_file():
            try:
                shutil.copy2(py_exe, py3_exe)
                healed.append('created_python3_exe')
            except Exception:
                pass

    # 2. Samoleczenie ścieżek hooka native_guard.py
    p_gov = cwd / '.governance' / 'hooks' / 'native_guard.py'
    p_ag_gov = cwd / '.agents' / '.governance' / 'hooks' / 'native_guard.py'
    p_ag = cwd / '.agents' / 'hooks' / 'native_guard.py'
    p_tpl = Path.home() / '.gemini' / 'config' / 'skills' / 'init' / 'template' / '.governance' / 'hooks' / 'native_guard.py'

    src = None
    if p_gov.is_file(): src = p_gov
    elif p_ag_gov.is_file(): src = p_ag_gov
    elif p_ag.is_file(): src = p_ag
    elif p_tpl.is_file(): src = p_tpl

    if src:
        # Jeśli w projekcie istnieje jakikolwiek katalog zarządczy, powiel guard w kluczowych ścieżkach
        has_mgmt = (cwd / '.governance').is_dir() or (cwd / '.agents').is_dir()
        if has_mgmt:
            for dest in [p_gov, p_ag_gov]:
                if not dest.is_file():
                    try:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest)
                        healed.append(f'reconciled_{dest.relative_to(cwd).as_posix()}')
                    except Exception:
                        pass
    return healed

def detect_stack(cwd: Path):
    if (cwd / 'package.json').exists(): return 'node'
    if any((cwd / f).exists() for f in ['pytest.ini', 'pyproject.toml', 'requirements.txt']): return 'python'
    if (cwd / 'Cargo.toml').exists(): return 'rust'
    if (cwd / 'go.mod').exists(): return 'go'
    if any((cwd / d).is_dir() for d in ['src', 'app', 'lib', 'tests', 'test']): return 'generic_code'
    return 'empty'

def probe(target_path: str = '.'):
    cwd = Path(target_path).resolve()
    
    # Uruchomienie procedury samoleczenia środowiska
    healed = immunize_environment(cwd)
    
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
        'gov_status': gov_status,
        'environment_healed': healed
    }
    return output

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    print(json.dumps(probe(target), indent=2, ensure_ascii=False))
