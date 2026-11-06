#!/usr/bin/env python3
"""Native write guard interceptor for Antigravity Ultra Framework v7.5.

Fail-safe, crash-proof, resilient against directory relocations,
and enforces atomic task handoff allowedToWrite boundaries.
"""
import importlib.util, json, os, shlex, sys, time
from pathlib import Path

def find_root(p: Path) -> Path:
    for env_var in ('GOV_WORKSPACE', 'GOV_ROOT', 'ANTIGRAVITY_WORKSPACE'):
        env_root = os.environ.get(env_var)
        if env_root and Path(env_root).is_dir():
            return Path(env_root).resolve()
    cur = p.resolve().parent if p.is_file() else p.resolve()

    # 1. Check .active_workspace marker
    for candidate in [cur, Path.cwd()] + list(cur.parents):
        marker = candidate / '.active_workspace'
        if marker.is_file():
            try:
                line = marker.read_text(encoding='utf-8').strip()
                if line:
                    target = (candidate / line).resolve()
                    if target.is_dir() and (target / '.governance').is_dir():
                        return target
            except Exception:
                pass

    # 2. Nearest Project Marker Check (Stop at subproject before bubbling to monorepo root!)
    PROJECT_MARKERS = {'.governance/config.json', 'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod', '.project-root'}
    candidate = cur
    while candidate.parent != candidate:
        if candidate.name in {'.agents', '.governance', 'hooks', 'bin', 'scripts', 'node_modules', '.git'}:
            candidate = candidate.parent
            continue
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
        candidate = candidate.parent

    # 3. Monorepo Fallback
    for candidate in [cur] + list(cur.parents):
        if candidate.name in {'.agents', '.governance', 'hooks', 'bin', 'scripts'}:
            continue
        if (candidate / '.governance' / 'config.json').is_file() or (candidate / 'AGENTS.md').is_file() or (candidate / '.git').exists():
            return candidate

    return cur

ROOT = find_root(Path(__file__))

def load_gov(root: Path):
    candidates = [
        root / '.governance' / 'bin' / 'gov.py',
        root / '.agents' / '.governance' / 'bin' / 'gov.py',
        root / '.agents' / 'bin' / 'gov.py',
        Path.home() / '.gemini' / 'config' / 'skills' / 'init' / 'template' / '.governance' / 'bin' / 'gov.py'
    ]
    for c in candidates:
        if c and c.is_file():
            try:
                spec = importlib.util.spec_from_file_location('gov', c)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    return mod
            except Exception:
                continue
    return None

gov = load_gov(ROOT)

WRITE = {'write_to_file', 'replace_file_content', 'multi_replace_file_content', 'write_file', 'edit_file'}
READ = {'view_file', 'grep_search', 'list_dir', 'find_by_name', 'read_file'}
SAFE_COMMAND_PREFIXES = (
    'git status', 'git diff', 'git log', 'pwd', 'echo', 'dir',
    'python .governance/bin/gov.py', 'python -m unittest', 'pytest',
    'npm test', 'npm run build', 'npm run lint', 'npx tsc', 'cargo test',
    'python3 .governance/bin/gov.py', 'python3 -m unittest'
)

def is_task_in_progress(active_root: Path, payload: dict) -> bool:
    active_gov = load_gov(active_root) or gov
    if not active_gov:
        return False
    try:
        c = active_gov.db()
        try:
            active_gov.require_lock(c)
            now = time.time()
            conv_id = payload.get('conversationId', '')
            if conv_id:
                row = c.execute("SELECT id FROM tasks WHERE session=? AND state='ACTIVE' AND expires>?", (conv_id, now)).fetchone()
                if row:
                    return True
            row_any = c.execute("SELECT id FROM tasks WHERE state='ACTIVE' AND expires>?", (now,)).fetchone()
            if row_any:
                return True
        finally:
            c.close()
    except Exception:
        pass
    return False

def is_anti_introspection_target(target_str: str) -> bool:
    if not target_str:
        return False
    norm = str(target_str).replace('\\', '/').lower()
    blocked_patterns = (
        '.governance/bin/gov.py',
        '.governance/hooks',
        '.agents/hooks',
        '.agents/.governance/bin/gov.py',
        '.agents/.governance/hooks'
    )
    return any(p in norm for p in blocked_patterns)

def decide(payload):
    tool = payload.get('toolCall', {})
    name = tool.get('name')
    args = tool.get('args', {})
    if not name:
        return {'decision': 'deny', 'reason': 'Malformed hook input'}
    if name in READ:
        target = (
            args.get('AbsolutePath') or args.get('SearchPath') or args.get('DirectoryPath') or
            args.get('Path') or args.get('path') or args.get('file_path') or
            args.get('TargetFile') or args.get('SearchDirectory') or args.get('file') or ''
        )
        if is_anti_introspection_target(target) and is_task_in_progress(ROOT, payload):
            return {
                'decision': 'deny',
                'reason': '[ANTI_INTROSPECTION] Lock 4 (Anti-Introspection Guard): Odczyt silnika walidacji (.governance/bin/gov.py, .governance/hooks/) jest zablokowany w trakcie trwania zadania (IN_PROGRESS).'
            }
        return {'decision': 'allow', 'reason': 'Read delegates to native permissions'}
    if name == 'run_command':
        command = args.get('CommandLine', '') or args.get('command', '')
        try:
            shlex.split(command)
        except ValueError:
            return {'decision': 'deny', 'reason': 'Malformed command'}
        cmd_strip = command.strip()
        if is_anti_introspection_target(command) and not any(cmd_strip.startswith(p) for p in ('python .governance/bin/gov.py', 'python3 .governance/bin/gov.py')) and is_task_in_progress(ROOT, payload):
            return {
                'decision': 'deny',
                'reason': '[ANTI_INTROSPECTION] Lock 4 (Anti-Introspection Guard): Badanie silnika walidacji (.governance/bin/gov.py, .governance/hooks/) jest zablokowane w trakcie trwania zadania (IN_PROGRESS).'
            }
        # Chained commands or subshells require explicit review
        if any(c in command for c in [';', '&&', '||', '|', '&', '`', '$(']):
            return {'decision': 'force_ask', 'reason': 'Chained or subshell commands require explicit verification'}
        if any(cmd_strip.startswith(prefix) for prefix in SAFE_COMMAND_PREFIXES):
            return {'decision': 'allow', 'reason': 'Safe development/verification command'}
        # Block destructive commands
        if any(d in cmd_strip for d in ['rm -rf /', 'format ', 'diskpart', 'del /f', 'rd /s /q', 'git push --force main']):
            return {'decision': 'deny', 'reason': 'Destructive command blocked'}
        return {'decision': 'force_ask', 'reason': 'Terminal command requires explicit verification'}
    if name in WRITE:
        target = args.get('TargetFile') or args.get('Path') or args.get('path')
        if not target:
            return {'decision': 'deny', 'reason': 'Missing TargetFile'}
        target_p = Path(target)
        active_root = ROOT
        p = (active_root / target_p).resolve() if not target_p.is_absolute() else target_p.resolve()

        if not p.is_relative_to(active_root):
            return {
                'decision': 'deny',
                'reason': f"HERMETIC_BOUNDARY_VIOLATION: Path '{target}' escapes active workspace '{active_root}'. Cross-project mutations in multi-workspace repos are forbidden."
            }
        
        active_gov = load_gov(active_root) or gov
        rel = p.relative_to(active_root).as_posix()
        
        # Guard against ungoverned codebase mutation when framework is intended
        is_agentic = (active_root / 'AGENTS.md').is_file() or (active_root / '.agents').is_dir() or (active_root / 'specs').is_dir()
        is_source_code = any(rel == d or rel.startswith(d + '/') for d in ['src', 'crates', 'lib', 'app', 'internal'])
        
        if not active_gov:
            if is_agentic and is_source_code:
                return {
                    'decision': 'deny',
                    'reason': f"[NEXUS Guard] UNGOVERNED_WRITE_BLOCKED: Próba zapisu do kodu źródłowego ('{rel}') bez zainstalowanego frameworka .governance/. Uruchom najpierw /init lub bootstrap.py!"
                }
            return {'decision': 'allow', 'reason': 'Governance unconfigured; deferring to native permissions'}

        try:
            cfg = active_gov.config()
            if any(rel == x or rel.startswith(x.rstrip('/') + '/') for x in cfg.get('protected_paths', [])):
                return {'decision': 'force_ask', 'reason': 'Governance change needs owner review'}
        except Exception:
            pass

        if rel.startswith('.specify/') or rel.startswith('docs/') or rel.startswith('specs/') or rel.startswith('tasks/'):
            return {'decision': 'allow', 'reason': 'Spec/documentation/task management allowed'}

        try:
            c = active_gov.db()
            try:
                active_gov.require_lock(c)
                row = c.execute("SELECT * FROM tasks WHERE session=? AND state='ACTIVE' AND expires>?",
                                (payload.get('conversationId', ''), time.time())).fetchone()
                if row is None:
                    if is_source_code:
                        return {
                            'decision': 'deny',
                            'reason': f"NO_ACTIVE_CLAIM: Brak aktywnego claimu zadania dla sesji '{payload.get('conversationId', '')}' przy próbie zapisu do '{rel}'. Pobierz zadanie przez 'python .governance/bin/gov.py claim --task <ID>'."
                        }
                    return {'decision': 'allow', 'reason': 'Non-source file edit allowed outside claim'}
                
                task_id = row['id']
                # V4 Atomic Handoff check: check allowedToWrite if handoff exists
                allowed_targets = None
                handoff_file = active_root / '.governance' / 'handoffs' / f'{task_id}.json'
                if handoff_file.is_file():
                    try:
                        h_data = json.loads(handoff_file.read_text(encoding='utf-8'))
                        allowed_targets = h_data.get('targetFiles', {}).get('allowedToWrite')
                    except Exception:
                        pass
                
                if allowed_targets is None:
                    allowed_targets = active_gov.task_def(task_id)['allowed_paths']

                if not any(rel == x or rel.startswith(x.rstrip('/') + '/') for x in allowed_targets):
                    return {'decision': 'deny', 'reason': f'Outside task handoff scope: {rel} not in {allowed_targets}'}
                return {'decision': 'allow', 'reason': 'Current spec and scoped task; native permissions still apply'}
            finally:
                c.close()
        except Exception as e:
            if type(e).__name__ == 'Rejected':
                return {'decision': 'deny', 'reason': str(e)}
            return {'decision': 'force_ask', 'reason': f'Governance verification error: {type(e).__name__}'}

    return {'decision': 'force_ask', 'reason': 'Unclassified tool, including MCP side effects, requires review'}

def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        result = decide(payload)
    except Exception as e:
        result = {'decision': 'force_ask', 'reason': f'Hook fail-safe recovery (review required): {type(e).__name__}'}
    print(json.dumps(result))
    sys.exit(0)

if __name__ == '__main__':
    main()
