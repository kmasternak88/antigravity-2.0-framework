---
trigger: model_decision
description: "Delegowanie agentom, worktrees i integracja gałęzi."
---

# Reguła 20: Izolacja Zadań i Zasobów (Task & Resource Isolation)

1. **Jeden writer na zakres plików:** Każdy subagent operuje wyłącznie w granicach zadeklarowanego `allowed_paths`. Modyfikacja plików poza zakresem jest twardo blokowana przez `native_guard.py`.
2. **Triple Lock Concurrency:**
   - **Pliki:** Sprawdzane przez `overlaps()`.
   - **Symbole AST:** Rezerwowane w tabeli `symbol_leases` w SQLite WAL.
   - **Trasy API:** Rezerwowane pod kluczem `ROUTE:<ścieżka>`.
3. **Brak współdzielenia środowisk mutowalnych:** Testy agentów nie mogą współdzielić portów sieciowych, baz danych ani tymczasowych plików bez unikalnych namespace/UUID.
4. **Izolacja Git Worktree:** Każde zadanie wykonywane jest w odrębnym worktree (`.worktrees/<TASK_ID>`), zapobiegając zanieczyszczeniu drzewa roboczego gałęzi głównej.
5. **Centralna koordynacja SQLite:** Baza `.governance/state/state.sqlite` w trybie WAL jest jedynym nienaruszalnym rejestrem stanów, tokenów szermierczych i dzierżaw.
