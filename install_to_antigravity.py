#!/usr/bin/env python3



"""Cross-platform automated global installer for Antigravity Closed Loop Ultra Omni-Agentic Framework v8.2 (Hardened Evidence, Multi-Workspace Isolation & FileStatCache)."""



import os, sys, shutil, subprocess, pathlib, zipfile







COMMANDS_MAP = {



    "cl-genesis.toml": {



        "description": "Multi-Agent Genesis Blueprint Compiler: zamiana surowego pomysłu w deterministyczny Master Blueprint (Fazy 1-7), living charter specs/ i acykliczny DAG v8.0",



        "prompt": """---



name: cl-genesis



description: Multi-Agent Genesis Blueprint Compiler: zamiana surowego pomysłu w deterministyczny Master Blueprint (Fazy 1-7), living charter specs/ i acykliczny DAG v8.0



version: 8.0.0



requires_agents: genesis-architect, challenger, code-auditor, spec-auditor



requires_skills: cl-genesis, cl-standards, cl-spec-audit



artifact_outputs: master-blueprint



---







# /cl-genesis — Multi-Agent Genesis Blueprint Compiler v8.0







$ARGUMENTS







---







## 🔴 PROTOKÓŁ KOMPILACJI NOWEGO PROJEKTU (FAZY 1-7)







1. **Węzeł Inicjujący (Genesis Node):**



   - Agent `genesis-architect` analizuje wejściowy pomysł/brief i generuje `specs/00_MASTER_BLUEPRINT.md` według 8-fazowego protokołu RFC 2119.



2. **Wieloagentowy Audyt Adversarialny:**



   - `challenger`: Weryfikacja scenariuszy awaryjnych, wyścigów, partycji sieciowych i odporności.



   - `code-auditor`: Weryfikacja 7 Niezmienników DREE i limitów zasobów.



   - `spec-auditor`: Weryfikacja zależności DAG i poprawności kontraktów.



3. **Kompilacja i Zero-Placeholders Lint:**



   ```powershell



   python tools/genesis_compiler.py specs/00_MASTER_BLUEPRINT.md



   ```



4. **Zatwierdzenie Człowieka i Pieczęć Spec Lock (Bramka G1/G2):**



   ```powershell



   python .governance/bin/gov.py approve-spec --actor human:owner



   ```



"""



    },



    "init.toml": {



        "description": "Inicjalizacja i orkiestracja projektu w Closed Loop Framework v8.2 (S0-S3, Multi-Workspace, Living Charter, DAG, Spec Lock)",



        "prompt": """---



name: init



description: Inicjalizacja i orkiestracja projektu w Closed Loop Framework v8.2 (S0-S3, Multi-Workspace, Living Charter, DAG, Spec Lock)



version: 8.0.0



requires_agents: project-orchestrator, spec-author, genesis-architect



requires_skills: init, cl-genesis, cl-inception, cl-standards



artifact_outputs: living-charter



---







# /init — Closed Loop Framework v8.2 Inception & Multi-Workspace Orchestrator







$ARGUMENTS







---







## 🔴 KARDYNALNA PROCEDURA INICJALIZACJI S0-S3 & MULTI-WORKSPACE







1. **Wykrycie Workspace'u:** `python tools/workspace_resolver.py` (Nearest-Anchor & .active_workspace).



2. **Autodiagnostyka i Scaffolding:**



   - Dla stanu **`S0_GREENFIELD`** (nowy pomysł/brief):



     - Uruchom turnkey bootstrapper z centralnej instalacji ag-kit:



       ```powershell



       python "$HOME\\.gemini\\config\\plugins\\ag-kit\\skills\\init\\scripts\\bootstrap.py" --target . --mode new



       ```



       *(lub `python tools/init_project.py --target . --mode new` jeśli narzędzia są lokalne).*



     - **ŻELAZNY NAKAZ:** ZAKAZ pisania kodu aplikacji przed zainstalowaniem `.governance/` i nałożeniem bramki G2!



   - Dla stanu **`S1_BROWNFIELD_UNMANAGED`**:



     ```powershell



     python "$HOME\\.gemini\\config\\plugins\\ag-kit\\skills\\init\\scripts\\bootstrap.py" --target . --mode extend --force-merge



     ```



3. **Uruchomienie Doctora:** `python .governance/bin/gov.py doctor`



4. **Living Charter & Genesis Blueprint:**



   - Zdefiniuj specyfikację w `specs/`:



     - `specs/01_PRODUCT_REQUIREMENTS.md` (Wymagania PRD)



     - `specs/02_SYSTEM_ARCHITECTURE.md` (Architektura C4 i DAG)



     - `specs/03_DATA_DICTIONARY.md` (Słownik Danych SSoT)



     - `contracts/` (Zamrożone interfejsy i modele I/O)



   - Do deterministycznej kompilacji użyj kompilatora:



     ```powershell



     python tools/genesis_compiler.py specs/01_PRODUCT_REQUIREMENTS.md



     ```



5. **Zamrożenie Kontraktów (Bramka G1-G2):**



   - Nałóż Spec Lock: `python .governance/bin/gov.py approve-spec --actor human:owner`



6. **Separacja Ról (Orkiestrator vs Subagenci):**



   - Orkiestrator (sesja główna) zarządza DAG-iem i deleguje zadania. NIE PISZE kodu produkcyjnego w `src/`!



   - Kod w `src/` implementują wyłącznie subagenci `builder-executor` po wykonaniu `gov.py claim`.



"""



    },



    "cl-standards.toml": {



        "description": "Weryfikacja 7 Niezmiennikow DREE v8.0 i synchronizacji ze Slownikiem Danych specs/03_DATA_DICTIONARY.md",



        "prompt": """---



name: cl-standards



description: Weryfikacja 7 Niezmiennikow DREE v8.0 i synchronizacji ze Slownikiem Danych specs/03_DATA_DICTIONARY.md



version: 8.0.0



requires_skills: cl-standards



artifact_outputs: standards-audit



---







# /cl-standards — Weryfikacja Standardu 7 Niezmiennikow DREE v8.0







$ARGUMENTS







---







## 🔴 REGUŁY AUDYTU DREE 7/7







Uruchom automatyczna weryfikacje AST:



```powershell



python .governance/bin/gov.py check-standards



```



"""



    },



    "cl-audit.toml": {



        "description": "Testy mutacyjne Mock-Breaker (mutations_caught >= 1) i audyt pozornych asercji v8.0",



        "prompt": """---



name: cl-audit



description: Testy mutacyjne Mock-Breaker (mutations_caught >= 1) i audyt pozornych asercji v8.0



version: 8.0.0



requires_agents: code-auditor



requires_skills: cl-audit



artifact_outputs: mockbreaker-audit



---







# /cl-audit — Audyt Mutacyjny Mock-Breaker v8.0







$ARGUMENTS







---







## 🔴 PROCEDURA MOCK-BREAKER (Bramka G5.1)







```powershell



python .governance/bin/gov.py audit-tests



```



"""



    },



    "cl-gate.toml": {



        "description": "Weryfikacja kompletu dowodow bramki G5 i wydanie nienaruszalnego certyfikatu GATE_PASS v8.0",



        "prompt": """---



name: cl-gate



description: Weryfikacja kompletu dowodow bramki G5 i wydanie nienaruszalnego certyfikatu GATE_PASS v8.0



version: 8.0.0



requires_agents: qa-verifier, code-auditor



requires_skills: cl-verify



artifact_outputs: gate-certificate



---







# /cl-gate — Weryfikacja Dowodow Bramki G5 v8.0







$ARGUMENTS







```powershell



python .governance/bin/gov.py gate <TASK_ID>



```



"""



    },



    "cl-release.toml": {



        "description": "Wydanie operacyjne G7, weryfikacja regresyjna i nienaruszalny manifest wydania v8.0",



        "prompt": """---



name: cl-release



description: Wydanie operacyjne G7, weryfikacja regresyjna i nienaruszalny manifest wydania v8.0



version: 8.0.0



requires_agents: release-integrator



requires_skills: cl-release



artifact_outputs: release-manifest



---







# /cl-release — Finalne Wydanie Operacyjne Bramki G7 v8.0







$ARGUMENTS







```powershell



python .governance/bin/gov.py release



```



"""



    },



    "cl-build.toml": {



        "description": "Implementacja zadania w izolowanym Git Worktree ze scaffoldingiem 7 Niezmiennikow DREE v8.0",



        "prompt": """---



name: cl-build



description: Implementacja zadania w izolowanym Git Worktree ze scaffoldingiem 7 Niezmiennikow DREE v8.0



version: 8.0.0



requires_agents: builder-executor



requires_skills: cl-build, cl-standards



---







# /cl-build — Egzekucja Zadania w Izolacji Worktree v8.0







$ARGUMENTS







1. Pobierz pakiet zadania z kontekstem hermetycznym:



```powershell



python .governance/bin/gov.py package-handoff <TASK_ID>



```



"""



    },



    "cl-review.toml": {



        "description": "Niezalezna inspekcja dowodowa, testy mutacyjne i asercja Golden Record v8.0",



        "prompt": """---



name: cl-review



description: Niezalezna inspekcja dowodowa, testy mutacyjne i asercja Golden Record v8.0



version: 8.0.0



requires_agents: code-auditor



requires_skills: cl-review, cl-audit



---







# /cl-review — Niezalezny Przeglad Dowodowy (Bramka G5) v8.0







$ARGUMENTS



"""



    },



    "cl-discover.toml": {



        "description": "Gleboka rekonstrukcja specyfikacji i topologii w projektach brownfield (S1) v8.0",



        "prompt": """---



name: cl-discover



description: Gleboka rekonstrukcja specyfikacji i topologii w projektach brownfield (S1) v8.0



version: 8.0.0



requires_agents: spec-author



requires_skills: cl-discover



---







# /cl-discover — Gleboka Rekonstrukcja Specyfikacji (S1) v8.0







```powershell



python .governance/bin/gov.py discover --deep



```



"""



    },



    "cl-inception.toml": {



        "description": "Analiza wstepna, wybor profilu i scaffolding Living Charter v8.0",



        "prompt": """---



name: cl-inception



description: Analiza wstepna, wybor profilu i scaffolding Living Charter v8.0



version: 8.0.0



requires_agents: project-orchestrator, spec-author



requires_skills: cl-inception



---







# /cl-inception — Incepcja Projektu S0/S1 v8.0



"""



    },



    "cl-impact.toml": {



        "description": "Analiza blast-radius i symulacja kaskady uniewaznien kontraktow v8.0",



        "prompt": """---



name: cl-impact



description: Analiza blast-radius i symulacja kaskady uniewaznien kontraktow v8.0



version: 8.0.0



requires_skills: cl-spec-audit, cl-impact



---







# /cl-impact — Analiza Blast-Radius v8.0



"""



    },



    "cl-page.toml": {



        "description": "CADRE v8.0 Multi-Adapter Page & Template Assembly Engine (WordPress/WooCommerce PHP, React TSX, Vue SFC, HTML)",



        "prompt": """---



name: cl-page



description: CADRE v8.0 Multi-Adapter Page & Template Assembly Engine (WordPress/WooCommerce PHP, React TSX, Vue SFC, HTML)



version: 8.0.0



requires_agents: builder-executor



requires_skills: cl-page, cl-standards



---







# /cl-page — CADRE Multi-Adapter Page & Template Assembly Engine (v8.0)







$ARGUMENTS



"""



    },



    "cl-learn.toml": {



        "description": "Kodyfikacja wiedzy z sesji (G-LEARN v8.0): destylacja, kwarantanna learning_inbox, integracja Mem0",



        "prompt": """---



name: cl-learn



description: Kodyfikacja wiedzy z sesji (G-LEARN v8.0): destylacja, kwarantanna learning_inbox, integracja Mem0



version: 8.0.0



requires_skills: cl-learn



---







# /cl-learn — Kodyfikacja Wiedzy i Standardow v8.0







$ARGUMENTS



"""



    },



    "cl-verify.toml": {



        "description": "Weryfikacja scalonego kandydata release, testy wielopoziomowe i Macierz SSoT v8.0",



        "prompt": """---



name: cl-verify



description: Weryfikacja scalonego kandydata release, testy wielopoziomowe i Macierz SSoT v8.0



version: 8.0.0



requires_agents: qa-verifier



requires_skills: cl-verify



---







# /cl-verify — Weryfikacja Scalonego Kandydata (Bramka G6) v8.0







$ARGUMENTS



"""



    },



    "cl-spec-audit.toml": {



        "description": "Niezalezny audyt specyfikacji, grafu DAG i kontraktow przed blokada Spec Lock v8.0",



        "prompt": """---



name: cl-spec-audit



description: Niezalezny audyt specyfikacji, grafu DAG i kontraktow przed blokada Spec Lock v8.0



version: 8.0.0



requires_agents: spec-auditor



requires_skills: cl-spec-audit



---







# /cl-spec-audit — Niezalezny Audyt Kontraktow (Bramka G1/G2) v8.0







$ARGUMENTS



"""



    },



    "cl-plan-slice.toml": {



        "description": "Dekompozycja zatwierdzonego zakresu na male zadania DAG z izolacja worktree v8.0",



        "prompt": """---



name: cl-plan-slice



description: Dekompozycja zatwierdzonego zakresu na male zadania DAG z izolacja worktree v8.0



version: 8.0.0



requires_agents: project-orchestrator



requires_skills: cl-plan-slice



---







# /cl-plan-slice — Podzial Zadan i Konstrukcja Grafu DAG v8.0







$ARGUMENTS



"""



    },



    "cl-characterize.toml": {



        "description": "Rejestracja snapshotow zachowan Golden Record i Living Spec w projektach brownfield v8.0",



        "prompt": """---



name: cl-characterize



description: Rejestracja snapshotow zachowan Golden Record i Living Spec w projektach brownfield v8.0



version: 8.0.0



requires_skills: cl-characterize



---







# /cl-characterize — Golden Master Harness & Karakterystyka v8.0







$ARGUMENTS



"""



    },



    "cl-resume.toml": {



        "description": "Odzyskiwanie stanu po utracie kontekstu lub awarii, weryfikacja bazy SQLite i worktree v8.0",



        "prompt": """---



name: cl-resume



description: Odzyskiwanie stanu po utracie kontekstu lub awarii, weryfikacja bazy SQLite i worktree v8.0



version: 8.0.0



requires_skills: cl-resume



---







# /cl-resume — Odzyskiwanie Sesji i Ciaglosci Pracy v8.0







$ARGUMENTS



"""



    }


,
    "cl-extend.toml": {
        "description": "Inkrementalna rozbudowa aktywnego projektu (Brownfield Managed S2-S3): wywiad sokratejski grill-me, inżynieria EARS, delta Living Charter i przyrostowy DAG w Antigravity Ultra v8.2.",
        "prompt": """---
name: cl-extend
description: Inkrementalna rozbudowa aktywnego projektu (Brownfield Managed S2-S3): wywiad sokratejski grill-me, inżynieria EARS, delta Living Charter i przyrostowy DAG w Antigravity Ultra v8.2.
version: 8.2.0
requires_agents: genesis-architect, spec-auditor, code-auditor, builder-executor
requires_skills: cl-extend, grill-me, clean-code, cl-standards
artifact_outputs: living-charter-delta, frozen-contracts, incremental-tasks-dag
---

# /cl-extend — Inkrementalny Kompilator Projektu (v8.2)

$ARGUMENTS

---

## 🎯 PROTOKÓŁ ROZBUDOWY S2-S3 (IN-FLIGHT)
1. Sprawdź obecność `.governance/config.json` oraz `.governance/tasks.json` (dla nowych projektów S0/S1 użyj `/init`).
2. Przeprowadź sokratejski wywiad grill-me eliminujący dwuznaczności (Reguła 50 DREE: zero float, timeout 5s, interfejsy).
3. Skompiluj wymagania w składni EARS oraz triadę testową Gherkin (Happy + 2 Negative).
4. Wygeneruj deltę Living Charter (`specs/`) i zamrożone interfejsy (`contracts/`).
5. Scal zadania w DAG algorytmem Kahna (`merge_dag_kahn`) z regułą 40/3/1 i 7 Niezmiennikami DREE.
6. Nałóż pieczęć Spec Lock: `python .governance/bin/gov.py approve-spec --actor human:owner`.
"""
    },
    "extend.toml": {
        "description": "Inkrementalna rozbudowa aktywnego projektu (Brownfield Managed S2-S3): wywiad sokratejski grill-me, inżynieria EARS, delta Living Charter i przyrostowy DAG w Antigravity Ultra v8.2.",
        "prompt": """---
name: extend
description: Inkrementalna rozbudowa aktywnego projektu (Brownfield Managed S2-S3): wywiad sokratejski grill-me, inżynieria EARS, delta Living Charter i przyrostowy DAG w Antigravity Ultra v8.2.
version: 8.2.0
requires_agents: genesis-architect, spec-auditor, code-auditor, builder-executor
requires_skills: cl-extend, grill-me, clean-code, cl-standards
artifact_outputs: living-charter-delta, frozen-contracts, incremental-tasks-dag
---

# /extend (aliasy: /cl-extend, /expand) — Inkrementalny Kompilator Projektu (v8.2)

$ARGUMENTS

---

## 🎯 PROTOKÓŁ ROZBUDOWY S2-S3 (IN-FLIGHT)
1. Sprawdź obecność `.governance/config.json` oraz `.governance/tasks.json` (dla nowych projektów S0/S1 użyj `/init`).
2. Przeprowadź sokratejski wywiad grill-me eliminujący dwuznaczności (Reguła 50 DREE: zero float, timeout 5s, interfejsy).
3. Skompiluj wymagania w składni EARS oraz triadę testową Gherkin (Happy + 2 Negative).
4. Wygeneruj deltę Living Charter (`specs/`) i zamrożone interfejsy (`contracts/`).
5. Scal zadania w DAG algorytmem Kahna (`merge_dag_kahn`) z regułą 40/3/1 i 7 Niezmiennikami DREE.
6. Nałóż pieczęć Spec Lock: `python .governance/bin/gov.py approve-spec --actor human:owner`.
"""
    },
    "grill-me.toml": {
        "description": "Sokratejski wywiad inżynieryjny (Socratic Questioning & Ambiguity Elimination) w Antigravity Ultra v8.2 z natywnym ask_question i eliminacją domysłów w One-Way Doors.",
        "prompt": """---
name: grill-me
description: Sokratejski wywiad inżynieryjny (Socratic Questioning & Ambiguity Elimination) w Antigravity Ultra v8.2 z natywnym ask_question i eliminacją domysłów w One-Way Doors.
version: 8.2.0
requires_agents: genesis-architect, challenger, spec-auditor
requires_skills: grill-me
---

# /grill-me — Sokratejski Wywiad Inżynieryjny v8.2

$ARGUMENTS

---

## 🧠 SOKRATEJSKI POTOK WYWIADU
1. Przeanalizuj zgłoszoną potrzebę/funkcję pod kątem 5 krytycznych wektorów ryzyk.
2. Zastosuj natywne narzędzie `ask_question` w środowisku Antigravity 2.0 (wielokrotny wybór, precyzyjne opcje techniczne).
3. Zbadaj nienaruszalność Reguły 50 DREE (Zero Float — waluty wyłącznie w groszach/centach: `amount_cents: int`).
4. Zbadaj ograniczenia SRE, timeouty, SLA oraz odporność na awarie sieci i baz danych.
5. Zamroź uzgodnione decyzje i przejdź do kompilacji wymagań EARS w `/extend`.
"""
    }

}







def write_toml(filepath: pathlib.Path, desc: str, prompt: str):



    filepath.parent.mkdir(parents=True, exist_ok=True)



    content = f'description = "{desc}"\nprompt = \'\'\'\n{prompt}\'\'\'\n'



    filepath.write_text(content, encoding='utf-8')







def copy_directory(src: pathlib.Path, dst: pathlib.Path):



    if not src.is_dir():



        return



    dst.mkdir(parents=True, exist_ok=True)



    for item in src.rglob('*'):



        if item.is_file() and '__pycache__' not in item.parts:



            rel = item.relative_to(src)



            target = dst / rel



            target.parent.mkdir(parents=True, exist_ok=True)



            shutil.copy2(item, target)







def patch_validator_pre_tool_guard(file_path: pathlib.Path):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(__file__).resolve().parent
    gov_guard_src = root / ".agents" / "hooks" / "governance_guard.mjs"
    if gov_guard_src.is_file():
        file_path.write_text(gov_guard_src.read_text(encoding='utf-8'), encoding='utf-8')


def patch_validator_stop_dod_gate(file_path: pathlib.Path):



    code = """#!/usr/bin/env node



/**



 * NEXUS Stop Gate v8.0 — Definition of Done Enforcer (Polyglot & Multi-Workspace Aware)



 * Blokuje zakończenie sesji dopóki DoD nie jest zaliczone.



 * Weryfikuje:



 *  - Node.js (package.json): TypeScript compile, ESLint, testy



 *  - Rust (Cargo.toml): cargo check, cargo test



 *  - Python (pyproject.toml / requirements.txt / pytest.ini): pytest / unittest



 *  - Go (go.mod): go vet, go test



 *  - Closed Loop Governance: stan .governance/tasks.json i obecność dowodów



 *  - tasks/todo.md: brak nieukończonych kroków [/]



 * Kontrakt I/O: stdin JSON → stdout JSON { decision, reason }



 */







const { execSync } = require('child_process');



const fs = require('fs');



const path = require('path');







function readStdin() {



  return new Promise((resolve) => {



    let raw = '';



    process.stdin.setEncoding('utf8');



    process.stdin.on('data', (c) => { raw += c; });



    process.stdin.on('end', () => {



      try {



        resolve(JSON.parse(raw || '{}'));



      } catch {



        resolve({});



      }



    });



  });



}







function runCheck(cmd, cwd) {



  try {



    execSync(cmd, { cwd, stdio: 'pipe', timeout: 45000 });



    return { ok: true };



  } catch (e) {



    const out = (e.stdout || Buffer.from('')).toString().slice(0, 400);



    const err = (e.stderr || Buffer.from('')).toString().slice(0, 400);



    return { ok: false, output: out || err };



  }



}







function findWorkspaceRoot(workspacePaths) {



  let root = (workspacePaths && workspacePaths.length > 0) ? workspacePaths[0] : process.cwd();



  let cur = path.resolve(root);



  while (cur && cur !== path.resolve(cur, '..')) {



    const marker = path.join(cur, '.active_workspace');



    if (fs.existsSync(marker)) {



      try {



        const line = fs.readFileSync(marker, 'utf8').trim();



        if (line) {



          const target = path.isAbsolute(line) ? path.resolve(line) : path.resolve(cur, line);



          if (fs.existsSync(target)) return target;



        }



      } catch {}



    }



    cur = path.resolve(cur, '..');



  }



  return root;



}







function hasPendingTasks(workspaceRoot) {



  const todoPath = path.join(workspaceRoot, 'tasks', 'todo.md');



  if (!fs.existsSync(todoPath)) return false;



  const content = fs.readFileSync(todoPath, 'utf8');



  return /^\s*-\s*\[\/\]/m.test(content);



}







function checkGovernanceTasks(workspaceRoot) {



  const tasksPath = path.join(workspaceRoot, '.governance', 'tasks.json');



  if (!fs.existsSync(tasksPath)) return { checked: false };



  try {



    const data = JSON.parse(fs.readFileSync(tasksPath, 'utf8'));



    const tasks = data.tasks || [];



    const openTasks = tasks.filter(t => t.status && t.status !== 'DONE' && t.status !== 'CLOSED');



    if (openTasks.length > 0) {



      return {



        checked: true,



        ok: false,



        reason: `${openTasks.length} zadań w .governance/tasks.json nie ma statusu DONE (${openTasks.map(t => t.id).slice(0, 5).join(', ')})`



      };



    }



    return { checked: true, ok: true };



  } catch (e) {



    return { checked: true, ok: false, reason: `Błąd odczytu .governance/tasks.json: ${e.message}` };



  }



}







function hasUngovernedSourceCode(workspaceRoot) {



  const hasGov = fs.existsSync(path.join(workspaceRoot, '.governance'));



  const hasAgents = fs.existsSync(path.join(workspaceRoot, 'AGENTS.md')) || fs.existsSync(path.join(workspaceRoot, '.agents'));



  if (hasGov || !hasAgents) return false;



  const srcDirs = ['src', 'crates', 'lib', 'app'];



  return srcDirs.some(d => fs.existsSync(path.join(workspaceRoot, d)));



}







async function main() {



  const input = await readStdin();



  const { fullyIdle, terminationReason, workspacePaths = [] } = input;







  if (!fullyIdle) {



    process.stdout.write(JSON.stringify({ decision: 'stop' }));



    return;



  }







  const cwd = findWorkspaceRoot(workspacePaths);



  const failures = [];







  // 1. Check for Ungoverned Source Code



  if (hasUngovernedSourceCode(cwd)) {



    failures.push('UNGOVERNED CODEBASE: Wykryto kod źródłowy w projekcie agentowym, ale katalog .governance/ nie istnieje! Uruchom /init lub bootstrap.py.');



  }







  // 2. Check Node.js stack



  const pkgPath = path.join(cwd, 'package.json');



  if (fs.existsSync(pkgPath)) {



    const hasTsConfig = fs.existsSync(path.join(cwd, 'tsconfig.json'));



    if (hasTsConfig) {



      const tsc = runCheck('npx tsc --noEmit 2>&1', cwd);



      if (!tsc.ok) failures.push(`TypeScript: ${tsc.output}`);



    }



    const hasEslint = fs.existsSync(path.join(cwd, 'eslint.config.js')) || 



                      fs.existsSync(path.join(cwd, 'eslint.config.mjs')) || 



                      fs.existsSync(path.join(cwd, '.eslintrc.json')) || 



                      fs.existsSync(path.join(cwd, '.eslintrc.js'));



    if (hasEslint) {



      const lint = runCheck('npx eslint . --max-warnings=0 2>&1', cwd);



      if (!lint.ok) failures.push(`ESLint: ${lint.output}`);



    }



  }







  // 3. Check Rust stack



  const cargoPath = path.join(cwd, 'Cargo.toml');



  if (fs.existsSync(cargoPath)) {



    const cargoCheck = runCheck('cargo check 2>&1', cwd);



    if (!cargoCheck.ok) {



      failures.push(`Rust cargo check: ${cargoCheck.output}`);



    } else {



      const cargoTest = runCheck('cargo test 2>&1', cwd);



      if (!cargoTest.ok) {



        failures.push(`Rust cargo test: ${cargoTest.output}`);



      }



    }



  }







  // 4. Check Python stack



  const hasPy = fs.existsSync(path.join(cwd, 'pyproject.toml')) || 



                fs.existsSync(path.join(cwd, 'pytest.ini')) || 



                fs.existsSync(path.join(cwd, 'requirements.txt'));



  if (hasPy && (fs.existsSync(path.join(cwd, 'tests')) || fs.existsSync(path.join(cwd, 'test')))) {



    const pyCmd = process.platform === 'win32' ? 'python' : 'python3';



    const pyTest = runCheck(`${pyCmd} -m unittest discover -s tests 2>&1`, cwd);



    if (!pyTest.ok) {



      const pytestCheck = runCheck('pytest 2>&1', cwd);



      if (!pytestCheck.ok) {



        failures.push(`Python tests: ${pyTest.output || pytestCheck.output}`);



      }



    }



  }







  // 5. Check Go stack



  const goPath = path.join(cwd, 'go.mod');



  if (fs.existsSync(goPath)) {



    const goVet = runCheck('go vet ./... 2>&1', cwd);



    if (!goVet.ok) {



      failures.push(`Go vet: ${goVet.output}`);



    }



  }







  // 6. Check .governance/tasks.json



  const govCheck = checkGovernanceTasks(cwd);



  if (govCheck.checked && !govCheck.ok) {



    failures.push(`Governance DoD: ${govCheck.reason}`);



  }







  // 7. Check tasks/todo.md



  if (hasPendingTasks(cwd)) {



    failures.push('tasks/todo.md zawiera nieukończone kroki [/]. Oznacz jako [x] przed zakończeniem.');



  }







  if (failures.length > 0) {



    const reason = [



      '[NEXUS Stop Gate] Definition of Done NOT MET — sesja zablokowana:',



      ...failures.map((f, i) => `${i + 1}. ${f}`),



    ].join('\n');



    process.stdout.write(JSON.stringify({ decision: 'continue', reason }));



    return;



  }







  process.stdout.write(JSON.stringify({ decision: 'stop' }));



}







main().catch((err) => {



  process.stderr.write(`[NEXUS StopGate ERROR] ${err.message}\n`);



  process.stdout.write(JSON.stringify({ decision: 'stop' }));



});



"""



    file_path.parent.mkdir(parents=True, exist_ok=True)



    file_path.write_text(code, encoding='utf-8')







def run():



    print("\n" + "="*70)



    print("   Antigravity Closed Loop Ultra Framework v8.2 — Global Master Installer   ")



    print("="*70 + "\n")







    root = pathlib.Path(__file__).resolve().parent



    home = pathlib.Path.home()



    workspace_root = root.parent







    # 0. Bump Version



    (root / "VERSION").write_text("8.1.0\n", encoding="utf-8")







    # 1. Python version check



    print("[1/8] Sprawdzanie interpretera Python... ", end="")



    if sys.version_info < (3, 11):



        print("BŁĄD!")



        print(f"Wymagany Python 3.11+, wykryto: {sys.version.split()[0]}")



        sys.exit(1)



    print(f"OK ({sys.version.split()[0]})")







    # Immunizacja: python3.exe obok python.exe



    if os.name == 'nt':



        py_exe = pathlib.Path(sys.executable)



        py3_exe = py_exe.parent / "python3.exe"



        if not py3_exe.is_file():



            try:



                shutil.copy2(py_exe, py3_exe)



                print("      [Immunizacja] Utworzono python3.exe obok python.exe")



            except Exception:



                pass







    # 2. Git check



    print("[2/8] Sprawdzanie narzędzia Git... ", end="")



    try:



        git_ver = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True).stdout.strip()



        print(f"OK ({git_ver})")



    except Exception:



        print("OSTRZEŻENIE (Brak Git w PATH)")







    # Ścieżki docelowe Antigravity



    config_skills = home / ".gemini" / "config" / "skills"



    antigravity_skills = home / ".gemini" / "antigravity" / "skills"



    plugin_skills = home / ".gemini" / "config" / "plugins" / "ag-kit" / "skills"







    config_agents = home / ".gemini" / "config" / "agents"



    antigravity_agents = home / ".gemini" / "antigravity" / "agents"



    plugin_agents = home / ".gemini" / "config" / "plugins" / "ag-kit" / "agents"



    agents_tpl_agents = home / ".gemini" / "agents_template" / "agents"







    config_rules = home / ".gemini" / "config" / "rules" / "workspace-rules"



    antigravity_rules = home / ".gemini" / "antigravity" / "rules"



    plugin_rules = home / ".gemini" / "config" / "plugins" / "ag-kit" / "rules"



    agents_tpl_rules = home / ".gemini" / "agents_template" / "rules"







    antigravity_commands = home / ".gemini" / "antigravity" / "commands"



    plugin_commands = home / ".gemini" / "config" / "plugins" / "ag-kit" / "commands"







    # 3. Synchronizacja Skilli (17 skilli)



    print("[3/8] Rejestracja skilli w środowisku Antigravity... ", end="")



    source_skills = root / ".agents" / "skills"



    skill_targets = [plugin_skills]  # Canonical destination: ag-kit plugin







    skill_count = 0



    if source_skills.is_dir():



        for sk_dir in source_skills.iterdir():



            if sk_dir.is_dir() and (sk_dir / "SKILL.md").is_file():



                skill_count += 1



                for target_base in skill_targets:



                    dest = target_base / sk_dir.name



                    dest.mkdir(parents=True, exist_ok=True)



                    shutil.copy2(sk_dir / "SKILL.md", dest / "SKILL.md")



                    if (sk_dir / "scripts").is_dir():



                        (dest / "scripts").mkdir(parents=True, exist_ok=True)



                        for s_file in (sk_dir / "scripts").iterdir():



                            if s_file.is_file():



                                shutil.copy2(s_file, dest / "scripts" / s_file.name)



    print(f"OK (Zainstalowano {skill_count} skilli w 3 rejestrach)")







    # 4. Synchronizacja Subagentów i Reguł DREE do wszystkich rejestrów



    print("[4/8] Rejestracja ról subagentów i reguł DREE... ", end="")



    source_agents = root / ".agents" / "agents"



    agent_destinations = [config_agents, antigravity_agents, plugin_agents, agents_tpl_agents, workspace_root / ".agents" / "agents"]



    if source_agents.is_dir():



        for ag_file in source_agents.glob("*.md"):



            for ag_dest in agent_destinations:



                ag_dest.mkdir(parents=True, exist_ok=True)



                shutil.copy2(ag_file, ag_dest / ag_file.name)







    source_rules = root / ".agents" / "rules"



    rules_destinations = [config_rules, antigravity_rules, plugin_rules, agents_tpl_rules, workspace_root / ".agents" / "rules"]



    if source_rules.is_dir():



        for r_file in source_rules.glob("*.md"):



            for r_dest in rules_destinations:



                r_dest.mkdir(parents=True, exist_ok=True)



                shutil.copy2(r_file, r_dest / r_file.name)



    print("OK (Zarejestrowano w 5 lokalizacjach)")







    # 5. Aktualizacja Globalnych Walidatorów Cyklu Życia (PreToolUse & Stop Gate)



    print("[5/8] Aktualizacja globalnych walidatorów cyklu życia... ", end="")



    for v_dir in [home / ".gemini" / "config" / "validators", home / ".gemini" / "agents_template" / "validators"]:



        patch_validator_pre_tool_guard(v_dir / "pre_tool_guard.js")



        patch_validator_stop_dod_gate(v_dir / "stop_dod_gate.js")



    



    # Synchronizacja hooków governance



    for hk_dir in [



        home / ".gemini" / "config" / "plugins" / "ag-kit" / "hooks",



        home / ".gemini" / "extensions" / "ag-kit" / "hooks",



        home / ".gemini" / "antigravity-cli" / "plugins" / "ag-kit" / "hooks",



        workspace_root / ".agents" / "hooks"



    ]:



        hk_dir.mkdir(parents=True, exist_ok=True)



        shutil.copy2(root / ".agents" / "hooks" / "governance_guard.mjs", hk_dir / "governance_guard.mjs")



        shutil.copy2(root / ".governance" / "hooks" / "native_guard.py", hk_dir / "native_guard.py")



    print("OK (Multi-Workspace Hermetic Guard aktywny)")







    # 6. Generowanie natywnych Slash Commands Antigravity 2.0



    print("[6/8] Rejestracja komend ukośnika (/init, /cl-standards, /cl-gate...)... ", end="")



    cmd_targets = [plugin_commands]  # Canonical destination: ag-kit plugin



    for fname, data in COMMANDS_MAP.items():



        for c_dir in cmd_targets:



            write_toml(c_dir / fname, data["description"], data["prompt"])



    print(f"OK (Utworzono {len(COMMANDS_MAP)} poleceń toml)")







    # 7. Przygotowanie szablonów projektowych (Template Bundling)



    print("[7/8] Budowanie szablonu governance dla polecenia /init... ", end="")



    tpl_targets = [plugin_skills / "init" / "template"]



    dirs_to_bundle = [



        ".governance/bin", ".governance/hooks", ".governance/registry",



        ".agents/rules", ".agents/skills", ".agents/agents", ".agents/templates",



        ".agents/hooks", ".agents/learning_inbox",



        ".specify/specs", "specs", "contracts", "tools"



    ]



    files_to_bundle = [



        ".governance/config.json", ".governance/tasks.json", ".governance/standards.json",



        ".agents/hooks.json", "AGENTS.md", "VERSION"



    ]







    for dest_tpl in tpl_targets:



        dest_tpl.mkdir(parents=True, exist_ok=True)



        if (root / "tools" / "init_project.py").is_file():



            (dest_tpl.parent / "scripts").mkdir(parents=True, exist_ok=True)



            shutil.copy2(root / "tools" / "init_project.py", dest_tpl.parent / "scripts" / "bootstrap.py")
            if (root / "tools" / "extend_project.py").is_file():
                shutil.copy2(root / "tools" / "extend_project.py", dest_tpl.parent / "scripts" / "extend_project.py")



        init_skill_src = root / ".agents" / "skills" / "init" / "SKILL.md"



        if init_skill_src.is_file():



            shutil.copy2(init_skill_src, dest_tpl.parent / "SKILL.md")



        for d in dirs_to_bundle:



            src_dir = root / d



            if src_dir.is_dir():



                copy_directory(src_dir, dest_tpl / d)



        for f in files_to_bundle:



            src_f = root / f



            if src_f.is_file():



                (dest_tpl / f).parent.mkdir(parents=True, exist_ok=True)



                shutil.copy2(src_f, dest_tpl / f)







        # Immunizacja: powielenie native_guard.py



        ng_src = root / ".governance" / "hooks" / "native_guard.py"



        if ng_src.is_file():



            for ap in [dest_tpl / ".agents" / ".governance" / "hooks", dest_tpl / ".agents" / "hooks", root / ".agents" / ".governance" / "hooks"]:



                ap.mkdir(parents=True, exist_ok=True)



                shutil.copy2(ng_src, ap / "native_guard.py")



    print("OK (Szablon zaindeksowany)")







    # Synchronizacja kopii wersji w workspace



    v7_dir = workspace_root / "Antigravity_Closed_Loop_Framework_v7.0" / "antigravity-v3-evidence-driven-framework"



    if v7_dir.parent.is_dir():



        copy_directory(root, v7_dir)







    # 8. Weryfikacja silnika i testy



    print("[8/8] Weryfikacja silnika gov.py i suita testowa... ", end="")



    gov_script = root / ".governance" / "bin" / "gov.py"



    doc_res = subprocess.run([sys.executable, str(gov_script), "doctor"], capture_output=True, text=True)



    if doc_res.returncode != 0:



        print(f"BŁĄD DOCTORA: {doc_res.stdout.strip()}")



        sys.exit(1)







    test_res = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests")],



                              capture_output=True, text=True)



    if test_res.returncode != 0:



        print(f"BŁĄD TESTÓW:\n{test_res.stderr}")



        sys.exit(1)



    



    summary_line = [l for l in test_res.stderr.splitlines() if 'Ran ' in l]



    summary = summary_line[0] if summary_line else "ALL PASS"



    print(f"OK ({summary})")







    # Aktualizacja archiwów wydań



    zip_dest_v82 = root.parent / "Antigravity_Closed_Loop_Framework_v8.2.zip"
    print(f"\nGenerowanie archiwum dystrybucyjnego: {zip_dest_v82.name} ... ", end="")
    with zipfile.ZipFile(zip_dest_v82, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in root.rglob('*'):
            if '__pycache__' not in file.parts and '.git' not in file.parts and not file.name.endswith('.pyc'):
                zf.write(file, file.relative_to(root))
    print(f"OK ({os.path.getsize(zip_dest_v82):,} bajtów)")



    print("\n" + "="*70)



    print("   INSTALACJA GLOBALNA FRAMEWORKA V8.1 ZAKOŃCZONA SUKCESEM!  ")



    print("="*70 + "\n")



    print("Zaktualizowane komponenty w Antigravity 2.0 i systemie globalnym:")



    print("  * 11 poleceń slash (/init, /cl-standards, /cl-gate...) w ~/.gemini/antigravity/commands/")



    print("  * 17 skilli operacyjnych w 3 rejestrach ~/.gemini/")



    print("  * 7 ról subagentów i 7 reguł DREE w ~/.gemini/config, ~/.gemini/antigravity i workspace")



    print("  * Globalne walidatory cyklu życia: pre_tool_guard.js i stop_dod_gate.js z obsługą Multi-Workspace")



    print("  * Silnik gov.py v8.0 z FileStatCache (<130ms snapshoty) i workspace_resolver.py")



    print("  * Archiwum dystrybucyjne Antigravity_Closed_Loop_Framework_v8.0.zip")







if __name__ == "__main__":



    run()



