---
name: cl-audit
description: "Anti-Tautology & Mock-Breaker Mutation Auditor dla Antigravity Ultra v8.0. Wykrywa pozorne testy LLM i weryfikuje ich rzetelność poprzez testy mutacyjne (Fault Injection)."
version: 5.1.0
---

# /cl-audit — Anti-Tautology & Mock-Breaker Auditor

Komenda `/cl-audit` przeprowadza automatyczny audyt asercji testowych przypisanych do zadania, uniemożliwiając zaliczenie bramki G4 przez testy pozorne (np. testujące same siebie lub mockujące całą logikę).

## Użycie CLI

```powershell
python .governance/bin/gov.py audit-tests --task T001
```

## Działanie Algorytmu Mock-Breaker
1. **Analiza Heurystyczna AST:** Sprawdza, czy w plikach testowych znajdują się mierzalne asercje (`assert`, `assertEqual`, `expect`, `should`).
2. **Test Mutacyjny (Fault Injection):**
   - Tymczasowo wstrzykuje błąd wykonawczy (`raise RuntimeError`) do implementacji testowanej funkcji.
   - Uruchamia przypisany check testowy.
   - **Warunek Asercji:** Test **musi zakończyć się błędem**! Jeśli test przeszedł z kodem `0`, dowodzi to, że jest tautologią i zostaje zablokowany z kodem błędu `TAUTOLOGICAL_TEST_DETECTED`.
   - Oryginalny kod jest natychmiast bezpiecznie przywracany.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
