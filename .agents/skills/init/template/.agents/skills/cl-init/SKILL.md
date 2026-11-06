---
name: init
description: "Inicjalizacja i orkiestracja projektu w Antigravity Closed Loop Framework v8.1. Blyskawicznie wykrywa stan repozytorium (Greenfield / Brownfield / In-Flight), egzekwuje Multi-Workspace Isolation i prowadzi przez cykl dowodowy G0-G7."
---

# /init — Antigravity Evidence-Driven Closed Loop 3.0 Orchestrator

Komenda `/init` to nadrzędny punkt wejścia dla agenta i dewelopera w ekosystemie **Antigravity 2.0**. Daje agentowi natychmiastową wiedzę operacyjną o silniku bramek dowodowych, automatycznie bada stan dojrzałości projektu i dostosowuje dalsze kroki do aktualnego etapu.

---

## 🧭 KROK 1: NATYCHMIASTOWA AUTODIAGNOSTYKA STANU

Zanim wykonasz jakąkolwiek zmianę w kodzie, uruchom skrypt diagnostyczny:

```powershell
python "C:\Users\lpiku\.gemini\config\skills\init\scripts\detect_state.py"
```

Skrypt w ułamku sekundy klasyfikuje repozytorium do jednego z 4 Stanów Dojrzałości:
* **`S0_GREENFIELD`** — Pusty nowy projekt (brak kodu, brak `.governance/`).
* **`S1_BROWNFIELD_UNMANAGED`** — Istniejący kod/repozytorium bez frameworka governance.
* **`S2_GOVERNANCE_UNLOCKED`** — Framework obecny, ale `specLocked == false` (specyfikacja niezatwierdzona lub uległa zmianie).
* **`S3_IN_FLIGHT`** — Projekt zablokowany i w toku (zadanie aktywne, oczekujące na claim lub gotowe do wydania).

---

## ⚙️ KROK 2: PROTOKÓŁ DZIAŁANIA DLA WYKRYTEGO STANU

### ŚCIEŻKA A: STAN `S0_GREENFIELD` (Nowy Projekt od Zera)
1. **Scaffolding:** Uruchom bootstrapper:
   ```powershell
   .\antigravity-init.ps1 -Target . -Mode new
   ```
2. **Karta Projektu:** Zbierz od użytkownika 2–3 kluczowe wymagania i zapisz w `.specify/specs/01_CHARTER.md` oraz `.specify/specs/03_ACCEPTANCE.md`.
3. **Spec Lock:** Oblicz digest i poproś człowieka o zatwierdzenie:
   ```powershell
   python .governance/bin/gov.py spec-hash
   python .governance/bin/gov.py approve-spec --actor human:owner --reference init-bootstrap
   ```
4. **Początek prac:** Zarezerwuj bazowe zadanie `T001` (Inicjalizacja architektury i pipeline testowego):
   ```powershell
   python .governance/bin/gov.py claim --task T001 --actor agent:builder-1 --session $CONVERSATION_ID
   ```

---

### ŚCIEŻKA B: STAN `S1_BROWNFIELD_UNMANAGED` (Rozbudowa Istniejącego Projektu)
1. **Bezpieczny Overlay:** Nałóż framework z zachowaniem istniejących reguł:
   ```powershell
   .\antigravity-init.ps1 -Target . -Mode extend -ForceMerge
   ```
   * *Zasada bezpieczeństwa:* Istniejący `AGENTS.md` zostaje zachowany na szczycie (kopia w `.bak`), a `checks` w `.governance/config.json` zostają automatycznie podpięte pod rzeczywiste testy projektu (`npm test`, `pytest`, `cargo test` itp.).
2. **Inwentaryzacja (`/cl-discover`):** Przeskanuj architekturę projektu, zmapuj zależności i określ obszar planowanej rozbudowy.
3. **Task Scoping (Vertical Slice):** W `.governance/tasks.json` zdefiniuj zadanie `T001` ograniczone wyłącznie do ścieżek nowej funkcji (`allowed_paths: ["src/feature", "tests/feature"]`). Chroni to resztę projektu przed naruszeniem zakresu (`OUT_OF_SCOPE`).
4. **Specyfikacja & Approval:** Zdefiniuj kryteria w `.specify/specs/` i zatwierdź z operatorem przed edycją kodu aplikacji.

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
   * **Claim:** Jeśli zadanie czeka w PENDING $\rightarrow$ `gov.py claim --task <ID> --actor agent:builder --session <UUID>`
   * **Implementacja:** Modyfikuj pliki wyłącznie wewnątrz zadeklarowanego `allowed_paths`.
   * **Dowód testu:** `python .governance/bin/gov.py run --task <ID> --check <CHECK_NAME>` (musi zwrócić exit code 0; log SHA256 zostanie trwale zapisany).
   * **Niezależne Review:** Poproś innego agenta/audytora o recenzję bieżącego snapshotu:
     ```powershell
     python .governance/bin/gov.py review --task <ID> --reviewer agent:qa-verifier --decision APPROVED --reference "raport-qa"
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

## 📋 FORMAT ODPOWIEDZI DLA UŻYTKOWNIKA PO WYWOŁANIU `/init`

Zawsze przedstaw użytkownikowi czytelną tabelę diagnostyczną i jeden konkretny następny krok:

```markdown
### 🎯 Status Inicjalizacji Antigravity Closed Loop 3.0
- **Zidentyfikowany Stan:** S1_BROWNFIELD_UNMANAGED (Projekt Node.js)
- **Repozytorium Git:** Zainicjalizowane
- **Silnik Governance:** Gotowy do instalacji / Aktywny
- **Bramka Testowa:** `npm test` (timeout: 180s)
- **Stan Specyfikacji:** WYMAGA BLOKADY (Spec Lock)

**Rekomendowany następny krok:**
[Jedno konkretne, klikalne polecenie lub pytanie do użytkownika]
```
