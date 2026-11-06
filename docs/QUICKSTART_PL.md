# Start w praktyce

## Kolejność

1. Przeczytaj README i AUDIT_V2.
2. Selftests w rozpakowanej paczce.
3. Installer dry-run, rozwiązanie kolizji, apply.
4. Antigravity Customizations: sprawdź rules, skills, agents i hook. Nie zostawiaj równocześnie sprzecznych reguł V2.
5. Project settings=Request Review, sandbox z potwierdzonym działaniem, brak produkcyjnych credentials.
6. Użyj promptu examples/START_PROMPT_PL.md i /cl-discover.
7. Zastąp bootstrap spec/tasks/checks rzeczywistym zakresem. Dla AgenticPayload przeczytaj docs/PROJECT_AGENTICPAYLOAD.md i umieść zatwierdzony blueprint w repo.
8. /cl-spec-audit → niezależny audyt i spec digest → decyzja człowieka.
9. /cl-plan-slice → /cl-build → /cl-review → /cl-verify → /cl-release.
10. /cl-resume przy zmianie sesji; /cl-learn tylko jako propozycja po incydencie.

## Polecenia

```bash
python3 -m unittest discover -s tests -v
python3 tools/install.py --target /absolute/path/to/project
python3 tools/install.py --target /absolute/path/to/project --apply
```

Powyższy target to parametr polecenia do zastąpienia rzeczywistą ścieżką, nie plik istniejący w paczce. Installer nie przyjmuje celu będącego rodzicem ani potomkiem katalogu źródłowego; użyj osobnego katalogu rozpakowania.

## Pierwsze zlecenie dla agenta

„Odczytaj AGENTS.md i docs/OPERATING_MODEL.md. Użyj cl-discover dla istniejącego projektu. Przygotuj inventory, mapę luk i jeden testowalny vertical slice. Nie pisz kodu aplikacji i nie zatwierdzaj spec w moim imieniu. Pokaż digest spec+config+tasks do akceptacji.”

## Najważniejsze ograniczenie

To workflow evidence-driven, nie system gwarantujący brak błędów. Szczelność wymaga chronionego CI, realnego review i sandboxa, których nie zastąpi lokalny JSON ani długi prompt.
