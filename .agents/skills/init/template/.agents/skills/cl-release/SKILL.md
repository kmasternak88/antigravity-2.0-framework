---
name: cl-release
description: "Przygotowuje release candidate, rollback i operator approval."
---

# cl-release

1. Stwórz candidate z zatwierdzonych tasków i sprawdź brak konfliktów.
2. Re-run globalne checks na candidate. Lokalna kontrola nie zastępuje protected CI.
3. Sprawdź migrations/backups/restore/secrets/dependency scan/observability według ryzyka.
4. Pokaż użytkownikowi konkretny deployment target, commit/image digest, migracje, ryzyko i rollback. Czekaj na zgodę.
5. Postdeploy smoke i metryki. Regression oznacza rollback lub operator response, nie ciche naprawianie prod.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
