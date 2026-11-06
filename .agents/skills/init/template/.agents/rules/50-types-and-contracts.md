---
trigger: glob
description: "Zgodność typów i stabilność kontraktów."
globs: "**/*.ts, **/*.tsx, **/*.py, **/*.sql, **/*.json"
---

# 50-types-and-contracts

Strict input, rozróżniaj omitted/null, kontrakty wersjonowane. Pieniądze integer minor, brak float. Nie zmieniaj schematu i klienta osobno bez testów kompatybilności. Nowy efekt biznesowy wymaga idempotency key, stanu niepewnego przy network timeout i uzgodnienia gdy dotyczy płatności/integracji.
