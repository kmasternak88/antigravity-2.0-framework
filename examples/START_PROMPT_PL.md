# Prompt startowy

Pracuj zgodnie z AGENTS.md i frameworkiem closed-loop. Najpierw odczytaj repozytorium, status Git, istniejący blueprint i wymagania. Nie pisz jeszcze kodu aplikacji. Wykryj powierzchnię i faktycznie dostępne funkcje Antigravity. Użyj cl-discover i cl-spec-audit.

Przygotuj:
1. inventory faktycznie odczytanych plików;
2. luki/konflikty i decyzje z dowodami;
3. minimalny pionowy slice oraz profile ryzyka;
4. kontrakty, acceptance i DAG tasks z allowed_paths;
5. rzeczywiste check argv i plan niezależnego review;
6. dokładny spec digest do zatwierdzenia przeze mnie.

Nie nagrywaj approval w moim imieniu. Po mojej zgodzie buduj zadania sekwencyjnie lub w rozłącznych worktrees, zbierając dowody i odrzucając stare PASS. Zatrzymaj się po3 nieudanych cyklach tego samego błędu, przy braku uprawnień lub konieczności niezatwierdzonej zmiany zakresu. Wydanie i operacje produkcyjne wymagają osobnej zgody na konkretny target i payload.
