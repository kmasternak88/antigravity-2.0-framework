---
name: cl-release
description: "Przygotowuje wydanie operacyjne (G7), buduje macierz śledzenia SSoT, aktualizuje Living Charter i generuje nienaruszalny manifest release v8.0."
version: 5.1.0
---

# /cl-release — Operational Release Gate (G7) & Traceability Matrix

Procedura finalnego wydania produkcyjnego, weryfikacji braku regresji oraz wygenerowania nadrzędnego manifestu wdrożeniowego.

## Protokół Bramki G7 (Operational Release)

1. **Weryfikacja Stanu Wszystkich Zadań:**
   - Wszystkie zaplanowane zadania w `.governance/tasks.json` muszą mieć status `DONE` w bazie dowodowej SQLite.
   - Uruchomienie `gov.py release` przy jakimkolwiek otwartym lub niescalonym zadaniu zostanie maszynowo zablokowane.

2. **Krok 1: Wygenerowanie Macierzy Śledzenia SSoT:**
   - Wygeneruj zintegrowaną macierz wymagań, kontraktów, kodu i testów:
     ```bash
     python .governance/bin/gov.py trace-matrix --format markdown
     ```
   - Każde kryterium akceptacyjne ze specyfikacji (`AC-*`) musi mieć potwierdzone powiązanie z konkretnym testem i statusem `PASS`.

3. **Krok 2: Aktualizacja Living Charter (Post-Release):**
   - Zaktualizuj dokumentację architektoniczną o scalone encje i zindeksowane komponenty:
     ```bash
     python .governance/bin/gov.py generate-charter --out specs
     ```
   - Sprawdź wygenerowane pliki w `specs/`:
     - `01_PRODUCT_REQUIREMENTS.md`
     - `02_SYSTEM_ARCHITECTURE.md` (diagramy C4 i przepływy)
     - `03_DATA_DICTIONARY.md` (zindeksowane dataclass i modele)
     - `04_DEPENDENCY_AND_IMPACT.md`
     - `05_ACCEPTANCE_MATRIX.md`

4. **Krok 3: Generowanie Manifestu Release:**
   - Wywołaj maszynową certyfikację wydania:
     ```bash
     python .governance/bin/gov.py release
     ```
   - Silnik weryfikuje sumy kontrolne `specDigest` oraz `sourceDigest` i tworzy nienaruszalny manifest `.governance/RELEASE_MANIFEST.json` ze statusem `G7_PASS_OPERATIONAL_RELEASE`.

5. **Przedstawienie Raportu Operatorowi:**
   - Pokaż użytkownikowi identyfikator wydania (`releaseId`), listę zrealizowanych zadań, stan testów oraz procedurę ewentualnego rollbacku.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
