---
name: cl-verify
description: "Weryfikuje scalony candidate, testy wielopoziomowe (Unit, Integration, Contract), Mock-Breaker oraz powiązanie z Macierzą Śledzenia SSoT v8.0."
version: 5.1.0
---

# /cl-verify — Comprehensive Verification & SSoT Evidence Suite

Weryfikacja jakościowa zintegrowanego kodu, dowodów testowych i powiązań z kryteriami akceptacyjnymi przed wydaniem operacyjnym.

## Protokół Weryfikacji

1. **Weryfikacja Wielopoziomowa:**
   - **Testy jednostkowe (Unit):** weryfikacja logiki biznesowej i gałęzi brzegowych.
   - **Audyt Mock-Breaker (`gov.py audit-tests`):** test mutacyjny weryfikujący brak tautologii i atrap testów.
   - **Testy kontraktowe (Contract):** asercja zgodności z modelami OpenAPI/TypeSpec.
   - **Testy integracyjne / UI:** weryfikacja zachowania w realnym środowisku wykonawczym.

2. **Weryfikacja Dowodów Maszynowych:**
   - Każdy zaliczony check rejestruje w SQLite:
     - `task_id` i nazwę checku
     - `sourceDigest` (SHA-256 źródeł)
     - `logSha256` (SHA-256 wyjścia testu)
     - kod zakończenia `exitCode: 0`
   - Jakakolwiek modyfikacja kodu po uruchomieniu testu natychmiastowo unieważnia dowód (`stale evidence`).

3. **Macierz Śledzenia SSoT:**
   - Wygeneruj aktualną macierz pokrycia wymagań:
     ```bash
     python .governance/bin/gov.py trace-matrix --format markdown
     ```
   - Każde kryterium `AC-*` ze specyfikacji musi posiadać status dowodowy `PASS`.

4. **Weryfikacja Bramki Zadania:**
   - Sprawdź lokalną bramkę zadania:
     ```bash
     python .governance/bin/gov.py gate --task <TASK_ID>
     ```
   - Potwierdza obecność dowodów wykonania, audytu AST standardów DREE oraz zatwierdzonego przeglądu niezależnego G5.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
