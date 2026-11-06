---
trigger: model_decision
description: "Implementacja, błąd testu, regresja lub przygotowanie merge."
---

# Reguła 30: Testowanie, Odporność i Procedura Naprawy (Test & Repair)

1. **Zasada Prawdy Dowodowej:** Wynik `PASS` istnieje wyłącznie wtedy, gdy test został fizycznie uruchomiony na BIEŻĄCYM kodzie (`sourceDigest == snapshot()`) i zwrócił exit code 0.
2. **Zakaz fałszowania dowodów:** Zakaz wprowadzania mocków do kodu produkcyjnego, zakaz usuwania testów failing, zakaz zmyślania screenshotów lub logów.
3. **Pokrycie Przypadków Brzegowych (Edge-Cases):** Suity testowe muszą obowiązkowo pokrywać:
   - Wartości `null`, puste ciągi i struktury danych.
   - Duplikaty kluczy i identyfikatorów.
   - Granice uprawnień (próby nieautoryzowanego dostępu).
   - Limity numeryczne i przepełnienia.
   - Timeouty sieciowe, symulacje awarii i rollback transakcji.
   - Wyścigi współbieżności (race conditions).
4. **Zasada Dowodowa UI:** Screenshot jest dowodem wyglądu interfejsu użytkownika, a NIE poprawności bazy danych, logiki biznesowej czy transakcji finansowej.
5. **Ścisły Budżet Napraw (3-Cycle Self-Healing):**
   - Cykl 1: Minimalna reprodukcja błędu.
   - Cykl 2: Sformułowanie hipotezy przyczynowej (Root Cause) i punktowa zmiana w 1 miejscu.
   - Cykl 3: Uruchomienie pełnego pakietu testów modułu.
   - Po 3 nieudanych próbach: natychmiastowe zamrożenie zadania, zachowanie minimalnej reprodukcji i eskalacja do operatora.
