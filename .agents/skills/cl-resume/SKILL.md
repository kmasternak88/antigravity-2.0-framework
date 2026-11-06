---
name: cl-resume
description: "Odzyskuje pracę po utracie kontekstu, awarii subagenta lub wygaśnięciu leasingu, weryfikuje integralność worktree i stan bramek dowodowych v8.0."
version: 5.1.0
---

# /cl-resume — Context Recovery, Worktree Reconciliation & Lease Takeover

Protokół bezpiecznego wznawiania pracy po awarii agenta, restarcie sesji czatu lub utracie kontekstu w środowisku Antigravity Ultra v8.0.

## Procedura Odzyskiwania Stanu

1. **Autodiagnostyka Stanu Repozytorium:**
   - Wywołaj diagnostykę silnika:
     ```bash
     python .governance/bin/gov.py doctor
     python .governance/bin/gov.py status
     ```
   - Sprawdź aktywne rezerwacje (`claims`), blokady (`spec-lock`) i stan zadań w DAG.

2. **Rekoncyliacja Worktree i Środowisk Subagentów:**
   - Zidentyfikuj aktywne katalogi `.worktrees/<TASK_ID>` lub `.shadow_worktrees/<TASK_ID>`.
   - W przypadku porzuconego zadania, posprzątaj lub zrekonstruuj gałąź:
     ```bash
     python .governance/bin/gov.py worktree --task <TASK_ID> --action cleanup
     ```

3. **Przejęcie Wygasłego Leasingu (Expired Lease Takeover):**
   - Jeśli poprzedni agent przekroczył `lease_seconds`, wywołaj ponowną rezerwację z nowym fencing tokenem:
     ```bash
     python .governance/bin/gov.py claim --task <TASK_ID> --actor <NOWY_ACTOR> --session <NOWY_SESSION>
     ```
   - Poprzedni fencing token staje się bezpowrotnie nieważny.

4. **Audyt Źródeł i Weryfikacja Standardów:**
   - Sprawdź, czy dotknięte pliki nie zawierają błędów składni lub naruszeń:
     ```bash
     python .governance/bin/gov.py check-standards --task <TASK_ID>
     ```
   - Jeśli dowody testowe uległy przedawnieniu (`stale evidence`), uruchom testy ponownie poleceniem `gov.py run`.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
