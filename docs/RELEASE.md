# Integracja i wydanie

## CI dostarczone w paczce

`python3 tools/ci_checks.py` wykonuje required_release_checks na bieżącym candidate, z exit codes i hashami logów; potwierdza niezmienność source podczas testów. Nie wymaga podszycia się pod human lokalnym approve-spec. Nie autoryzuje deployment.

`.github/workflows/governance-checks.yml` jest szablonem GitHub Actions z minimalnymi permissions i bez sekretów. Actions podane jako major tag ze względu na brak zweryfikowanych commit SHA podczas generowania. Przed critical deployment przypnij każdy action do zweryfikowanego pełnego commit SHA; nie wpisujemy zmyślonych hashy. Nie używaj pull_request_target z kodem niezaufanego PR i sekretami.

`required_release_checks` w domyślnym config sprawdza WYŁĄCZNIE framework. Zastąp/dodaj rzeczywiste build/unit/integration/contracts/e2e/security projektu przed jakimkolwiek wydaniem produktu. CI green frameworka nie jest green aplikacji.

## Kontrole po stronie serwera

Włącz branch protection: required check governance-checks oraz checks produktu, required review niezależnego konta, dismiss stale approvals, brak direct push i brak admin bypass w normalnym procesie. CODEOWNERS musi obejmować AGENTS.md, .agents/, .governance/, workflow CI, lockfile, schemas i migrations. Właściciel repo ustawia te zabezpieczenia; paczka nie może wymusić konfiguracji hostingu przez plik Markdown.

## Candidate flow

1. Builder kończy task gate na feature snapshot.
2. Integrator tworzy candidate merge do aktualnego target. Konflikt wymaga review zmienionego diff.
3. CI buduje/testuje exact candidate; zapisuje commit SHA, tree SHA, lockfile digest, image digest, toolchain i sourceDigest.
4. Niezależny reviewer ocenia diff i acceptance; na critical dodatkowa ocena security/domain.
5. Deploy do staging, testy prawdziwych integracji i recovery zależne od profilu.
6. Operator zatwierdza konkretne środowisko, artefakt, migracje i plan rollback. Używaj protected environment approval, nie samej frazy „kontynuuj”.
7. Postdeploy smoke, alerty i obserwacja. Błąd przy danych nieodwracalnych może wymagać forward fix/operator response zamiast automatycznego rollback DB.

## Definicja zakończenia

Zadanie DONE nie oznacza release. Release nie oznacza bezbłędności. Raport ma: wymagania i testy, NOT_RUN i wyłączenia, unresolved findings, known limits, deploy target, provenance, odzyskiwanie i właściciela operacyjnego.
