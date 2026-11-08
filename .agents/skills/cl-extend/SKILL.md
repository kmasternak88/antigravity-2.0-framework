---
name: cl-extend
description: "Inkrementalna rozbudowa aktywnych projektów (Brownfield Managed / In-Flight S2-S3) w Antigravity Ultra v8.3. Integruje tryb sokratejski /grill-me, inżynierię wymagań EARS, triady Gherkin, aktualizację Living Charter (specs/01-04), zamrożone kontrakty oraz przyrostową kompilację DAG (tasks.json)."
version: 8.2.0
---

# /cl-extend (aliasy: /extend, /expand) — Incremental Living Charter & DAG Compiler (v8.2)

Komenda `/cl-extend` jest nadrzędnym punktem wejścia dla agenta i inżyniera przy **rozbudowie JUŻ AKTYWNYCH, zarządzanych projektów** (stany `S2_GOVERNANCE_UNLOCKED` oraz `S3_IN_FLIGHT`). 

W odróżnieniu od `/init` (które inicjalizuje repozytoria od zera `S0` lub adoptuje projekty niezarządzane `S1`), `/cl-extend` przeprowadza precyzyjne wstrzyknięcie delty funkcjonalnej bez naruszania ukończonych modułów i bez ryzyka wprowadzenia regresji.

---

## 🧭 KROK 1: WERYFIKACJA STANU PROJEKTU (PRE-FLIGHT GATE)

Przed rozpoczęciem rozbudowy agent MUSI zweryfikować stan zarządzania w repozytorium:

```powershell
python -c "
import pathlib, json, sys
root = pathlib.Path.cwd()
gov_cfg = root / '.governance' / 'config.json'
tasks_file = root / '.governance' / 'tasks.json'
if not gov_cfg.exists() or not tasks_file.exists():
    print('ERROR: Projekt nie jest zainicjalizowany w frameworku governance. Użyj /init lub /cl-genesis.')
    sys.exit(1)
cfg = json.loads(gov_cfg.read_text(encoding='utf-8'))
tasks = json.loads(tasks_file.read_text(encoding='utf-8')).get('tasks', [])
print(f'STATUS: Managed Project Ready. Active tasks: {len(tasks)}, SpecLocked: {cfg.get(\"spec_locked\", False)}')
"
```

Jeżeli projekt nie posiada katalogu `.governance/`, agent natychmiast zatrzymuje proces i kieruje użytkownika do komendy `/init`.

---

## 🧠 KROK 2: WYWIAD SOKRATEJSKI "GRILL-ME" (ASK_QUESTION PROTOCOL)

Zanim powstanie jakakolwiek specyfikacja delta, agent MUSI wyeliminować wszelkie domysły i niejednoznaczności, uruchamiając tryb **Grill-Me**.

### Standard 5 Wymiarów Pytań Sokratejskich:
1. **One-Way Doors (Decyzje Nieodwracalne):** Architektura magazynu danych (ACID SQL vs Append-Only Ledger vs Key-Value).
2. **Data & Money Invariants (Reguła 50 DREE):** Czy moduł przetwarza finanse/salda/limity? Wymóg: kwoty wyłącznie jako liczby całkowite w jednostkach podrzędnych (`integer minor`, np. grosze/centy) oraz nagłówek `X-Idempotency-Key`. Bezwzględny zakaz `float`!
3. **Kontrakty Komunikacji & API:** Model interfejsu (REST ze ściśle typowanymi DTO `slots=True, frozen=True` vs Event-Driven Bus).
4. **SRE & Odporność:** Domyślny timeout 5000ms, Circuit Breaker, Exponential Backoff z Jitterem, zasada Fail-Closed.
5. **Kompatybilność Wsteczna:** 100% addytywność (brak mutacji istniejących sygnatur) i ochrona przed regresją testów.

W interfejsie Antigravity 2.0 agent zadaje pytania za pomocą narzędzia `ask_question` lub generuje ustrukturyzowany formularz wielokrotnego wyboru z jawnie oznaczonymi opcjami `[REKOMENDOWANE]`.

---

## 📝 KROK 3: INŻYNIERIA WYMAGAŃ EARS & TRIADY GHERKIN

Wszystkie ustalenia z wywiadu zostają skompilowane w ścisłe wymagania **EARS (Easy Approach to Requirements Syntax)**:
- **Ubiquitous:** `System SHALL [działanie nadrzędne].`
- **Event-driven:** `WHEN [zdarzenie], system SHALL [reakcja i walidacja].`
- **State-driven:** `WHILE [stan systemu], system SHALL [inwariant].`
- **Unwanted behavior:** `IF [błąd/nieprawidłowy payload], THEN system SHALL [rzucić DomainError].`
- **Optional feature:** `WHERE [włączona flaga], system SHALL [funkcja opcjonalna].`
- **Complex:** `WHILE [stan], WHEN [zdarzenie], system SHALL [reakcja].`

Dla każdego wymagania agent generuje **Triadę Gherkin (Dual-Test Suite + Adversarial)**:
1. **Happy Path:** Scenariusz sukcesu spełniający zamrożony kontrakt.
2. **Negative Path 1 (Boundary Failure):** Walidacja odrzucenia brakujących pól, kwot ujemnych lub błędnych typów.
3. **Negative Path 2 (Adversarial / Fault Injection):** Ochrona przed kolizją idempotency_key, timeouty sieciowe, wyścigi danych.

---

## 🏗️ KROK 4: AUTOMATYCZNA AKTUALIZACJA LIVING CHARTER (SPECS/)

Uruchomienie kompilatora delty:
```powershell
python tools/extend_project.py --brief "<opis_rozszerzenia>" --slug "<slug_modulu>" --domain "<domena>"
```

Kompilator deterministycznie aktualizuje:
1. `specs/01_PRODUCT_REQUIREMENTS.md`: Dopisuje nową sekcję z tabelą EARS i blokami scenariuszy Gherkin.
2. `specs/02_SYSTEM_ARCHITECTURE.md`: Aktualizuje diagram C4 Component/Container w Mermaid, definiując nowe przepływy i granice bezpieczeństwa.
3. `specs/03_DATA_DICTIONARY.md`: Rejestruje nowe encje, DTO i wyjątki domenowe w SSoT (wymusza `int` cents, zakaz `float`).
4. `specs/04_DEPENDENCY_AND_IMPACT.md`: Oblicza Blast Radius i rejestruje listę dotkniętych ścieżek.
5. `contracts/<slug>.py`: Generuje niezmienne interfejsy DTO (`slots=True, frozen=True`, walidacja w `__post_init__`, błędy domenowe `class DomainError`).

---

## 🔗 KROK 5: PRZYROSTOWY DAG & ZASADA 40/3/1 (.GOVERNANCE/TASKS.JSON)

Kompilator `extend_project.py` scala nowe zadania z istniejącym grafem za pomocą **algorytmu Kahna (Topological Sort)**:
- **Acykliczność:** Matematyczny dowód braku cykli zależności $A \rightarrow B \rightarrow A$.
- **Reguła 40/3/1:** Każde zadanie to SRP $\le 40$ linii kodu, $\le 3$ pliki w `allowed_paths`, dokładnie 1 writer subagent.
- **7 Niezmienników DREE:** Każde zadanie zawiera pełną checklistę:
  `["interface_contract", "input_validation", "domain_exception", "pure_logic_srp", "telemetry_logging", "dual_test_suite", "export_registration"]`.
- **Deterministyczne DoD:** Każde zadanie posiada komendę weryfikacyjną (np. `pytest tests/test_<slug>_service.py`), której exit code 0 decyduje o sukcesie.

---

## 🔒 KROK 6: PIECZĘĆ SPECYFIKACJI (BRAMKA G1/G2 SPEC LOCK)

Po aktualizacji Living Charter i tasks.json blokada `spec_locked` zostaje automatycznie zwolniona (`spec_locked = false`).
Przed rozpoczęciem kodowania przez `builder-executor` w Git Worktree, specyfikacja musi zostać ponownie zatwierdzona:

```powershell
python .governance/bin/gov.py spec-hash
python .governance/bin/gov.py approve-spec --actor human:owner --reference "Approved extension: <slug>"
```

Dopiero po uzyskaniu kodu wyjścia 0 dla `approve-spec` orkiestrator może przydzielić zadanie do izolowanego worktree:
```powershell
python .governance/bin/gov.py claim <task_id> --actor builder-executor
```
