---
name: cl-build
description: "Implementuje jeden zatwierdzony task w odizolowanym worktree z zachowaniem Standardu 7 Niezmienników DREE v8.0 i przygotowuje dowody wykonania."
version: 5.1.0
---

# /cl-build — Subagent Task Implementation & DREE 7-Invariant Standard

Wykonuje pojedyncze zadanie z kolejki DAG w wyizolowanym środowisku roboczym (Git Worktree) w oparciu o atomowy pakiet zadań Mythos XML (`subagent_packet.xml`).

## Protokół Działania Subagenta

1. **Inicjalizacja i Środowisko:**
   - Odczytaj wygenerowany pakiet zadania `.governance/handoffs/<TASK_ID>.json`.
   - Zweryfikuj `specDigest` oraz upewnij się, że wszystkie zależności w DAG mają status `DONE`.
   - Wywołaj rezerwację zadania:
     ```bash
     python .governance/bin/gov.py claim --task <TASK_ID> --actor <ACTOR_ID> --session <SESSION_ID>
     ```
   - Zainicjalizuj dedykowane środowisko robocze:
     ```bash
     python .governance/bin/gov.py worktree --task <TASK_ID> --action create
     ```

2. **DREE: Generowanie Szkieletu (Standard 7 Niezmienników):**
   - W przypadku nowej jednostki/funkcji wygeneruj wzorcowy szkielet:
     ```bash
     python .governance/bin/gov.py scaffold-unit --name <Name> --domain <domain> --type <service|controller|repository>
     ```
   - Każda funkcja MUSI spełniać 7 niezmienników jakościowych:
     1. **Contract-First:** Dane wejściowe i wyjściowe zdefiniowane w `dataclass(frozen=True)` / interfejsie TS.
     2. **Boundary Validation:** Asercja poprawności argumentów na wejściu (brak pustych pól, nieprawidłowych zakresów).
     3. **Domain Exceptions:** Dedykowany błąd domenowy dziedziczący po `Exception` (zakaz surowego `except:`).
     4. **Clean Code (SRP):** Maksymalnie 40 linii kodu na funkcję.
     5. **Zero Console / Telemetry:** Zakaz `print()` i `console.log`. Ustrukturyzowane logowanie.
     6. **Dual Test Suite:** Min. 1 test Happy-Path + min. 1 test Negative Edge-Case (z asercją wyjątku).
     7. **SSoT & Spec Sync:** Rejestracja w `__all__` oraz synchronizacja `specs/03_DATA_DICTIONARY.md`.

3. **Lokalna Weryfikacja Standardów:**
   - Przed uruchomieniem testów zweryfikuj zgodność z AST:
     ```bash
     python .governance/bin/gov.py check-standards --file <path>
     ```
   - Kod naruszający którąkolwiek z reguł zostanie odrzucony przez Bramkę G4 z kodem 2 (`STANDARDS_VIOLATION`).

4. **Wykonanie Testów i Ewidencja Dowodów:**
   - Uruchom przypisany test:
     ```bash
     python .governance/bin/gov.py run --task <TASK_ID> --check <CHECK_NAME>
     ```
   - Zmiany kodu po uruchomieniu testu unieważniają dowód (stale evidence protection).

5. **Przekazanie do Niezależnego Przeglądu:**
   - Wyślij raport wykonania do niezależnego subagenta `code-auditor`.
   - Zmiany poza sekcją `allowed_paths` są surowo zabronione i blokowane przez `native_guard.py`.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
