---
name: cl-review
description: "Wykonuje niezależny przegląd i kontrprzykłady przed task gate."
---

# cl-review

1. Potwierdź, że reviewer nie jest autorem i ma czysty dokładny candidate.
2. Czytaj diff i downstream callers, uruchom testy. Nie polegaj tylko na logu buildera.
3. Findings: id/severity/path/line/reproduction/fix acceptance.
4. Po fix nowy source hash i review. Zapisz gov review z referencją raportu/PR.
5. gov gate może potwierdzić lokalne warunki, nie autentyczność człowieka ani production readiness.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
