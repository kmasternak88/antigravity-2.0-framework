---

name: init

description: "Inicjalizacja i orkiestracja projektu w Antigravity Closed Loop Framework v8.1. Blyskawicznie wykrywa stan repozytorium (Greenfield / Brownfield / In-Flight), egzekwuje Multi-Workspace Isolation i prowadzi przez cykl dowodowy G0-G7."

---



# /init — Antigravity Evidence-Driven Closed Loop v8.0 Orchestrator



Komenda `/cl-init` (lub `/init`) to nadrzędny punkt wejścia dla agenta i dewelopera w ekosystemie **Antigravity 2.0**. Daje agentowi natychmiastową wiedzę operacyjną o silniku bramek dowodowych, automatycznie bada stan dojrzałości projektu i dostosowuje dalsze kroki do aktualnego etapu.



---



## 🧭 KROK 1: NATYCHMIASTOWA AUTODIAGNOSTYKA STANU



Zanim wykonasz jakąkolwiek zmianę w kodzie, uruchom skrypt diagnostyczny:



```powershell

python -c "

import os, sys, pathlib

root = pathlib.Path.cwd()

gov_cfg = root / '.governance' / 'config.json'

tasks_file = root / '.governance' / 'tasks.json'

has_code = any((root / d).is_dir() for d in ['src', 'app', 'lib', 'tests', 'test']) or any((root / f).is_file() for f in ['package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod'])



if not gov_cfg.exists():

    print('S0_GREENFIELD' if not has_code else 'S1_BROWNFIELD_UNMANAGED')

else:

    import json

    tasks = json.loads(tasks_file.read_text(encoding='utf-8')).get('tasks', []) if tasks_file.exists() else []

    print('S2_GOVERNANCE_UNLOCKED' if tasks else 'S3_IN_FLIGHT')

"

```



Klasyfikacja do jednego z 4 Stanów Dojrzałości:

* **`S0_GREENFIELD`** — Pusty nowy projekt (brak kodu, brak `.governance/`).

* **`S1_BROWNFIELD_UNMANAGED`** — Istniejący kod/repozytorium bez frameworka governance.

* **`S2_GOVERNANCE_UNLOCKED`** — Framework obecny, ale `specLocked == false` (specyfikacja niezatwierdzona lub uległa zmianie).

* **`S3_IN_FLIGHT`** — Projekt zablokowany i w toku (zadanie aktywne, oczekujące na claim lub gotowe do wydania).



---



## ⚙️ KROK 2: PROTOKÓŁ DZIAŁANIA DLA WYKRYTEGO STANU



### ŚCIEŻKA A: STAN `S0_GREENFIELD` (Nowy Projekt od Zera)

1. **Scaffolding:** Uruchom bootstrapper z centralnej instalacji ag-kit lub lokalnego tools/:

   ```powershell

   python "$HOME\.gemini\config\plugins\ag-kit\skills\init\scripts\bootstrap.py" --target . --mode new

   ```

   *(Alternatywnie: `python tools/init_project.py --target . --mode new` jeśli narzędzia są już obecne).*

   > **ŻELAZNY NAKAZ:** Nigdy nie pomijaj instalacji frameworka! Jeśli tools/init_project.py nie istnieje lokalnie, MUSISZ użyć globalnego bootstrap.py. ZAKAZ pisania kodu aplikacji przed zainstalowaniem `.governance/` i nałożeniem bramki G2!

2. **Living Charter & Genesis Blueprint:**

   - Wygeneruj kompletny zestaw specyfikacji w `specs/`:

     - `specs/01_PRODUCT_REQUIREMENTS.md` (Wymagania i PRD)

     - `specs/02_SYSTEM_ARCHITECTURE.md` (Architektura C4 i DAG)

     - `specs/03_DATA_DICTIONARY.md` (Słownik Danych SSoT)

     - `contracts/` (Zamrożone interfejsy i modele)

   - W przypadku złożonego projektu uruchom automatyczny kompilator:

     ```powershell

     python tools/genesis_compiler.py specs/01_PRODUCT_REQUIREMENTS.md

     ```

3. **Spec Lock (Bramka G2):** Oblicz digest i poproś człowieka o zatwierdzenie:

   ```powershell

   python .governance/bin/gov.py spec-hash

   python .governance/bin/gov.py approve-spec --actor human:owner --reference init-bootstrap

   ```

4. **Początek prac w Zespole Subagentów (Separacja Ról):**

   - **Orkiestrator (Sesja Główna):** Nadzoruje DAG, rejestruje decyzje ADR i wywołuje subagentów przez `invoke_subagent`. Nie modyfikuje bezpośrednio kodu produkcyjnego w `src/`, `crates/`, `lib/`!

   - **Subagenci Wykonawczy (`builder-executor`):** Rezerwują zadanie atomowe z DAG:

     ```powershell

     python .governance/bin/gov.py claim --task T001 --actor agent:builder-1 --session $CONVERSATION_ID

     ```

   - **Subagenci Audytujący (`code-auditor`):** Weryfikują dowody w `.governance/evidence/` i zatwierdzają bramkę G5:

     ```powershell

     python .governance/bin/gov.py gate T001

     ```



---



### ŚCIEŻKA B: STAN `S1_BROWNFIELD_UNMANAGED` (Rozbudowa Istniejącego Projektu)

1. **Bezpieczny Autonomiczny Overlay:** Nałóż framework z zachowaniem istniejących reguł (użyj globalnego bootstrappera lub lokalnego tools/):

   ```powershell

   python "$HOME\.gemini\config\plugins\ag-kit\skills\init\scripts\bootstrap.py" --target . --mode extend --force-merge

   ```

   *(Alternatywnie: `python tools/init_project.py --target . --mode extend --force-merge`)*

   * *Zasada bezpieczeństwa:* Istniejący `AGENTS.md` zostaje zachowany na szczycie (kopia w `.bak`), a `checks` w `.governance/config.json` zostają automatycznie podpięte pod rzeczywiste testy projektu (`npm test`, `pytest`, `cargo test` itp.).

2. **Inwentaryzacja (`/cl-discover`):** Przeskanuj architekturę projektu, zmapuj zależności AST i określ obszar planowanej rozbudowy.

3. **Task Scoping (Vertical Slice):** W `.governance/tasks.json` zdefiniuj zadanie `T001` ograniczone wyłącznie do ścieżek nowej funkcji (`allowed_paths: ["src/feature", "tests/feature"]`). Chroni to resztę projektu przed naruszeniem zakresu (`OUT_OF_SCOPE`).

4. **Specyfikacja & Approval:** Zdefiniuj kryteria w `specs/` i zatwierdź z operatorem przed edycją kodu aplikacji.



---



### ŚCIEŻKA C: STAN `S2_GOVERNANCE_UNLOCKED` (Wymagany Spec Lock)

1. **Weryfikacja spójności:** Uruchom walidator DAG:

   ```powershell

   python .governance/bin/gov.py validate

   ```

2. **Niezależny audyt specyfikacji:** Sprawdź czy acceptance criteria są mierzalne, a profile ryzyka (`tiny`, `standard`, `critical`) adekwatne do zmian.

3. **Zablokowanie specyfikacji:** Oblicz digest i zarejestruj decyzję człowieka:

   ```powershell

   python .governance/bin/gov.py approve-spec --actor human:owner --reference review-zatwierdzony

   ```



---



### ŚCIEŻKA D: STAN `S3_IN_FLIGHT` (Projekt w Trakcie Realizacji)

1. **Sprawdzenie statusu:** `python .governance/bin/gov.py status`

2. **Pętla Zadania (Closed-Loop):**

   * **Claim:** Jeśli zadanie czeka w PENDING $

ightarrow$ `gov.py claim --task <ID> --actor agent:builder --session <UUID>`

   * **Implementacja:** Modyfikuj pliki wyłącznie wewnątrz zadeklarowanego `allowed_paths` z zachowaniem 7 niezmienników DREE.

   * **Dowód testu:** `python .governance/bin/gov.py run --task <ID> --check <CHECK_NAME>` (musi zwrócić exit code 0; log SHA-256 zostanie trwale zapisany w `evidence/`).

   * **Niezależne Review:** Poproś innego agenta/audytora o recenzję bieżącego snapshotu:

     ```powershell

     python .governance/bin/gov.py review --task <ID> --reviewer agent:code-auditor --decision APPROVED --reference "raport-qa"

     ```

     *(Pamiętaj: builder nie może zatwierdzić własnego zadania!)*

   * **Bramka Gate & Finish:**

     ```powershell

     python .governance/bin/gov.py gate --task <ID>

     python .governance/bin/gov.py finish --task <ID> --token <FENCING_TOKEN>

     ```

3. **Finalizacja etapu:** Po wykonaniu wszystkich zadań uruchom `python tools/ci_checks.py`.



---



## 🛡️ NIEZMIENNIKI I ZASADY OPERACYJNE (CARDINAL RULES)

1. **Brak samocertyfikacji:** Agent implementujący kod (`builder`) pod żadnym pozorem nie może recenzować swojego zadania w `gov.py review`. Reviewer musi mieć inny identyfikator.

2. **NOT_RUN to nie PASS:** Nigdy nie deklaruj sukcesu bez rzeczywistego wykonania procesu z kodem powrotu 0.

3. **Ścisły budżet napraw:** Maksymalnie 3 iteracje naprawcze dla tego samego błędu testu. Po 3 próbach zatrzymaj się, przedstaw minimalną reprodukcję i eskaluj do operatora.

4. **Izolacja zapisu:** Hook `native_guard.py` odrzuca operacje zapisu bez aktywnego claimu oraz operacje wykraczające poza `allowed_paths`.

5. **Mem0 Sync:** Kluczowe decyzje architektoniczne utrwalaj w pamięci projektu (`add_memory` / `mem0_remember`).



---



## 📋 FORMAT ODPOWIEDZI DLA UŻYTKOWNIKA PO WYWOŁANIU /init

Zawsze przedstaw użytkownikowi czytelną tabelę diagnostyczną i jeden konkretny następny krok:



```markdown

### 🎯 Status Inicjalizacji Antigravity Closed Loop v8.0

- **Zidentyfikowany Stan:** S1_BROWNFIELD_UNMANAGED (Projekt Node.js / Python)

- **Repozytorium Git:** Zainicjalizowane

- **Silnik Governance:** Gotowy do instalacji / Aktywny

- **Bramka Testowa:** Skonfigurowana

- **Stan Specyfikacji:** WYMAGA BLOKADY (Spec Lock G2)



**Rekomendowany następny krok:**

[Jedno konkretne, klikalne polecenie lub pytanie do użytkownika]

```



Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.


