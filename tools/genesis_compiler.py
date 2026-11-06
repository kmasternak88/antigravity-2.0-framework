#!/usr/bin/env python3
"""Genesis Blueprint Compiler & Validator for Antigravity Closed Loop Framework v8.1.

Compiles Master Implementation Blueprints (Phases 1-7) into deterministic
Living Charter files in specs/, baseline contracts in contracts/, and an acyclic topological
hierarchical DAG (Epics -> Milestones/Sprints -> Atomic Tasks) in .governance/tasks.json.
Enforces Zero Placeholders, Strict DAG Order, Disjoint Parallel Write-Sets, and Verifiable DoD Commands.
"""
import argparse, json, os, re, sys
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional, Union

__all__ = [
    "lint_zero_placeholders",
    "parse_hierarchical_phase_6",
    "parse_markdown_table_dag",
    "validate_dag_acyclic",
    "validate_disjoint_parallel_paths",
    "validate_task_complexity_limits",
    "detect_tech_stack",
    "is_valid_mutation_target",
    "validate_gate_g4_cardinal_rule",
    "scaffold_baseline_contracts",
    "compile_blueprint",
    "find_workspace_root",
    "main",
]

FORBIDDEN_CONFIG_PATTERNS = re.compile(
    r'^(vite\.config|tsconfig|package|webpack|babel\.config|rollup\.config|eslint|prettier|jest\.config|vitest\.config)',
    re.IGNORECASE
)

def is_valid_mutation_target(candidate_path: Path) -> bool:
    """Intelligent Mock-Breaker: exclude config files, strictly target src/ or domain modules."""
    if candidate_path.suffix not in ['.py', '.ts', '.tsx', '.js', '.jsx', '.php', '.go', '.rs']:
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

def validate_gate_g4_cardinal_rule(task_id: str, allowed_paths: List[str], audited_files_count: int):
    """Kardynalna Zasada Bramki G4: jeśli zadanie modyfikuje pliki w src/, a auditedFiles == 0, rzuć błąd ZERO_FILES_AUDITED."""
    modifies_src = any(p == 'src' or p.startswith('src/') or p.startswith('src\\') or '/src/' in p.replace('\\', '/') for p in allowed_paths)
    if modifies_src and audited_files_count == 0:
        raise ValueError(f"ZERO_FILES_AUDITED: Task '{task_id}' targets files in src/ but 0 files were audited by Gate G4 standards check!")

def detect_tech_stack(workspace_root: Path) -> Dict[str, Any]:
    """Detects project tech stack and dynamically binds language-aware test runner."""
    pkg_json = workspace_root / "package.json"
    tsconfig = workspace_root / "tsconfig.json"
    if pkg_json.is_file() or tsconfig.is_file():
        runner_argv = ["npm", "test"]
        gate_prefix = "npm test --"
        if pkg_json.is_file():
            try:
                pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                scripts = pkg_data.get("scripts", {})
                if "vitest" in deps or "vitest" in scripts.get("test", ""):
                    runner_argv = ["npx", "vitest", "run"]
                    gate_prefix = "npx vitest run"
                elif "test" in scripts:
                    runner_argv = ["npm", "test"]
                    gate_prefix = "npm test --"
                elif "jest" in deps or "jest" in scripts.get("test", ""):
                    runner_argv = ["npx", "jest"]
                    gate_prefix = "npx jest"
                else:
                    runner_argv = ["node", "--test"]
                    gate_prefix = "node --test"
            except Exception:
                runner_argv = ["npm", "test"]
                gate_prefix = "npm test --"
        return {
            "stack": "typescript",
            "runner_argv": runner_argv,
            "gate_cmd": gate_prefix,
            "gate_ext": ".ts"
        }
    py_pytest = (workspace_root / "pytest.ini").is_file() or (workspace_root / "pyproject.toml").is_file()
    has_pytest_dir = (workspace_root / "tests").is_dir()
    runner_argv = ["pytest"] if (py_pytest or has_pytest_dir) else ["python", "-m", "unittest"]
    return {
        "stack": "python",
        "runner_argv": runner_argv,
        "gate_cmd": "pytest",
        "gate_ext": ".py"
    }

FORBIDDEN_PLACEHOLDER_REGEX = re.compile(
    r'\b(?:do ustalenia|w zależności od potrzeb|itd\.?|itp\.?|//\s*TODO|/\*\s*TODO|#\s*TODO|TODO:|FIXME:|TBD|placeholder|stub|\.\.\.\s*\(reszta|zabezpiecz odpowiednio|dowolny|jakis|jakikolwiek)\b',
    re.IGNORECASE
)

REQUIRED_PHASES = [
    ("FAZA 1", "DEKONSTRUKCJA DOMENY, WYMAGANIA I PRZYPADKI BRZEGOWE"),
    ("FAZA 2", "ARCHITEKTURA DANYCH I ZARZĄDZANIE STANEM"),
    ("FAZA 3", "KONTRAKTY KOMUNIKACYJNE I WALIDACJA I/O"),
    ("FAZA 4", "BEZPIECZEŃSTWO, ODPORNOŚĆ I OBSERWOWALNOŚĆ"),
    ("FAZA 5", "STOS TECHNOLOGICZNY, KONFIGURACJA I DRZEWO PLIKÓW"),
    ("FAZA 6", "ATOMOWY PLAN IMPLEMENTACJI"),
    ("FAZA 7", "STRATEGIA TESTOWANIA I KONTROLI JAKOŚCI")
]

def find_workspace_root() -> Path:
    env_root = os.environ.get('GOV_WORKSPACE') or os.environ.get('ANTIGRAVITY_WORKSPACE')
    if env_root and Path(env_root).is_dir():
        return Path(env_root).resolve()
    cur = Path.cwd()
    while cur != cur.parent:
        if (cur / '.active_workspace').is_file():
            line = (cur / '.active_workspace').read_text(encoding='utf-8').strip()
            if line:
                target = (cur / line).resolve()
                if target.is_dir():
                    return target
        if (cur / '.governance' / 'config.json').is_file():
            return cur
        cur = cur.parent
    return Path.cwd().resolve()

def lint_zero_placeholders(content: str) -> List[Dict[str, Any]]:
    violations = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        if line.strip().startswith('#') or 'FORBIDDEN_PLACEHOLDER' in line or 'Regex' in line:
            continue
        matches = FORBIDDEN_PLACEHOLDER_REGEX.findall(line)
        for m in matches:
            violations.append({
                "line": idx,
                "text": line.strip(),
                "matchedToken": m,
                "rule": "ZERO_PLACEHOLDERS_AND_ZERO_AMBIGUITY"
            })
    return violations

def parse_hierarchical_phase_6(content: str, workspace_root: Optional[Path] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parse Phase 6 markdown into Epics (L1), Milestones/Sprints (L2), and Tasks DAG (L3)."""
    epics: List[Dict[str, Any]] = []
    milestones: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []
    
    ws = workspace_root or find_workspace_root()
    stack = detect_tech_stack(ws)
    default_m1_gate = f"{stack['gate_cmd']} tests/integration/test_m1_gate{stack['gate_ext']}"

    current_epic = {"id": "EPIC-01", "title": "Architektura Bazowa i Fundamenty", "description": "Podstawa technologiczna i model danych.", "milestones": []}
    current_milestone = {"id": "M1", "epic_id": "EPIC-01", "title": "Inicjalizacja Schematu i Kontraktów", "depends_on_milestones": [], "gate_check": default_m1_gate, "tasks": []}
    
    epic_seen = False
    milestone_seen = False

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 1. Epic header: ### Epic EPIC-XX: Title lub ### Epik ...
        epic_match = re.match(r'^###\s+(?:Epic|Epik)\s+([A-Za-z0-9_-]+)\s*:\s*([^\n]+)', line, re.IGNORECASE)
        if epic_match:
            epic_seen = True
            current_epic = {
                "id": epic_match.group(1).strip(),
                "title": epic_match.group(2).strip(),
                "description": f"Strumień wartości {epic_match.group(2).strip()}",
                "milestones": []
            }
            epics.append(current_epic)
            i += 1
            continue
            
        # 2. Milestone / Sprint header: #### Milestone MXX: Title lub #### Sprint SXX: ...
        ms_match = re.match(r'^####\s+(?:Milestone|Sprint|Kamień\s+Milowy)\s+([A-Za-z0-9_-]+)\s*:\s*([^\n]+)', line, re.IGNORECASE)
        if ms_match:
            milestone_seen = True
            ms_id = ms_match.group(1).strip()
            ms_title = ms_match.group(2).strip()
            ms_gate = f"{stack['gate_cmd']} tests/integration/test_{ms_id.lower()}_gate{stack['gate_ext']}"
            current_milestone = {
                "id": ms_id,
                "epic_id": current_epic["id"],
                "title": ms_title,
                "depends_on_milestones": [epics[-1]["milestones"][-1]] if epics and epics[-1]["milestones"] else [],
                "gate_check": ms_gate,
                "tasks": []
            }
            milestones.append(current_milestone)
            if current_epic and ms_id not in current_epic["milestones"]:
                current_epic["milestones"].append(ms_id)
            i += 1
            continue

        # 3. Task header: ##### Task TXXX: Title lub ### Task TXXX: ...
        task_match = re.match(r'^(?:#####|####|###)\s+(?:Zadanie|Task)\s+([A-Za-z0-9_-]+)\s*:\s*([^\n]+)', line, re.IGNORECASE)
        if task_match:
            t_id = task_match.group(1).strip()
            t_title = task_match.group(2).strip()
            
            # Read block until next header
            t_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^(?:#####|####|###)\s+(?:Zadanie|Task|Epic|Epik|Milestone|Sprint)', lines[i].strip(), re.IGNORECASE):
                t_lines.append(lines[i])
                i += 1
                
            t_body = "\n".join(t_lines)
            
            deps = []
            dep_match = re.search(r'[-*]\s+\*\*Zależności\*\*:\s*\[?(.*?)\]?(?:\n|$)', t_body, re.IGNORECASE)
            if dep_match and dep_match.group(1).strip():
                raw_deps = dep_match.group(1).strip()
                deps = [d.strip().strip('`"\'') for d in raw_deps.split(',') if d.strip() and d.strip().lower() not in ('brak', 'none', '-')]
                
            allowed_paths = []
            paths_match = re.search(r'[-*]\s+\*\*Pliki\s+docelowe\*\*:\s*([^\n]+)', t_body, re.IGNORECASE)
            if paths_match:
                raw_paths = paths_match.group(1)
                allowed_paths = [p.strip().strip('`"\'') for p in re.findall(r'`([^`]+)`', raw_paths)]
                if not allowed_paths:
                    allowed_paths = [p.strip().strip('`"\'') for p in raw_paths.split(',') if p.strip()]

            context_files = []
            ctx_match = re.search(r'[-*]\s+\*\*Kontekst\s+wejściowy\*\*:\s*([^\n]+)', t_body, re.IGNORECASE)
            if ctx_match:
                raw_ctx = ctx_match.group(1)
                context_files = [p.strip().strip('`"\'') for p in re.findall(r'`([^`]+)`', raw_ctx)]
                if not context_files:
                    context_files = [p.strip().strip('`"\'') for p in raw_ctx.split(',') if p.strip()]

            dod_command = ""
            dod_match = re.search(r'[-*]\s+\*\*(?:Kryterium\s+Odbioru(?:\s*\(DoD\))?|DoD|Verifiable\s+Command)\*\*:\s*`?([^`\n]+)`?', t_body, re.IGNORECASE)
            if dod_match:
                dod_command = dod_match.group(1).strip()

            task_obj = {
                "id": t_id,
                "epic_id": current_epic["id"],
                "milestone_id": current_milestone["id"],
                "title": t_title,
                "depends_on": deps,
                "allowed_paths": allowed_paths if allowed_paths else ["src"],
                "context_files": context_files,
                "checks": ["unit"] if dod_command else ["unit"],
                "acceptance": [f"DOD verified: {dod_command}"] if dod_command else [f"Completed {t_title}"],
                "dod_command": dod_command,
                "risk": "medium",
                "standards_checklist": [
                    "interface_contract",
                    "input_validation",
                    "domain_exception",
                    "pure_logic_srp",
                    "telemetry_logging",
                    "dual_test_suite",
                    "export_registration"
                ]
            }
            tasks.append(task_obj)
            current_milestone["tasks"].append(t_id)
            continue
            
        i += 1

    # Fallback to markdown table parser if block parser found no tasks
    if not tasks:
        tasks = parse_markdown_table_dag(content)
        
    # Auto-synthesize default Epics and Milestones if none explicitly declared
    if not epics and tasks:
        epics = [
            {"id": "EPIC-01", "title": "Architektura Bazowa i Fundament Danych", "description": "Konfiguracja, bazy danych i bazowe modele.", "milestones": ["M1"]},
            {"id": "EPIC-02", "title": "Rdzenna Logika Biznesowa i Usługi", "description": "Kluczowe moduły domenowe i przetwarzanie.", "milestones": ["M2"]},
            {"id": "EPIC-03", "title": "API, Bezpieczeństwo i Integracja", "description": "Endpointy komunikacyjne, autoryzacja i bramka wydania.", "milestones": ["M3"]}
        ]
        milestones = [
            {"id": "M1", "epic_id": "EPIC-01", "title": "Fundament i Schematy", "depends_on_milestones": [], "gate_check": f"{stack['gate_cmd']} tests/integration/test_m1_gate{stack['gate_ext']}", "tasks": []},
            {"id": "M2", "epic_id": "EPIC-02", "title": "Usługi Domenowe", "depends_on_milestones": ["M1"], "gate_check": f"{stack['gate_cmd']} tests/integration/test_m2_gate{stack['gate_ext']}", "tasks": []},
            {"id": "M3", "epic_id": "EPIC-03", "title": "Integracja i Hardening", "depends_on_milestones": ["M2"], "gate_check": f"{stack['gate_cmd']} tests/integration/test_m3_gate{stack['gate_ext']}", "tasks": []}
        ]
        # Distribute tasks evenly into M1, M2, M3
        n = len(tasks)
        chunk = max(1, (n + 2) // 3)
        for idx, t in enumerate(tasks):
            if idx < chunk:
                t["epic_id"] = "EPIC-01"
                t["milestone_id"] = "M1"
                milestones[0]["tasks"].append(t["id"])
            elif idx < chunk * 2:
                t["epic_id"] = "EPIC-02"
                t["milestone_id"] = "M2"
                milestones[1]["tasks"].append(t["id"])
            else:
                t["epic_id"] = "EPIC-03"
                t["milestone_id"] = "M3"
                milestones[2]["tasks"].append(t["id"])

    return epics, milestones, tasks

def parse_markdown_table_dag(content: str) -> List[Dict[str, Any]]:
    """Parse markdown table in Phase 6 into DAG tasks."""
    tasks = []
    in_table = False
    headers = []
    
    for line in content.splitlines():
        line_clean = line.strip()
        if not line_clean.startswith('|'):
            in_table = False
            continue
        
        cols = [c.strip() for c in line_clean.split('|')[1:-1]]
        if not in_table:
            if any('Task ID' in c or 'ID' in c for c in cols):
                headers = [c.lower() for c in cols]
                in_table = True
            continue
        
        if all(re.match(r'^[-:]+$', c) for c in cols):
            continue
            
        row_dict = dict(zip(headers, cols))
        task_id = next((row_dict[k] for k in row_dict if 'id' in k), f"T{len(tasks)+1:03d}").strip('` ')
        task_title = next((row_dict[k] for k in row_dict if 'nazwa' in k or 'name' in k or 'zadanie' in k or 'title' in k), "Task").strip('` ')
        
        raw_deps = next((row_dict[k] for k in row_dict if 'zależno' in k or 'depend' in k), "[]")
        deps = [d.strip().strip('`[]"\'') for d in raw_deps.split(',') if d.strip().strip('`[]"\'') and d.strip().lower() not in ('brak', 'none', '-')]
        
        raw_paths = next((row_dict[k] for k in row_dict if 'pliki' in k or 'paths' in k or 'target' in k), "src")
        paths = [p.strip().strip('`"\'') for p in re.findall(r'`([^`]+)`', raw_paths)] or [raw_paths.strip('` ')]
        
        dod = next((row_dict[k] for k in row_dict if 'dod' in k or 'kryterium' in k or 'command' in k), "").strip('` ')
        
        tasks.append({
            "id": task_id,
            "title": task_title,
            "depends_on": deps,
            "allowed_paths": paths,
            "checks": ["unit"] if dod else ["unit"],
            "acceptance": [f"DOD verified: {dod}"] if dod else [f"Completed {task_title}"],
            "dod_command": dod,
            "risk": "medium",
            "standards_checklist": [
                "interface_contract",
                "input_validation",
                "domain_exception",
                "pure_logic_srp",
                "telemetry_logging",
                "dual_test_suite",
                "export_registration"
            ]
        })
        
    return tasks

def validate_dag_acyclic(tasks: List[Dict[str, Any]]):
    """Ensure tasks form a strictly topologically sorted acyclic graph."""
    id_map = {t["id"]: t for t in tasks}
    seen_ids = set()
    
    # 1. Topological order check: Task N may only depend on Tasks already declared (< N)
    for idx, t in enumerate(tasks):
        tid = t["id"]
        for dep in t.get("depends_on", []):
            if dep not in id_map:
                raise ValueError(f"Task '{tid}' references unknown dependency '{dep}'")
            if dep not in seen_ids:
                raise ValueError(
                    f"STRICT_DAG_VIOLATION: Task '{tid}' (index {idx}) depends on '{dep}' which is defined later or concurrently. Forward references are forbidden."
                )
        seen_ids.add(tid)
        
    # 2. Cycle detection via Kahn's algorithm
    in_degree = {t["id"]: 0 for t in tasks}
    adj = {t["id"]: [] for t in tasks}
    for t in tasks:
        for dep in t.get("depends_on", []):
            adj[dep].append(t["id"])
            in_degree[t["id"]] += 1
            
    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    visited = 0
    while queue:
        u = queue.pop(0)
        visited += 1
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    if visited != len(tasks):
        raise ValueError("CYCLIC_DAG_DETECTED: CIRCULAR_DEPENDENCY_DETECTED: Execution graph contains a cycle.")

def validate_disjoint_parallel_paths(tasks: List[Dict[str, Any]]):
    """Enforce Disjoint Write-Set Rule: concurrent tasks must not share mutable allowed_paths."""
    # Build ancestor sets via transitive closure
    ancestors: Dict[str, Set[str]] = {t["id"]: set() for t in tasks}
    for t in tasks:
        stack = list(t.get("depends_on", []))
        while stack:
            parent = stack.pop()
            if parent not in ancestors[t["id"]]:
                ancestors[t["id"]].add(parent)
                # add parent's dependencies
                for other in tasks:
                    if other["id"] == parent:
                        stack.extend(other.get("depends_on", []))
                        
    # Check all pairs
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            tA = tasks[i]
            tB = tasks[j]
            idA, idB = tA["id"], tB["id"]
            
            # If one is ancestor of another, they are strictly sequential -> allowed
            if idA in ancestors[idB] or idB in ancestors[idA]:
                continue
                
            # Otherwise they are concurrent -> allowed_paths MUST be disjoint
            pathsA = set(tA.get("allowed_paths", []))
            pathsB = set(tB.get("allowed_paths", []))
            overlap = pathsA.intersection(pathsB)
            if overlap:
                raise ValueError(
                    f"DAG_CONCURRENT_COLLISION: Tasks '{idA}' and '{idB}' run in parallel but share mutable allowed_paths: {overlap}. Parallel execution requires disjoint write-sets!"
                )

def validate_task_complexity_limits(tasks: Union[List[Dict[str, Any]], List[str]]):
    """Enforce The 40/3/1 Rule: max 3 allowed_paths and max 5 context_files per atomic task."""
    violations = []
    if tasks and isinstance(tasks[0], str):
        if len(tasks) > 3:
            violations.append(f"Task specified {len(tasks)} allowed_paths: {tasks} (limit is 3). Atomize the task.")
        if violations:
            raise ValueError(f"TASK_COMPLEXITY_LIMIT_EXCEEDED (Rule 40/3/1):\n" + "\n".join(f"  - {v}" for v in violations))
        return

    for t in tasks:
        paths = t.get("allowed_paths", [])
        contexts = t.get("context_files", [])
        if len(paths) > 3:
            violations.append(f"Task '{t.get('id', 'unknown')}' specifies {len(paths)} allowed_paths: {paths} (limit is 3). Atomize the task.")
        if len(contexts) > 5:
            violations.append(f"Task '{t.get('id', 'unknown')}' specifies {len(contexts)} context_files: {contexts} (limit is 5). Reduce context window blast-radius.")
    if violations:
        raise ValueError(f"TASK_COMPLEXITY_LIMIT_EXCEEDED (Rule 40/3/1):\n" + "\n".join(f"  - {v}" for v in violations))

def scaffold_baseline_contracts(contracts_dir: Path, workspace_root: Path):
    """Ensure baseline interface contracts exist in contracts/ for Interface-First Freeze (G3)."""
    contracts_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. OpenAPI 3.1.0 Contract
    openapi_file = contracts_dir / "openapi.json"
    if not openapi_file.exists():
        openapi_content = {
            "openapi": "3.1.0",
            "info": {
                "title": f"{workspace_root.name} API Contracts",
                "version": "1.0.0",
                "description": "Deterministic Interface Contracts frozen at Gate G1/G2 under DREE v8.1 standard."
            },
            "paths": {},
            "components": {
                "schemas": {
                    "DomainErrorEnvelope": {
                        "type": "object",
                        "required": ["error", "code", "correlation_id", "timestamp"],
                        "properties": {
                            "error": {"type": "string"},
                            "code": {"type": "string"},
                            "correlation_id": {"type": "string", "format": "uuid"},
                            "timestamp": {"type": "string", "format": "date-time"}
                        }
                    }
                }
            }
        }
        openapi_file.write_text(json.dumps(openapi_content, indent=2), encoding="utf-8")

    # 2. TypeScript Branded Types
    ts_file = contracts_dir / "types.ts"
    if not ts_file.exists():
        ts_content = """/**
 * Frozen Domain Interface Contracts (DREE v8.1 / TypeScript Strict)
 * Zero Float Monetarny Invariant: MinorUnits = number & { readonly __brand: unique symbol }
 */
export type MinorUnits = number & { readonly __brand: unique symbol };
export type UUIDv7 = string & { readonly __brand: unique symbol };

export interface BaseDomainEntity {
  readonly id: UUIDv7;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export type Result<T, E = Error> =
  | { readonly success: true; readonly data: T }
  | { readonly success: false; readonly error: E };
"""
        ts_file.write_text(ts_content, encoding="utf-8")

    # 3. Python Immutable Dataclasses
    py_file = contracts_dir / "models.py"
    if not py_file.exists():
        py_content = """# Frozen Domain Interface Contracts (DREE v8.1 / Python Strict)
from dataclasses import dataclass
from typing import Final, Optional

@dataclass(frozen=True, slots=True)
class BaseDomainEntity:
    id: str
    created_at: str
    updated_at: str

    def __post_init__(self):
        if not self.id:
            raise ValueError("Entity ID cannot be empty")

class DomainError(Exception):
    \"\"\"Base domain exception conforming to DREE v8.1.\"\"\"
    pass
"""
        py_file.write_text(py_content, encoding="utf-8")

def compile_blueprint(blueprint_path: Path, workspace_root: Path = None) -> Dict[str, Any]:
    ws = workspace_root or find_workspace_root()
    if not blueprint_path.is_file():
        raise FileNotFoundError(f"Master Blueprint file not found: {blueprint_path}")
        
    content = blueprint_path.read_text(encoding='utf-8')
    
    # 1. Verify Phase Structure
    missing_phases = []
    for p_id, p_name in REQUIRED_PHASES:
        if p_id not in content and p_name not in content:
            missing_phases.append(f"{p_id}: {p_name}")
            
    if missing_phases:
        raise ValueError(f"BLUEPRINT_INCOMPLETE: Missing required phases:\n" + "\n".join(f"- {p}" for p in missing_phases))
        
    # 2. Zero-Placeholder & Ambiguity Lint
    violations = lint_zero_placeholders(content)
    if violations:
        msg = f"ZERO_PLACEHOLDER_VIOLATION: Found {len(violations)} forbidden ambiguous tokens:\n"
        for v in violations[:10]:
            msg += f"  Line {v['line']}: '{v['matchedToken']}' in \"{v['text']}\"\n"
        if len(violations) > 10:
            msg += f"  ... and {len(violations)-10} more violations."
        raise ValueError(msg)

    # 3. Parse Hierarchical Phase 6 DAG (L1 Epics, L2 Milestones, L3 Tasks)
    epics, milestones, tasks = parse_hierarchical_phase_6(content)
    if not tasks:
        raise ValueError("PHASE_6_PARSING_FAILED: No structured tasks could be extracted from Phase 6.")
        
    # 4. Rigorous DAG Validation
    validate_dag_acyclic(tasks)
    validate_disjoint_parallel_paths(tasks)
    validate_task_complexity_limits(tasks)
    
    # 5. Write decomposed specs/ files
    specs_dir = ws / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    
    (specs_dir / "00_MASTER_BLUEPRINT.md").write_text(content, encoding='utf-8')
    
    phase_split = re.split(r'(?=###\s+FAZA\s+\d+:)', content)
    phase_map = {
        1: "01_PRD_AND_ADR.md",
        2: "02_DATA_AND_STATE.md",
        3: "03_API_CONTRACTS.md",
        4: "04_SECURITY_AND_SRE.md",
        5: "05_TOPOLOGY_AND_ENV.md",
        6: "06_EXECUTION_DAG.md",
        7: "07_QA_VERIFICATION_MATRIX.md"
    }
    
    for section in phase_split:
        m = re.match(r'###\s+FAZA\s+(\d+):', section.strip())
        if m:
            num = int(m.group(1))
            if num in phase_map:
                (specs_dir / phase_map[num]).write_text(section.strip() + "\n", encoding='utf-8')

    # Maintain compatibility with standard Living Charter filenames
    if (specs_dir / "01_PRD_AND_ADR.md").is_file():
        (specs_dir / "01_PRODUCT_REQUIREMENTS.md").write_text((specs_dir / "01_PRD_AND_ADR.md").read_text(encoding='utf-8'), encoding='utf-8')
    if (specs_dir / "05_TOPOLOGY_AND_ENV.md").is_file():
        (specs_dir / "02_SYSTEM_ARCHITECTURE.md").write_text((specs_dir / "05_TOPOLOGY_AND_ENV.md").read_text(encoding='utf-8'), encoding='utf-8')
    if (specs_dir / "02_DATA_AND_STATE.md").is_file() and not (specs_dir / "03_DATA_DICTIONARY.md").is_file():
        (specs_dir / "03_DATA_DICTIONARY.md").write_text((specs_dir / "02_DATA_AND_STATE.md").read_text(encoding='utf-8'), encoding='utf-8')

    # Automatically synthesize Living SSoT Traceability Matrix
    tm_rows = [
        "# Living SSoT Traceability Matrix (DREE v8.1)\n",
        "| Task ID | Epik | Kamień Milowy | Tytuł | Zależności | Dozwolone Ścieżki | Weryfikacja DoD |",
        "|:---|:---|:---|:---|:---|:---|:---|"
    ]
    for t in tasks:
        deps_str = ", ".join(t.get("depends_on", [])) or "brak"
        paths_str = ", ".join(f"`{p}`" for p in t.get("allowed_paths", []))
        dod_str = f"`{t.get('dod_command') or t.get('acceptance', ['exit 0'])[0]}`"
        tm_rows.append(f"| **{t['id']}** | {t.get('epic_id', '-')} | {t.get('milestone_id', '-')} | {t['title']} | {deps_str} | {paths_str} | {dod_str} |")
    (specs_dir / "05_TRACEABILITY_MATRIX.md").write_text("\n".join(tm_rows) + "\n", encoding='utf-8')

    # 6. Scaffold baseline contracts in contracts/
    contracts_dir = ws / "contracts"
    scaffold_baseline_contracts(contracts_dir, ws)

    # 7. Compile into .governance/tasks.json (Schema v2 with 100% backward compatibility)
    gov_dir = ws / ".governance"
    gov_dir.mkdir(parents=True, exist_ok=True)
    
    tasks_json_path = gov_dir / "tasks.json"
    tasks_payload = {
        "version": 2,
        "blueprint_source": "specs/00_MASTER_BLUEPRINT.md",
        "epics": epics,
        "milestones": milestones,
        "tasks": tasks
    }
    tasks_json_path.write_text(json.dumps(tasks_payload, indent=2, ensure_ascii=False), encoding='utf-8')
    
    # 8. Update .governance/config.json with comprehensive spec_files list
    cfg_path = gov_dir / "config.json"
    cfg = {}
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
        except Exception:
            pass
            
    canonical_specs = [
        "specs/00_MASTER_BLUEPRINT.md",
        "specs/01_PRD_AND_ADR.md",
        "specs/02_DATA_AND_STATE.md",
        "specs/03_API_CONTRACTS.md",
        "specs/04_SECURITY_AND_SRE.md",
        "specs/05_TOPOLOGY_AND_ENV.md",
        "specs/06_EXECUTION_DAG.md",
        "specs/07_QA_VERIFICATION_MATRIX.md",
        "specs/05_TRACEABILITY_MATRIX.md"
    ]
    spec_files = [s for s in canonical_specs if (ws / s).is_file()]
    if "contracts/**/*" not in spec_files:
        spec_files.append("contracts/**/*")
    if (ws / "contracts").is_dir():
        for p in sorted((ws / "contracts").rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(ws)).replace('\\', '/')
                if rel not in spec_files:
                    spec_files.append(rel)
    cfg["spec_files"] = spec_files

    stack_info = detect_tech_stack(ws)
    if "checks" not in cfg or not isinstance(cfg["checks"], dict):
        cfg["checks"] = {}
    if "unit" not in cfg["checks"]:
        cfg["checks"]["unit"] = {"argv": stack_info["runner_argv"], "timeout": 120}
    else:
        current_argv = cfg["checks"].get("unit", {}).get("argv", [])
        if stack_info["stack"] == "typescript" and any("python" in str(arg) for arg in current_argv):
            cfg["checks"]["unit"] = {"argv": stack_info["runner_argv"], "timeout": 120}

    if not cfg.get("required_release_checks"):
        cfg["required_release_checks"] = ["unit"]
    if not cfg.get("protected_paths"):
        cfg["protected_paths"] = [".governance", ".agents", "specs", "contracts", "AGENTS.md"]
        
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
    
    return {
        "status": "BLUEPRINT_COMPILED",
        "workspaceRoot": str(ws),
        "hierarchy": {
            "epicsExtracted": len(epics),
            "milestonesExtracted": len(milestones),
            "tasksExtracted": len(tasks)
        },
        "specFilesGenerated": len(cfg["spec_files"]),
        "contractsScaffolded": True,
        "nextStep": "python .governance/bin/gov.py approve-spec --actor human:owner"
    }

EARS_PATTERNS = [
    re.compile(r'^\s*THE\s+SYSTEM\s+SHALL\b', re.IGNORECASE),
    re.compile(r'^\s*WHEN\b.+\bTHE\s+SYSTEM\s+SHALL\b', re.IGNORECASE),
    re.compile(r'^\s*WHILE\b.+\bTHE\s+SYSTEM\s+SHALL\b', re.IGNORECASE),
    re.compile(r'^\s*IF\b.+\bTHEN\s+THE\s+SYSTEM\s+SHALL\b', re.IGNORECASE),
    re.compile(r'^\s*WHERE\b.+\bTHE\s+SYSTEM\s+SHALL\b', re.IGNORECASE),
]

WISHFUL_PHRASES = re.compile(
    r'\b(powinien|powinno|powinna|powinny|może|mógłby|szybko|bezawaryjnie|w\s+razie\s+potrzeby|w\s+miarę\s+możliwości|itp\.?|itd\.?|itp|itd|dowolny|jakikolwiek|ładny|czytelny|odpowiednio)\b',
    re.IGNORECASE
)

def validate_ears_syntax(content: str) -> bool:
    """Validates that functional requirements strictly adhere to EARS and RFC 2119.
    Rejects wishful thinking, vague statements, and missing EARS triggers.
    Raises ValueError('NON_EARS_REQUIREMENT_DETECTED: ...') on failure.
    """
    req_lines = []
    for line in content.splitlines():
        line_s = line.strip()
        m = re.match(r'^(?:[-*]|\d+\.)\s+(REQ-[0-9A-Za-z_-]+)\s*:\s*(.+)', line_s)
        if m:
            req_lines.append((m.group(1), m.group(2).strip()))
        elif "REQ-" in line_s and ":" in line_s:
            parts = line_s.split(":", 1)
            req_id = parts[0].strip().lstrip("-* ").strip()
            req_lines.append((req_id, parts[1].strip()))

    if not req_lines:
        return True

    for req_id, req_text in req_lines:
        if WISHFUL_PHRASES.search(req_text):
            raise ValueError(
                f"NON_EARS_REQUIREMENT_DETECTED: Requirement '{req_id}' contains wishful or vague language: '{req_text}'. "
                "All requirements must adhere to EARS syntax (Ubiquitous, Event-driven, State-driven, Unwanted, or Optional)."
            )
        matched = any(p.search(req_text) for p in EARS_PATTERNS)
        if not matched:
            raise ValueError(
                f"NON_EARS_REQUIREMENT_DETECTED: Requirement '{req_id}' does not match any valid EARS pattern: '{req_text}'. "
                "Must be one of: 'THE SYSTEM SHALL', 'WHEN ... THE SYSTEM SHALL', 'WHILE ... THE SYSTEM SHALL', 'IF ... THEN THE SYSTEM SHALL', or 'WHERE ... THE SYSTEM SHALL'."
            )

    return True

def validate_contract_compatibility(old_contract: str, new_contract: str) -> bool:
    """AST Compatibility Checker: prevents breaking changes across contract generations.
    Ensures existing classes, fields, and field types are not removed or incompatibly altered.
    Raises ValueError('BREAKING_CONTRACT_CHANGE_DETECTED: ...') on breaking changes.
    """
    if "\\n" in old_contract:
        old_contract = old_contract.replace("\\r\\n", "\n").replace("\\n", "\n")
    if "\\n" in new_contract:
        new_contract = new_contract.replace("\\r\\n", "\n").replace("\\n", "\n")

    try:
        old_tree = ast.parse(old_contract)
    except Exception as e:
        if not old_contract.strip():
            return True
        import textwrap
        try:
            old_tree = ast.parse(textwrap.dedent(old_contract))
        except Exception:
            raise ValueError(f"BREAKING_CONTRACT_CHANGE_DETECTED: Old contract syntax error: {e}")

    try:
        new_tree = ast.parse(new_contract)
    except Exception as e:
        import textwrap
        try:
            new_tree = ast.parse(textwrap.dedent(new_contract))
        except Exception:
            raise ValueError(f"BREAKING_CONTRACT_CHANGE_DETECTED: New contract syntax error: {e}")

    def extract_classes(tree: ast.AST) -> Dict[str, Dict[str, str]]:
        classes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                fields = {}
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        field_name = item.target.id
                        type_str = ast.unparse(item.annotation).strip()
                        fields[field_name] = type_str
                classes[node.name] = fields
        return classes

    old_classes = extract_classes(old_tree)
    new_classes = extract_classes(new_tree)

    for cls_name, old_fields in old_classes.items():
        if cls_name not in new_classes:
            raise ValueError(
                f"BREAKING_CONTRACT_CHANGE_DETECTED: Class '{cls_name}' was removed from the contract."
            )
        new_fields = new_classes.get(cls_name, {})
        for f_name, old_type in old_fields.items():
            if f_name not in new_fields:
                raise ValueError(
                    f"BREAKING_CONTRACT_CHANGE_DETECTED: Field '{f_name}' in class '{cls_name}' was removed."
                )
            new_type = new_fields[f_name]
            if old_type != new_type:
                raise ValueError(
                    f"BREAKING_CONTRACT_CHANGE_DETECTED: Field '{f_name}' in class '{cls_name}' changed type "
                    f"from '{old_type}' to '{new_type}'. Incompatible type alteration is forbidden."
                )

    return True

FINANCIAL_NAME_KEYWORDS = {
    "price", "amount", "cost", "fee", "balance", "total", "subtotal", "tax",
    "salary", "wage", "cents", "grosze", "kwota", "cena", "oplata", "koszt", "saldo", "prowizja",
    "discount", "rabat", "rate"
}

def validate_dree_financial_invariants(dto_code: str) -> None:
    """Enforces DREE Rule 50: strictly prohibits float/double types in financial and monetary models.
    Raises ValueError('DREE_RULE_50_FLOAT_FORBIDDEN: ...') if floating point is detected.
    """
    try:
        tree = ast.parse(dto_code)
    except Exception:
        for line in dto_code.splitlines():
            line_l = line.lower()
            if any(kw in line_l for kw in FINANCIAL_NAME_KEYWORDS):
                if any(bad in line_l for bad in [": float", ": double", "float =", "double ="]):
                    raise ValueError(
                        "DREE_RULE_50_FLOAT_FORBIDDEN: Monetary or financial fields must not use floating-point types. "
                        "All monetary values must be integer minor units (cents/grosze) or basis points under DREE v8.2 Rule 50."
                    )
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            fname = node.target.id.lower()
            ftype = ast.unparse(node.annotation).lower()
            if any(kw in fname for kw in FINANCIAL_NAME_KEYWORDS):
                if any(bad in ftype for bad in ["float", "double", "decimal", "number"]):
                    raise ValueError(
                        f"DREE_RULE_50_FLOAT_FORBIDDEN: Field '{node.target.id}' uses forbidden floating-point type '{ftype}'. "
                        "All monetary values must be integer minor units (cents/grosze) or basis points under DREE v8.2 Rule 50."
                    )

def main():
    parser = argparse.ArgumentParser(description="Genesis Blueprint Compiler & Validator v8.1")
    parser.add_argument("blueprint", nargs="?", default="specs/00_MASTER_BLUEPRINT.md", help="Path to Master Blueprint file")
    parser.add_argument("--workspace", "-w", help="Workspace root directory")
    parser.add_argument("--validate-only", action="store_true", help="Only lint and validate without writing files")
    args = parser.parse_args()
    
    ws = Path(args.workspace).resolve() if args.workspace else find_workspace_root()
    b_path = (ws / args.blueprint).resolve() if not Path(args.blueprint).is_absolute() else Path(args.blueprint).resolve()
    
    try:
        if args.validate_only:
            content = b_path.read_text(encoding='utf-8')
            violations = lint_zero_placeholders(content)
            epics, milestones, tasks = parse_hierarchical_phase_6(content)
            validate_dag_acyclic(tasks)
            validate_disjoint_parallel_paths(tasks)
            validate_task_complexity_limits(tasks)
            print(json.dumps({
                "status": "VALID",
                "epics": len(epics),
                "milestones": len(milestones),
                "tasks": len(tasks),
                "placeholderViolations": len(violations)
            }, indent=2))
        else:
            res = compile_blueprint(b_path, ws)
            print(json.dumps(res, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "ERROR", "error": type(e).__name__, "message": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
