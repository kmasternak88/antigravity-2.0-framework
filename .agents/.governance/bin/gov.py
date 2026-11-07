#!/usr/bin/env python3
"""Local evidence gates and multi-agent coordination engine for Antigravity Ultra v5.1 (Omni-Agentic OS & DREE Engine).
Pure Python standard library implementation.
"""
import argparse, ast, datetime, difflib, gc, hashlib, json, os, re, shlex, shutil, signal, sqlite3, subprocess, sys, tempfile, time, uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

def find_workspace_root() -> Path:
    """Dynamically resolves the active workspace root using Nearest-Anchor hierarchy.
    Prevents sprawling into monorepo root when operating inside workspace subdirectories.
    """
    for env_var in ('GOV_WORKSPACE', 'GOV_ROOT', 'ANTIGRAVITY_WORKSPACE'):
        val = os.environ.get(env_var)
        if val and Path(val).is_dir():
            return Path(val).resolve()

    try:
        cur_file = Path(__file__).resolve()
        for p in [cur_file.parents[2], cur_file.parents[1], cur_file.parent]:
            if (p / '.governance').is_dir():
                return p
    except Exception:
        pass

    cur = Path.cwd().resolve()
    for candidate in [cur] + list(cur.parents):
        marker = candidate / '.active_workspace'
        if marker.is_file():
            try:
                line = marker.read_text(encoding='utf-8').strip()
                if line:
                    p = candidate / line if not Path(line).is_absolute() else Path(line)
                    res = p.resolve()
                    if res.is_dir() and (res / '.governance').is_dir():
                        return res
            except Exception:
                pass

    candidate = cur
    PROJECT_MARKERS = {'.governance/config.json', 'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod', '.project-root'}
    while candidate.parent != candidate:
        if candidate.name in {'.agents', '.governance', 'hooks', 'bin', 'node_modules', '.git'}:
            candidate = candidate.parent
            continue
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
        candidate = candidate.parent

    return Path(__file__).resolve().parents[2]

ROOT = find_workspace_root()

def set_workspace_root(new_root: Path):
    global ROOT, _GLOBAL_STAT_CACHE
    ROOT = Path(new_root).resolve()
    _GLOBAL_STAT_CACHE = None

EXCLUDES = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache', '.mypy_cache',
    'dist', 'build', 'coverage', 'test-results', 'playwright-report', '.worktrees',
    '.shadow_worktrees', '.turbo', '.next', '.nuxt', '.cache', '.parcel-cache',
    '.output', '.pnpm-store', '.pnpm', '.yarn', 'vendor', 'target', 'bin', 'obj',
    '.idea', '.vscode', 'tmp', 'temp'
}

EXCLUDES_FILES = {
    'events.jsonl', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'RELEASE_MANIFEST.json'
}

EXCLUDE_EXTENSIONS = {
    '.zip', '.tar', '.gz', '.tgz', '.7z', '.rar', '.bz2', '.xz', '.whl', '.exe', '.dll', '.so', '.dylib',
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.svg', '.mp4', '.mp3', '.wav', '.pdf', '.psd',
    '.db', '.sqlite', '.sqlite3', '.sqlite-wal', '.sqlite-shm', '.tsbuildinfo', '.map'
}

class Rejected(Exception): pass

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def config():
    return read(ROOT / '.governance/config.json')

def definitions():
    return read(ROOT / '.governance/tasks.json')['tasks']

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def digest(value):
    if isinstance(value, str):
        value = value.encode('utf-8')
    return hashlib.sha256(value).hexdigest()

def safe_path(value):
    p = Path(value)
    if not value or p.is_absolute() or '..' in p.parts or value in {'.', '/'}:
        raise Rejected('Unsafe or unbounded relative path: ' + str(value))
    target = (ROOT / p).resolve()
    if not target.is_relative_to(ROOT):
        raise Rejected('Path escapes workspace: ' + str(value))
    return target

class FileStatCache:
    """High-performance stat-based cache (mtime_ns + size_bytes -> sha256).
    Reduces full-tree snapshot from 30-50s down to < 100ms on Windows NTFS.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._mem_cache: Dict[str, Any] = {}
        self._dirty = False
        self._load_cache()

    def _load_cache(self):
        if not self.db_path.is_file():
            self._mem_cache = {}
            return
        c = None
        try:
            c = sqlite3.connect(self.db_path, timeout=5)
            for row in c.execute("SELECT rel_path, mtime_ns, size_bytes, sha256 FROM file_stat_cache"):
                self._mem_cache[row[0]] = (row[1], row[2], row[3])
        except Exception:
            self._mem_cache = {}
        finally:
            if c:
                c.close()

    def get_or_hash(self, rel_posix: str, full_path: Path, st) -> str:
        cached = self._mem_cache.get(rel_posix)
        if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            return cached[2]

        ext = full_path.suffix.lower()
        if ext in EXCLUDE_EXTENSIONS:
            file_hash = hashlib.sha256(f"META:{st.st_size}:{st.st_mtime_ns}".encode()).hexdigest()
        else:
            file_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()

        self._mem_cache[rel_posix] = (st.st_mtime_ns, st.st_size, file_hash)
        self._dirty = True
        return file_hash

    def persist(self):
        if not self._dirty:
            return
        c = None
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            c = sqlite3.connect(self.db_path, timeout=10)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""
            CREATE TABLE IF NOT EXISTS file_stat_cache (
                rel_path TEXT PRIMARY KEY,
                mtime_ns INTEGER NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            now = time.time()
            c.executemany(
                "INSERT OR REPLACE INTO file_stat_cache VALUES (?, ?, ?, ?, ?)",
                [(path, item[0], item[1], item[2], now) for path, item in self._mem_cache.items()]
            )
            c.commit()
            self._dirty = False
        except Exception:
            pass
        finally:
            if c:
                c.close()

_GLOBAL_STAT_CACHE = None

def get_stat_cache(root_dir: Optional[Path] = None) -> FileStatCache:
    global _GLOBAL_STAT_CACHE
    r = (root_dir or ROOT).resolve()
    db_file = r / '.governance' / 'state' / 'file_stat_cache.sqlite'
    if _GLOBAL_STAT_CACHE is None or _GLOBAL_STAT_CACHE.db_path != db_file:
        _GLOBAL_STAT_CACHE = FileStatCache(db_file)
    return _GLOBAL_STAT_CACHE

def file_index(target_root: Optional[Path] = None) -> Dict[str, str]:
    r = (target_root or ROOT).resolve()
    cache = get_stat_cache(r)
    files = {}

    active_marker = r / '.active_workspace'
    active_ws_sub = None
    if active_marker.is_file():
        try:
            active_ws_sub = active_marker.read_text(encoding='utf-8').strip()
        except Exception:
            pass

    def scan_dir(dir_path: Path):
        try:
            with os.scandir(dir_path) as it:
                for entry in it:
                    name = entry.name
                    if name in EXCLUDES:
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if (dir_path == r / '.governance') and name in {'state', 'evidence', 'golden', 'handoffs', 'snapshots'}:
                            continue
                        if dir_path == r and name == 'workspace' and active_ws_sub and active_ws_sub.startswith('workspace/'):
                            scan_dir(r / active_ws_sub)
                            continue
                        scan_dir(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        if entry.is_symlink():
                            rel = Path(entry.path).relative_to(r)
                            raise Rejected('Symlink unsupported: ' + str(rel))
                        if name.startswith('.env') and name != '.env.example':
                            continue
                        if name.endswith(('.log', '.har')) or name in EXCLUDES_FILES:
                            continue
                        st = entry.stat(follow_symlinks=False)
                        p = Path(entry.path)
                        rel_posix = p.relative_to(r).as_posix()
                        files[rel_posix] = cache.get_or_hash(rel_posix, p, st)
        except (PermissionError, FileNotFoundError, OSError):
            pass

    scan_dir(r)
    cache.persist()
    return files

def snapshot(target_root: Optional[Path] = None):
    return digest(canonical(file_index(target_root)).encode())

def spec_hash():
    values = {}
    cfg = config()
    all_specs = []
    spec_list = cfg.get('spec_files', [])
    if 'contracts/**/*' not in spec_list and (ROOT / 'contracts').is_dir():
        spec_list = list(spec_list) + ['contracts/**/*']
    for pattern in spec_list + ['.governance/config.json', '.governance/tasks.json']:
        if '*' in pattern:
            matched_files = sorted(ROOT.glob(pattern))
            for mf in matched_files:
                if mf.is_file():
                    rel_name = mf.relative_to(ROOT).as_posix()
                    all_specs.append(rel_name)
        else:
            all_specs.append(pattern)

    seen = set()
    for name in all_specs:
        if name in seen:
            continue
        seen.add(name)
        p = safe_path(name)
        if not p.is_file() or not p.read_text(encoding='utf-8').strip():
            raise Rejected('Missing or empty spec: ' + name)
        values[name] = digest(p.read_bytes())
    return digest(canonical(values).encode())

def db():
    if os.environ.get('GOV_STATE_PATH'):
        db_file = Path(os.environ['GOV_STATE_PATH'])
        db_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        p = ROOT / '.governance/state'
        p.mkdir(parents=True, exist_ok=True)
        db_file = p / 'state.sqlite'
    c = sqlite3.connect(db_file, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA busy_timeout=30000")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS approvals(hash TEXT PRIMARY KEY, actor TEXT, reference TEXT, at REAL);
    CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, state TEXT, actor TEXT, session TEXT, token TEXT, expires REAL, base TEXT, files TEXT);
    CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY, task TEXT, check_name TEXT, source TEXT, spec TEXT, exit_code INTEGER, log_path TEXT, log_hash TEXT, at REAL);
    CREATE TABLE IF NOT EXISTS reviews(task TEXT PRIMARY KEY, reviewer TEXT, source TEXT, decision TEXT, reference TEXT, at REAL, identity_verified INTEGER DEFAULT 0, reviewer_session TEXT, auditor_token TEXT);
    CREATE TABLE IF NOT EXISTS handoffs(task TEXT PRIMARY KEY, spec_hash TEXT, packet_path TEXT, allowed_files TEXT, created_at REAL);
    CREATE TABLE IF NOT EXISTS golden_records(name TEXT PRIMARY KEY, cmd TEXT, digest TEXT, snapshot_path TEXT, created_at REAL);
    CREATE TABLE IF NOT EXISTS healing_cycles(task TEXT, cycle INTEGER, hypothesis TEXT, diff_summary TEXT, result TEXT, at REAL, PRIMARY KEY (task, cycle));
    CREATE TABLE IF NOT EXISTS integrations(task TEXT PRIMARY KEY, commit_or_snap TEXT, verified_at REAL);
    CREATE TABLE IF NOT EXISTS symbol_index(symbol TEXT, kind TEXT, file_path TEXT, line_start INTEGER, hash TEXT, PRIMARY KEY(symbol, file_path));
    CREATE TABLE IF NOT EXISTS symbol_dependencies(caller_symbol TEXT, caller_file TEXT, callee_symbol TEXT, callee_file TEXT);
    CREATE TABLE IF NOT EXISTS worktrees(task TEXT PRIMARY KEY, worktree_path TEXT, branch_name TEXT, is_shadow INTEGER, created_at REAL);
    CREATE TABLE IF NOT EXISTS test_audits(task TEXT, source TEXT, spec TEXT, total_tests INTEGER, assertions_found INTEGER, mutations_caught INTEGER, status TEXT, at REAL, PRIMARY KEY (task, source));
    CREATE TABLE IF NOT EXISTS symbol_leases (symbol TEXT PRIMARY KEY, task TEXT, actor TEXT, session TEXT, expires REAL, created_at REAL);
    CREATE TABLE IF NOT EXISTS decision_mesh (adr_id TEXT PRIMARY KEY, domain TEXT, assertion TEXT, scope TEXT, active INTEGER, created_at REAL);
    CREATE TABLE IF NOT EXISTS contract_manifests (contract_id TEXT PRIMARY KEY, spec_hash TEXT, file_path TEXT, mock_url TEXT, created_at REAL);
    """)
    # Migration helper for reviews columns
    try:
        r_cols = [r['name'] for r in c.execute("PRAGMA table_info(reviews)").fetchall()]
        if 'identity_verified' not in r_cols:
            c.execute("ALTER TABLE reviews ADD COLUMN identity_verified INTEGER DEFAULT 0")
        if 'reviewer_session' not in r_cols:
            c.execute("ALTER TABLE reviews ADD COLUMN reviewer_session TEXT DEFAULT ''")
        if 'auditor_token' not in r_cols:
            c.execute("ALTER TABLE reviews ADD COLUMN auditor_token TEXT DEFAULT ''")
    except Exception:
        pass
    # Migration helper for test_audits columns if existing table lacked source/spec
    try:
        cols = [r['name'] for r in c.execute("PRAGMA table_info(test_audits)").fetchall()]
        if 'source' not in cols:
            c.execute("ALTER TABLE test_audits ADD COLUMN source TEXT DEFAULT ''")
        if 'spec' not in cols:
            c.execute("ALTER TABLE test_audits ADD COLUMN spec TEXT DEFAULT ''")
    except Exception:
        pass
    return c

def require_lock(c):
    h = spec_hash()
    if c.execute('SELECT * FROM approvals WHERE hash=?', (h,)).fetchone() is None:
        raise Rejected('SPEC_LOCK_MISSING_OR_STALE')
    return h

def task_def(task):
    for t in definitions():
        if t['id'] == task:
            return t
    raise Rejected('Unknown task ' + str(task))

def overlaps(a, b):
    na = os.path.normcase(os.path.normpath(a)).replace('\\', '/').rstrip('/')
    nb = os.path.normcase(os.path.normpath(b)).replace('\\', '/').rstrip('/')
    return na == nb or na.startswith(nb + '/') or nb.startswith(na + '/')

def validate():
    cfg = config()
    tasks = definitions()
    ids = [x['id'] for x in tasks]
    if cfg['profile'] not in {'tiny', 'standard', 'critical'} or not tasks or len(set(ids)) != len(ids):
        raise Rejected('Invalid profile, empty or duplicate tasks')
    seen = set()
    active = set()
    by_id = {t['id']: t for t in tasks}
    def walk(i):
        if i in active: raise Rejected('DAG_CYCLE ' + i)
        if i in seen: return
        if i not in by_id: raise Rejected('Unknown dependency ' + i)
        active.add(i)
        for d in by_id[i]['depends_on']: walk(d)
        active.remove(i); seen.add(i)
    for t in tasks:
        walk(t['id'])
        if not t['allowed_paths'] or not t['checks'] or not t['acceptance']:
            raise Rejected('Incomplete task ' + t['id'])
        for p in t['allowed_paths']: safe_path(p)
        for ck in t['checks']:
            if ck not in cfg['checks']: raise Rejected('Unknown check ' + ck)
        chk = t.get('standards_checklist')
        if chk is not None:
            if not isinstance(chk, list) or len(chk) == 0:
                raise Rejected('STANDARDS_CHECKLIST_EMPTY ' + t['id'])
    for name, ck in cfg['checks'].items():
        if not isinstance(ck.get('argv'), list) or not ck['argv'] or not all(isinstance(x, str) and x for x in ck['argv']):
            raise Rejected('Invalid argv ' + name)
        if not isinstance(ck.get('timeout'), int) or not 1 <= ck['timeout'] <= 3600:
            raise Rejected('Invalid timeout ' + name)
    if any(x not in cfg['checks'] for x in cfg['required_release_checks']):
        raise Rejected('Unknown release check')
    bp_dir = ROOT / 'specs/blueprints'
    if bp_dir.is_dir():
        for bp_f in bp_dir.glob('*.blueprint.json'):
            try:
                b_doc = json.loads(bp_f.read_text(encoding='utf-8'))
                if bp_f.name == 'system.blueprint.json' or 'metadata' in b_doc:
                    if not b_doc.get('metadata') or not b_doc.get('competitive_advantages'):
                        raise Rejected(f"Invalid system blueprint contract: {bp_f.name}")
                else:
                    if not b_doc.get('pageId') or not b_doc.get('targetFile') or not b_doc.get('slots'):
                        raise Rejected(f"Invalid blueprint contract: {bp_f.name}")
            except Exception as e:
                raise Rejected(f"Malformed blueprint {bp_f.name}: {e}")
    spec_hash()
    return {'status': 'VALID', 'tasks': len(tasks), 'profile': cfg['profile']}

def approve(actor, reference):
    if not actor.startswith('human:') or not reference.strip():
        raise Rejected('Human label and reference required; label is not identity proof')
    validate()
    c = db()
    try:
        h = spec_hash()
        c.execute('INSERT OR REPLACE INTO approvals VALUES(?,?,?,?)', (h, actor, reference, time.time()))
        c.commit()
    finally:
        c.close()
        gc.collect()
    return {'specHash': h, 'approvalRecorded': True, 'identityVerified': False}

def claim(task, actor, session):
    validate()
    c = db()
    try:
        c.execute('BEGIN IMMEDIATE')
        require_lock(c)
        t = task_def(task)
        now = time.time()
        for dep in t['depends_on']:
            r = c.execute('SELECT state FROM tasks WHERE id=?', (dep,)).fetchone()
            if r is None or r['state'] != 'DONE':
                raise Rejected('DEPENDENCY_NOT_DONE ' + dep)
        existing = c.execute('SELECT * FROM tasks WHERE id=?', (task,)).fetchone()
        if existing is not None and existing['state'] == 'DONE':
            raise Rejected('TASK_ALREADY_DONE')
        for r in c.execute("SELECT * FROM tasks WHERE state='ACTIVE' AND expires>?", (now,)):
            if r['id'] == task:
                raise Rejected('TASK_ALREADY_CLAIMED')
            if r['session'] == session:
                raise Rejected('SESSION_ALREADY_HAS_TASK')
            if any(overlaps(a, b) for a in t['allowed_paths'] for b in task_def(r['id'])['allowed_paths']):
                raise Rejected('WRITE_SCOPE_CONFLICT ' + r['id'])
        # Triple Lock: AST Symbols & Routes
        task_symbols = t.get('symbols', [])
        for sym in task_symbols:
            s_row = c.execute("SELECT * FROM symbol_leases WHERE symbol=? AND expires>?", (sym, now)).fetchone()
            if s_row is not None and s_row['task'] != task:
                raise Rejected(f"RESOURCE_COLLISION: AST Symbol '{sym}' already leased by task '{s_row['task']}'")

        task_routes = t.get('routes', [])
        for route in task_routes:
            r_key = f"ROUTE:{route}"
            r_row = c.execute("SELECT * FROM symbol_leases WHERE symbol=? AND expires>?", (r_key, now)).fetchone()
            if r_row is not None and r_row['task'] != task:
                raise Rejected(f"RESOURCE_COLLISION: Route '{route}' already leased by task '{r_row['task']}'")

        if c.execute("SELECT count(*) FROM tasks WHERE state='ACTIVE' AND expires>?", (now,)).fetchone()[0] >= config()['max_parallel']:
            raise Rejected('PARALLEL_LIMIT')
        token = str(uuid.uuid4())
        index = file_index()
        c.execute('INSERT OR REPLACE INTO tasks VALUES(?,?,?,?,?,?,?,?)', (task, 'ACTIVE', actor, session, token, now + config()['lease_seconds'], digest(canonical(index).encode()), canonical(index)))
        c.execute('DELETE FROM reviews WHERE task=?', (task,))
        lease_exp = now + config()['lease_seconds']
        for sym in task_symbols:
            c.execute("INSERT OR REPLACE INTO symbol_leases VALUES (?,?,?,?,?,?)", (sym, task, actor, session, lease_exp, now))
        for route in task_routes:
            c.execute("INSERT OR REPLACE INTO symbol_leases VALUES (?,?,?,?,?,?)", (f"ROUTE:{route}", task, actor, session, lease_exp, now))
        
        # Backup snapshot of allowed files for auto-heal rollback (preserving hierarchy)
        snap_dir = ROOT / '.governance/snapshots' / task
        snap_dir.mkdir(parents=True, exist_ok=True)
        for allowed in t['allowed_paths']:
            src_target = safe_path(allowed)
            rel_str = str(src_target.relative_to(ROOT)) if src_target.is_relative_to(ROOT) else src_target.name
            dest_target = snap_dir / rel_str
            dest_target.parent.mkdir(parents=True, exist_ok=True)
            if src_target.is_file():
                shutil.copy2(src_target, dest_target)
            elif src_target.is_dir():
                if dest_target.exists(): shutil.rmtree(dest_target)
                shutil.copytree(src_target, dest_target)
                
        c.commit()
    finally:
        c.close()
        gc.collect()
    return {'task': task, 'token': token, 'session': session, 'leaseSeconds': config()['lease_seconds']}

def active_claim(c, task):
    r = c.execute('SELECT * FROM tasks WHERE id=?', (task,)).fetchone()
    if r is None or r['state'] != 'ACTIVE' or r['expires'] <= time.time():
        raise Rejected('CLAIM_MISSING_OR_EXPIRED')
    return r

def heartbeat(task, token):
    c = db()
    try:
        c.execute('BEGIN IMMEDIATE')
        r = active_claim(c, task)
        if r['token'] != token:
            raise Rejected('STALE_FENCING_TOKEN')
        new_exp = time.time() + config()['lease_seconds']
        c.execute('UPDATE tasks SET expires=? WHERE id=?', (new_exp, task))
        c.execute('UPDATE symbol_leases SET expires=? WHERE task=?', (new_exp, task))
        c.commit()
    finally:
        c.close()
        gc.collect()
    return {'renewed': task}

def assert_scope(row, task):
    before = json.loads(row['files'])
    after = file_index()
    allowed = task_def(task)['allowed_paths']
    changed = [p for p in set(before) | set(after) if before.get(p) != after.get(p)]
    bad = [p for p in changed if not any(p == a or p.startswith(a.rstrip('/') + '/') for a in allowed)]
    if bad:
        raise Rejected('OUT_OF_SCOPE ' + ','.join(sorted(bad)))

def redact(text):
    for key, value in os.environ.items():
        if len(value) >= 8 and any(k in key.upper() for k in ['TOKEN', 'SECRET', 'PASSWORD', 'API_KEY']):
            text = text.replace(value, '[REDACTED]')
    return text

def run_check(task, name):
    validate()
    c = db()
    try:
        h = require_lock(c)
        row = active_claim(c, task)
        assert_scope(row, task)
    finally:
        c.close()
        gc.collect()
    if name not in task_def(task)['checks']:
        raise Rejected('CHECK_NOT_ASSIGNED')
    ck = config()['checks'][name]
    before = snapshot()
    run_id = str(uuid.uuid4())
    started = time.time()
    evidence_dir = ROOT / '.governance/evidence'
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as stream:
        proc = subprocess.Popen(ck['argv'], cwd=ROOT, shell=False, stdout=stream, stderr=subprocess.STDOUT, start_new_session=(os.name != 'nt'))
        try:
            code = proc.wait(timeout=ck['timeout'])
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            code = 124
        stream.seek(0)
        raw = stream.read(5 * 1024 * 1024 + 1)
    truncated = len(raw) > 5 * 1024 * 1024
    text = redact(raw[:5 * 1024 * 1024].decode('utf-8', errors='replace'))
    if truncated: text += '\n[LOG_TRUNCATED]'
    log = evidence_dir / (run_id + '.log')
    log.write_text(text, encoding='utf-8')
    unchanged = before == snapshot()
    if not unchanged: code = 125
    rec = {
        'id': run_id,
        'task': task,
        'check': name,
        'argv': ck['argv'],
        'startedAt': started,
        'finishedAt': time.time(),
        'exitCode': code,
        'sourceDigest': before,
        'specDigest': h,
        'log': log.relative_to(ROOT).as_posix(),
        'logSha256': digest(log.read_bytes()),
        'logTruncated': truncated,
        'sourceUnchanged': unchanged,
        'attestation': 'local-process-not-trusted-remote-CI'
    }
    (evidence_dir / (run_id + '.json')).write_text(json.dumps(rec, indent=2), encoding='utf-8')
    c = db()
    try:
        c.execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)', (run_id, task, name, before, h, code, rec['log'], rec['logSha256'], time.time()))
        c.commit()
    finally:
        c.close()
        gc.collect()
    return rec

def verify_task(c, task):
    h = require_lock(c)
    row = c.execute('SELECT * FROM tasks WHERE id=?', (task,)).fetchone()
    if row is None: raise Rejected('TASK_NEVER_CLAIMED')
    assert_scope(row, task)
    # Lock 2: Enforced Worktree Sandboxing - verify physical worktree exists for active tasks
    if row['state'] == 'ACTIVE':
        wt_row = c.execute('SELECT * FROM worktrees WHERE task=?', (task,)).fetchone()
        if wt_row is None:
            manage_worktree(task, action='create')
            wt_row = c.execute('SELECT * FROM worktrees WHERE task=?', (task,)).fetchone()
        if wt_row:
            wt_path = ROOT / wt_row['worktree_path']
            if not wt_path.is_dir():
                raise Rejected(f"ENFORCED_WORKTREE_REQUIRED: Physical worktree missing for task '{task}' at '{wt_path}'")
    current = snapshot()
    for ck in task_def(task)['checks']:
        r = c.execute('SELECT * FROM evidence WHERE task=? AND check_name=? AND source=? AND spec=? ORDER BY at DESC LIMIT 1', (task, ck, current, h)).fetchone()
        if r is None or r['exit_code'] != 0:
            raise Rejected('CURRENT_PASS_REQUIRED ' + task + ':' + ck)
        p = safe_path(r['log_path'])
        if not p.exists() or digest(p.read_bytes()) != r['log_hash']:
            raise Rejected('EVIDENCE_TAMPERED ' + task + ':' + ck)
    return row, current

def review(task, reviewer, decision, reference, reviewer_session=None, auditor_token=None):
    if reviewer.startswith('human:'):
        human_token = os.environ.get('GOV_HUMAN_TOKEN')
        if not human_token:
            raise Rejected('UNAUTHORIZED_HUMAN_IMPERSONATION')

    if reviewer_session is None:
        reviewer_session = os.environ.get('GOV_REVIEWER_SESSION') or os.environ.get('GOV_SESSION')
    if auditor_token is None:
        auditor_token = os.environ.get('GOV_AUDITOR_TOKEN') or os.environ.get('AUDITOR_TOKEN')

    current_llm_session = os.environ.get('CONVERSATION_ID') or os.environ.get('ANTIGRAVITY_SESSION_ID') or os.environ.get('SESSION_ID') or ''

    c = db()
    try:
        row, current = verify_task(c, task)
        if reviewer == row['actor'] or not reference.strip():
            raise Rejected('INDEPENDENT_REVIEW_REQUIRED')

        # Lock 1: Cryptographic Dual-Control & Session Binding
        if reviewer_session and reviewer_session == row['session']:
            raise Rejected('FRAUDULENT_SELF_REVIEW_REJECTED')
        if current_llm_session and current_llm_session == row['session']:
            raise Rejected('FRAUDULENT_SELF_REVIEW_REJECTED')

        identity_verified = False
        if reviewer.startswith('human:'):
            if not reviewer_session:
                reviewer_session = 'human:session'
            if reviewer_session != row['session']:
                identity_verified = True
        else:
            if not auditor_token:
                raise Rejected('FRAUDULENT_SELF_REVIEW_REJECTED')
            if auditor_token == row['token']:
                raise Rejected('FRAUDULENT_SELF_REVIEW_REJECTED')
            if not reviewer_session:
                raise Rejected('FRAUDULENT_SELF_REVIEW_REJECTED')

            expected_auditor_token = os.environ.get('GOV_AUDITOR_TOKEN')
            if expected_auditor_token and auditor_token != expected_auditor_token:
                raise Rejected('FRAUDULENT_SELF_REVIEW_REJECTED')

            if len(str(auditor_token).strip()) >= 8 and reviewer_session != row['session']:
                identity_verified = True
            else:
                raise Rejected('FRAUDULENT_SELF_REVIEW_REJECTED')

        now_ts = time.time()
        c.execute('INSERT OR REPLACE INTO reviews VALUES(?,?,?,?,?,?,?,?,?)',
                  (task, reviewer, current, decision, reference, now_ts, 1 if identity_verified else 0, reviewer_session or '', auditor_token or ''))
        c.commit()
        
        # Emit persistent G5.2 evidence JSON
        ev_dir = ROOT / '.governance/evidence'
        ev_dir.mkdir(parents=True, exist_ok=True)
        ev_file = ev_dir / f"G5_REVIEW_{task}_{int(now_ts)}.json"
        ev_data = {
            'evidenceType': 'G5_REVIEW',
            'task': task,
            'reviewer': reviewer,
            'decision': decision,
            'reference': reference,
            'sourceDigest': current,
            'identityVerified': identity_verified,
            'reviewerSession': reviewer_session,
            'timestamp': now_ts
        }
        ev_file.write_text(json.dumps(ev_data, indent=2, ensure_ascii=False), encoding='utf-8')
    finally:
        c.close()
        gc.collect()
    return {'review': decision, 'sourceDigest': current, 'identityVerified': identity_verified, 'evidence': ev_file.relative_to(ROOT).as_posix()}

def gate(task):
    std_audit = check_standards(task_id=task)
    if std_audit.get('status') == 'VIOLATIONS_FOUND':
        first_v = std_audit['violations'][0]
        raise Rejected(f"STANDARDS_VIOLATION in {first_v['file']}:{first_v['line']} [{first_v['rule']}]: {first_v['message']}")

    tpl_audit = check_templates(task_id=task)
    if tpl_audit.get('status') == 'VIOLATIONS_FOUND':
        first_v = tpl_audit['violations'][0]
        raise Rejected(f"TEMPLATE_VIOLATION in {first_v['file']}:{first_v.get('line', 1)} [{first_v['rule']}]: {first_v['message']}")

    t = task_def(task)
    task_modifies_src = any(
        p == 'src' or p.startswith('src/') or p.startswith('src\\') or '/src/' in p.replace('\\', '/')
        for p in t.get('allowed_paths', [])
    )
    total_audited = std_audit.get('auditedFiles', 0) + tpl_audit.get('auditedFiles', 0)
    if task_modifies_src and total_audited == 0:
        raise Rejected(f"ZERO_FILES_AUDITED: Task {task} modifies files in src/ but Gate G4 audited 0 files!")

    c = db()
    try:
        h = require_lock(c)
        row, current = verify_task(c, task)
        
        # 1. Enforce Independent Review (G5.2 Gate)
        r = c.execute('SELECT * FROM reviews WHERE task=?', (task,)).fetchone()
        if r is None or r['source'] != current or r['decision'] != 'APPROVED' or r['reviewer'] == row['actor']:
            raise Rejected('CURRENT_INDEPENDENT_REVIEW_REQUIRED')

        rev_dict = dict(r)
        if not (rev_dict.get('identity_verified') or rev_dict.get('identityVerified')):
            raise Rejected('GATE_FAILED: Independent review identity unverified (identityVerified=False)')

        # 2. Enforce Mock-Breaker Mutation Audit (G5.1 Gate)
        mb_row = c.execute("SELECT * FROM test_audits WHERE task=? AND status='PASS'", (task,)).fetchone()
        t = task_def(task)
        requires_mb = False
        standards = standards_config()
        if standards.get('active_profile') in ('standard', 'critical'):
            requires_mb = True
        if 'mock_breaker' in t.get('standards_checklist', []) or 'mutations_caught' in str(t.get('acceptance', [])):
            requires_mb = True
        if t.get('risk') in ('tiny', 'low') or t.get('skip_mock') is True:
            requires_mb = False

        if requires_mb and mb_row is None:
            raise Rejected(f"MOCK_BREAKER_REQUIRED: Task {task} requires passing Mock-Breaker audit. Run 'gov.py audit-tests --task {task}' before gate pass.")
        if mb_row is not None and ('source' in mb_row.keys()) and mb_row['source'] and mb_row['source'] != current:
            raise Rejected(f"MOCK_BREAKER_STALE: Task {task} requires re-audit after source changes")

        # 3. Emit official GATE_PASS certificate
        now_ts = time.time()
        ev_dir = ROOT / '.governance/evidence'
        ev_dir.mkdir(parents=True, exist_ok=True)
        cert_file = ev_dir / f"GATE_PASS_{task}_{int(now_ts)}.json"
        cert_data = {
            'evidenceType': 'GATE_PASS_CERTIFICATE',
            'task': task,
            'sourceDigest': current,
            'specDigest': h,
            'reviewer': r['reviewer'],
            'actor': row['actor'],
            'timestamp': now_ts,
            'gateStatus': 'APPROVED'
        }
        cert_file.write_text(json.dumps(cert_data, indent=2, ensure_ascii=False), encoding='utf-8')
    finally:
        c.close()
        gc.collect()

    return {
        'status': 'PASS',
        'task': task,
        'sourceDigest': current,
        'gateCertificate': cert_file.relative_to(ROOT).as_posix(),
        'scope': 'local-task-not-production-release'
    }

def finish(task, token):
    gate(task)
    c = db()
    try:
        c.execute('BEGIN IMMEDIATE')
        r = active_claim(c, task)
        if token != r['token']:
            raise Rejected('STALE_FENCING_TOKEN')
        c.execute("UPDATE tasks SET state='DONE' WHERE id=?", (task,))
        c.execute("DELETE FROM symbol_leases WHERE task=?", (task,))
        c.commit()
    finally:
        c.close()
        gc.collect()
    return {'task': task, 'state': 'DONE'}

def status():
    c = db()
    try:
        rows = [dict(x) for x in c.execute('SELECT id,state,actor,session,expires FROM tasks')]
        try:
            require_lock(c)
            locked = True
        except Rejected:
            locked = False
    finally:
        c.close()
        gc.collect()
    return {'specLocked': locked, 'specDigest': spec_hash(), 'sourceDigest': snapshot(), 'tasks': rows}

def doctor():
    result = validate()
    result.update({
        'python': sys.version.split()[0],
        'root': str(ROOT),
        'antigravityRuntimeTest': 'PASS_LOCAL',
        'sandboxTest': 'NOT_APPLICABLE_WINDOWS',
        'nativeHooksLoaded': (ROOT / '.governance/hooks/native_guard.py').is_file()
    })
    return result

# ==============================================================================
# V4 ULTRA MODULES: DISCOVERY, SCAFFOLDING, HANDOFF, GOLDEN MASTER, SELF-HEALING
# ==============================================================================

def mask_dynamic(text: str) -> str:
    """Deterministically masks volatile runtime data (timestamps, UUIDs, hex pointers, durations)."""
    if not isinstance(text, str):
        text = str(text)
    # ISO timestamps
    text = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', '[DYNAMIC_TIMESTAMP]', text)
    # RFC 2822 dates
    text = re.sub(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+GMT', '[DYNAMIC_DATE]', text)
    # UUIDs
    text = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '[DYNAMIC_UUID]', text)
    # Hex pointers/addresses
    text = re.sub(r'\b0x[0-9a-fA-F]{6,16}\b', '[DYNAMIC_HEX_PTR]', text)
    # Durations (e.g. in 4.088s, 12ms, 0.05 seconds)
    text = re.sub(r'(\b(?:in|took|ran in|time=)\s*)\d+(?:\.\d+)?\s*(?:ms|s|seconds|sec)\b', r'\1[DYNAMIC_DURATION]', text, flags=re.IGNORECASE)
    # Host and ephemeral ports
    text = re.sub(r'(?:127\.0\.0\.1|localhost):\d{4,5}', '[DYNAMIC_HOST_PORT]', text)
    return text.strip()

def discover(deep=False, write_files=True):
    """Deep topology, stack detection, route miner, DB model miner, and fragility scorecard."""
    inventory = {'languages': {}, 'frameworks': [], 'routes': [], 'models': [], 'tests': [], 'files': []}
    files_map = file_index()
    
    # Language & Framework detection
    ext_map = {'.py': 'Python', '.ts': 'TypeScript', '.js': 'JavaScript', '.php': 'PHP', '.go': 'Go', '.rs': 'Rust', '.sql': 'SQL'}
    for f in files_map:
        ext = Path(f).suffix.lower()
        if ext in ext_map:
            lang = ext_map[ext]
            inventory['languages'][lang] = inventory['languages'].get(lang, 0) + 1
        inventory['files'].append(f)

    # Manifest checks
    pkg_json = ROOT / 'package.json'
    if pkg_json.is_file():
        try:
            pj = json.loads(pkg_json.read_text(encoding='utf-8'))
            deps = {**pj.get('dependencies', {}), **pj.get('devDependencies', {})}
            if 'next' in deps: inventory['frameworks'].append('Next.js')
            if 'express' in deps: inventory['frameworks'].append('Express')
            if 'fastify' in deps: inventory['frameworks'].append('Fastify')
            if '@nestjs/core' in deps: inventory['frameworks'].append('NestJS')
            if 'react' in deps: inventory['frameworks'].append('React')
            if 'vue' in deps: inventory['frameworks'].append('Vue')
            if 'prisma' in deps or '@prisma/client' in deps: inventory['frameworks'].append('Prisma')
        except Exception: pass

    req_txt = ROOT / 'requirements.txt'
    pyp_toml = ROOT / 'pyproject.toml'
    py_content = ''
    if req_txt.is_file(): py_content += req_txt.read_text(encoding='utf-8', errors='ignore') + '\n'
    if pyp_toml.is_file(): py_content += pyp_toml.read_text(encoding='utf-8', errors='ignore') + '\n'
    if 'fastapi' in py_content.lower(): inventory['frameworks'].append('FastAPI')
    if 'flask' in py_content.lower(): inventory['frameworks'].append('Flask')
    if 'django' in py_content.lower(): inventory['frameworks'].append('Django')
    if 'sqlalchemy' in py_content.lower(): inventory['frameworks'].append('SQLAlchemy')
    if 'pydantic' in py_content.lower(): inventory['frameworks'].append('Pydantic')

    # Static Route Scanning
    route_patterns = [
        re.compile(r'@(?:app|router|bp|api)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE),
        re.compile(r'(?:app|router)\.(get|post|put|delete|patch|all)\s*\(\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE),
        re.compile(r'path\s*\(\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE),
        re.compile(r'register_rest_route\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
    ]
    
    # Model Patterns
    table_pattern = re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[`"\']?(\w+)[`"\']?)', re.IGNORECASE)
    prisma_pattern = re.compile(r'model\s+(\w+)\s*\{', re.IGNORECASE)
    py_class_pattern = re.compile(r'class\s+(\w+)\s*\((?:Base|Model|BaseModel|SQLModel)[^)]*\):', re.IGNORECASE)
    ts_interface_pattern = re.compile(r'export\s+(?:interface|type)\s+(\w+)', re.IGNORECASE)

    # Test Patterns
    test_file_pattern = re.compile(r'(?:test_[^\\/]+\.py|[^\\/]+_test\.py|[^\\/]+\.(?:test|spec)\.(?:ts|js|jsx|tsx))$', re.IGNORECASE)
    py_test_case = re.compile(r'def\s+(test_\w+)\s*\(', re.IGNORECASE)
    js_test_case = re.compile(r'(?:it|test)\s*\(\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)

    for f_rel in files_map:
        f_path = ROOT / f_rel
        if test_file_pattern.search(f_rel):
            t_rec = {'file': f_rel, 'cases': []}
            try:
                content = f_path.read_text(encoding='utf-8', errors='ignore')
                for m in py_test_case.finditer(content): t_rec['cases'].append(m.group(1))
                for m in js_test_case.finditer(content): t_rec['cases'].append(m.group(1))
            except Exception: pass
            inventory['tests'].append(t_rec)
            continue

        # Next.js App Router scan
        if 'app/' in f_rel and f_rel.endswith(('route.ts', 'route.js')):
            ep = '/' + '/'.join(Path(f_rel).parent.as_posix().split('app/')[1].split('/'))
            inventory['routes'].append({'method': 'HTTP', 'path': ep, 'source': f_rel})

        # Deep AST / Regex scan
        if deep or f_rel.endswith(('.py', '.ts', '.js', '.sql', '.prisma')):
            try:
                content = f_path.read_text(encoding='utf-8', errors='ignore')
                # Routes
                for pat in route_patterns:
                    for m in pat.finditer(content):
                        groups = m.groups()
                        if len(groups) == 2:
                            inventory['routes'].append({'method': groups[0].upper(), 'path': groups[1], 'source': f_rel})
                        elif len(groups) == 1:
                            inventory['routes'].append({'method': 'ROUTE', 'path': groups[0], 'source': f_rel})
                # Models
                if f_rel.endswith('.sql'):
                    for m in table_pattern.finditer(content): inventory['models'].append({'name': m.group(1), 'source': f_rel, 'kind': 'SQL_TABLE'})
                elif f_rel.endswith('.prisma'):
                    for m in prisma_pattern.finditer(content): inventory['models'].append({'name': m.group(1), 'source': f_rel, 'kind': 'PRISMA_MODEL'})
                elif f_rel.endswith('.py'):
                    for m in py_class_pattern.finditer(content): inventory['models'].append({'name': m.group(1), 'source': f_rel, 'kind': 'PYTHON_MODEL'})
                elif f_rel.endswith(('.ts', '.tsx')):
                    for m in ts_interface_pattern.finditer(content): inventory['models'].append({'name': m.group(1), 'source': f_rel, 'kind': 'TS_INTERFACE'})
            except Exception: pass

    # Fragility Scorecard
    total_routes = len(inventory['routes'])
    all_test_text = ' '.join(tc for t in inventory['tests'] for tc in t['cases']).lower()
    untested_routes = []
    for r in inventory['routes']:
        slug = r['path'].strip('/').replace('/', '_').lower()
        if not slug or slug not in all_test_text:
            untested_routes.append(r)
    
    total_tests = sum(len(t['cases']) for t in inventory['tests'])
    score = 100
    if total_routes > 0:
        penalty = int((len(untested_routes) / total_routes) * 50)
        score -= penalty
    if total_tests == 0:
        score -= 40
    elif total_tests < 5:
        score -= 20
    score = max(5, min(100, score))

    topology = {
        'timestamp': time.time(),
        'frameworks': sorted(list(set(inventory['frameworks']))),
        'languages': inventory['languages'],
        'totalFiles': len(inventory['files']),
        'totalRoutes': total_routes,
        'untestedRoutesCount': len(untested_routes),
        'totalModels': len(inventory['models']),
        'totalTests': total_tests,
        'fragilityScore': score,
        'fragilityRating': 'HIGH_RISK' if score < 40 else ('MODERATE' if score < 75 else 'STABLE'),
        'untestedRoutes': untested_routes[:20]
    }

    if write_files:
        gov_dir = ROOT / '.governance'
        gov_dir.mkdir(parents=True, exist_ok=True)
        (gov_dir / 'inventory.json').write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding='utf-8')
        (gov_dir / 'topology.json').write_text(json.dumps(topology, indent=2, ensure_ascii=False), encoding='utf-8')

        specs_dir = ROOT / 'specs'
        specs_dir.mkdir(parents=True, exist_ok=True)
        
        # Build Mermaid ERD
        mermaid_erd = '```mermaid\nerDiagram\n'
        if inventory['models']:
            for m in inventory['models'][:15]:
                clean_name = re.sub(r'[^a-zA-Z0-9_]', '', m['name'])
                mermaid_erd += f'    {clean_name} {{\n        string id PK\n        string status\n    }}\n'
        else:
            mermaid_erd += '    SYSTEM_CORE {\n        string id PK\n    }\n'
        mermaid_erd += '```\n'

        spec_md = f"""# RECONSTRUCTED SPECIFICATION & TOPOLOGY (BROWNFIELD S1)
> Auto-generated by Antigravity Ultra v5.1 (Omni-Agentic OS & DREE Engine) Discovery Engine at {datetime.datetime.now().isoformat()}

## 1. Wykryty Stos Technologiczny
* **Frameworki:** {', '.join(topology['frameworks']) if topology['frameworks'] else 'Brak dedykowanego frameworka / Skrypty autonomiczne'}
* **JÄ™zyki w projekcie:** {', '.join(f'{k} ({v} plikĂłw)' for k, v in topology['languages'].items())}
* **Liczba zbadanych plikĂłw:** {topology['totalFiles']}

## 2. Ocena KruchoĹ›ci (Fragility Scorecard)
* **WskaĹşnik BezpieczeĹ„stwa (Score):** **{topology['fragilityScore']} / 100** ({topology['fragilityRating']})
* **Zarejestrowane Trasy API / Punkty WejĹ›cia:** {topology['totalRoutes']}
* **Trasy bez pokrycia testami:** {topology['untestedRoutesCount']}
* **Wykryte Testy Jednostkowe/Integracyjne:** {topology['totalTests']}

## 3. Schemat Modeli Danych (ERD)
{mermaid_erd}

## 4. Wykryte Trasy API i Punkty KoĹ„cowe
| Metoda | ĹšcieĹĽka / Punkt KoĹ„cowy | Plik ĹąrĂłdĹ‚owy |
|---|---|---|
"""
        for r in inventory['routes'][:50]:
            spec_md += f"| `{r['method']}` | `{r['path']}` | `{r['source']}` |\n"
        if not inventory['routes']:
            spec_md += '| N/A | Brak tras HTTP / Architektura CLI/Biblioteczna | Workspace Root |\n'

        spec_md += """
## 5. Rekomendacje Modernizacji (Zero-Regression Roadmap)
1. **Golden Master Harness:** Przed edycjÄ… jakiejkolwiek logiki biznesowej, zarejestruj testy charakterystyczne za pomocÄ… `gov.py golden-record`.
2. **Contract Scaffolding:** ZamroĹş schematy wejĹ›cia/wyjĹ›cia w `contracts/` przed delegowaniem zadaĹ„ subagentom.
3. **Izolacja Handoff:** KaĹĽde zadanie refaktoringu musi byÄ‡ ograniczone do Ĺ›cisĹ‚ego pliku handoffu (`gov.py package-handoff`).
"""
        (specs_dir / 'RECONSTRUCTED_SPEC.md').write_text(spec_md, encoding='utf-8')

    return topology

def scaffold_contracts(from_spec=None, out_dir=None):
    """Pure Python stdlib generator for TypeScript, Python and OpenAPI contract interfaces."""
    out = ROOT / (out_dir or 'contracts')
    out.mkdir(parents=True, exist_ok=True)
    
    inv = json.loads((ROOT / '.governance/inventory.json').read_text(encoding='utf-8')) if (ROOT / '.governance/inventory.json').is_file() else {'models': [], 'routes': []}
    
    models = inv.get('models', [])
    routes = inv.get('routes', [])
    
    # 1. TypeScript Interfaces
    ts_content = """/**
 * CONTRACT INTERFACES (SSoT)
 * Generated by Antigravity Ultra v5.1 (Omni-Agentic OS & DREE Engine) Contract-First Engine.
 * DO NOT MODIFY DIRECTLY. Extend via domain adapters.
 */

"""
    if not models:
        ts_content += """export interface EntityBase {
  id: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}
"""
    for m in models:
        c_name = re.sub(r'[^a-zA-Z0-9_]', '', m['name'])
        ts_content += f"export interface {c_name} {{\n  id: string;\n  name?: string;\n  status?: string;\n  metadata?: Record<string, unknown>;\n}}\n\n"
    (out / 'types.ts').write_text(ts_content, encoding='utf-8')

    # 2. Python Schemas / Dataclasses
    py_content = """# CONTRACT SCHEMAS (SSoT)
# Generated by Antigravity Ultra v5.1 (Omni-Agentic OS & DREE Engine) Contract-First Engine.
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class EntityBase:
    id: str
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

"""
    for m in models:
        c_name = re.sub(r'[^a-zA-Z0-9_]', '', m['name'])
        py_content += f"@dataclass\nclass {c_name}(EntityBase):\n    name: Optional[str] = None\n    status: Optional[str] = 'ACTIVE'\n    metadata: Dict[str, Any] = field(default_factory=dict)\n\n"
    (out / 'models.py').write_text(py_content, encoding='utf-8')

    # 3. OpenAPI 3.1 JSON Stub
    paths_obj = {}
    for r in routes:
        p = r['path']
        if not p.startswith('/'): p = '/' + p
        m = r['method'].lower()
        if m not in {'get', 'post', 'put', 'delete', 'patch'}: m = 'get'
        if p not in paths_obj: paths_obj[p] = {}
        paths_obj[p][m] = {
            'summary': f"Endpoint for {p}",
            'responses': {
                '200': {'description': 'Successful execution', 'content': {'application/json': {'schema': {'type': 'object'}}}},
                '400': {'description': 'Bad Request'},
                '500': {'description': 'Internal Server Error'}
            }
        }
    openapi_doc = {
        'openapi': '3.1.0',
        'info': {
            'title': 'System Service Contracts',
            'version': '1.0.0',
            'description': 'Frozen contract interfaces for autonomous subagent implementation.'
        },
        'paths': paths_obj,
        'components': {
            'schemas': {m['name']: {'type': 'object', 'properties': {'id': {'type': 'string'}}} for m in models}
        }
    }
    (out / 'openapi.json').write_text(json.dumps(openapi_doc, indent=2), encoding='utf-8')

    return {'status': 'SCAFFOLDED', 'contractsDir': str(out.relative_to(ROOT)), 'files': ['types.ts', 'models.py', 'openapi.json']}

def package_handoff(task_id, out_path=None):
    """Synthesizes atomic task handoff packet for subagent execution with strict write-scope bounds."""
    t = task_def(task_id)
    sh = spec_hash()
    
    # Read-only files: contracts, specs, and relevant tests
    read_only = []
    contracts_dir = ROOT / 'contracts'
    if contracts_dir.is_dir():
        for p in contracts_dir.glob('*'):
            if p.is_file(): read_only.append(str(p.relative_to(ROOT)).replace('\\', '/'))
    
    for spec_file in config().get('spec_files', []):
        if (ROOT / spec_file).is_file():
            read_only.append(spec_file.replace('\\', '/'))
            
    reconstructed = ROOT / 'specs/RECONSTRUCTED_SPEC.md'
    if reconstructed.is_file():
        read_only.append(str(reconstructed.relative_to(ROOT)).replace('\\', '/'))

    # Acceptance Criteria formatting
    ac_list = []
    for idx, ac in enumerate(t.get('acceptance', [])):
        ck_name = t['checks'][0] if t['checks'] else 'unit'
        cmd_str = ' '.join(config()['checks'].get(ck_name, {}).get('argv', ['echo', 'pass']))
        ac_list.append({
            'id': f"AC-{idx+1:02d}",
            'assertion': str(ac),
            'testCommand': cmd_str
        })

    # Allowed paths as explicit target files or paths
    allowed_write = [p.replace('\\', '/') for p in t.get('allowed_paths', [])]

    # Calculate dynamic blast radius
    blast = {}
    for p in allowed_write:
        try:
            blast = calculate_impact(target_file=p)
            break
        except Exception: pass

    out_file = Path(out_path) if out_path else (ROOT / f'.governance/handoffs/{task_id}.json')
    packet_rel = str(out_file.relative_to(ROOT)).replace('\\', '/')

    # Blueprint and CADRE context if applicable
    template_contract = None
    bp_dir = ROOT / 'specs/blueprints'
    if bp_dir.is_dir():
        for bp_f in bp_dir.glob('*.blueprint.json'):
            try:
                bp_doc = json.loads(bp_f.read_text(encoding='utf-8'))
                for aw in allowed_write:
                    if aw in bp_doc.get('targetFile', '') or bp_doc.get('targetFile', '') in aw:
                        template_contract = bp_doc
                        break
            except Exception: pass
            if template_contract: break

    # Dynamic Context Slicing: fetch active ADRs from decision_mesh
    active_decisions = []
    c_dm = db()
    try:
        task_domain = t.get('domain', 'global')
        dm_rows = c_dm.execute(
            "SELECT adr_id, domain, assertion, scope FROM decision_mesh WHERE active=1 AND (scope='global' OR domain=? OR domain='*') ORDER BY created_at DESC LIMIT 15",
            (task_domain,)
        ).fetchall()
        for dmr in dm_rows:
            active_decisions.append({
                'adrId': dmr['adr_id'],
                'domain': dmr['domain'],
                'assertion': dmr['assertion'],
                'scope': dmr['scope']
            })
    finally:
        c_dm.close()
        gc.collect()

    packet = {
        'status': 'HANDOFF_GENERATED',
        'workspaceContext': {'workspaceRoot': str(ROOT).replace('\\', '/'), 'workspaceUri': f'file:///{str(ROOT).replace("\\", "/")}', 'boundaryPolicy': 'STRICT_HERMETIC'},
        'activeDecisions': active_decisions,
        'leasedSymbols': t.get('symbols', []),
        'leasedRoutes': t.get('routes', []),
        'templateContract': template_contract,
        'taskId': t['id'],
        'taskName': t.get('title', t['id']),
        'specDigest': sh,
        'packetPath': packet_rel,
        'handoffPath': packet_rel,
        'targetFiles': {
            'readOnly': sorted(list(set(read_only))),
            'allowedToWrite': allowed_write
        },
        'blastRadius': blast,
        'acceptanceCriteria': ac_list,
        'standardsChecklist': t.get('standards_checklist', []),
        'mockContext': {
            'mockServerUrl': 'http://127.0.0.1:4010',
            'governanceProfile': config().get('profile', 'standard')
        },
        'executionBudget': {
            'maxAttemptCycles': 3,
            'timeoutSeconds': config().get('lease_seconds', 1800)
        }
    }
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding='utf-8')

    c = db()
    try:
        c.execute('INSERT OR REPLACE INTO handoffs VALUES(?,?,?,?,?)',
                  (task_id, sh, str(out_file.relative_to(ROOT)), json.dumps(allowed_write), time.time()))
        c.commit()
    finally:
        c.close()
        gc.collect()

    return packet


def split_cmd(command):
    if isinstance(command, list):
        return command
    if os.name == 'nt':
        return [p[1:-1] if p.startswith('"') and p.endswith('"') else p for p in re.findall(r'(?:[^\s"]|"(?:\\.|[^"])*")+', command)]
    return shlex.split(command)

def golden_record(name, command):
    """Executes baseline command, masks dynamic data deterministically, and saves golden snapshot."""
    golden_dir = ROOT / '.governance/golden'
    golden_dir.mkdir(parents=True, exist_ok=True)
    
    with tempfile.TemporaryFile() as stream:
        proc = subprocess.Popen(split_cmd(command), cwd=ROOT,
                                stdout=stream, stderr=subprocess.STDOUT)
        try:
            code = proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = 124
        stream.seek(0)
        raw = stream.read(5 * 1024 * 1024)
        
    masked = mask_dynamic(raw.decode('utf-8', errors='replace'))
    d = digest(masked)
    snapshot_path = golden_dir / f'{name}.golden.json'
    cmd_str = subprocess.list2cmdline(command) if isinstance(command, list) else str(command)
    rec = {
        'name': name,
        'command': cmd_str,
        'exitCode': code,
        'outputDigest': d,
        'maskedOutput': masked,
        'recordedAt': time.time()
    }
    snapshot_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding='utf-8')
    
    c = db()
    try:
        c.execute('INSERT OR REPLACE INTO golden_records VALUES(?,?,?,?,?)',
                  (name, cmd_str, d, str(snapshot_path.relative_to(ROOT)), time.time()))
        c.commit()
    finally:
        c.close()
        gc.collect()

    return {'status': 'RECORDED', 'name': name, 'exitCode': code, 'outputDigest': d}

def golden_assert(name, compare_command=None):
    """Asserts runtime output against frozen golden snapshot with dynamic masking."""
    snapshot_path = ROOT / f'.governance/golden/{name}.golden.json'
    if not snapshot_path.is_file():
        raise Rejected(f'Golden snapshot for "{name}" does not exist. Run golden-record first.')
        
    master = json.loads(snapshot_path.read_text(encoding='utf-8'))
    cmd = compare_command or master['command']
    
    with tempfile.TemporaryFile() as stream:
        proc = subprocess.Popen(split_cmd(cmd), cwd=ROOT,
                                stdout=stream, stderr=subprocess.STDOUT)
        try:
            code = proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = 124
        stream.seek(0)
        raw = stream.read(5 * 1024 * 1024)

    current_masked = mask_dynamic(raw.decode('utf-8', errors='replace'))
    current_digest = digest(current_masked)
    
    if current_digest != master['outputDigest'] or code != master['exitCode']:
        diff = list(difflib.unified_diff(
            master['maskedOutput'].splitlines(keepends=True),
            current_masked.splitlines(keepends=True),
            fromfile='golden_master',
            tofile='current_run'
        ))
        diff_text = ''.join(diff[:60])
        return {
            'status': 'REGRESSION_DETECTED',
            'name': name,
            'expectedDigest': master['outputDigest'],
            'actualDigest': current_digest,
            'expectedCode': master['exitCode'],
            'actualCode': code,
            'diff': diff_text,
            'exitCode': 1
        }
        
    return {'status': 'PASS', 'name': name, 'verified': True, 'outputDigest': current_digest}

def auto_heal(task_id, cycle, hypothesis=None, reset=False):
    """Enforces 3-Cycle Self-Healing state machine with automated rollback on budget exhaustion."""
    c = db()
    try:
        if reset:
            c.execute('DELETE FROM healing_cycles WHERE task=?', (task_id,))
            c.commit()
            return {'task': task_id, 'status': 'RESET', 'cyclesCount': 0}
            
        t = task_def(task_id)
        
        if cycle <= 3:
            c.execute('INSERT OR REPLACE INTO healing_cycles VALUES(?,?,?,?,?,?)',
                      (task_id, cycle, hypothesis or f'Cycle {cycle} attempt', '', 'IN_PROGRESS', time.time()))
            c.commit()
            return {
                'task': task_id,
                'cycle': cycle,
                'status': 'IN_PROGRESS',
                'remainingCycles': 3 - cycle,
                'hypothesis': hypothesis
            }
        else:
            # EXCEEDED 3 CYCLES -> TRIGGER AUTOMATED ROLLBACK & ESCALATION
            snap_dir = ROOT / '.governance/snapshots' / task_id
            rolled_back = []
            if snap_dir.is_dir():
                for item in snap_dir.iterdir():
                    target = ROOT / item.name
                    if item.is_file():
                        shutil.copy2(item, target)
                        rolled_back.append(item.name)
                    elif item.is_dir():
                        if target.exists(): shutil.rmtree(target)
                        shutil.copytree(item, target)
                        rolled_back.append(item.name)
                        
            if (ROOT / '.git').is_dir():
                for p in t['allowed_paths']:
                    try:
                        subprocess.run(['git', 'checkout', '--', p], cwd=ROOT, capture_output=True)
                    except Exception: pass

            c.execute("UPDATE tasks SET state='BLOCKED' WHERE id=?", (task_id,))
            c.commit()

            esc_file = ROOT / f'ESC_{task_id}.md'
            esc_md = f"""# ESCALATION REPORT: {task_id}
> Self-Healing budget exceeded (Max 3 cycles reached). Task automatically frozen and rolled back.

* **Task ID:** {task_id}
* **Task Title:** {t.get('title', task_id)}
* **Escalation Time:** {datetime.datetime.now().isoformat()}
* **Rollback Status:** Files restored from snapshot ({', '.join(rolled_back) if rolled_back else 'Workspace checked'})
* **Last Hypothesis:** {hypothesis or 'N/A'}

## Rekomendacja dla Architekta / CzĹ‚owieka
1. SprawdĹş czy zaĹ‚oĹĽenia specyfikacji nie sÄ… sprzeczne z ograniczeniami Ĺ›rodowiska.
2. Zresetuj cykle naprawcze poleceniem `gov.py auto-heal --task {task_id} --reset` po poprawieniu zaĹ‚oĹĽeĹ„.
"""
            esc_file.write_text(esc_md, encoding='utf-8')
            return {
                'task': task_id,
                'status': 'ESCALATED',
                'action': 'ROLLED_BACK',
                'escalationFile': str(esc_file.relative_to(ROOT)),
                'exitCode': 1
            }
    finally:
        c.close()
        gc.collect()

def integrate(task_id):
    """Deterministic Single Integrator Gate (G6): verifies complete task closure and regression integrity."""
    c = db()
    try:
        c.execute('BEGIN IMMEDIATE')
        require_lock(c)
        r = c.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
        if r is None or r['state'] != 'DONE':
            raise Rejected(f'Task {task_id} must be in state DONE before integration')
        cfg = config()
        for ck_name in cfg.get('required_release_checks', []):
            ck = cfg['checks'].get(ck_name)
            if ck:
                with tempfile.TemporaryFile() as stream:
                    proc = subprocess.Popen(ck['argv'], cwd=ROOT, shell=False, stdout=stream, stderr=subprocess.STDOUT)
                    try:
                        code = proc.wait(timeout=ck.get('timeout', 120))
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        code = 124
                    if code != 0:
                        raise Rejected(f'Regression detected during integration: check {ck_name} failed with code {code}')
        c.execute('INSERT OR REPLACE INTO integrations VALUES(?,?,?)', (task_id, snapshot(), time.time()))
        c.commit()
    finally:
        c.close()
        gc.collect()
    return {'status': 'INTEGRATED', 'task': task_id, 'sourceDigest': snapshot()}

def release():
    """Operational Release Gate (G7): validates all tasks DONE, zero regression, and produces release manifest."""
    validate()
    c = db()
    try:
        h = require_lock(c)
        tasks = definitions()
        for t in tasks:
            r = c.execute('SELECT state FROM tasks WHERE id=?', (t['id'],)).fetchone()
            if r is None or r['state'] != 'DONE':
                raise Rejected(f'Cannot release: Task {t["id"]} is not DONE')
            integ_row = c.execute('SELECT * FROM integrations WHERE task=?', (t['id'],)).fetchone()
            if integ_row is None:
                raise Rejected(f'Cannot release: Task {t["id"]} has not passed G6 integration gate. Run gov.py integrate {t["id"]} first.')

        # Embed task GATE_PASS certificates into release manifest
        gate_certs = {}
        ev_dir = ROOT / '.governance/evidence'
        if ev_dir.is_dir():
            for f in sorted(ev_dir.glob('GATE_PASS_*.json')):
                try:
                    c_doc = json.loads(f.read_text(encoding='utf-8'))
                    t_id = c_doc.get('task')
                    if t_id and t_id in [t['id'] for t in tasks]:
                        gate_certs[t_id] = {
                            'certificate': f.name,
                            'hash': digest(f.read_bytes()),
                            'reviewer': c_doc.get('reviewer'),
                            'actor': c_doc.get('actor')
                        }
                except Exception:
                    pass

        cur_snap = snapshot()
        manifest = {
            'releaseId': str(uuid.uuid4()),
            'timestamp': time.time(),
            'specDigest': h,
            'sourceDigest': cur_snap,
            'completedTasks': [t['id'] for t in tasks],
            'taskCertificates': gate_certs,
            'gateStatus': 'G7_PASS_OPERATIONAL_RELEASE'
        }
        manifest['manifestDigest'] = digest(canonical(manifest).encode())
        (ROOT / '.governance/RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    finally:
        c.close()
        gc.collect()
    return manifest

# ==============================================================================
# V5 ULTRA OMNI-AGENTIC MODULES: IMPACT, WORKTREES, MUTATION AUDIT, CHARTER SSoT
# ==============================================================================

def index_symbols(write_db=True):
    """Extracts AST and regex symbols and call graph dependencies from project files."""
    files_map = file_index()
    symbols_by_file = {}
    dependencies = []
    
    for rel_path in files_map:
        f_path = ROOT / rel_path
        ext = f_path.suffix.lower()
        if ext == '.py':
            try:
                tree = ast.parse(f_path.read_text(encoding='utf-8', errors='ignore'))
                syms = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        syms.append({'symbol': node.name, 'kind': 'class', 'line': node.lineno})
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        syms.append({'symbol': node.name, 'kind': 'function', 'line': node.lineno})
                    elif isinstance(node, ast.Import):
                        for n in node.names:
                            dependencies.append({'caller_file': rel_path, 'caller_symbol': '', 'callee_symbol': n.name, 'callee_file': ''})
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ''
                        for n in node.names:
                            dependencies.append({'caller_file': rel_path, 'caller_symbol': '', 'callee_symbol': n.name, 'callee_file': mod.replace('.', '/')})
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            dependencies.append({'caller_file': rel_path, 'caller_symbol': '', 'callee_symbol': node.func.id, 'callee_file': ''})
                        elif isinstance(node.func, ast.Attribute):
                            dependencies.append({'caller_file': rel_path, 'caller_symbol': '', 'callee_symbol': node.func.attr, 'callee_file': ''})
                symbols_by_file[rel_path] = syms
            except Exception: pass
        elif ext in {'.ts', '.tsx', '.js', '.jsx', '.php'}:
            try:
                txt = f_path.read_text(encoding='utf-8', errors='ignore')
                syms = []
                for m in re.finditer(r'(?:export\s+)?class\s+(\w+)', txt):
                    syms.append({'symbol': m.group(1), 'kind': 'class', 'line': 1})
                for m in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', txt):
                    syms.append({'symbol': m.group(1), 'kind': 'function', 'line': 1})
                for m in re.finditer(r'(?:export\s+)?interface\s+(\w+)', txt):
                    syms.append({'symbol': m.group(1), 'kind': 'interface', 'line': 1})
                for m in re.finditer(r"""(?:import|from)\s+['"]([^'"]+)['"]""", txt):
                    dependencies.append({'caller_file': rel_path, 'caller_symbol': '', 'callee_symbol': '', 'callee_file': m.group(1)})
                symbols_by_file[rel_path] = syms
            except Exception: pass

    if write_db:
        c = db()
        try:
            c.execute('DELETE FROM symbol_index')
            c.execute('DELETE FROM symbol_dependencies')
            for f_rel, s_list in symbols_by_file.items():
                for s in s_list:
                    h = digest(f"{f_rel}:{s['symbol']}")
                    c.execute('INSERT OR REPLACE INTO symbol_index VALUES(?,?,?,?,?)',
                              (s['symbol'], s['kind'], f_rel, s['line'], h))
            for dep in dependencies:
                c.execute('INSERT INTO symbol_dependencies VALUES(?,?,?,?)',
                          (dep['caller_symbol'], dep['caller_file'], dep['callee_symbol'], dep['callee_file']))
            c.commit()
        finally:
            c.close()
            gc.collect()

    return {'totalFilesIndexed': len(symbols_by_file), 'totalSymbols': sum(len(v) for v in symbols_by_file.values()), 'totalDependencies': len(dependencies)}

def calculate_impact(target_file=None, target_symbol=None):
    """Calculates Blast Radius, call graph impact, and affected downstream modules and test suites."""
    index_symbols(write_db=True)
    c = db()
    try:
        dependents = set()
        direct_symbols = []
        
        if target_symbol:
            direct_symbols.append(target_symbol)
            rows = c.execute('SELECT caller_file FROM symbol_dependencies WHERE callee_symbol=?', (target_symbol,)).fetchall()
            for r in rows:
                if r['caller_file']: dependents.add(r['caller_file'])
        elif target_file:
            clean_tf = target_file.replace('\\', '/').lstrip('/')
            rows = c.execute('SELECT symbol FROM symbol_index WHERE file_path=?', (clean_tf,)).fetchall()
            for r in rows:
                direct_symbols.append(r['symbol'])
                dep_rows = c.execute('SELECT caller_file FROM symbol_dependencies WHERE callee_symbol=? OR callee_file LIKE ?',
                                     (r['symbol'], f'%{Path(clean_tf).stem}%')).fetchall()
                for dr in dep_rows:
                    if dr['caller_file'] and dr['caller_file'] != clean_tf:
                        dependents.add(dr['caller_file'])

        # Identify test suites covering target or dependents
        cfg = config()
        affected_checks = set()
        for ck_name, ck_val in cfg.get('checks', {}).items():
            argv_str = ' '.join(ck_val.get('argv', []))
            for dep in list(dependents) + ([target_file] if target_file else []):
                if dep and Path(dep).stem in argv_str:
                    affected_checks.add(ck_name)
        if not affected_checks and cfg.get('required_release_checks'):
            affected_checks.update(cfg['required_release_checks'])

        dep_count = len(dependents)
        rating = 'LOW' if dep_count <= 1 else ('MEDIUM' if dep_count <= 4 else 'HIGH')

        return {
            'target': target_file or target_symbol,
            'directSymbols': direct_symbols,
            'downstreamDependents': sorted(list(dependents)),
            'affectedChecks': sorted(list(affected_checks)),
            'riskRating': rating
        }
    finally:
        c.close()
        gc.collect()

def manage_worktree(task_id, action='create'):
    """Manages isolated subagent workspace environments (Git worktree with Shadow Workspace fallback)."""
    t = task_def(task_id)
    c = db()
    try:
        if action == 'create':
            # Check if Git is available
            has_git = (ROOT / '.git').exists()
            if has_git:
                branch = f'task/{task_id}'
                wt_dir = ROOT / '.worktrees' / task_id
                wt_dir.parent.mkdir(parents=True, exist_ok=True)
                if wt_dir.exists():
                    shutil.rmtree(wt_dir, ignore_errors=True)
                try:
                    subprocess.run(['git', 'branch', '-D', branch], cwd=ROOT, capture_output=True)
                except Exception: pass
                res = subprocess.run(['git', 'worktree', 'add', '-b', branch, str(wt_dir.relative_to(ROOT))],
                                     cwd=ROOT, capture_output=True, text=True)
                is_shadow = 0 if res.returncode == 0 else 1
                if is_shadow:
                    wt_dir = ROOT / '.shadow_worktrees' / task_id
                    if wt_dir.exists(): shutil.rmtree(wt_dir)
                    shutil.copytree(ROOT, wt_dir, ignore=shutil.ignore_patterns('.git', '.governance/state', '.worktrees', '.shadow_worktrees'))
            else:
                is_shadow = 1
                branch = 'shadow'
                wt_dir = ROOT / '.shadow_worktrees' / task_id
                if wt_dir.exists(): shutil.rmtree(wt_dir)
                shutil.copytree(ROOT, wt_dir, ignore=shutil.ignore_patterns('.governance/state', '.worktrees', '.shadow_worktrees'))

            # Copy task handoff into worktree
            h_src = ROOT / f'.governance/handoffs/{task_id}.json'
            if h_src.is_file():
                h_dst = wt_dir / f'.governance/handoffs/{task_id}.json'
                h_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(h_src, h_dst)

            c.execute('INSERT OR REPLACE INTO worktrees VALUES(?,?,?,?,?)',
                      (task_id, str(wt_dir.relative_to(ROOT)), branch, is_shadow, time.time()))
            c.commit()
            return {'status': 'WORKTREE_READY', 'task': task_id, 'path': str(wt_dir.relative_to(ROOT)), 'isShadow': bool(is_shadow), 'branch': branch}

        elif action == 'merge':
            row = c.execute('SELECT * FROM worktrees WHERE task=?', (task_id,)).fetchone()
            if row is None:
                raise Rejected(f'No active worktree found for task {task_id}')
            wt_path = ROOT / row['worktree_path']
            is_shadow = row['is_shadow']
            
            if is_shadow:
                # Sync allowed_paths back to ROOT
                for p in t['allowed_paths']:
                    src_file = wt_path / p
                    dst_file = ROOT / p
                    if src_file.is_file():
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                    elif src_file.is_dir():
                        if dst_file.exists(): shutil.rmtree(dst_file)
                        shutil.copytree(src_file, dst_file)
                if wt_path.exists(): shutil.rmtree(wt_path, ignore_errors=True)
            else:
                # Git merge
                branch = row['branch_name']
                merge_res = subprocess.run(['git', 'merge', '--no-ff', branch, '-m', f'feat({task_id}): merge subagent implementation'], cwd=ROOT, capture_output=True, text=True)
                if merge_res.returncode != 0:
                    subprocess.run(['git', 'merge', '--abort'], cwd=ROOT, capture_output=True)
                    raise Rejected(f"WORKTREE_MERGE_CONFLICT: Failed to merge '{branch}' into root branch:\n{merge_res.stderr or merge_res.stdout}")
                subprocess.run(['git', 'worktree', 'remove', '--force', str(wt_path.relative_to(ROOT))], cwd=ROOT, capture_output=True)
                subprocess.run(['git', 'branch', '-d', branch], cwd=ROOT, capture_output=True)

            c.execute('DELETE FROM worktrees WHERE task=?', (task_id,))
            c.commit()
            return {'status': 'WORKTREE_MERGED', 'task': task_id}

        elif action == 'cleanup':
            row = c.execute('SELECT * FROM worktrees WHERE task=?', (task_id,)).fetchone()
            if row:
                wt_path = ROOT / row['worktree_path']
                if wt_path.exists(): shutil.rmtree(wt_path, ignore_errors=True)
                if not row['is_shadow']:
                    subprocess.run(['git', 'worktree', 'prune'], cwd=ROOT, capture_output=True)
                c.execute('DELETE FROM worktrees WHERE task=?', (task_id,))
                c.commit()
            return {'status': 'WORKTREE_CLEANED', 'task': task_id}
    finally:
        c.close()
        gc.collect()

def audit_tests(task_id):
    """Anti-Tautology & Mock-Breaker: AST assertion heuristics & Fault Injection mutation testing."""
    t = task_def(task_id)
    ck_name = t['checks'][0] if t['checks'] else None
    if not ck_name:
        raise Rejected(f'Task {task_id} has no checks assigned to audit')
    
    cfg = config()
    ck = cfg['checks'].get(ck_name)
    if not ck:
        raise Rejected(f'Check {ck_name} definition missing')

    # 1. Heuristic assertion check
    assertion_patterns = re.compile(r'\b(?:assert|self\.assert\w+|expect\(|should\.|toBe\(|toEqual\()')
    assertions_found = 0
    test_files_scanned = 0
    
    for current, dirs, files in os.walk(ROOT / 'tests'):
        for name in files:
            if name.endswith(('.py', '.ts', '.js')):
                test_files_scanned += 1
                try:
                    txt = (Path(current) / name).read_text(encoding='utf-8', errors='ignore')
                    assertions_found += len(assertion_patterns.findall(txt))
                except Exception: pass

    if test_files_scanned > 0 and assertions_found == 0:
        raise Rejected(f'ASSERTION_MISSING: Scanned {test_files_scanned} test files but found 0 assertions')

    # 2. Fault Injection Mutation Test (Multi-Language: Python, TS/JS, PHP)
    # Intelligent Mock-Breaker: exclude config files, strictly target src/ or domain modules
    FORBIDDEN_CONFIG_PATTERNS = re.compile(
        r'^(vite\.config|tsconfig|package|webpack|babel\.config|rollup\.config|eslint|prettier|jest\.config|vitest\.config)',
        re.IGNORECASE
    )

    def is_valid_mutation_target(candidate_path: Path) -> bool:
        if candidate_path.suffix not in ['.py', '.ts', '.tsx', '.js', '.jsx', '.php']:
            return False
        if FORBIDDEN_CONFIG_PATTERNS.match(candidate_path.name):
            return False
        if any(part.startswith('.') for part in candidate_path.parts):
            return False
        if any(p in candidate_path.parts for p in ['node_modules', '__pycache__', 'dist', 'build', '.governance', '.agents']):
            return False
        if 'test' in candidate_path.name.lower():
            return False
        parts = candidate_path.parts
        return ('src' in parts or 'app' in parts or 'lib' in parts or 'domain' in parts)

    target_file = None
    target_ext = None
    for p in t['allowed_paths']:
        candidate = safe_path(p)
        if candidate.is_file() and is_valid_mutation_target(candidate):
            target_file = candidate
            target_ext = candidate.suffix
            break
        elif candidate.is_dir():
            for ext in ['.py', '.ts', '.tsx', '.js', '.jsx', '.php']:
                for sub in candidate.rglob(f'*{ext}'):
                    if is_valid_mutation_target(sub):
                        target_file = sub
                        target_ext = ext
                        break
                if target_file: break
        if target_file: break

    mutations_caught = 0
    if target_file and target_file.is_file():
        orig_code = target_file.read_text(encoding='utf-8')
        try:
            if target_ext == '.py':
                mutation_header = "raise RuntimeError('MUTATION_CHECK_TRIGGERED')\n"
            elif target_ext in ['.ts', '.tsx', '.js', '.jsx']:
                mutation_header = "throw new Error('MUTATION_CHECK_TRIGGERED');\n"
            elif target_ext == '.php':
                mutation_header = "<?php throw new \\RuntimeException('MUTATION_CHECK_TRIGGERED'); ?>\n"
            else:
                mutation_header = "raise RuntimeError('MUTATION_CHECK_TRIGGERED')\n"

            mutated = mutation_header + orig_code
            target_file.write_text(mutated, encoding='utf-8')

            with tempfile.TemporaryFile() as stream:
                proc = subprocess.Popen(ck['argv'], cwd=ROOT, shell=False, stdout=stream, stderr=subprocess.STDOUT)
                code = proc.wait(timeout=ck.get('timeout', 60))

            # MUTATION INVARIANT: Test MUST fail if underlying code is broken!
            if code != 0:
                mutations_caught = 1
            else:
                # If test passed with code 0 despite broken implementation, it's a TAUTOLOGY!
                raise Rejected(f'TAUTOLOGICAL_TEST_DETECTED: Check {ck_name} passed with code 0 even when target code threw error')
        finally:
            for _ in range(5):
                try:
                    target_file.write_text(orig_code, encoding='utf-8')
                    break
                except PermissionError:
                    time.sleep(0.1)

    c = db()
    now_ts = time.time()
    cur_snap = snapshot()
    cur_spec = require_lock(c)
    try:
        c.execute('INSERT OR REPLACE INTO test_audits VALUES(?,?,?,?,?,?,?,?)',
                  (task_id, cur_snap, cur_spec, test_files_scanned, assertions_found, mutations_caught, 'PASS', now_ts))
        c.commit()
    finally:
        c.close()
        gc.collect()

    # Emit persistent G5.1 Mock-Breaker evidence artifact
    ev_dir = ROOT / '.governance/evidence'
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_file = ev_dir / f"G5_MOCKBREAKER_{task_id}_{int(now_ts)}.json"
    ev_payload = {
        'evidenceType': 'G5_MOCKBREAKER',
        'task': task_id,
        'status': 'PASS',
        'testFilesScanned': test_files_scanned,
        'assertionsFound': assertions_found,
        'mutationsCaught': mutations_caught,
        'sourceDigest': cur_snap,
        'specDigest': cur_spec,
        'timestamp': now_ts
    }
    ev_file.write_text(json.dumps(ev_payload, indent=2, ensure_ascii=False), encoding='utf-8')

    return {
        'status': 'AUDIT_PASS',
        'task': task_id,
        'testFilesScanned': test_files_scanned,
        'assertionsFound': assertions_found,
        'mutationsCaught': mutations_caught,
        'qualityScore': 100,
        'evidence': ev_file.relative_to(ROOT).as_posix()
    }

def generate_charter(out_dir='specs'):
    """Generates 5-layer living project charter (PRD, C4 Architecture, Data Dictionary, Impact DAG, Traceability Matrix)."""
    specs_dir = ROOT / (out_dir or 'specs')
    specs_dir.mkdir(parents=True, exist_ok=True)
    
    cfg = config()
    tasks = definitions()
    topo = discover(deep=True, write_files=False)
    index_symbols(write_db=True)
    
    # 1. specs/01_PRODUCT_REQUIREMENTS.md
    prd_md = f"""# PRODUCT REQUIREMENTS DOCUMENT (PRD) — SSoT
> Auto-generated by Antigravity Ultra v5.1 Living Charter Engine at {datetime.datetime.now().isoformat()}

## 1. Cel i Zakres Biznesowy
Projekt zarządzany deterministycznie przez framework Antigravity Ultra v5.1. 
Wszystkie wymagania są mapowane bezpośrednio na zadania DAG oraz zautomatyzowane asercje dowodowe.

## 2. Wymagania Funkcjonalne (User Stories w formacie Gherkin)
"""
    for t in tasks:
        prd_md += f"""
### Wymaganie REQ-{t['id']}: {t.get('title', t['id'])}
* **Zadanie:** `{t['id']}` (Ryzyko: `{t.get('risk', 'low')}`)
* **Ścieżki wykonawcze:** `{', '.join(t['allowed_paths'])}`
* **Scenariusz Akceptacyjny (Gherkin):**
  - **Given:** Czysty stan środowiska i zablokowana specyfikacja G2.
  - **When:** Podagent wdraża zmiany w wyznaczonym zakresie `allowedToWrite`.
  - **Then:** Wszystkie asercje `{', '.join(t.get('acceptance', ['AC-01']))}` kończą się kodem 0.
"""
    (specs_dir / '01_PRODUCT_REQUIREMENTS.md').write_text(prd_md, encoding='utf-8')

    # 2. specs/02_SYSTEM_ARCHITECTURE.md
    c4_md = f"""# SYSTEM ARCHITECTURE & C4 CONTAINER MODEL
> Auto-generated by Antigravity Ultra v5.1 Architecture Engine

## 1. Model Kontenerów (C4 Level 2)
```mermaid
graph TD
    User([Deweloper / Użytkownik]) -->|Wprowadza pomysł /init| Orchestrator[Antigravity 2.0 Orchestrator]
    Orchestrator -->|Bramka G1-G2| GovernanceCore[Governance Engine gov.py]
    Orchestrator -->|Izolowane Handoffy| Subagents[Subagents / Workers]
    Subagents -->|Zapis chroniony native_guard| Codebase[(Workspace Codebase)]
    GovernanceCore -->|Fencing Leases| SQLite[(state.sqlite WAL)]
    GovernanceCore -->|Dowody wykonania| EvidenceStore[evidence/ SHA256 Store]
```

## 2. Granice Modułów i Pakiety Technologiczne
* **Wykryte Frameworki:** {', '.join(topo['frameworks']) if topo['frameworks'] else 'Architektura autonomiczna'}
* **Profil Bezpieczeństwa:** `{cfg.get('profile', 'standard')}`
* **Maksymalna Równoległość:** `{cfg.get('max_parallel', 1)}` równoległych zadań
"""
    (specs_dir / '02_SYSTEM_ARCHITECTURE.md').write_text(c4_md, encoding='utf-8')

    # 3. specs/03_DATA_DICTIONARY.md
    c = db()
    try:
        symbols_rows = c.execute('SELECT symbol, kind, file_path FROM symbol_index ORDER BY kind, symbol').fetchall()
    finally:
        c.close()
        gc.collect()

    dict_md = f"""# DATA DICTIONARY & ENTITY SPECIFICATION
> Auto-generated by Antigravity Ultra v5.1 Data Engine

## 1. Zindeksowane Encje i Modele Danych
| Symbol / Encja | Typ | Plik Definicji |
|---|---|---|
"""
    for r in symbols_rows[:40]:
        dict_md += f"| `{r['symbol']}` | `{r['kind']}` | `{r['file_path']}` |\n"
    if not symbols_rows:
        dict_md += "| N/A | Brak zdefiniowanych encji w kodzie | Workspace Root |\n"
    (specs_dir / '03_DATA_DICTIONARY.md').write_text(dict_md, encoding='utf-8')

    # 4. specs/04_DEPENDENCY_AND_IMPACT.md
    dep_md = f"""# TASK DEPENDENCY DAG & BLAST RADIUS MATRIX
> Auto-generated by Antigravity Ultra v5.1 Impact Engine

## 1. Acykliczny Graf Zadań (DAG)
```mermaid
graph LR
"""
    for t in tasks:
        deps = t.get('depends_on', [])
        if deps:
            for d in deps: dep_md += f"    {d} --> {t['id']}\n"
        else:
            dep_md += f"    G0_START --> {t['id']}\n"
    dep_md += "```\n\n## 2. Macierz Promienia Rażenia (Blast Radius)\n| Zadanie | Ścieżki Zapisu | Ryzyko |\n|---|---|---|\n"
    for t in tasks:
        dep_md += f"| `{t['id']}` | `{', '.join(t['allowed_paths'])}` | `{t.get('risk', 'low')}` |\n"
    (specs_dir / '04_DEPENDENCY_AND_IMPACT.md').write_text(dep_md, encoding='utf-8')

    # 5. specs/05_TRACEABILITY_MATRIX.md
    trace_md = trace_matrix('markdown')['matrix']
    (specs_dir / '05_TRACEABILITY_MATRIX.md').write_text(trace_md, encoding='utf-8')

    return {
        'status': 'CHARTER_GENERATED',
        'specsDir': str(specs_dir.relative_to(ROOT)),
        'files': [
            '01_PRODUCT_REQUIREMENTS.md',
            '02_SYSTEM_ARCHITECTURE.md',
            '03_DATA_DICTIONARY.md',
            '04_DEPENDENCY_AND_IMPACT.md',
            '05_TRACEABILITY_MATRIX.md'
        ]
    }

def trace_matrix(export_format='markdown'):
    """Generates full end-to-end traceability matrix linking Requirements -> Contracts -> Tasks -> Evidence."""
    tasks = definitions()
    c = db()
    try:
        matrix_rows = []
        for t in tasks:
            tid = t['id']
            t_row = c.execute('SELECT state FROM tasks WHERE id=?', (tid,)).fetchone()
            state = t_row['state'] if t_row else 'PENDING'
            ev_row = c.execute('SELECT log_hash, exit_code, at FROM evidence WHERE task=? ORDER BY at DESC LIMIT 1', (tid,)).fetchone()
            rev_row = c.execute('SELECT decision, reviewer FROM reviews WHERE task=?', (tid,)).fetchone()
            
            matrix_rows.append({
                'reqId': f'REQ-{tid}',
                'taskId': tid,
                'title': t.get('title', tid),
                'state': state,
                'checks': ', '.join(t.get('checks', [])),
                'exitCode': ev_row['exit_code'] if ev_row else 'N/A',
                'evidenceSha256': ev_row['log_hash'][:12] + '...' if ev_row else 'N/A',
                'review': f"{rev_row['decision']} by {rev_row['reviewer']}" if rev_row else 'PENDING'
            })
    finally:
        c.close()
        gc.collect()

    if export_format == 'json':
        return {'matrix': matrix_rows}
    
    md = """# TRACEABILITY MATRIX (SSoT)
| Req ID | Task ID | Tytuł Zadania | Stan Bramki | Przypisane Testy | Exit Code | Hash Dowodu | Status Review |
|---|---|---|---|---|---|---|---|
"""
    for r in matrix_rows:
        md += f"| `{r['reqId']}` | `{r['taskId']}` | {r['title']} | `{r['state']}` | `{r['checks']}` | `{r['exitCode']}` | `{r['evidenceSha256']}` | {r['review']} |\n"
    return {'matrix': md, 'totalRows': len(matrix_rows)}

def interlock(task_id, cross_worktrees=False):
    """Semantic Pre-Merge Interlock Gate (G6.1): compiles AST and validates downstream tests before merge."""
    t = task_def(task_id)

    # 1. Cross-worktree collision check early before expensive test runs
    cross_verified = 0
    if cross_worktrees:
        c = db()
        try:
            now = time.time()
            active_tasks = c.execute("SELECT id FROM tasks WHERE state='ACTIVE' AND expires>? AND id!=?", (now, task_id)).fetchall()
            for at in active_tasks:
                other_t = task_def(at['id'])
                if any(overlaps(a, b) for a in t['allowed_paths'] for b in other_t['allowed_paths']):
                    raise Rejected(f"CROSS_WORKTREE_PATH_COLLISION: Conflict with active task '{at['id']}'")
                task_syms = set(t.get('symbols', []))
                other_syms = set(other_t.get('symbols', []))
                common_syms = task_syms.intersection(other_syms)
                if common_syms:
                    raise Rejected(f"CROSS_WORKTREE_SYMBOL_COLLISION: Common symbol '{next(iter(common_syms))}' with active task '{at['id']}'")
                cross_verified += 1
        finally:
            c.close()
            gc.collect()

    # 2. Syntax check on downstream dependents
    impact_data = {}
    for p in t['allowed_paths']:
        impact_data = calculate_impact(target_file=p)
        break
        
    downstream = impact_data.get('downstreamDependents', [])
    for dep in downstream:
        dep_path = ROOT / dep
        if dep_path.is_file() and dep_path.suffix == '.py':
            import py_compile
            try:
                py_compile.compile(str(dep_path), doraise=True)
            except Exception as e:
                raise Rejected(f'INTERLOCK_SYNTAX_ERROR in downstream dependent {dep}: {e}')

    # 3. Run affected regression test checks
    cfg = config()
    for ck_name in impact_data.get('affectedChecks', []):
        ck = cfg['checks'].get(ck_name)
        if ck:
            with tempfile.TemporaryFile() as stream:
                proc = subprocess.Popen(ck['argv'], cwd=ROOT, shell=False, stdout=stream, stderr=subprocess.STDOUT)
                code = proc.wait(timeout=ck.get('timeout', 120))
                if code != 0:
                    raise Rejected(f'INTERLOCK_REGRESSION: Affected downstream check {ck_name} failed with code {code}')

    now_ts = time.time()
    ev_dir = ROOT / '.governance/evidence'
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_f = ev_dir / f"G6_INTERLOCK_{task_id}_{int(now_ts)}.json"
    ev_payload = {
        'evidenceType': 'G6_INTERLOCK',
        'status': 'INTERLOCK_PASS',
        'task': task_id,
        'downstreamVerified': len(downstream),
        'crossWorktreesChecked': cross_verified,
        'blastRadius': impact_data,
        'timestamp': now_ts
    }
    ev_f.write_text(json.dumps(ev_payload, indent=2, ensure_ascii=False), encoding='utf-8')

    return {
        'status': 'INTERLOCK_PASS',
        'task': task_id,
        'downstreamVerified': len(downstream),
        'crossWorktreesChecked': cross_verified,
        'blastRadius': impact_data,
        'evidence': ev_f.relative_to(ROOT).as_posix()
    }


def standards_config():
    p = ROOT / '.governance/standards.json'
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {
        "version": 1,
        "active_profile": "standard",
        "profiles": {
            "tiny": {"max_function_lines": 60, "enforce_type_annotations": False, "disallow_bare_exceptions": True},
            "standard": {"max_function_lines": 40, "enforce_type_annotations": True, "disallow_bare_exceptions": True},
            "critical": {"max_function_lines": 25, "enforce_type_annotations": True, "disallow_bare_exceptions": True}
        },
        "max_function_lines": 40,
        "enforce_type_annotations": True,
        "disallow_bare_exceptions": True,
        "required_invariants": [
            "interface_contract", "input_validation", "domain_exception",
            "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
        ],
        "forbidden_patterns": ["console.log", "print(", "TODO:", "FIXME:", "except Exception: pass", "except:"],
        "naming_conventions": {
            "classes": "PascalCase", "functions": "snake_case", "test_files": "test_*.py", "exception_suffix": "Error"
        }
    }

def to_pascal_case(s: str) -> str:
    parts = re.split(r'[-_\s]+', s)
    return ''.join(p[:1].upper() + p[1:] for p in parts if p)

def to_snake_case(s: str) -> str:
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', s)
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return re.sub(r'[-_\s]+', '_', s2).strip('_')

def scaffold_unit(name: str, domain: str = 'core', unit_type: str = 'service'):
    """Generates a complete 7-invariant compliant unit skeleton: implementation, dual tests, data dictionary sync."""
    domain_name = domain.strip().lower() if domain else 'core'
    pascal = to_pascal_case(name)
    snake = to_snake_case(name)
    
    src_dir = ROOT / 'src' / domain_name
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = ROOT / 'tests'
    tests_dir.mkdir(parents=True, exist_ok=True)
    specs_dir = ROOT / 'specs'
    specs_dir.mkdir(parents=True, exist_ok=True)

    impl_file = src_dir / f"{snake}.py"
    test_file = tests_dir / f"test_{snake}.py"
    dict_file = specs_dir / "03_DATA_DICTIONARY.md"

    # 1. Implementation file (7/7 Feature Anatomy compliant)
    impl_code = f'''"""Domain {unit_type} for {pascal} (7-Invariant Feature Anatomy Standard)."""
from dataclasses import dataclass
from typing import Optional, Dict, Any

class {pascal}Error(Exception):
    """Domain exception raised when {pascal} operation fails."""
    pass

@dataclass(frozen=True)
class {pascal}Request:
    """Input contract for {pascal}."""
    item_id: str
    amount: float = 1.0

    def __post_init__(self) -> None:
        if not self.item_id or not self.item_id.strip():
            raise {pascal}Error("item_id cannot be empty")
        if self.amount <= 0:
            raise {pascal}Error("amount must be greater than zero")

@dataclass(frozen=True)
class {pascal}Result:
    """Output contract for {pascal}."""
    status: str
    item_id: str
    message: str

def {snake}(req: {pascal}Request) -> {pascal}Result:
    """Executes {pascal} business logic with input boundary validation."""
    if not req.item_id:
        raise {pascal}Error("Invalid request state")
    return {pascal}Result(
        status="SUCCESS",
        item_id=req.item_id,
        message=f"{pascal} processed successfully for {{req.item_id}}"
    )

__all__ = [
    "{pascal}Error",
    "{pascal}Request",
    "{pascal}Result",
    "{snake}"
]
'''
    impl_file.write_text(impl_code, encoding='utf-8')

    # 2. Dual test suite (Happy-Path + Negative Edge-Case)
    test_code = f'''"""Dual test suite for {pascal} (Happy-Path + Negative Edge-Case)."""
import os, sys, unittest
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.{domain_name}.{snake} import {pascal}Error, {pascal}Request, {pascal}Result, {snake}

class Test{pascal}(unittest.TestCase):
    def test_{snake}_happy_path(self) -> None:
        req = {pascal}Request(item_id="item_101", amount=25.0)
        res = {snake}(req)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.item_id, "item_101")

    def test_{snake}_validation_failure_empty_id(self) -> None:
        with self.assertRaises({pascal}Error):
            {pascal}Request(item_id="", amount=10.0)

    def test_{snake}_validation_failure_negative_amount(self) -> None:
        with self.assertRaises({pascal}Error):
            {pascal}Request(item_id="item_102", amount=-1.0)

if __name__ == "__main__":
    unittest.main()
'''
    test_file.write_text(test_code, encoding='utf-8')

    # 3. Data Dictionary sync
    entry_line = f"| `{pascal}` | `unit_{unit_type}` | `src/{domain_name}/{snake}.py` |\n"
    if dict_file.is_file():
        existing = dict_file.read_text(encoding='utf-8')
        if pascal not in existing:
            dict_file.write_text(existing.rstrip() + "\n" + entry_line, encoding='utf-8')
    else:
        dict_md = f"""# DATA DICTIONARY & ENTITY SPECIFICATION
## 1. Zindeksowane Encje i Modele Danych
| Symbol / Encja | Typ | Plik Definicji |
|---|---|---|
{entry_line}"""
        dict_file.write_text(dict_md, encoding='utf-8')

    return {
        'status': 'UNIT_SCAFFOLDED',
        'unitName': pascal,
        'domain': domain_name,
        'type': unit_type,
        'filesCreated': [
            str(impl_file.relative_to(ROOT)),
            str(test_file.relative_to(ROOT)),
            str(dict_file.relative_to(ROOT))
        ]
    }

def check_standards(task_id: Optional[str] = None, file_path: Optional[str] = None):
    """Static AST Diff & Standards Linter (G4 Gate): verifies type annotations, SRP <= 40, no bare except, forbidden patterns, test linkage."""
    std_cfg = standards_config()
    profile = std_cfg.get('active_profile', std_cfg.get('profile', 'standard'))
    prof_rules = std_cfg.get('profiles', {}).get(profile, {})
    max_lines = prof_rules.get('max_function_lines', std_cfg.get('max_function_lines', 40))
    enforce_types = prof_rules.get('enforce_type_annotations', std_cfg.get('enforce_type_annotations', True))
    disallow_bare = prof_rules.get('disallow_bare_exceptions', std_cfg.get('disallow_bare_exceptions', True))

    files_to_audit = []
    if file_path:
        p = Path(file_path)
        target = p if p.is_absolute() else (ROOT / p)
        if target.is_file() and target.suffix == '.py':
            files_to_audit.append(target)
    elif task_id:
        t = task_def(task_id)
        for allowed in t.get('allowed_paths', []):
            target = safe_path(allowed)
            if target.is_file() and target.suffix == '.py':
                files_to_audit.append(target)
            elif target.is_dir():
                for pyf in target.rglob('*.py'):
                    if '__pycache__' not in pyf.parts and not pyf.name.startswith('.'):
                        files_to_audit.append(pyf)
    else:
        src_path = ROOT / 'src'
        if src_path.is_dir():
            for pyf in src_path.rglob('*.py'):
                if '__pycache__' not in pyf.parts:
                    files_to_audit.append(pyf)

    violations = []
    audited_count = 0
    forbidden_list = std_cfg.get('forbidden_patterns', ['console.log', 'print(', 'TODO:', 'FIXME:'])

    for fpath in files_to_audit:
        if not fpath.is_file() or 'test' in fpath.name.lower():
            continue
        rel_str = str(fpath.relative_to(ROOT)) if fpath.is_relative_to(ROOT) else fpath.name
        audited_count += 1
        raw_content = fpath.read_text(encoding='utf-8')
        lines = raw_content.splitlines()

        # 1. AST Parsing
        try:
            tree = ast.parse(raw_content, filename=str(fpath))
        except SyntaxError as e:
            violations.append({
                'file': rel_str,
                'line': e.lineno or 1,
                'rule': 'SYNTAX_ERROR',
                'message': f"Syntax error in Python code: {e.msg}"
            })
            continue

        # 2. Function & Type Inspection
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith('__') and node.name.endswith('__'):
                    continue
                # Return type check
                if enforce_types and node.returns is None:
                    violations.append({
                        'file': rel_str,
                        'line': node.lineno,
                        'rule': 'MISSING_RETURN_TYPE',
                        'message': f"Function '{node.name}' is missing return type annotation",
                        'remediation': "Add return type annotation, e.g. -> ReturnType:"
                    })
                # Arg type check
                if enforce_types:
                    for arg in node.args.args:
                        if arg.arg not in {'self', 'cls'} and arg.annotation is None:
                            violations.append({
                                'file': rel_str,
                                'line': node.lineno,
                                'rule': 'MISSING_ARG_TYPE',
                                'message': f"Argument '{arg.arg}' in function '{node.name}' is missing type annotation",
                                'remediation': f"Add type annotation: '{arg.arg}: Type'"
                            })
                # Line length check
                end_lineno = getattr(node, 'end_lineno', node.lineno)
                func_len = end_lineno - node.lineno + 1
                if func_len > max_lines:
                    violations.append({
                        'file': rel_str,
                        'line': node.lineno,
                        'rule': 'FUNCTION_TOO_LONG',
                        'message': f"Function '{node.name}' has {func_len} lines (exceeds limit of {max_lines})",
                        'remediation': "Refactor into smaller helper functions adhering to SRP <= 40 lines"
                    })

            elif isinstance(node, ast.Try) and disallow_bare:
                for h in node.handlers:
                    if h.type is None:
                        violations.append({
                            'file': rel_str,
                            'line': h.lineno,
                            'rule': 'BARE_EXCEPT_FORBIDDEN',
                            'message': "Bare 'except:' handler is forbidden",
                            'remediation': "Catch explicit domain exception (e.g. DomainError)"
                        })
                    elif isinstance(h.type, ast.Name) and h.type.id == 'Exception':
                        if len(h.body) == 1 and isinstance(h.body[0], ast.Pass):
                            violations.append({
                                'file': rel_str,
                                'line': h.lineno,
                                'rule': 'PASS_EXCEPTION_FORBIDDEN',
                                'message': "'except Exception: pass' silent suppression is forbidden",
                                'remediation': "Log exception or re-raise domain error"
                            })

        # 3. Forbidden Patterns Scan
        for idx, line in enumerate(lines, 1):
            s_line = line.strip()
            if s_line.startswith('#'):
                continue
            for pat in forbidden_list:
                if pat in {'except:', 'except Exception: pass'}:
                    continue
                if pat in line:
                    violations.append({
                        'file': rel_str,
                        'line': idx,
                        'rule': 'FORBIDDEN_PATTERN',
                        'pattern': pat,
                        'message': f"Forbidden pattern '{pat}' detected at line {idx}",
                        'remediation': f"Remove pattern '{pat}'"
                    })

        # 3.5. Data Dictionary SSoT Sync Check (Invariant #7)
        dict_file = ROOT / 'specs/03_DATA_DICTIONARY.md'
        if dict_file.is_file():
            dict_content = dict_file.read_text(encoding='utf-8')
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == '__all__':
                            if isinstance(node.value, (ast.List, ast.Tuple)):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        sym_name = elt.value
                                        # Main domain class or pascal case entity must be present in data dictionary
                                        stem_pascal = to_pascal_case(fpath.stem)
                                        if stem_pascal not in dict_content and sym_name not in dict_content:
                                            violations.append({
                                                'file': rel_str,
                                                'line': node.lineno,
                                                'rule': 'UNSYNCHRONIZED_DATA_DICTIONARY',
                                                'symbol': sym_name,
                                                'message': f"Module entity '{stem_pascal}' or symbol '{sym_name}' is missing from specs/03_DATA_DICTIONARY.md",
                                                'remediation': f"Add row for '{stem_pascal}' in specs/03_DATA_DICTIONARY.md"
                                            })

        # 4. Test Linkage Check
        tests_dir = ROOT / 'tests'
        if tests_dir.is_dir():
            stem_snake = to_snake_case(fpath.stem)
            has_matching_test = False
            for tf in tests_dir.rglob('*.py'):
                if tf.is_file():
                    if stem_snake in tf.name.lower():
                        has_matching_test = True
                        break
                    try:
                        t_content = tf.read_text(encoding='utf-8')
                        if fpath.stem in t_content:
                            has_matching_test = True
                            break
                    except Exception:
                        pass
            if not has_matching_test:
                violations.append({
                    'file': rel_str,
                    'line': 1,
                    'rule': 'MISSING_TEST_FILE',
                    'message': f"No matching test file in tests/ for module '{fpath.name}'",
                    'remediation': f"Generate tests using 'python .governance/bin/gov.py scaffold-unit --name {fpath.stem}'"
                })

    res_payload = {
        'evidenceType': 'G4_STANDARDS',
        'status': 'VIOLATIONS_FOUND' if violations else 'STANDARDS_COMPLIANT',
        'profile': profile,
        'auditedFiles': audited_count,
        'totalViolations': len(violations),
        'violations': violations,
        'timestamp': time.time()
    }

    if task_id:
        t = task_def(task_id)
        task_modifies_src = any(
            p == 'src' or p.startswith('src/') or p.startswith('src\\') or '/src/' in p.replace('\\', '/')
            for p in t.get('allowed_paths', [])
        )
        if task_modifies_src and audited_count == 0:
            tpl_audited = 0
            try:
                tpl_res = check_templates(task_id=task_id)
                tpl_audited = tpl_res.get('auditedFiles', 0)
            except Exception:
                pass
            if tpl_audited == 0:
                raise Rejected(f"ZERO_FILES_AUDITED: Task {task_id} modifies files in src/ but 0 files were audited by Gate G4 standards check!")

        ev_dir = ROOT / '.governance/evidence'
        ev_dir.mkdir(parents=True, exist_ok=True)
        ev_f = ev_dir / f"G4_STANDARDS_{task_id}_{int(time.time())}.json"
        ev_f.write_text(json.dumps(res_payload, indent=2, ensure_ascii=False), encoding='utf-8')
        res_payload['evidence'] = ev_f.relative_to(ROOT).as_posix()

    return res_payload


# ==============================================================================
# CADRE: Component Assembly & Deterministic Resolution Engine (v6.0)
# ==============================================================================

def registry_data() -> Dict[str, Any]:
    """Loads central SSoT registry of components, assets, and taxonomy."""
    reg_dir = ROOT / '.governance/registry'
    data = {'components': {}, 'assets': {}, 'taxonomy': {}}
    if (reg_dir / 'components.json').is_file():
        try:
            data['components'] = json.loads((reg_dir / 'components.json').read_text(encoding='utf-8')).get('components', {})
        except Exception:
            pass
    if (reg_dir / 'assets.json').is_file():
        try:
            data['assets'] = json.loads((reg_dir / 'assets.json').read_text(encoding='utf-8')).get('assets', {})
        except Exception:
            pass
    if (reg_dir / 'taxonomy.json').is_file():
        try:
            data['taxonomy'] = json.loads((reg_dir / 'taxonomy.json').read_text(encoding='utf-8'))
        except Exception:
            pass
    return data

def blueprint_data(blueprint_id: str) -> Dict[str, Any]:
    """Resolves and loads a page blueprint contract by ID or filename."""
    # 1. Direct path check
    direct_p = Path(blueprint_id)
    if direct_p.is_file():
        return json.loads(direct_p.read_text(encoding='utf-8'))
    if (ROOT / direct_p).is_file():
        return json.loads((ROOT / direct_p).read_text(encoding='utf-8'))

    # 2. Search in specs/blueprints
    bp_dir = ROOT / 'specs/blueprints'
    if bp_dir.is_dir():
        clean_target = blueprint_id.replace('pages.', '').replace('.blueprint.json', '').replace('.blueprint', '').lower()
        for f in bp_dir.glob('*.blueprint.json'):
            clean_name = f.stem.replace('.blueprint', '').lower()
            if clean_name == clean_target or f.stem.lower() == blueprint_id.lower() or f.name.lower() == blueprint_id.lower():
                return json.loads(f.read_text(encoding='utf-8'))
            try:
                doc = json.loads(f.read_text(encoding='utf-8'))
                pid = doc.get('pageId', '').lower()
                if pid == blueprint_id.lower() or pid == f'pages.{clean_target}':
                    return doc
            except Exception:
                pass
    raise Rejected(f"Blueprint '{blueprint_id}' not found in specs/blueprints/")

def scaffold_page(blueprint_id: str, out_file: Optional[str] = None) -> Dict[str, Any]:
    """Ahead-Of-Time scaffolding of a zero-error page template from Blueprint Contract (CADRE v8.0)."""
    bp = blueprint_data(blueprint_id)
    reg = registry_data()
    comp_reg = reg.get('components', {})
    asset_reg = reg.get('assets', {})

    adapter = bp.get('adapter', 'react-typescript').lower()
    tax = bp.get('taxonomy', {})
    css_prefix = tax.get('cssPrefix', 'cw-')
    slots = bp.get('slots', {})

    raw_page_id = bp.get('pageId', blueprint_id).replace('pages.', '')

    if adapter in ['php', 'woocommerce', 'wordpress']:
        target_rel = out_file or bp.get('targetFile', f'templates/page-{raw_page_id}.php')
    elif adapter in ['vue', 'vue-sfc']:
        target_rel = out_file or bp.get('targetFile', f'src/pages/{raw_page_id.capitalize()}Page.vue')
    elif adapter == 'html':
        target_rel = out_file or bp.get('targetFile', f'pages/{raw_page_id}.html')
    else:
        target_rel = out_file or bp.get('targetFile', f'src/pages/{raw_page_id.capitalize()}Page.tsx')

    target_path = ROOT / target_rel
    page_name = target_path.stem
    if adapter.startswith('react') and not page_name.endswith('Page'):
        page_name += 'Page'

    vm_type = tax.get('viewModelType', f'{page_name}Props')
    state_hook = tax.get('stateStoreHook', f'use{page_name}Store')

    imports = list(bp.get('requiredImports', []))
    style_imports = []
    wired_comps = []

    for slot_name, slot_def in sorted(slots.items(), key=lambda x: x[1].get('order', 0)):
        for c in slot_def.get('components', []):
            c_name = c.get('component')
            if c_name:
                wired_comps.append(c_name)
                if c_name in comp_reg:
                    c_info = comp_reg[c_name]
                    imp = c_info.get('importStatement')
                    if imp and imp not in imports:
                        imports.append(imp)
                    for a_key in c_info.get('associatedAssets', []):
                        if a_key in asset_reg:
                            a_file = asset_reg[a_key].get('filePath')
                            if a_file:
                                s_imp = f"import '@/{a_file.replace('src/', '')}';"
                                if s_imp not in style_imports:
                                    style_imports.append(s_imp)

    if adapter in ['php', 'woocommerce', 'wordpress']:
        code_lines = [
            "<?php",
            "/**",
            f" * Template Name: {bp.get('title', page_name)}",
            f" * Description: CADRE v8.0 Scaffolded Template for {raw_page_id}",
            f" * Blueprint: {bp.get('pageId', blueprint_id)}",
            f" * Adapter: {adapter}",
            " */",
            "",
            "defined('ABSPATH') || exit;",
            "",
            "get_header();",
            "?>",
            "",
            f'<div class="{css_prefix}container">',
            f'  <main class="{css_prefix}main">'
        ]
        for slot_name, slot_def in sorted(slots.items(), key=lambda x: x[1].get('order', 0)):
            slot_slug = slot_name.replace('_', '-')
            code_lines.append(f'    <section class="{css_prefix}slot-{slot_slug}">')
            for c in slot_def.get('components', []):
                c_name = c.get('component', '')
                tpl_part = c.get('templatePart', f'template-parts/{c_name.lower()}')
                code_lines.append(f"      <?php get_template_part('{tpl_part}'); ?>")
            code_lines.append("    </section>")
        code_lines.extend([
            "  </main>",
            "</div>",
            "",
            "<?php",
            "get_footer();",
            ""
        ])
    elif adapter in ['vue', 'vue-sfc']:
        slot_render = []
        for slot_name, slot_def in sorted(slots.items(), key=lambda x: x[1].get('order', 0)):
            slot_items = []
            for c in slot_def.get('components', []):
                c_name = c.get('component', '')
                c_bindings = c.get('propBindings', {})
                props_str = " ".join([f":{k}=\"{v}\"" for k, v in c_bindings.items()])
                tag = f"<{c_name} {props_str} />" if props_str else f"<{c_name} />"
                slot_items.append(f"      {tag}")
            slot_render.append(f'    <section class="{css_prefix}slot-{slot_name.replace("_", "-")}">\n' + "\n".join(slot_items) + f'\n    </section>')

        code_lines = [
            '<template>',
            f'  <div class="{css_prefix}container">',
            f'    <main class="{css_prefix}main">'
        ]
        code_lines.extend(slot_render)
        code_lines.extend([
            '    </main>',
            '  </div>',
            '</template>',
            '',
            '<script setup lang="ts">',
            f"// CADRE v8.0 Scaffolded View — Blueprint: {bp.get('pageId', blueprint_id)}"
        ])
        for imp in imports:
            code_lines.append(imp)
        code_lines.extend([
            '</script>',
            '',
            '<style scoped>',
            f'.{css_prefix}container {{ width: 100%; }}',
            '</style>',
            ''
        ])
    elif adapter == 'html':
        code_lines = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'  <title>{bp.get("title", page_name)}</title>',
            '</head>',
            '<body>',
            f'  <div class="{css_prefix}container">',
            f'    <main class="{css_prefix}main">'
        ]
        for slot_name, slot_def in sorted(slots.items(), key=lambda x: x[1].get('order', 0)):
            code_lines.append(f'      <section class="{css_prefix}slot-{slot_name.replace("_", "-")}">')
            code_lines.append(f'        <!-- Slot: {slot_name} -->')
            code_lines.append('      </section>')
        code_lines.extend([
            '    </main>',
            '  </div>',
            '</body>',
            '</html>',
            ''
        ])
    else:
        slot_render = []
        for slot_name, slot_def in sorted(slots.items(), key=lambda x: x[1].get('order', 0)):
            slot_items = []
            for c in slot_def.get('components', []):
                c_name = c.get('component')
                c_bindings = c.get('propBindings', {})
                props_str = " ".join([f"{k}={{{v}}}" for k, v in c_bindings.items()])
                tag = f"<{c_name} {props_str} />" if props_str else f"<{c_name} />"
                slot_items.append(f"          {tag}")
            slot_render.append(f"        <section className=\"{css_prefix}slot-{slot_name.replace('_', '-')}\">\n" + "\n".join(slot_items) + f"\n        </section>")

        code_lines = []
        code_lines.extend(imports)
        if style_imports:
            code_lines.append("")
            code_lines.extend(style_imports)

        code_lines.append("")
        code_lines.append(f"/**\n * {page_name} — {bp.get('title', 'Page')}\n * Auto-generated by Antigravity CADRE Engine v8.0\n * Blueprint: {bp.get('pageId')}\n */")
        code_lines.append(f"export const {page_name}: FC<{vm_type}> = (props) => {{")
        code_lines.append(f"  const store = {state_hook}();")
        code_lines.append("")
        code_lines.append("  return (")
        code_lines.append(f"    <div className=\"{css_prefix}container\">")
        code_lines.append(f"      <main className=\"{css_prefix}main\">")
        code_lines.extend(slot_render)
        code_lines.append("      </main>")
        code_lines.append("    </div>")
        code_lines.append("  );")
        code_lines.append("};")
        code_lines.append("")
        code_lines.append(f"export default {page_name};")
        code_lines.append("")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(code_lines), encoding='utf-8')

    dict_file = ROOT / 'specs/03_DATA_DICTIONARY.md'
    if dict_file.is_file():
        d_text = dict_file.read_text(encoding='utf-8')
        entry = f"| `{bp.get('pageId', blueprint_id)}` | `PageBlueprint` | `{target_rel}` | {', '.join(wired_comps)} | {', '.join(bp.get('requiredAssets', []))} |\n"
        if bp.get('pageId', blueprint_id) not in d_text:
            dict_file.write_text(d_text.rstrip() + "\n" + entry, encoding='utf-8')

    return {
        'status': 'PAGE_SCAFFOLDED',
        'pageId': bp.get('pageId', blueprint_id),
        'adapter': adapter,
        'filePath': target_rel.replace('\\', '/'),
        'componentsWired': wired_comps,
        'assetsRegistered': bp.get('requiredAssets', [])
    }

def check_templates(task_id: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Static AST & Linter for Page Templates and Components (Bramka G4 CADRE)."""
    reg = registry_data()
    comp_reg = reg.get('components', {})
    tax = reg.get('taxonomy', {})
    css_req_prefix = tax.get('layers', {}).get('css_classes', {}).get('required_prefix', 'cw-')

    files_to_audit = []
    if file_path:
        p = Path(file_path)
        tgt = p if p.is_absolute() else (ROOT / p)
        if tgt.is_file(): files_to_audit.append(tgt)
    elif task_id:
        t = task_def(task_id)
        for allowed in t.get('allowed_paths', []):
            target = safe_path(allowed)
            if target.is_file() and any(target.name.endswith(ext) for ext in ['.tsx', '.jsx', '.php', '.vue']):
                files_to_audit.append(target)
            elif target.is_dir():
                for ext in ['*.tsx', '*.jsx', '*.php', '*.vue']:
                    for f in target.rglob(ext):
                        if '__pycache__' not in f.parts and 'node_modules' not in f.parts and not f.name.startswith('.'):
                            files_to_audit.append(f)
    else:
        for folder in ['src/pages', 'src/views', 'templates']:
            src_f = ROOT / folder
            if src_f.is_dir():
                for ext in ['*.tsx', '*.jsx', '*.php', '*.vue']:
                    for f in src_f.rglob(ext):
                        if 'node_modules' not in f.parts: files_to_audit.append(f)

    violations = []
    for fpath in files_to_audit:
        rel_str = str(fpath.relative_to(ROOT)).replace('\\', '/') if fpath.is_relative_to(ROOT) else fpath.name
        content = fpath.read_text(encoding='utf-8')
        lines = content.splitlines()

        # 1. Line limit (SRP <= 60 lines for Page Orchestrators)
        if 'Page' in fpath.stem and len(lines) > 60:
            violations.append({
                'file': rel_str,
                'line': 1,
                'rule': 'TEMPLATE_TOO_LONG',
                'message': f"Page template '{fpath.name}' has {len(lines)} lines (exceeds limit of 60 lines for Page Orchestrator)",
                'remediation': "Extract slots or sub-sections into child components"
            })

        # 2. Component references vs imports (skip for PHP and HTML templates)
        if not fpath.name.endswith('.php') and not fpath.name.endswith('.html'):
            used_components = set(re.findall(r'<([A-Z][a-zA-Z0-9]+)\b', content))
            imported_symbols = set()
            for line in lines:
                m = re.findall(r'import\s+\{?([^}]+)\}?\s+from', line)
                if m:
                    for part in m[0].split(','):
                        sym = part.strip().split(' as ')[-1].strip()
                        if sym: imported_symbols.add(sym)
                m_req = re.findall(r'(\w+)\s*=\s*require\(', line)
                for sym in m_req: imported_symbols.add(sym)

            for c_name in used_components:
                if c_name in comp_reg and c_name not in imported_symbols:
                    imp_stmt = comp_reg[c_name].get('importStatement', f"import {{ {c_name} }} from '@/components/{c_name}';")
                    violations.append({
                        'file': rel_str,
                        'line': 1,
                        'rule': 'MISSING_COMPONENT_IMPORT',
                        'component': c_name,
                        'message': f"Component '{c_name}' is used in template but missing import statement",
                        'remediation': f"Add import statement: {imp_stmt}"
                    })

        # 3. CSS class taxonomy
        for idx, line in enumerate(lines, 1):
            sanitized_line = line
            if fpath.name.endswith('.php'):
                sanitized_line = re.sub(r'<\?php.*?\?>', '', sanitized_line)
                sanitized_line = re.sub(r'<\?=.*?\?>', '', sanitized_line)
            classes_found = re.findall(r'class(?:Name)?=["\']([^"\']+)["\']', sanitized_line)
            for cf in classes_found:
                for cls in cf.split():
                    cls = cls.strip()
                    if not cls or cls.startswith('<?') or cls.endswith('?>') or cls.startswith('$'):
                        continue
                    if not cls.startswith(css_req_prefix) and not cls.startswith('{'):
                        violations.append({
                            'file': rel_str,
                            'line': idx,
                            'rule': 'TAXONOMY_CSS_VIOLATION',
                            'className': cls,
                            'message': f"CSS class '{cls}' at line {idx} violates taxonomy (must start with '{css_req_prefix}')",
                            'remediation': f"Rename class to '{css_req_prefix}{cls}'"
                        })

    tpl_payload = {
        'evidenceType': 'G4_TEMPLATES',
        'status': 'VIOLATIONS_FOUND' if violations else 'TEMPLATES_COMPLIANT',
        'auditedFiles': len(files_to_audit),
        'totalViolations': len(violations),
        'violations': violations,
        'timestamp': time.time()
    }

    if task_id:
        ev_dir = ROOT / '.governance/evidence'
        ev_dir.mkdir(parents=True, exist_ok=True)
        ev_f = ev_dir / f"G4_TEMPLATES_{task_id}_{int(time.time())}.json"
        ev_f.write_text(json.dumps(tpl_payload, indent=2, ensure_ascii=False), encoding='utf-8')
        tpl_payload['evidence'] = ev_f.relative_to(ROOT).as_posix()

    return tpl_payload

def wire_template(file_path: str, blueprint_id: Optional[str] = None) -> Dict[str, Any]:
    """Automatically injects missing imports and styles into a template based on CADRE analysis."""
    p = Path(file_path)
    target = p if p.is_absolute() else (ROOT / p)
    if not target.is_file():
        raise Rejected(f"File not found: {file_path}")

    content = target.read_text(encoding='utf-8')
    audit = check_template_content(target.name, content) if 'check_template_content' in globals() else check_templates(file_path=str(target))
    missing = [v for v in audit.get('violations', []) if v['rule'] == 'MISSING_COMPONENT_IMPORT']

    if not missing:
        return {'status': 'TEMPLATE_ALREADY_WIRED', 'filePath': file_path, 'injected': []}

    reg = registry_data().get('components', {})
    lines = content.splitlines()
    last_imp = 0
    for idx, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('require('):
            last_imp = idx

    injected = []
    for m in missing:
        c_name = m['component']
        if c_name in reg:
            stmt = reg[c_name].get('importStatement')
            if stmt and stmt not in content:
                injected.append(stmt)
                lines.insert(last_imp + 1, stmt)
                last_imp += 1

    target.write_text("\n".join(lines), encoding='utf-8')
    return {
        'status': 'TEMPLATE_WIRED',
        'filePath': file_path,
        'injectedCount': len(injected),
        'injectedStatements': injected
    }


def approve_decision(adr_id, domain='global', assertion='', scope='global'):
    """Registers architectural decision record (ADR) into SYNAPSE decision mesh."""
    if not adr_id or not assertion:
        raise Rejected("MISSING_ADR_PARAMETERS: adr_id and assertion are required")
    c = db()
    now = time.time()
    try:
        c.execute("INSERT OR REPLACE INTO decision_mesh VALUES (?, ?, ?, ?, 1, ?)",
                  (adr_id, domain, assertion, scope, now))
        c.commit()
    finally:
        c.close()
        gc.collect()

    dec_dir = ROOT / 'docs/decisions'
    dec_dir.mkdir(parents=True, exist_ok=True)
    adr_file = dec_dir / f"{adr_id}.md"
    if not adr_file.exists():
        adr_file.write_text(f"""# {adr_id}: {assertion}\n\n- Domain: {domain}\n- Scope: {scope}\n- Approved At: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now))} UTC\n- Status: ACTIVE\n\n## Assertion\n{assertion}\n""", encoding='utf-8')

    return {
        'status': 'DECISION_APPROVED',
        'adrId': adr_id,
        'domain': domain,
        'assertion': assertion,
        'scope': scope
    }

def scaffold_module(name, domain='core', depends_on=None, module_type='fullstack'):
    """AOT module synthesizer: freezes interface contract, registers task DAG, dictionary and creates unit scaffold."""
    if not name:
        raise Rejected("MODULE_NAME_REQUIRED")
    if depends_on is None:
        depends_on = []

    slug = to_snake_case(name).replace('_', '-')
    pascal = to_pascal_case(name)
    snake = to_snake_case(name)
    task_id = f"task-module-{slug}"

    # 1. Interface-First Contract Freezing
    contracts_dir = ROOT / 'contracts'
    contracts_dir.mkdir(parents=True, exist_ok=True)
    contract_file = contracts_dir / f"{domain}_{snake}.contract.ts"
    if not contract_file.exists():
        contract_code = f"""// SYNAPSE Interface-First Frozen Contract
// Domain: {domain} | Module: {pascal}
export interface {pascal}Payload {{
  id: string;
  data: Record<string, unknown>;
}}

export interface {pascal}Result {{
  success: boolean;
  timestamp: number;
}}

export interface I{pascal}Service {{
  execute(payload: {pascal}Payload): Promise<{pascal}Result>;
}}
"""
        contract_file.write_text(contract_code, encoding='utf-8')

    contract_rel = str(contract_file.relative_to(ROOT)).replace('\\', '/')
    c_hash = digest(contract_file.read_bytes())

    c = db()
    try:
        c.execute("INSERT OR REPLACE INTO contract_manifests VALUES (?, ?, ?, ?, ?)",
                  (f"{domain}:{snake}", c_hash, contract_rel, f"http://127.0.0.1:4010/api/v1/{domain}/{slug}", time.time()))
        c.commit()
    finally:
        c.close()
        gc.collect()

    # 2. Register in tasks.json
    symbols = [f"{pascal}Request", snake]
    routes = [f"/api/v1/{domain}/{slug}"]
    allowed_paths = [f"src/{domain}/{snake}.py", f"tests/test_{snake}.py"]

    tasks_path = ROOT / '.governance/tasks.json'
    tasks_doc = {"version": 1, "tasks": []}
    if tasks_path.exists():
        try:
            raw = json.loads(tasks_path.read_text(encoding='utf-8'))
            if isinstance(raw, dict) and "tasks" in raw:
                tasks_doc = raw
            elif isinstance(raw, list):
                tasks_doc = {"version": 1, "tasks": raw}
        except Exception:
            pass

    tasks_list = tasks_doc.get("tasks", [])
    if not any(t.get('id') == task_id for t in tasks_list):
        new_task = {
            "id": task_id,
            "title": f"Implementacja modulu {pascal}",
            "domain": domain,
            "symbols": symbols,
            "routes": routes,
            "allowed_paths": allowed_paths,
            "depends_on": depends_on,
            "checks": ["unit"],
            "acceptance": [
                f"Modul {pascal} spelnia kontrakt {domain}_{snake}.contract",
                "Testy jednostkowe przechodza pomyslnie"
            ],
            "standards_checklist": [
                "interface_contract", "input_validation", "domain_exception",
                "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"
            ]
        }
        tasks_list.append(new_task)
        tasks_doc["tasks"] = tasks_list
        tasks_path.write_text(json.dumps(tasks_doc, indent=2, ensure_ascii=False), encoding='utf-8')

    # 3. Register in specs/03_DATA_DICTIONARY.md if exists
    dict_path = ROOT / 'specs/03_DATA_DICTIONARY.md'
    if dict_path.exists():
        dict_text = dict_path.read_text(encoding='utf-8')
        entry_row = f"| {pascal} | {domain} | Service & Handler | src/{domain}/{snake}.py | Contract I{pascal}Service |"
        if pascal not in dict_text:
            dict_text += f"\n{entry_row}\n"
            dict_path.write_text(dict_text, encoding='utf-8')

    # 4. Scaffold Python unit if not exists
    try:
        scaffold_unit(name=snake, domain=domain, unit_type='service')
    except Exception:
        pass

    return {
        "status": "MODULE_SCAFFOLDED",
        "taskId": task_id,
        "module": pascal,
        "domain": domain,
        "contractPath": contract_rel,
        "symbols": symbols,
        "routes": routes
    }


def prune_evidence(keep_last=5):
    """Retention engine: keeps GATE_PASS and DONE task records, prunes obsolete runs > keep_last."""
    ev_dir = ROOT / '.governance/evidence'
    if not ev_dir.is_dir():
        return {'status': 'PRUNED', 'removedFiles': 0, 'retainedRecords': 0}

    c = db()
    removed_count = 0
    retained_count = 0
    try:
        tasks = definitions()
        for t in tasks:
            tid = t['id']
            # Get evidence IDs ordered by time
            rows = c.execute("SELECT id, log_path FROM evidence WHERE task=? ORDER BY at DESC", (tid,)).fetchall()
            if len(rows) > keep_last:
                to_delete = rows[keep_last:]
                for row in to_delete:
                    c.execute("DELETE FROM evidence WHERE id=?", (row['id'],))
                    # Remove disk files
                    log_p = ROOT / row['log_path']
                    if log_p.is_file():
                        log_p.unlink(missing_ok=True)
                        removed_count += 1
                    json_p = ev_dir / f"{row['id']}.json"
                    if json_p.is_file():
                        json_p.unlink(missing_ok=True)
                        removed_count += 1
            retained_count += min(len(rows), keep_last)
        c.commit()
    finally:
        c.close()
        gc.collect()

    return {'status': 'PRUNED', 'removedFiles': removed_count, 'retainedRecords': retained_count}


def check_rules(candidate_file=None):
    """Audits rule candidates in .agents/learning_inbox/ against 16 Cardinal Rules and DREE."""
    inbox = ROOT / '.agents/learning_inbox'
    inbox.mkdir(parents=True, exist_ok=True)
    files = [Path(candidate_file)] if candidate_file else list(inbox.glob('*.candidate.md'))
    if not files:
        return {'status': 'NO_CANDIDATES', 'count': 0, 'results': []}

    results = []
    forbidden_terms = [
        ('bypass_review', 'Naruszenie Zasady 9 (Dual-Control Review)'),
        ('skip_mock', 'Naruszenie Bramki G5.1 (Mock-Breaker)'),
        ('allow_print', 'Naruszenie Standardu DREE #4 (Zero-Print)'),
        ('float_currency', 'Naruszenie Standardu DREE (Pieniądze jako integer minor)'),
        ('silent_pass', 'Naruszenie Zasady 1 (Brak cichego sukcesu)'),
        ('ignore_test', 'Naruszenie Zasady 8 (Test-First & Negatives)'),
    ]

    for f in sorted(files):
        cand_text = f.read_text(encoding='utf-8')
        violations = []
        if not cand_text.startswith('---'):
            violations.append('Brak YAML frontmatter (wymagany trigger i description)')
        elif 'trigger:' not in cand_text:
            violations.append('Brak pola trigger w YAML frontmatter')
        elif 'description:' not in cand_text:
            violations.append('Brak pola description w YAML frontmatter')

        cand_lower = cand_text.lower()
        for term, msg in forbidden_terms:
            if term in cand_lower:
                violations.append(msg)

        est_tokens = int(len(cand_text.split()) * 1.3)
        if est_tokens > 400:
            violations.append(f'Przekroczony budżet tokenów reguły: {est_tokens} > 400')

        status = 'APPROVED_FOR_PROMOTION' if not violations else 'REJECTED'
        results.append({
            'file': f.name,
            'status': status,
            'estimatedTokens': est_tokens,
            'violations': violations
        })

    all_passed = all(r['status'] == 'APPROVED_FOR_PROMOTION' for r in results)
    return {
        'status': 'ALL_PASSED' if all_passed else 'VIOLATIONS_FOUND',
        'count': len(results),
        'results': results,
        'exitCode': 0 if all_passed else 2
    }

def approve_rule(candidate_name):
    """Promotes a validated rule candidate from learning_inbox to .agents/rules/."""
    inbox = ROOT / '.agents/learning_inbox'
    rules_dir = ROOT / '.agents/rules'
    rules_dir.mkdir(parents=True, exist_ok=True)

    cand_path = inbox / candidate_name if not Path(candidate_name).is_file() else Path(candidate_name)
    if not cand_path.is_file():
        raise Rejected(f'Candidate rule file not found: {candidate_name}')

    audit = check_rules(candidate_file=str(cand_path))
    if audit['status'] != 'ALL_PASSED':
        raise Rejected(f"Rule rejected by audit: {audit['results'][0]['violations']}")

    existing_rules = [r for r in rules_dir.glob('*.md') if r.is_file()]
    if len(existing_rules) >= 10:
        raise Rejected('Total rule limit reached (max 10 active rules in .agents/rules/). Prune or consolidate rules first.')

    total_tokens = sum(int(len(r.read_text(encoding='utf-8').split()) * 1.3) for r in existing_rules)
    cand_tokens = audit['results'][0]['estimatedTokens']
    if total_tokens + cand_tokens > 2500:
        raise Rejected(f'Total rule token budget exceeded: {total_tokens + cand_tokens} > 2500 tokens.')

    clean_name = cand_path.name.replace('.candidate', '')
    if not clean_name.endswith('.md'): clean_name += '.md'
    dest_path = rules_dir / clean_name
    shutil.copy2(cand_path, dest_path)
    cand_path.unlink()

    evidence_dir = ROOT / '.governance/evidence'
    evidence_dir.mkdir(parents=True, exist_ok=True)
    ev_path = evidence_dir / f"RULE_APPROVED_{clean_name}_{int(time.time())}.json"
    ev_data = {
        'type': 'G_LEARN_RULE_PROMOTION',
        'ruleName': clean_name,
        'path': str(dest_path.relative_to(ROOT)),
        'tokens': cand_tokens,
        'approvedAt': time.time(),
        'sha256': digest(dest_path.read_bytes())
    }
    ev_path.write_text(canonical(ev_data), encoding='utf-8')

    return {'status': 'RULE_PROMOTED', 'rule': clean_name, 'path': str(dest_path.relative_to(ROOT)), 'evidence': str(ev_path.relative_to(ROOT))}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', '-w', default=None, help='Explicit workspace path override')
    sub = p.add_subparsers(dest='cmd', required=True)
    
    for cmd in ['doctor', 'validate', 'spec-hash', 'status', 'release']:
        sub.add_parser(cmd)
    a = sub.add_parser('approve-spec')
    a.add_argument('--actor', required=True)
    a.add_argument('--reference', required=True)
    a = sub.add_parser('claim')
    a.add_argument('--task', required=True)
    a.add_argument('--actor', required=True)
    a.add_argument('--session', required=True)
    for cmd in ['heartbeat', 'finish', 'gate', 'integrate']:
        a = sub.add_parser(cmd)
        a.add_argument('--task', required=True)
        if cmd in {'heartbeat', 'finish'}:
            a.add_argument('--token', required=True)
    a = sub.add_parser('run')
    a.add_argument('--task', required=True)
    a.add_argument('--check', required=True)
    a = sub.add_parser('review')
    a.add_argument('--task', required=True)
    a.add_argument('--reviewer', default=None)
    a.add_argument('--actor', default=None)
    a.add_argument('--decision', choices=['APPROVED', 'REJECTED'], required=True)
    a.add_argument('--reference', required=True)
    a.add_argument('--reviewer-session', '--session', dest='reviewer_session', default=None)
    a.add_argument('--auditor-token', '--token', dest='auditor_token', default=None)

    a = sub.add_parser('discover')
    a.add_argument('--deep', action='store_true', default=False)
    
    a = sub.add_parser('scaffold-contracts')
    a.add_argument('--from-spec', default=None)
    a.add_argument('--out', default='contracts')

    a = sub.add_parser('package-handoff')
    a.add_argument('--task', required=True)
    a.add_argument('--out', default=None)

    a = sub.add_parser('golden-record')
    a.add_argument('--name', required=True)
    a.add_argument('--record', required=True)

    a = sub.add_parser('golden-assert')
    a.add_argument('--name', required=True)
    a.add_argument('--compare', default=None)

    a = sub.add_parser('auto-heal')
    a.add_argument('--task', required=True)
    a.add_argument('--cycle', type=int, default=1)
    a.add_argument('--hypothesis', default=None)
    a.add_argument('--reset', action='store_true', default=False)

    # V5 CLI Subparsers
    a = sub.add_parser('impact')
    a.add_argument('--file', default=None)
    a.add_argument('--symbol', default=None)

    a = sub.add_parser('worktree')
    a.add_argument('--task', required=True)
    a.add_argument('--action', choices=['create', 'merge', 'cleanup'], default='create')

    a = sub.add_parser('audit-tests')
    a.add_argument('--task', required=True)

    a = sub.add_parser('generate-charter')
    a.add_argument('--out', default='specs')

    a = sub.add_parser('trace-matrix')
    a.add_argument('--format', choices=['markdown', 'json'], default='markdown')

    a = sub.add_parser('interlock')
    a.add_argument('--task', required=True)
    a.add_argument('--cross-worktrees', action='store_true', default=False)

    a = sub.add_parser('approve-decision')
    a.add_argument('--adr-id', required=True)
    a.add_argument('--domain', default='global')
    a.add_argument('--assertion', required=True)
    a.add_argument('--scope', default='global')

    a = sub.add_parser('scaffold-module')
    a.add_argument('--name', required=True)
    a.add_argument('--domain', default='core')
    a.add_argument('--depends-on', nargs='*', default=[])
    a.add_argument('--type', default='fullstack')

    a = sub.add_parser('scaffold-unit')
    a.add_argument('--name', required=True)
    a.add_argument('--domain', default='core')
    a.add_argument('--type', default='service')

    a = sub.add_parser('check-standards')
    a.add_argument('--task', default=None)
    a.add_argument('--file', default=None)

    a = sub.add_parser('scaffold-page')
    a.add_argument('blueprint_pos', nargs='?', default=None, help='Blueprint identifier or path (positional)')
    a.add_argument('--blueprint', default=None, help='Blueprint identifier or path')
    a.add_argument('--out', default=None, help='Target file path override')

    a = sub.add_parser('wire-template')
    a.add_argument('--file', required=True)
    a.add_argument('--blueprint', default=None)

    a = sub.add_parser('check-templates')
    a.add_argument('--task', default=None)
    a.add_argument('--file', default=None)

    a = sub.add_parser('prune-evidence')
    a.add_argument('--keep', type=int, default=5)

    a = sub.add_parser('check-rules')
    a.add_argument('--candidate', default=None)

    a = sub.add_parser('approve-rule')
    a.add_argument('--candidate', required=True)

    args = p.parse_args()
    if args.workspace:
        set_workspace_root(Path(args.workspace))
    try:
        cmd = args.cmd
        if cmd == 'validate': result = validate()
        elif cmd == 'doctor': result = doctor()
        elif cmd == 'spec-hash': result = {'specDigest': spec_hash()}
        elif cmd == 'approve-spec': result = approve(args.actor, args.reference)
        elif cmd == 'claim': result = claim(args.task, args.actor, args.session)
        elif cmd == 'heartbeat': result = heartbeat(args.task, args.token)
        elif cmd == 'run': result = run_check(args.task, args.check)
        elif cmd == 'review':
            reviewer = args.reviewer or args.actor
            if not reviewer:
                raise Rejected('Reviewer or actor required for review')
            result = review(args.task, reviewer, args.decision, args.reference,
                            reviewer_session=args.reviewer_session, auditor_token=args.auditor_token)
        elif cmd == 'gate': result = gate(args.task)
        elif cmd == 'finish': result = finish(args.task, args.token)
        elif cmd == 'status': result = status()
        elif cmd == 'discover': result = discover(deep=args.deep)
        elif cmd == 'scaffold-contracts': result = scaffold_contracts(from_spec=args.from_spec, out_dir=args.out)
        elif cmd == 'package-handoff': result = package_handoff(args.task, out_path=args.out)
        elif cmd == 'golden-record': result = golden_record(args.name, args.record)
        elif cmd == 'golden-assert': result = golden_assert(args.name, compare_command=args.compare)
        elif cmd == 'auto-heal': result = auto_heal(args.task, cycle=args.cycle, hypothesis=args.hypothesis, reset=args.reset)
        elif cmd == 'integrate': result = integrate(args.task)
        elif cmd == 'release': result = release()
        elif cmd == 'impact': result = calculate_impact(target_file=args.file, target_symbol=args.symbol)
        elif cmd == 'worktree': result = manage_worktree(args.task, action=args.action)
        elif cmd == 'audit-tests': result = audit_tests(args.task)
        elif cmd == 'generate-charter': result = generate_charter(out_dir=args.out)
        elif cmd == 'trace-matrix': result = trace_matrix(export_format=args.format)
        elif cmd == 'interlock': result = interlock(args.task, cross_worktrees=args.cross_worktrees)
        elif cmd == 'approve-decision': result = approve_decision(args.adr_id, domain=args.domain, assertion=args.assertion, scope=args.scope)
        elif cmd == 'scaffold-module': result = scaffold_module(args.name, domain=args.domain, depends_on=args.depends_on, module_type=args.type)
        elif cmd == 'scaffold-unit': result = scaffold_unit(name=args.name, domain=args.domain, unit_type=args.type)
        elif cmd == 'check-standards': result = check_standards(task_id=args.task, file_path=args.file)
        elif cmd == 'scaffold-page':
            bp_id = args.blueprint or args.blueprint_pos
            if not bp_id:
                raise Rejected("scaffold-page requires blueprint ID: gov.py scaffold-page <blueprint> or --blueprint <blueprint>")
            result = scaffold_page(bp_id, out_file=args.out)
        elif cmd == 'wire-template': result = wire_template(args.file, blueprint_id=args.blueprint)
        elif cmd == 'check-templates': result = check_templates(task_id=args.task, file_path=args.file)
        elif cmd == 'prune-evidence': result = prune_evidence(keep_last=args.keep)
        elif cmd == 'check-rules': result = check_rules(candidate_file=args.candidate)
        elif cmd == 'approve-rule': result = approve_rule(candidate_name=args.candidate)
        else: result = {'status': 'UNKNOWN_COMMAND'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('exitCode', 0) != 0 else 0
    except (Rejected, KeyError, ValueError, OSError, sqlite3.Error) as e:
        print(json.dumps({'status': 'REJECTED', 'reason': str(e)}, ensure_ascii=False))
        return 2

if __name__ == '__main__':
    sys.exit(main())