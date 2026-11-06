---
name: cl-plan-slice
description: "Dzieli zatwierdzony zakres na małe zadania z własnością plików i DAG."
---

# cl-plan-slice

1. Zidentyfikuj jeden mierzalny efekt użytkownika, nie warstwę bez użycia.
2. Dodaj id/dependencies/allowed_paths/checks/acceptance/risk.
3. Kontrakty i migracje zaplanuj z single integrator i compatibility gates.
4. Max1 writer per overlapping scope. Oddziel DB/ports/resources worktrees.
5. Validate DAG i przy zmianie spec pozyskaj nowy approval.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
