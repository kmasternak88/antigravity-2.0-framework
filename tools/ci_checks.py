#!/usr/bin/env python3
"""Run configured global checks on the CI candidate; workspace-aware and hermetic."""
import importlib.util, json, os, subprocess, sys, time, re
from pathlib import Path
from typing import Optional, Tuple, List

ROOT = Path(__file__).resolve().parents[1]

# Multi-Workspace delegation: prevent accidental root-test mutation when working in a subproject
ACTIVE_MARKER = ROOT / '.active_workspace'
env_ws = os.environ.get('GOV_WORKSPACE') or os.environ.get('ANTIGRAVITY_WORKSPACE')

if '--root' not in sys.argv:
    target_ws = None
    if env_ws and Path(env_ws).is_dir():
        target_ws = Path(env_ws).resolve()
    elif ACTIVE_MARKER.is_file():
        try:
            ws_rel = ACTIVE_MARKER.read_text(encoding='utf-8').strip()
            if ws_rel:
                target_ws = (ROOT / ws_rel).resolve()
        except Exception:
            pass

    if target_ws and target_ws != ROOT:
        if not target_ws.is_relative_to(ROOT):
            raise RuntimeError(f"Security Violation: Target workspace {target_ws} escapes repository boundary")
        target_ci = target_ws / 'tools' / 'ci_checks.py'
        if not target_ci.is_file():
            # DO NOT SILENTLY FALL BACK TO ROOT! Check if target_ws has .governance/config.json
            if (target_ws / '.governance' / 'config.json').is_file():
                # Anchored execution inside target_ws
                print(f"[CI] Executing CI checks within active workspace: {target_ws}")
                env = os.environ.copy()
                env['GOV_WORKSPACE'] = str(target_ws)
                env['ANTIGRAVITY_WORKSPACE'] = str(target_ws)
                env['GOV_ROOT'] = str(target_ws)
                gov_bin = target_ws / '.governance' / 'bin' / 'gov.py'
                if not gov_bin.is_file():
                    gov_bin = ROOT / '.governance' / 'bin' / 'gov.py'
                # Run anchored checks
                s_sub = importlib.util.spec_from_file_location('gov', gov_bin)
                g_sub = importlib.util.module_from_spec(s_sub)
                s_sub.loader.exec_module(g_sub)
                g_sub.set_workspace_root(target_ws)
                # Delegate to target workspace
            else:
                raise RuntimeError(
                    f"Active workspace {target_ws} missing required tools/ci_checks.py or .governance/config.json. "
                    "Fallback to root tests is blocked to prevent context contamination."
                )
        else:
            print(f"[CI] Delegating CI check to active workspace: {target_ws}")
            py_bin = sys.executable or 'python'
            r = subprocess.run([py_bin, str(target_ci)], cwd=target_ws)
            sys.exit(r.returncode)

gov_script = ROOT / '.governance/bin/gov.py'
s = importlib.util.spec_from_file_location('gov', gov_script)
g = importlib.util.module_from_spec(s)
s.loader.exec_module(g)


def verify_prd_traceability(
    prd_path: Optional[Path] = None,
    specs_dir: Optional[Path] = None,
    tests_dir: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """G6 Gate: Verify every REQ-XXX in PRD is mapped in specs and tested."""
    prd_path = prd_path or ROOT / "specs/00_PRD.md"
    specs_dir = specs_dir or ROOT / "specs"
    tests_dir = tests_dir or ROOT / "tests"

    if not prd_path.exists():
        return True, []

    content = prd_path.read_text(encoding="utf-8")
    reqs = re.findall(r'(REQ-\d{3})', content)
    reqs = list(set(reqs))

    matrix_path = specs_dir / "05_TRACEABILITY_MATRIX.md"
    reqs_spec_path = specs_dir / "01_PRODUCT_REQUIREMENTS.md"

    matrix_content = matrix_path.read_text(encoding="utf-8") if matrix_path.exists() else ""
    reqs_spec_content = reqs_spec_path.read_text(encoding="utf-8") if reqs_spec_path.exists() else ""

    missing = []

    test_files = list(tests_dir.rglob("*.py"))
    test_contents = [f.read_text(encoding="utf-8") for f in test_files]

    for req in reqs:
        # Check in specs
        if req not in matrix_content and req not in reqs_spec_content:
            missing.append(f"UNCOVERED_PRD_REQUIREMENTS: {req} missing in specs.")
            continue

        # Check in tests
        found_in_tests = False
        for tc in test_contents:
            if f'@test_req("{req}")' in tc or req in tc:
                found_in_tests = True
                break

        if not found_in_tests:
             missing.append(f"UNCOVERED_PRD_REQUIREMENTS: {req} missing in tests.")

    if missing:
        return False, missing
    return True, []


def main():
    g.validate()
    cfg = g.config()
    source = g.snapshot()
    reports = []
    dest = ROOT / '.governance/evidence/ci'
    dest.mkdir(parents=True, exist_ok=True)

    # Check PRD traceability first (G6)
    is_traceable, trace_errors = verify_prd_traceability()
    if not is_traceable:
        print("\n".join(trace_errors), file=sys.stderr)
        return 1

    for name in cfg['required_release_checks']:
        ck = cfg['checks'][name]
        started = time.time()
        try:
            r = subprocess.run(ck['argv'], cwd=ROOT, shell=False, capture_output=True, text=True, timeout=ck['timeout'])
            code = r.returncode
            log = r.stdout + '\n' + r.stderr
        except subprocess.TimeoutExpired as e:
            code = 124
            log = 'TIMEOUT: ' + str(e)
        path = dest / (name.replace('/', '_') + '.log')
        path.write_text(g.redact(log), encoding='utf-8')
        reports.append({
            'check': name,
            'argv': ck['argv'],
            'exitCode': code,
            'seconds': time.time() - started,
            'log': str(path.relative_to(ROOT)),
            'logSha256': g.digest(path.read_bytes())
        })
    unchanged = (source == g.snapshot())
    report = {
        'status': 'PASS' if unchanged and reports and all(x['exitCode'] == 0 for x in reports) else 'FAIL',
        'sourceDigest': source,
        'specDigest': g.spec_hash(),
        'sourceUnchanged': unchanged,
        'checks': reports,
        'humanApproval': 'MUST_BE_ENFORCED_BY_PROTECTED_REPOSITORY',
        'deploymentAuthorization': False
    }
    (dest / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
