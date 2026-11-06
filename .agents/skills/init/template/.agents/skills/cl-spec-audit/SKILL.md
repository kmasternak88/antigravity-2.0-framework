---
name: cl-spec-audit
description: "Audytuje spec, DAG, kontrakty i testability bez samo-zatwierdzania."
---

# cl-spec-audit

1. Przeczytaj wszystkie spec_files oraz tasks/config.
2. Szukaj counterexamples: null/duplicate/authz/timeout/race/recovery/rollbacks według domeny.
3. Uruchom validate; zmapuj każde acceptance do check i zadania.
4. Zwróć findings, nie edytuj spec autora. Max2 review rounds; unresolved critical=BLOCKED.
5. Przekaż aktualny digest człowiekowi do akceptacji konkretnej wersji.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
