---
trigger: model_decision
description: "Delegowanie agentom, worktrees i integracja gałęzi."
---

# 20-task-isolation

Jeden writer na task i path scope. Nowy worktree przy spawn, nie niesprawdzone frontmatter workspace. Nie dziel DB/portów/sekretów między testami agentów bez osobnych namespace. Lockfile/migracje/contracts single integrator. Lokalny SQLite nie synchronizuje wielu worktrees; koordynator centralnie rozdziela zadania. Reviewer czyta dokładny candidate diff i uruchamia testy zależnych modułów.
