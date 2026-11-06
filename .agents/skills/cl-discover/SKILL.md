---
name: cl-discover
description: "Inwentaryzuje repozytorium, analizuje kruchość kodu (Deep Discovery), generuje Living Charter oraz przygotowuje plan z profilowaniem ryzyka w standardzie Framework v8.0."
version: 5.1.0
---

# /cl-discover — Repository Deep Discovery & Living Charter Architecture

Protokół inwentaryzacji bazy kodu, mapowania modeli i tras oraz generowania żywej specyfikacji architektonicznej.

## Protokół Działania

1. **Weryfikacja Środowiska i Spójności Bazowej:**
   - Sprawdź stan środowiska i integralność bazy SQLite:
     ```bash
     python .governance/bin/gov.py doctor
     ```

2. **Głęboka Eksploracja Kodu (Deep Discovery):**
   - Zindeksuj pliki źródłowe, frameworki, modele baz danych, punkty końcowe API i pokrycie testami:
     ```bash
     python .governance/bin/gov.py discover --deep
     ```
   - Silnik wyliczy wskaźnik kruchości (`fragilityScore`), wskaże trasy bez testów i zapisze `.governance/inventory.json` oraz `.governance/topology.json`.

3. **Generowanie 5-Wymiarowego Living Charteru:**
   - Wygeneruj kompletną dokumentację architektoniczną w katalogu `specs/`:
     ```bash
     python .governance/bin/gov.py generate-charter --out specs
     ```
   - Składniki wygenerowanego Living Charteru:
     - `01_PRODUCT_REQUIREMENTS.md` — cele biznesowe, profile i ograniczenia.
     - `02_SYSTEM_ARCHITECTURE.md` — architektura C4, diagramy przepływu Mermaid i topologia.
     - `03_DATA_DICTIONARY.md` — słownik encji i modeli danych SSoT.
     - `04_DEPENDENCY_AND_IMPACT.md` — macierz zależności i analiza blast radius.
     - `05_ACCEPTANCE_MATRIX.md` — powiązanie kryteriów z testami automatycznymi.

4. **Scaffolding Kontraktów API i Modeli:**
   - W przypadku nowych usług wygeneruj bazowe kontrakty:
     ```bash
     python .governance/bin/gov.py scaffold-contracts
     ```
   - Utworzy `contracts/models.py`, `contracts/types.ts` oraz `contracts/openapi.json`.

5. **Walidacja DAG i Przygotowanie Spec Lock (G1/G2):**
   - Zweryfikuj poprawność grafu zadań:
     ```bash
     python .governance/bin/gov.py validate
     ```
   - Zapewnij niepustą checklistę standardów dla każdego zadania w `.governance/tasks.json`.
   - Przedstaw operatorowi podsumowanie do zatwierdzenia przez `gov.py approve-spec`.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
