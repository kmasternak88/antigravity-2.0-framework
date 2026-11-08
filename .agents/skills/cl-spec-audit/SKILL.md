---
name: cl-spec-audit
description: "Audytuje specyfikację, graf zadań DAG, kontrakty danych oraz testowalność przed nałożeniem kryptograficznej blokady Spec Lock (G1/G2) w standardzie v8.3."
version: 5.1.0
---

# /cl-spec-audit — Independent Spec & Invariant Verification Gate

Protokół rygorystycznego przeglądu specyfikacji i planu DAG przed zatwierdzeniem przez człowieka w Bramce G2.

## Zakres Audytu Specyfikacji

1. **Weryfikacja Kompletności Kontraktów i Słownika:**
   - Sprawdź, czy wszystkie encje biznesowe posiadają definicje w `contracts/` oraz `specs/03_DATA_DICTIONARY.md`.
   - Sprawdź stany brzegowe: brakujące pola, błędne formaty, brak autoryzacji, limity transakcji.

2. **Audyt Struktury Zadań (Bramka G1):**
   - Wywołaj walidator DAG:
     ```bash
     python .governance/bin/gov.py validate
     ```
   - Upewnij się, że każde zadanie w `.governance/tasks.json` ma zdefiniowaną **niepustą listę standardów DREE** (`standards_checklist`).

3. **Weryfikacja Śledzenia Wymagań (Traceability):**
   - Zmapuj każde kryterium akceptacyjne (`AC-*`) do zadania i konkretnego testu automatycznego.
   - Puste lub niesprawdzalne kryteria muszą zostać odrzucone.

4. **Przedłożenie do Zatwierdzenia (G2 Spec Lock):**
   - Po pozytywnym audycie wygeneruj skrót specyfikacji:
     ```bash
     python .governance/bin/gov.py spec-hash
     ```
   - Przekaż unikalny `specDigest` człowiekowi/operatorowi do ostatecznego zatwierdzenia komendą:
     ```bash
     python .governance/bin/gov.py approve-spec --actor human:owner --reference "<REFERENCE>"
     ```

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
