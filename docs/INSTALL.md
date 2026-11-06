# Instalacja i migracja V2→V3

## Wymagania

Python3.11+ i Git dla pracy repo. Core używa stdlib; brak pip install. Antigravity App/CLI: dostęp do Customizations i uprawnień terminala. IDE może mieć inne funkcje subagentów; w tym przypadku wykorzystaj skills/rules i sekwencyjny fallback. Nie kopiuj globalnych ustawień na wszystkie projekty.

## Kroki

1. Zachowaj backup istniejących `.agents`, `AGENTS.md` i `.specify`. Przejrzyj git status.
2. Przeczytaj AUDIT_V2. Usuń/zmień stare reguły dopiero po porównaniu; rules kumulują się i sprzeczne stare instrukcje mogą pozostać aktywne.
3. Uruchom selftests w katalogu rozpakowanego pakietu.
4. Installer dry-run: `python3 tools/install.py --target /absolute/repo`. Domyślnie nic nie zapisuje.
5. Jeśli są kolizje, installer odmawia całej operacji. Przenieś dopasowane sekcje ręcznie, zachowując specyfikę projektu. Nie ma --force ani automatycznego merge JSON.
6. Ponów z --apply gdy plan nie ma kolizji. Powtórzenie identycznej instalacji jest no-op.
7. Uruchom gov doctor i selftests w docelowym repo.
8. Zastąp bootstrap spec/tasks/check commands rzeczywistymi. Nie zatwierdzaj T001 jako planu budowy aplikacji.
9. Zweryfikuj natywne discovery poniżej i zapisz `docs/reports/PLATFORM_COMPATIBILITY.md`.

## Antigravity verification

- Rules: `.agents/rules/*.md`, poprawne `trigger`; zobacz aktywne reguły w Customizations.
- Skills: `.agents/skills/<name>/SKILL.md` z name/description. Sprawdź widoczność `/cl-discover`. Brak slash na danej powierzchni: wskaż agentowi ścieżkę SKILL.md, nie udawaj rejestracji.
- Agents: `.agents/agents/*.md`; sprawdź exact tools i model tiers inherit/pro. Nie ma obowiązkowego gemini-X.Y.
- Hooks: `.agents/hooks.json` named definitions/PreToolUse. Upewnij się, że `python3 .governance/hooks/native_guard.py` uruchamia się z root repo. Jeśli lokalna powierzchnia używa innego cwd, ustaw jawnie zaakceptowaną absolutną ścieżkę do skryptu. Nie uznawaj hook za aktywny bez testu jego uruchomienia.
- Test hooka: write unclaimed code musi dostać deny; run arbitrary terminal force_ask; governance write force_ask; claimed allowed path po spec lock allow (nadal obowiązują native permissions).
- Session claim musi używać prawdziwego conversationId z aktualnej sesji. Jeśli ID nie jest udostępnione agentowi, poproś operatora o odczyt przez narzędzia platformy i zapisz handoff; nie wpisuj fałszywego session1 do produkcyjnego hooka.
- Sandbox: wykonaj uzgodniony harmless denial probe poza workspace i zablokowanego egress. Ustawienie boolean nie dowodzi działającej izolacji.
- Platform/plan: `/boost` i `/teamwork` mogą zależeć od planu i powierzchni. Brak obsługi=sekwencyjny workflow.

## Uprawnienia

App: project Permission Preset=Request Review na start; sandbox i non-workspace access ustaw przez UI. CLI: przykład `examples/cli-settings.safe.json` służy do ręcznego merge w udokumentowanym `~/.gemini/antigravity-cli/settings.json`. Nie instalujemy `.agents/settings.json` z wymyślonym schematem. IDE: sprawdź Strict Mode i ograniczenia środowiska, nie zakładaj identycznych nazw przełączników.

Wersja CLI/OS, dostępność sandbox, hook loaded i tool inventory zapisane w compatibility report. Core tests nie zastępują tego raportu.
