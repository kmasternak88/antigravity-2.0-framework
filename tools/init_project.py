#!/usr/bin/env python3



"""One-command project bootstrapper for Antigravity Evidence-Driven Closed Loop Ultra Framework v5.1 (Omni-Agentic OS & DREE Engine).







Automates framework installation, environment adaptation, and verification



for both brand-new repositories and existing projects.



"""



import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path
from typing import Optional, List, Dict, Any

_this_dir = Path(__file__).resolve().parent
_parent_dir = _this_dir.parent
for _p in [_this_dir, _parent_dir]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from tools.ingestion_parser import IngestionParser
    from tools.genesis_compiler import compile_blueprint
except ImportError:
    try:
        from ingestion_parser import IngestionParser
        from genesis_compiler import compile_blueprint
    except ImportError:
        IngestionParser = None
        compile_blueprint = None

__all__ = [
    "detect_project_type",
    "get_default_check",
    "is_ecommerce_input",
    "clean_slate_purge_sample_files",
    "generate_clean_contracts_and_specs",
    "bootstrap",
    "main",
]

SAMPLE_ECOMMERCE_PATTERNS = [
    'billing', 'payment_processor', 'checkout.blueprint.json', 'checkoutpage.tsx',
    'test_billing_service.py', 'test_payment_processor.py'
]

def is_ecommerce_input(brief_text: Optional[str] = None, prd_path: Optional[str] = None, brief: Optional[str] = None, prd: Optional[str] = None) -> bool:
    check_text = (brief_text or brief or "")
    active_prd = prd_path or prd
    if active_prd and Path(active_prd).is_file():
        try:
            check_text += " " + Path(active_prd).read_text(encoding="utf-8")
        except Exception:
            pass
    elif active_prd:
        check_text += " " + active_prd
    kw = ["płatnoś", "payment", "stripe", "billing", "checkout", "koszyk", "faktura", "zamówien", "ecommerce", "e-commerce"]
    return any(k in check_text.lower() for k in kw)

def clean_slate_purge_sample_files(target: Path) -> List[Path]:
    """Clean-Slate Scaffolding: purge sample e-commerce/billing files in new non-ecommerce projects."""
    purged: List[Path] = []
    clean_slate_targets = [
        target / "contracts/billing_payment_processor.contract.ts",
        target / "specs/blueprints/checkout.blueprint.json",
        target / "src/billing",
        target / "src/pages/CheckoutPage.tsx",
        target / "tests/test_billing_service.py",
        target / "tests/test_payment_processor.py"
    ]
    for p in clean_slate_targets:
        if p.is_file():
            try:
                p.unlink()
                purged.append(p)
            except Exception: pass
        elif p.is_dir():
            try:
                shutil.rmtree(p)
                purged.append(p)
            except Exception: pass
            
    for folder in [target / "src", target / "specs", target / "tests", target / "contracts"]:
        if folder.is_dir():
            for f in list(folder.rglob("*")):
                if f.is_file() and any(pat in f.name.lower() for pat in ['billing', 'payment_processor', 'checkout']):
                    try:
                        f.unlink()
                        purged.append(f)
                    except Exception: pass
    return purged

def generate_clean_contracts_and_specs(target: Path, entities: List[str], archetype: str, project_slug: str, ptype: str):
    """Dynamically generates files in contracts/ and specs/ strictly matching entities from PRD / Data Dictionary."""
    contracts_dir = target / "contracts"
    specs_dir = target / "specs"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    specs_dir.mkdir(parents=True, exist_ok=True)

    # 1. contracts/models.py
    py_lines = [
        "# Frozen Domain Interface Contracts (DREE v8.1 / Python Strict)",
        "from dataclasses import dataclass",
        "from typing import Optional, List, Dict, Any",
        "",
        "class DomainError(Exception):",
        '    """Base domain exception conforming to DREE v8.1."""',
        "    pass",
        ""
    ]
    for ent in entities:
        py_lines.extend([
            f"class {ent}Error(DomainError):",
            f'    """Domain exception for entity {ent}."""',
            "    pass",
            "",
            "@dataclass(frozen=True, slots=True)",
            f"class {ent}:",
            "    id: str",
            "    created_at: str",
            "    updated_at: str",
            "",
            "    def __post_init__(self):",
            "        if not self.id:",
            f'            raise {ent}Error("{ent} ID cannot be empty")',
            ""
        ])
    (contracts_dir / "models.py").write_text("\n".join(py_lines), encoding="utf-8")

    # 2. contracts/types.ts
    ts_lines = [
        "/**",
        " * Frozen Domain Interface Contracts (DREE v8.1 / TypeScript Strict)",
        " */",
        "export type UUIDv7 = string & { readonly __brand: unique symbol };",
        "",
        "export interface BaseDomainEntity {",
        "  readonly id: UUIDv7;",
        "  readonly createdAt: string;",
        "  readonly updatedAt: string;",
        "}",
        "",
        "export type Result<T, E = Error> =",
        "  | { readonly success: true; readonly data: T }",
        "  | { readonly success: false; readonly error: E };",
        ""
    ]
    for ent in entities:
        ts_lines.extend([
            f"export interface {ent} extends BaseDomainEntity {{",
            "  // Domain entity properties",
            "}",
            ""
        ])
    (contracts_dir / "types.ts").write_text("\n".join(ts_lines), encoding="utf-8")

    # 3. contracts/openapi.json
    openapi_schemas = {
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
    for ent in entities:
        openapi_schemas[ent] = {
            "type": "object",
            "required": ["id", "created_at", "updated_at"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"}
            }
        }
    openapi_doc = {
        "openapi": "3.1.0",
        "info": {
            "title": f"{project_slug} API Contracts",
            "version": "1.0.0",
            "description": f"Deterministic Interface Contracts for {project_slug} frozen under DREE v8.1 standard."
        },
        "paths": {},
        "components": {
            "schemas": openapi_schemas
        }
    }
    (contracts_dir / "openapi.json").write_text(json.dumps(openapi_doc, indent=2), encoding="utf-8")

    # 4. specs/03_DATA_DICTIONARY.md
    if IngestionParser:
        dd_content = IngestionParser.generate_data_dictionary_content(entities, archetype)
        (specs_dir / "03_DATA_DICTIONARY.md").write_text(dd_content, encoding="utf-8")


def get_template_root() -> Path:



    # 1. Framework repository root (development / repo mode)



    repo_root = Path(__file__).resolve().parents[1]



    if (repo_root / '.governance').is_dir():



        return repo_root



    # 2. Local template folder next to skill (installed mode)



    skill_tpl = Path(__file__).resolve().parents[1] / 'template'



    if (skill_tpl / '.governance').is_dir():



        return skill_tpl



    # 3. Global fallback candidates in ~/.gemini



    home = Path.home()



    candidates = [



        home / '.gemini' / 'config' / 'plugins' / 'ag-kit' / 'skills' / 'init' / 'template',



        home / '.gemini' / 'config' / 'skills' / 'init' / 'template',



        home / '.gemini' / 'antigravity' / 'skills' / 'init' / 'template',



        Path(r'd:\hermes-workspaces-. agentic-framework-antigravityv3ntigravity-v3-evidence-driven-framework')



    ]



    for c in candidates:



        if (c / '.governance').is_dir():



            return c



    return repo_root







FRAMEWORK_ROOT = get_template_root()







def slugify(text: str) -> str:



    return re.sub(r'[^a-zA-Z0-9_-]', '-', text).strip('-').lower()







def detect_project_type(target: Path):
    indicators = {
        'node': ['package.json', 'tsconfig.json'],
        'python_pytest': ['pytest.ini', 'pyproject.toml', 'requirements.txt'],
        'rust': ['Cargo.toml'],
        'go': ['go.mod'],
    }
    for ptype, files in indicators.items():
        if any((target / f).exists() for f in files):
            return ptype
    has_code = any((target / d).is_dir() for d in ['src', 'app', 'lib', 'tests', 'test'])
    return 'generic_code' if has_code else 'empty'


def get_default_check(target: Path, ptype: str):
    py_bin = 'python' if os.name == 'nt' else 'python3'
    if ptype == 'node':
        pkg_file = target / 'package.json'
        try:
            pkg = json.loads(pkg_file.read_text(encoding='utf-8'))
            dev_deps = pkg.get('devDependencies', {})
            deps = pkg.get('dependencies', {})
            scripts = pkg.get('scripts', {})
            if 'vitest' in dev_deps or 'vitest' in deps or 'vitest' in scripts.get('test', ''):
                return {'check_name': 'project-tests', 'argv': ['npx', 'vitest', 'run'], 'timeout': 180}
            if 'test' in scripts:
                return {'check_name': 'project-tests', 'argv': ['npm', 'test'], 'timeout': 180}
        except Exception:
            pass
        return {'check_name': 'project-tests', 'argv': ['npm', 'test'], 'timeout': 180}



    elif ptype == 'python_pytest':



        return {'check_name': 'project-tests', 'argv': [py_bin, '-m', 'pytest'], 'timeout': 120}



    elif ptype == 'rust':



        return {'check_name': 'project-tests', 'argv': ['cargo', 'test'], 'timeout': 300}



    elif ptype == 'go':



        return {'check_name': 'project-tests', 'argv': ['go', 'test', './...'], 'timeout': 180}



    else:



        return {'check_name': 'framework-selftests', 'argv': [py_bin, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'timeout': 120}







def bootstrap(target_dir: str, mode: str = 'auto', force_merge: bool = False, dry_run: bool = False, prd: str = None, brief: str = None, auto_genesis: bool = False):



    target = Path(target_dir).resolve()



    target.mkdir(parents=True, exist_ok=True)







    # Immunization: Ensure python3.exe exists on Windows



    if os.name == 'nt':



        py_exe = Path(sys.executable)



        py3_exe = py_exe.parent / 'python3.exe'



        if not py3_exe.is_file():



            try:



                shutil.copy2(py_exe, py3_exe)



            except Exception:



                pass



    



    ptype = detect_project_type(target)
    effective_mode = mode
    if effective_mode == 'auto':
        effective_mode = 'extend' if ptype != 'empty' else 'new'
        
    is_ecommerce = is_ecommerce_input(brief, prd)
    project_slug = slugify(target.name or 'project')
    check_info = get_default_check(target, ptype)
    
    plan = []
    actions = []
    
    # 1. Directories to copy recursively
    dirs_to_copy = [
        '.governance/bin',
        '.governance/hooks',
        '.governance/registry',
        '.agents/rules',
        '.agents/skills',
        '.agents/agents',
        '.agents/templates',
        '.specify/specs',
        'specs',
        'contracts',
        'tools'
    ]
    
    for rel in dirs_to_copy:
        src = FRAMEWORK_ROOT / rel
        dst = target / rel
        if src.is_dir():
            for item in src.rglob('*'):
                if item.is_file() and '__pycache__' not in item.parts:
                    sub = item.relative_to(src)
                    dest_file = dst / sub
                    if not is_ecommerce and any(re.search(pat, dest_file.name, re.IGNORECASE) for pat in SAMPLE_ECOMMERCE_PATTERNS):
                        continue
                    plan.append(('copy', item, dest_file))



                    



    # 2. Files with customization / templates



    plan.append(('copy', FRAMEWORK_ROOT / '.agents/hooks.json', target / '.agents/hooks.json'))



    std_src = FRAMEWORK_ROOT / '.governance/standards.json'



    if std_src.is_file():



        plan.append(('copy', std_src, target / '.governance/standards.json'))



    



    # 2a. Default .gitignore for clean repo governance



    gitignore_target = target / '.gitignore'



    if not gitignore_target.exists():



        gitignore_content = """# Antigravity Governance Runtime Artifacts



.governance/state/



.governance/handoffs/



.governance/evidence/



.governance/snapshots/



.governance/golden/



.worktrees/



.shadow_worktrees/







# Python artifacts



__pycache__/



*.py[cod]



.pytest_cache/



.mypy_cache/



"""



        plan.append(('write_text', gitignore_target, gitignore_content))



    



    # 2c. Ensure runtime governance directories exist
    for rdir in ['.governance/state', '.governance/evidence', '.governance/snapshots', '.governance/handoffs', 'tests', 'src']:
        (target / rdir).mkdir(parents=True, exist_ok=True)

    # 2d. Baseline test to ensure immediate discovery and execution under unittest
    baseline_test = target / 'tests' / 'test_baseline.py'
    if not baseline_test.exists():
        baseline_code = (
            '"""Baseline Framework Verification Test."""\n'
            'import unittest\n\n'
            'class BaselineVerificationTest(unittest.TestCase):\n'
            '    def test_environment_and_framework_selftest(self):\n'
            '        """Verify testing harness is operational."""\n'
            '        self.assertTrue(True)\n\n'
            'if __name__ == "__main__":\n'
            '    unittest.main()\n'
        )
        plan.append(('write_text', baseline_test, baseline_code))



        



    # 2b. Immunization: Mirror native_guard.py into alternative hook paths (.agents/.governance/hooks and .agents/hooks)



    guard_src = FRAMEWORK_ROOT / '.governance' / 'hooks' / 'native_guard.py'



    if guard_src.is_file():



        plan.append(('copy', guard_src, target / '.agents' / '.governance' / 'hooks' / 'native_guard.py'))



        plan.append(('copy', guard_src, target / '.agents' / 'hooks' / 'native_guard.py'))



    



    # 3. Handle AGENTS.md



    target_agents = target / 'AGENTS.md'



    src_agents = FRAMEWORK_ROOT / 'AGENTS.md'



    if not target_agents.exists():



        plan.append(('copy', src_agents, target_agents))



    else:



        if force_merge:



            plan.append(('merge_agents', src_agents, target_agents))



        else:



            plan.append(('copy', src_agents, target / 'AGENTS_FRAMEWORK_V3.md'))







    # 4. Generate project.json for Mem0



    project_json_content = {



        "id": project_slug,



        "name": target.name,



        "tenant": project_slug,



        "mode": effective_mode,



        "mem0_categories": ["architecture", "adr", "tasks", "invariants"]



    }



    plan.append(('write_json', target / '.agents/project.json', project_json_content))



    



    # 5. Generate tailored .governance/config.json



    cfg = json.loads((FRAMEWORK_ROOT / '.governance/config.json').read_text(encoding='utf-8'))



    cfg['profile'] = 'standard'



    cfg['checks'] = {



        check_info['check_name']: {



            'argv': check_info['argv'],



            'timeout': check_info['timeout']



        }



    }



    cfg['required_release_checks'] = [check_info['check_name']]



    plan.append(('write_json', target / '.governance/config.json', cfg))



    



    # 6. Generate tailored .governance/tasks.json



    if effective_mode == 'new':



        tasks_data = {



            "version": 1,



            "tasks": [



                {



                    "id": "T001",



                    "title": "Inicjalizacja architektury i bazowego pipeline projektu",



                    "depends_on": [],



                    "allowed_paths": ["src", "tests", "docs", "specs"],



                    "checks": [check_info['check_name']],



                    "acceptance": ["AC-INIT-001"],



                    "risk": "low",



                    "standards_checklist": [



                        "CONTRACT_DEFINED",



                        "DOMAIN_EXCEPTION_DEFINED",



                        "INPUT_VALIDATED",



                        "CLEAN_CODE_SRP",



                        "ZERO_CONSOLE",



                        "DUAL_TESTS_CREATED",



                        "DATA_DICTIONARY_SYNCED"



                    ]



                }



            ]



        }



    else:



        tasks_data = {



            "version": 1,



            "tasks": [



                {



                    "id": "T001",



                    "title": f"Feature Slice: Rozbudowa modułu w projekcie {target.name}",



                    "depends_on": [],



                    "allowed_paths": ["src", "tests", "specs"],



                    "checks": [check_info['check_name']],



                    "acceptance": ["AC-FEAT-001"],



                    "risk": "standard"



                }



            ]



        }



    plan.append(('write_json', target / '.governance/tasks.json', tasks_data))







    if dry_run:



        return {



            "status": "DRY_RUN",



            "target": str(target),



            "mode": effective_mode,



            "detected_stack": ptype,



            "check": check_info,



            "planned_operations": len(plan)



        }







    # Execute plan



    for op in plan:



        op_type = op[0]



        if op_type == 'copy':



            src, dst = op[1], op[2]



            dst.parent.mkdir(parents=True, exist_ok=True)



            shutil.copy2(src, dst)



        elif op_type == 'write_json':



            dst, data = op[1], op[2]



            dst.parent.mkdir(parents=True, exist_ok=True)



            dst.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')



        elif op_type == 'write_text':



            dst, txt = op[1], op[2]



            dst.parent.mkdir(parents=True, exist_ok=True)



            dst.write_text(txt, encoding='utf-8')



        elif op_type == 'merge_agents':



            src, dst = op[1], op[2]



            orig = dst.read_text(encoding='utf-8')



            backup = dst.with_suffix('.md.bak')



            backup.write_text(orig, encoding='utf-8')



            added = "\n\n# --- Antigravity Evidence-Driven Framework v3 Rules ---\n" + src.read_text(encoding='utf-8')



            dst.write_text(orig + added, encoding='utf-8')







    # Initialize Git if missing



    git_initialized = False



    if not (target / '.git').exists():



        try:



            subprocess.run(['git', 'init'], cwd=target, check=True, capture_output=True)



            git_initialized = True



        except Exception:



            pass







    # Run gov doctor check



    py_bin = 'python' if os.name == 'nt' else 'python3'



    doctor_res = {"status": "UNKNOWN"}



    try:



        doc = subprocess.run([py_bin, str(target / '.governance/bin/gov.py'), 'doctor'],



                             cwd=target, capture_output=True, text=True)



        doctor_res = json.loads(doc.stdout) if doc.returncode == 0 else {"status": "ERROR", "stderr": doc.stderr}



    except Exception as e:



            doctor_res = {"status": "ERROR", "error": str(e)}



    # Clean-slate purge of sample files if non-ecommerce
    if not is_ecommerce and not dry_run:
        clean_slate_purge_sample_files(target)

    # 7. Ingestion & Genesis Blueprint Compilation
    genesis_res = None
    ingestion_ctx = None
    target_prd = prd
    if not target_prd and not brief and not dry_run:
        try:
            discovered = IngestionParser.auto_discover_prd(target)
            if discovered:
                target_prd = str(discovered)
        except Exception:
            pass

    if (target_prd or brief or auto_genesis) and not dry_run:
        try:
            raw_input = target_prd or brief
            ingestion_ctx = IngestionParser.parse_input(raw_input, target)
            
            # Generate clean domain contracts and data dictionary
            generate_clean_contracts_and_specs(target, ingestion_ctx.entities, ingestion_ctx.archetype, project_slug, ptype)

            blueprint_file = target / "specs" / "00_MASTER_BLUEPRINT.md"
            if target_prd and Path(target_prd).is_file():
                blueprint_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_prd, blueprint_file)
            elif not blueprint_file.is_file():
                blueprint_file.parent.mkdir(parents=True, exist_ok=True)
                adr_lines = "\n".join([f"### {a['id']}: {a['title']}\n- **Decyzja**: {a['decision']}\n- **Uzasadnienie**: {a['rationale']}" for a in ingestion_ctx.autonomous_adrs])
                entities_str = ", ".join(ingestion_ctx.entities) if ingestion_ctx.entities else "BaseEntity, DomainModel"
                actors_str = ", ".join(ingestion_ctx.actors) if ingestion_ctx.actors else "Administrator, StandardUser"
                
                if ingestion_ctx.archetype in ("fintech_transaction_ledger", "multi_tenant_saas") or is_ecommerce:
                    req_003 = "- REQ-003: System MUST NOT używać liczb zmiennoprzecinkowych dla kwot pieniężnych (Zero-Float Policy)."
                elif ingestion_ctx.archetype == "cli_system_tool":
                    req_003 = "- REQ-003: System MUST stosować konwencję POSIX CLI i kod wyjścia 0 przy sukcesie, >0 przy błędzie."
                elif ingestion_ctx.archetype == "realtime_telemetry_broker":
                    req_003 = "- REQ-003: System MUST zarządzać backpressure i unikać utraty pakietów telemetrycznych."
                elif ingestion_ctx.archetype == "data_pipeline_etl":
                    req_003 = "- REQ-003: System MUST gwarantować semantykę przetwarzania at-least-once z mechanizmem checkpointingu i DLQ."
                else:
                    req_003 = "- REQ-003: System MUST hermetycznie walidować granice domenowe i formaty zapytań I/O."

                draft_bp = f"""# MASTER IMPLEMENTATION BLUEPRINT: {target.name}
Standard: RFC 2119 / DREE v8.1 / Genesis Compiler SSoT
Archetyp: {ingestion_ctx.archetype} | IMS Score: {ingestion_ctx.ims_score} ({ingestion_ctx.classification})

### FAZA 1: DEKONSTRUKCJA DOMENY, WYMAGANIA I PRZYPADKI BRZEGOWE (PRD & ADR)
1. Cel Systemu: Realizacja założeń projektowych dla archetypu {ingestion_ctx.archetype}.
2. Aktorzy i Role: {actors_str}.
3. Rejestr Decyzji Architektonicznych (ADR):
{adr_lines}
4. Wymagania Normatywne (RFC 2119):
- REQ-001: System MUST zapewniać transakcyjność operacji mutujących stan.
- REQ-002: System MUST odrzucać nieprawidłowe payloady wejściowe z kodem błędu 422/400.
{req_003}



### FAZA 2: ARCHITEKTURA DANYCH I ZARZĄDZANIE STANEM (DATA & STATE LAYER)

1. Encje Domenowe SSoT: {entities_str}.

2. Stan Trwały: Baza relacyjna z integralnością referencyjną i indeksami na kluczach wyszukiwania.

3. Stan Ulotny: Pamięć podręczna z kluczami TTL i inwalidacją opartą o zdarzenia domenowe.



### FAZA 3: KONTRAKTY KOMUNIKACYJNE I WALIDACJA I/O (API & CONTRACTS)

1. Punkty Styku: REST API / CLI Actions ze znormalizowaną kopertą odpowiedzi i błędów.

2. Zamrożone Kontrakty: Modele zdefiniowane w contracts/ (OpenAPI 3.1.0, TypeScript types, Python immutable models).

3. Idempotencja: Wymóg unikalnego klucza X-Idempotency-Key dla mutacji.



### FAZA 4: BEZPIECZEŃSTWO, ODPORNOŚĆ I OBSERWOWALNOŚĆ (SECURITY & SRE)

1. Uwierzytelnianie: Asymetryczne tokeny z rotacją i kontrolą uprawnień RBAC.

2. Odporność: Jawne timeouty połączeń I/O, Circuit Breaker i Exponential Backoff.

3. Telemetria: Logowanie strukturalne JSON z unikalnym correlation_id.



### FAZA 5: STOS TECHNOLOGICZNY, KONFIGURACJA I DRZEWO PLIKÓW (TOPOLOGY)

1. Zamrożony Stos: Wykryty profil bazowy {ptype}.

2. Zmienne Środowiskowe: Fail-fast walidacja pliku .env przy starcie procesu.

3. Struktura Katalogów: Podział na warstwy (src, tests, specs, contracts, tools).



### FAZA 6: ATOMOWY PLAN IMPLEMENTACJI (TOPOLOGICAL EXECUTION DAG)

### Epic EPIC-01: Fundament Danych i Konfiguracja

#### Milestone M1: Schemat Bazodanowy i Kontrakty

##### Task T001: Inicjalizacja schematu bazy danych i konfiguracji środowiska

- **Zależności**: []

- **Pliki docelowe**: `src/config.py`, `src/db.py`, `tests/test_config.py`

- **Kontekst wejściowy**: `specs/02_DATA_AND_STATE.md`, `contracts/models.py`

- **Kryterium Odbioru (DoD)**: `{check_info['argv'][0]} tests/test_config.py`



##### Task T002: Implementacja bazowych encji domenowych i walidacji

- **Zależności**: [T001]

- **Pliki docelowe**: `src/models.py`, `tests/test_models.py`

- **Kontekst wejściowy**: `src/config.py`, `contracts/models.py`

- **Kryterium Odbioru (DoD)**: `{check_info['argv'][0]} tests/test_models.py`



### Epic EPIC-02: Usługi Domenowe i Integracja

#### Milestone M2: Serwisy Biznesowe

##### Task T003: Główny serwis domenowy i obsługa operacji

- **Zależności**: [T002]

- **Pliki docelowe**: `src/service.py`, `tests/test_service.py`

- **Kontekst wejściowy**: `src/models.py`, `src/db.py`

- **Kryterium Odbioru (DoD)**: `{check_info['argv'][0]} tests/test_service.py`



### FAZA 7: STRATEGIA TESTOWANIA I KONTROLI JAKOŚCI (QA & VERIFICATION MATRIX)

1. Piramida Testów: Pokrycie testami jednostkowymi i integracyjnymi.

2. Mock-Breaker: Testy mutacyjne weryfikujące odporność na awarie sieci i bazy.

"""

                blueprint_file.write_text(draft_bp, encoding="utf-8")

            

            genesis_res = compile_blueprint(blueprint_file, target)

        except Exception as e:

            genesis_res = {"status": "GENESIS_COMPILATION_ERROR", "error": str(e)}



    return {

        "status": "INITIALIZED",

        "target": str(target),

        "mode": effective_mode,

        "detected_stack": ptype,

        "default_check": check_info,

        "git_initialized": git_initialized,

        "doctor": doctor_res,

        "ingestion": {

            "source": ingestion_ctx.source_type if ingestion_ctx else "default",

            "ims_score": ingestion_ctx.ims_score if ingestion_ctx else 0.0,

            "classification": ingestion_ctx.classification if ingestion_ctx else "RAW_SEED"

        } if ingestion_ctx else None,

        "genesis": genesis_res,

        "quickstart_prompt": (

            f"Zainicjalizowano projekt w trybie {effective_mode.upper()} ({ptype}) ze wsparciem Genesis DREE v8.1.\n"

            f"1. Sprawdź Living Charter w specs/ oraz kontrakty w contracts/\n"

            f"2. Zablokuj specyfikację: python .governance/bin/gov.py approve-spec --actor human:owner --reference init-{project_slug}\n"

            f"3. Rozpocznij pierwsze zadanie DAG: python .governance/bin/gov.py claim --task T001 --actor agent:builder-1 --session <twoja_sesja>\n"

            f"4. W czacie agenta wywołaj: /cl-build lub /cl-standards"

        )

    }



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, help='Sciezka do docelowego projektu')
    parser.add_argument('--mode', choices=['auto', 'new', 'extend'], default='auto', help='Tryb: new, extend, auto')
    parser.add_argument('--force-merge', action='store_true', help='Dolacz reguly v3 do istniejacego AGENTS.md')
    parser.add_argument('--dry-run', action='store_true', help='Podglad planowanych operacji bez zapisu')
    parser.add_argument('--prd', help='Sciezka do pliku PRD / specyfikacji markdown')
    parser.add_argument('--brief', help='Krotki opis lub brief pomyslu w linii komend')
    parser.add_argument('--auto-genesis', action='store_true', help='Automatyczna dekompozycja Genesis Compiler i generowanie specs/')
    args = parser.parse_args()

    result = bootstrap(args.target, mode=args.mode, force_merge=args.force_merge, dry_run=args.dry_run, prd=args.prd, brief=args.brief, auto_genesis=args.auto_genesis)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':



    main()



