---
trigger: model_decision
description: "Delegowanie agentom, worktrees i integracja gałęzi."
---

# Reguła 20: Izolacja Zadań i Zasobów (Task & Resource Isolation)

1. **Trójwarstwowa Hierarchia i Praca w Tandemach:**
   - Warstwa 1: `project-orchestrator` (globalny harmonogram fal DAG, rezerwacje Triple Lock, bramki G6/G7).
   - Warstwa 2: `task-supervisor` (lokalny nadzorca zadania, niezależny token sesyjny, pętla feedbacku max 3 cykle).
   - Warstwa 3: `builder-executor` (implementator w granicach `allowed_paths`, bez praw do samocertyfikacji).
2. **Jeden writer na zakres plików:** Każdy subagent operuje wyłącznie w granicach zadeklarowanego `allowed_paths`. Modyfikacja plików poza zakresem jest twardo blokowana przez `native_guard.py`.
3. **Triple Lock Concurrency & Zero-Overlap:**
   - **Pliki:** Przed uruchomieniem równoległym weryfikowana jest rozłączność: $\text{allowed\_paths}(T_A) \cap \text{allowed\_paths}(T_B) = \emptyset$.
   - **Symbole AST:** Rezerwowane w tabeli `symbol_leases` w SQLite WAL.
   - **Trasy API:** Rezerwowane pod kluczem `ROUTE:<ścieżka>`.
4. **Ścisły Budżet Pętli Self-Healing (Cardinal Rule 12):**
   - Komunikacja nadzorca-koder odbywa się przez maszynowy plik `.governance/FEEDBACK_PACKET_<TASK_ID>.json`.
   - Po 3 nieudanych próbach następuje natychmiastowe zamrożenie stanu `BLOCKED_ESCALATED` i eskalacja do orchestratora / człowieka.
5. **Izolacja Git Worktree:** Każde zadanie wykonywane jest w odrębnym worktree (`.worktrees/<TASK_ID>`), zapobiegając zanieczyszczeniu drzewa roboczego gałęzi głównej.
6. **Centralna koordynacja SQLite:** Baza `.governance/state/state.sqlite` w trybie WAL jest jedynym nienaruszalnym rejestrem stanów, tokenów szermierczych, iteracji i dzierżaw.
