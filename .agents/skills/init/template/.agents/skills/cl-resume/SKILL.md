---
name: cl-resume
description: "Odzyskuje pracę po utracie kontekstu, awarii agenta lub wygaśnięciu lease."
---

# cl-resume

1. Odczytaj handoff/status, git HEAD/status i aktualny spec hash.
2. Sprawdź aktywne procesy, worktrees, ports i leases; nie zabijaj cudzych procesów.
3. Porównaj bieżący diff z scope; nie uznawaj starego PASS po zmianie źródeł.
4. Expired lease może zostać przejęte nowym claim token; stary token nie może finish/heartbeat.
5. Kontynuuj od pierwszej niezakończonej acceptance, nie od streszczenia rozmowy.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
