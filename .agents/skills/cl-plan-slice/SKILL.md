---
name: cl-plan-slice
description: "Dzieli zatwierdzony zakres na małe zadania w acyklicznym grafie DAG, definiuje checklisty standardów DREE v8.0, oblicza Blast Radius i przydziela izolację worktree."
version: 5.1.0
---

# /cl-plan-slice — Task Decomposition, DAG & Blast Radius Planning

Protokół dekompozycji wymagań biznesowych na atomowe, weryfikowalne plastry pionowe (*Vertical Slices*) z jawnym przypisaniem standardów jakościowych.

## Zasady Planowania Zadań (Bramka G1)

1. **Struktura Zadania w `.governance/tasks.json`:**
   Każde zadanie `T###` musi posiadać:
   - `id`: unikalny identyfikator (np. `T001`).
   - `title`: precyzyjny opis celu biznesowego.
   - `depends_on`: lista id zadań, które muszą osiągnąć stan `DONE`.
   - `allowed_paths`: ścisłe granice zapisu dla subagenta (np. `["src/billing", "tests/billing", "specs"]`).
   - `checks`: lista checków weryfikacyjnych ze zdefiniowanym limitem timeout.
   - `acceptance`: identyfikatory kryteriów z Living Charteru (`AC-*`).
   - `risk`: profil ryzyka (`tiny`, `standard`, `critical`).
   - `standards_checklist`: **obowiązkowa niepusta lista standardów DREE** (np. `["CONTRACT_DEFINED", "DOMAIN_EXCEPTION_DEFINED", "INPUT_VALIDATED", "CLEAN_CODE_SRP", "ZERO_CONSOLE", "DUAL_TESTS_CREATED", "DATA_DICTIONARY_SYNCED"]`).

2. **Analiza Zasięgu i Wpływu (Blast Radius):**
   - Przed sfinalizowaniem planu uruchom analizę wpływu dla każdego planowanego pliku:
     ```bash
     python .governance/bin/gov.py impact --file <path>
     ```
   - Zidentyfikuj moduły zależne i dodaj ich testy regresyjne do sprawdzanych checków zadania.

3. **Izolacja Workspace (Git Worktree):**
   - Zaplanuj niezależną gałąź dla każdego zadania, zapobiegając konfliktom zapisu równoległych subagentów.
   - Zasada: maksymalnie 1 subagent zapisujący w danym zakresie (`allowed_paths`).

4. **Weryfikacja Determinizmu Grafu:**
   - Sprawdź acykliczność i kompletność:
     ```bash
     python .governance/bin/gov.py validate
     ```
   - Każde naruszenie (cykl w DAG, pusta checklista standardów, brakujące checki) natychmiast blokuje przejście do Bramki G2.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
