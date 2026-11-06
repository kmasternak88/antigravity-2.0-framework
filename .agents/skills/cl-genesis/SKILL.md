---
name: cl-genesis
description: "Multi-Agent Genesis Blueprint Compiler & Inception Pipeline dla Antigravity Closed Loop Framework v8.0. Przekształca surowy pomysł/brief w kompletny, deterministyczny, zwalidowany Master Plan (Fazy 1-7) bez halucynacji i niedomówień, kompiluje Living Charter w specs/ oraz topologiczny DAG w .governance/tasks.json i nakłada pieczęć Spec Lock G1/G2."
version: 8.0.0
---

# /cl-genesis — Multi-Agent Genesis Blueprint Compiler & Inception Pipeline (v8.0)

Komenda `/cl-genesis` inicjuje wieloagentowy potok inżynieryjny, którego celem jest przekształcenie surowego pomysłu, briefu lub specyfikacji biznesowej w **KOMPLETNY, DETERMINISTYCZNY I ODPORNY NA AWARIE MASTER IMPLEMENTATION BLUEPRINT**. 

Dostarcza on dwie zsynchronizowane warstwy (Two-Tier Synchronized SSoT):
1. **Warstwa I: Specification-Driven Development Blueprint (SDB w `specs/`)** — PRD w EARS, architektura C4 i UI/UX (WCAG 2.1 AA / OKLCH), Słownik Danych i Traceability Matrix.
2. **Warstwa II: LLM-Executable Blueprint (`.governance/tasks.json` + `contracts/`)** — Deterministyczny graf DAG spełniający regułę 40/3/1, 7 niezmienników DREE, zamrożone kontrakty bez float dla walut oraz komendy weryfikacyjne DoD (exit code 0).

Plan ten stanowi fundament wykonawczy dla downstream coding agents (`builder-executor`, `code-auditor`, `qa-verifier`), gwarantując, że implementacja odbędzie się bez zgadywania założeń, bez dryfu architektonicznego i z zerową tolerancją na halucynacje.

---

## 🏗️ Architektura Potoku Multi-Agent Genesis

```
[Surowy Pomysł / Brief Biznesowy]
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 1. GENESIS NODE (`genesis-architect`)                  │
│    - Protokół 8 Faz Inicjalizacji                      │
│    - PRD, ADR, Schematy Bazy, Kontrakty Zod/Pydantic   │
│    - SRE, Topologia repozytorium, Graf DAG 1..N        │
└────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 2. ADVERSARIAL CHALLENGER (`challenger`)               │
│    - Testy obciążeniowe założeń (Edge & Failure Modes) │
│    - Symulacja wyścigów, timeoutów i awarii sieci      │
└────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 3. SRE & SYSTEM AUDITOR (`code-auditor`)               │
│    - Weryfikacja Standardu 7 Niezmienników DREE        │
│    - Sprawdzenie limitów zasobów, graceful shutdown    │
└────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 4. TOPOLOGICAL SPEC AUDITOR (`spec-auditor`)           │
│    - Weryfikacja acykliczności grafu DAG (Kahn's Sort) │
│    - Wymóg deterministycznych komend DoD per zadanie   │
└────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 5. GENESIS COMPILER (`tools/genesis_compiler.py`)      │
│    - Zero-Placeholders Lint (brak // TODO, itd., np.)  │
│    - Rozbicie na modułowe pliki specs/01..07           │
│    - Kompilacja zadań do .governance/tasks.json        │
│    - Aktualizacja spec_files w .governance/config.json │
└────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 6. HUMAN-IN-THE-LOOP & SPEC LOCK G1/G2                 │
│    - Przedstawienie planu człowiekowi do akceptacji    │
│    - Pieczęć kryptograficzna SHA-256 (approve-spec)    │
│    - Gotowość do autonomicznej egzekucji DAG           │
└────────────────────────────────────────────────────────┘
```

---

## 🛡️ Żelazne Reguły Architektoniczne (RFC 2119)

1. **ZERO PREMATURE CODING (Spec-First Invariant):**
   - Bezwzględny zakaz pisania kodu produkcyjnego przed zatwierdzeniem specyfikacji i nałożeniem blokady Spec Lock (Bramka G1/G2).
2. **ZERO PLACEHOLDERS & ZERO AMBIGUITY:**
   - Kompilator automatycznie odrzuca plany zawierające: `// TODO`, `do ustalenia`, `w zależności od potrzeb`, `np.`, `itd.`, `itp.`, `zabezpiecz odpowiednio`.
   - Każde niedookreślenie użytkownika musi zostać rozstrzygnięte autonomicznie i zapisane w sekcji ADR.
3. **TOPOLOGICAL DAG INVARIANT:**
   - Krok $N$ może zależeć wyłącznie od kroków $< N$. Wykluczone są jakiekolwiek zależności cykliczne lub odwołania w przód.
4. **MACHINE-VERIFIABLE DEFINITION OF DONE:**
   - Każde zadanie w grafie DAG musi posiadać atomową komendę weryfikacyjną (test, linter, typecheck). Exit code 0 = PASS, inny = FAIL.
5. **HERMETIC WRITE ISOLATION:**
   - Każde zadanie określa ścisłe `allowed_paths`. Hook `native_guard.py` blokuje wszelkie próby zapisu poza ten obszar.

---

## 📋 Procedura Krok po Kroku

### Krok 1: Inicjalizacja i Synteza Założeń
Uruchom rolę `genesis-architect`, przekazując opis pomysłu użytkownika. Agent generuje dokument `specs/00_MASTER_BLUEPRINT.md` zawierający 8 faz:
- **FAZA 1:** Dekonstrukcja Domeny, Wymagania i Przypadki Brzegowe (PRD & ADR)
- **FAZA 2:** Architektura Danych i Zarządzanie Stanem (Data & State Layer)
- **FAZA 3:** Kontrakty API, Modele i Protokoły Komunikacji (API & Contracts)
- **FAZA 4:** Inżynieria Niezawodności, Bezpieczeństwo i Observability (SRE & Security)
- **FAZA 5:** Topologia Repozytorium, Środowisko i Konfiguracja (Environment & Structure)
- **FAZA 6:** Topologiczny Graf Wdrożenia (DAG Implementation Steps)
- **FAZA 7:** Strategia Testów i Weryfikacja Jakości (QA & Verification Matrix)

### Krok 2: Wieloagentowy Audyt Adversarialny
Orkiestrator powołuje subagentów:
1. `challenger`: Testuje scenariusze awarii (Race Conditions, Network Partitions, Idempotency Violations).
2. `code-auditor`: Weryfikuje zgodność z 7 Niezmiennikami DREE i odpornością procesów (Graceful Shutdown, Circuit Breakers).
3. `spec-auditor`: Weryfikuje poprawność relacji zależności w DAG i brak martwych ścieżek.

### Krok 3: Automatyczna Kompilacja i Linting
Uruchom kompilator maszynowy:
```powershell
python tools/genesis_compiler.py specs/00_MASTER_BLUEPRINT.md
```
Kompilator:
- Bada obecność zakazanych tokenów wieloznacznych (Zero-Placeholders Lint).
- Przeprowadza sortowanie topologiczne algorytmem Kahna.
- Rozbija monolit na pliki `specs/01_PRD_AND_ADR.md` do `specs/07_QA_VERIFICATION_MATRIX.md`.
- Generuje deterministyczny plik `.governance/tasks.json`.
- Rejestruje pliki w `.governance/config.json`.

### Krok 4: Pieczęć Spec Lock (Bramka G1/G2)
Po zatwierdzeniu planu przez człowieka:
```powershell
python .governance/bin/gov.py approve-spec --actor human:owner
```
Wygenerowany kryptograficzny hash SHA-256 blokuje specyfikację. Od tego momentu downstream coding agenci mogą równolegle lub sekwencyjnie pobierać zadania za pomocą `gov.py package-handoff <TASK_ID>` i realizować je w czystych Git Worktrees.
