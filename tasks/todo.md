# Plan Implementacji Wzmocnień Bezpieczeństwa Silnika Governance

## Zakres prac:
- [x] 1. Implementacja Lock 1 (Kryptograficzny Dual-Control & Session Binding) w `.governance/bin/gov.py`
  - Weryfikacja sesji w `def review`: odrzucenie z `FRAUDULENT_SELF_REVIEW_REJECTED` w przypadku tej samej sesji lub braku tokenu audytora
  - Ustawienie `identityVerified = True` TYLKO przy zweryfikowanym tokenie audytora z odrębnej sesji
  - Zablokowanie podszywania się pod `--actor human:*` / `reviewer human:*` bez `GOV_HUMAN_TOKEN` (`UNAUTHORIZED_HUMAN_IMPERSONATION`)
  - Wprowadzenie w `def gate(task)` twardego warunku `identityVerified == True` (odrzucenie z `GATE_FAILED: Independent review identity unverified (identityVerified=False)`)
- [x] 2. Implementacja Lock 2 (Enforced Worktree Sandboxing) w `.governance/bin/gov.py`
  - Usunięcie wszystkich bypassów `WORKTREE_PASSTHROUGH` (m.in. `ANTIGRAVITY_WORKSPACE_MODE == 'share'`, `GOV_WORKTREE_PASSTHROUGH == '1'`, `.worktrees` parent)
  - Wymuszenie fizycznej izolacji worktree dla każdego aktywnego zadania IN_PROGRESS
- [x] 3. Implementacja Lock 4 (Anti-Introspection Guard) w `.governance/hooks/native_guard.py` i `C:\Users\lpiku\.gemini\config\validators\pre_tool_guard.js`
  - Zablokowanie operacji odczytu (`view_file`, `read_file`, `grep_search`, `list_dir`, itp.) plików `.governance/bin/gov.py` oraz `.governance/hooks/` w trakcie trwania zadania (`IN_PROGRESS` / `ACTIVE`)
- [x] 4. Synchronizacja zmian z `.agents/hooks/` oraz szablonami:
  - Synchronizacja `.agents/hooks/native_guard.py`
  - Synchronizacja `.agents/.governance/hooks/native_guard.py`
  - Synchronizacja `.agents/skills/init/template/.governance/hooks/native_guard.py`
  - Synchronizacja `.agents/skills/init/template/.governance/bin/gov.py`
  - Synchronizacja `.agents/.governance/bin/gov.py`
  - Aktualizacja `.agents/hooks/governance_guard.mjs`
- [x] 5. Weryfikacja testami jednostkowymi i integracyjnymi (rozszerzenie `test_governance.py` o suitę `SecurityLocksTests` - 92/92 testów zdanych)
- [x] 6. Przygotowanie raportu i diffów dla koordynatora via `send_message`
