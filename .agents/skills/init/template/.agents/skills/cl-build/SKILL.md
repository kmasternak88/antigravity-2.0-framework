---
name: cl-build
description: "Implementuje jeden zatwierdzony task i przygotowuje evidence handoff."
---

# cl-build

1. Odczytaj packet; sprawdź spec digest i dependencies.
2. Wybierz branch workspace przy invoke_subagent lub utwórz worktree po zgodzie. Claim session=rzeczywisty conversationId; zapisz fencing token.
3. Napisz test, implementację, error paths i regression. Zmiany poza scope wymagają powrotu do planu.
4. Uruchom przypisane gov run checks. Source mutating test jest nieważny.
5. Przekaż candidate hash, wyniki i diff do niezależnego code-auditor.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
