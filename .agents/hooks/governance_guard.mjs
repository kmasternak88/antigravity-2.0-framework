#!/usr/bin/env node
/**
 * Ultra-Fast Governance Guard Hook for Antigravity 2.0 (Latency target: < 10ms)
 * Implements PreToolUse and Stop (DoD Gate Enforcer).
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { resolve, relative, join, isAbsolute } from 'node:path';
import { execFileSync } from 'node:child_process';
import process from 'node:process';

const INTROSPECTION_PATTERNS = [
  /\.governance[\\/]bin[\\/]gov\.py/i,
  /\.governance[\\/]hooks/i,
  /\.agents[\\/]hooks/i,
  /\.agents[\\/]\.governance/i
];

function isAntiIntrospectionTarget(targetStr) {
  if (!targetStr) return false;
  return INTROSPECTION_PATTERNS.some((rx) => rx.test(String(targetStr)));
}

function isTaskInProgress(rootDir, conversationId) {
  if (!rootDir) return false;
  const dbPath = join(rootDir, '.governance', 'state', 'state.sqlite');
  const dbPathAlt = join(rootDir, '.governance', 'state', 'gov.db');
  const targetDb = existsSync(dbPath) ? dbPath : (existsSync(dbPathAlt) ? dbPathAlt : null);
  if (!targetDb) return false;

  try {
    const pyScript = `import sqlite3, sys, time
try:
    c = sqlite3.connect(sys.argv[1], timeout=2)
    now = time.time()
    conv = sys.argv[2] if len(sys.argv) > 2 else ''
    if conv:
        r = c.execute("SELECT id FROM tasks WHERE session=? AND state='ACTIVE' AND expires>?", (conv, now)).fetchone()
        if r:
            print("ACTIVE")
            sys.exit(0)
    r_any = c.execute("SELECT id FROM tasks WHERE state='ACTIVE' AND expires>?", (now,)).fetchone()
    print("ACTIVE" if r_any else "INACTIVE")
except Exception:
    print("INACTIVE")
`;
    const out = execFileSync('python', ['-c', pyScript, targetDb, conversationId || ''], {
      encoding: 'utf8',
      timeout: 1500,
      windowsHide: true
    }).trim();
    return out === 'ACTIVE';
  } catch {
    return false;
  }
}

const SAFE_CMD_PREFIXES = [
  'git status', 'git diff', 'git log', 'pwd', 'echo', 'dir',
  'python .governance/bin/gov.py', 'python -m unittest', 'pytest',
  'npm test', 'npm run', 'npx tsc', 'cargo test', 'node '
];

const BLOCKED_COMMANDS = [
  /rm\s+-rf\s+\//i,
  /del\s+\/[fsq]/i,
  /format\s+[a-z]:/i,
  /diskpart/i,
  /git\s+push\s+.*--force\s+.*main/i,
  /drop\s+table/i
];

const PROTECTED_FILES = [
  /SESSION_STATE\.json$/,
  /\.env(\..+)?$/,
  /id_rsa/,
  /id_ed25519/
];

function readStdin() {
  return new Promise((resolvePromise) => {
    let raw = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { raw += chunk; });
    process.stdin.on('end', () => {
      try {
        resolvePromise(JSON.parse(raw || '{}'));
      } catch {
        resolvePromise({});
      }
    });
  });
}

const SUBPROJECT_MARKERS = [
  join('.governance', 'config.json'),
  'package.json',
  'pyproject.toml',
  'Cargo.toml',
  'go.mod',
  '.project-root'
];

function findRoot(startDir) {
  if (process.env.GOV_WORKSPACE && existsSync(process.env.GOV_WORKSPACE)) {
    return resolve(process.env.GOV_WORKSPACE);
  }
  if (process.env.GOV_ROOT && existsSync(process.env.GOV_ROOT)) {
    return resolve(process.env.GOV_ROOT);
  }
  if (process.env.ANTIGRAVITY_WORKSPACE && existsSync(process.env.ANTIGRAVITY_WORKSPACE)) {
    return resolve(process.env.ANTIGRAVITY_WORKSPACE);
  }

  let cur = resolve(startDir || process.cwd());

  // 1. Check .active_workspace upwards
  let checkMarker = cur;
  while (checkMarker && checkMarker !== resolve(checkMarker, '..')) {
    const markerFile = join(checkMarker, '.active_workspace');
    if (existsSync(markerFile)) {
      try {
        const line = readFileSync(markerFile, 'utf8').trim();
        if (line) {
          const target = isAbsolute(line) ? resolve(line) : resolve(checkMarker, line);
          if (existsSync(target)) return target;
        }
      } catch {}
    }
    checkMarker = resolve(checkMarker, '..');
  }

  // 2. Nearest project marker
  let iter = cur;
  while (iter && iter !== resolve(iter, '..')) {
    if (SUBPROJECT_MARKERS.some(m => existsSync(join(iter, m)))) {
      return iter;
    }
    iter = resolve(iter, '..');
  }

  // 3. Fallback to git or AGENTS.md
  iter = cur;
  while (iter && iter !== resolve(iter, '..')) {
    if (existsSync(join(iter, '.governance', 'config.json')) || existsSync(join(iter, 'AGENTS.md')) || existsSync(join(iter, '.git'))) {
      return iter;
    }
    iter = resolve(iter, '..');
  }
  return process.cwd();
}

async function handlePreTool(payload) {
  const toolCall = payload.toolCall || {};
  const name = toolCall.name || '';
  const args = toolCall.args || {};

  if (!name) {
    return { decision: 'allow' };
  }

  // 0. Anti-Introspection Guard (Lock 4)
  const READ_TOOLS = ['view_file', 'read_file', 'grep_search', 'list_dir', 'find_by_name'];
  if (READ_TOOLS.includes(name)) {
    const target = args.AbsolutePath || args.SearchPath || args.DirectoryPath || args.Path || args.path || args.file_path || args.TargetFile || args.SearchDirectory || args.file || '';
    if (isAntiIntrospectionTarget(target)) {
      const rootDir = findRoot();
      if (rootDir && isTaskInProgress(rootDir, payload.conversationId)) {
        return {
          decision: 'deny',
          reason: '[GovernanceGuard] [ANTI_INTROSPECTION] Lock 4 (Anti-Introspection Guard): Odczyt silnika Governance (.governance/bin/gov.py, .governance/hooks/) jest zablokowany podczas trwania zadania (IN_PROGRESS).'
        };
      }
    }
    return { decision: 'allow' };
  }

  // 1. Terminal Command Check
  if (name === 'run_command') {
    const cmd = (args.CommandLine || args.command || '').trim();
    if (!cmd) return { decision: 'allow' };

    if (isAntiIntrospectionTarget(cmd)) {
      const isGovRun = /python3?\s+\.governance[\\/]bin[\\/]gov\.py/i.test(cmd);
      if (!isGovRun) {
        const rootDir = findRoot();
        if (rootDir && isTaskInProgress(rootDir, payload.conversationId)) {
          return {
            decision: 'deny',
            reason: '[GovernanceGuard] [ANTI_INTROSPECTION] Lock 4 (Anti-Introspection Guard): Badanie silnika walidacji (.governance/bin/gov.py, .governance/hooks/) w terminalu jest zablokowane podczas trwania zadania (IN_PROGRESS).'
          };
        }
      }
    }

    for (const rx of BLOCKED_COMMANDS) {
      if (rx.test(cmd)) {
        return { decision: 'deny', reason: `[GovernanceGuard] Zablokowano destrukcyjne polecenie: "${cmd.slice(0, 80)}"` };
      }
    }

    if (SAFE_CMD_PREFIXES.some(prefix => cmd.startsWith(prefix))) {
      return { decision: 'allow', reason: 'Bezpieczne polecenie deweloperskie / weryfikacyjne' };
    }

    return { decision: 'allow' };
  }

  // 2. File Write Guard
  const writeTools = ['write_to_file', 'replace_file_content', 'multi_replace_file_content', 'write_file', 'edit_file'];
  if (writeTools.includes(name)) {
    const target = args.TargetFile || args.Path || args.path || args.targetFile || '';
    if (!target) return { decision: 'deny', reason: 'Missing target file path' };

    for (const rx of PROTECTED_FILES) {
      if (rx.test(target)) {
        return { decision: 'deny', reason: `[GovernanceGuard] Zablokowano modyfikację chronionego pliku stanu: "${target}"` };
      }
    }

    const rootDir = findRoot();
    const absTarget = isAbsolute(target) ? resolve(target) : resolve(rootDir, target);
    const rel = relative(rootDir, absTarget);
    if (rel.startsWith('..') || isAbsolute(rel)) {
      return {
        decision: 'deny',
        reason: `[GovernanceGuard] HERMETIC_BOUNDARY_VIOLATION: Write to "${target}" escapes active workspace "${rootDir}". Cross-project mutations are forbidden.`
      };
    }
    const relTarget = rel.replace(/\\/g, '/');

    // Guard against ungoverned codebase mutation when framework is intended
    const isAgentic = existsSync(join(rootDir, 'AGENTS.md')) || existsSync(join(rootDir, '.agents')) || existsSync(join(rootDir, 'specs'));
    const hasGov = existsSync(join(rootDir, '.governance'));
    const isSource = ['src/', 'crates/', 'lib/', 'app/', 'internal/'].some(d => relTarget.startsWith(d) || relTarget === d.slice(0, -1));
    if (isAgentic && !hasGov && isSource) {
      return {
        decision: 'deny',
        reason: `[GovernanceGuard] UNGOVERNED_WRITE_BLOCKED: Próba zapisu do kodu produkcyjnego ("${relTarget}") w projekcie agentowym bez zainstalowanego frameworka .governance/. Zainicjalizuj projekt za pomocą /init lub bootstrap.py!`
      };
    }

    // Protected governance paths
    if (relTarget.startsWith('.governance/state/') || relTarget.startsWith('.governance/golden/')) {
      return { decision: 'deny', reason: `[GovernanceGuard] Bezpośrednia modyfikacja wewnętrznych struktur governance zabroniona: ${relTarget}` };
    }

    // Task Handoff Scope Guard (P0-3 Hardening: enforce allowed_paths when handoff is active)
    try {
      const handoffsDir = join(rootDir, '.governance', 'handoffs');
      if (existsSync(handoffsDir)) {
        const hFiles = readdirSync(handoffsDir).filter(f => f.endsWith('.json'));
        for (const hf of hFiles) {
          const hContent = JSON.parse(readFileSync(join(handoffsDir, hf), 'utf8'));
          const allowed = hContent.allowedToWrite || hContent.allowed_paths || [];
          if (allowed.length > 0) {
            const isAllowed = allowed.some(a => {
              const normA = a.replace(/\\/g, '/').replace(/^\.\//, '').replace(/\/$/, '');
              return relTarget === normA || relTarget.startsWith(normA + '/');
            });
            if (!isAllowed) {
              return {
                decision: 'deny',
                reason: `[GovernanceGuard] OUT_OF_SCOPE: Zapis do "${relTarget}" wykracza poza allowed_paths aktywnego zadania (${allowed.join(', ')}).`
              };
            }
          }
        }
      }
    } catch {}

    return { decision: 'allow', reason: 'Dozwolony zapis w granicach workspace' };
  }

  return { decision: 'allow' };
}

async function handleStop(payload) {
  const rootDir = process.env.GOV_ROOT || findRoot();

  // 1. Sprawdź tasks/todo.md pod kątem niedokończonych zadań [- /]
  const todoFile = join(rootDir, 'tasks', 'todo.md');
  if (existsSync(todoFile)) {
    try {
      const content = readFileSync(todoFile, 'utf8');
      if (/^\s*-\s*\[\/\]/m.test(content)) {
        return {
          decision: 'continue',
          reason: '[DoD Stop Gate] Zadanie w tasks/todo.md ma status W TOKU (- [/]). Dokończ implementację, testy lub zaktualizuj status przed zakończeniem sesji!'
        };
      }
    } catch {}
  }

  // 2. Sprawdź tasks.json pod kątem aktywnego zadania bez GATE_PASS
  const tasksJson = join(rootDir, '.governance', 'tasks.json');
  if (existsSync(tasksJson)) {
    try {
      const data = JSON.parse(readFileSync(tasksJson, 'utf8'));
      const activeTasks = (data.tasks || []).filter(t => t.state === 'in_progress');
      if (activeTasks.length > 0) {
        return {
          decision: 'continue',
          reason: `[DoD Stop Gate] Zadanie "${activeTasks[0].id}" ma status in_progress. Wymagane zaliczenie bramki G5 (gov.py gate) przed opuszczeniem tury!`
        };
      }
    } catch {}
  }

  return { decision: 'allow', reason: 'Definicja ukończenia (DoD) spełniona' };
}

async function main() {
  const action = process.argv[2] || 'pre-tool';
  const payload = await readStdin();

  let response;
  if (action === 'stop') {
    response = await handleStop(payload);
  } else {
    response = await handlePreTool(payload);
  }

  process.stdout.write(JSON.stringify(response) + '\n');
}

main().catch((err) => {
  process.stderr.write(`[GovernanceGuard Error] ${err.message}\n`);
  process.stdout.write(JSON.stringify({ decision: 'allow' }) + '\n');
});
