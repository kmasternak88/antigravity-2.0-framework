# AGENTS.md — Globalny Manifest Koordynacji i Niezmienników (Antigravity v8.3)

> **Zasada nadrzędna:** Niniejszy plik definiuje nienaruszalny kontrakt epistemologiczny, etyczny i operacyjny dla wszystkich agentów LLM pracujących w ekosystemie **Antigravity 2.0 (Ultra Swarm Engine)**. Każdy subagent przed podjęciem działania ma obowiązek zapoznać się z poniższymi regułami.

---

## 🛡️ 16 KARDYNALNYCH ZASAD ANTY-HALUCYNACYJNYCH (CARDINAL RULES)

1. **Brak cichego sukcesu:** Brak narzędzia, brak credentials, brak środowiska lub brak wykonania to bezwzględnie `NOT_RUN` albo `BLOCKED`, nigdy `PASS`.
2. **Brak halucynacji narzędzi:** Nigdy nie twierdzimy, że polecenie zadziałało, dopóki nie ma realnego exit code (kod powrotu 0) i zbadanego stdout/stderr.
3. **Prawda w repozytorium (Evidence-First):** Wszystkie decyzje dotyczące zakresu, architektury i ryzyk opierają się na twardych dowodach w repozytorium, nie na domysłach ani założeniach modelu.
4. **Brak aktualnego Spec Lock (Bramka G2):** Przy braku ważnego `approve-spec` dopuszczalny jest wyłącznie research, specyfikacja i izolowane testy frameworka. Kod aplikacyjny nie ma prawa powstać.
5. **Implementacja Vertical Slice:** Implementuj najmniejszy pionowy wycinek funkcji z działającym testem akceptacyjnym. Spec-first nie oznacza tworzenia gigantycznych, niestestowalnych monolitów.
6. **Jeden writer na zakres plików:** Dokładnie jeden agent implementuje zadanie w wyznaczonym `allowed_paths` w dedykowanym Git Worktree. Zakaz równoległych modyfikacji wspólnych plików.
7. **Deterministyczny Handoff:** Każdy koordynator przekazuje do subagenta: `taskId`, `base commit`, `specDigest`, `allowed_paths`, `acceptance criteria` oraz wycinek decyzji architektonicznych ADR.
8. **Ocena rozwiązań:** Oceniaj kod według: *poprawności (correctness) -> bezpieczeństwa (security) -> operacyjności (operability) -> kosztu*, a nie liczby użytych narzędzi czy subagentów.
9. **Zakaz samocertyfikacji (Dual-Control):** Agent implementujący (`builder`) nie może odbierać ani recenzować własnego kodu jako niezależny audytor (`reviewer != actor`).
10. **Świeżość dowodów (Zero Drift):** Status `PASS` wymaga wykonanego testu na BIEŻĄCYM stanie kodu (`sourceDigest == snapshot()`). Każda zmiana pliku natychmiast unieważnia wcześniejszy dowód testu.
11. **Ochrona testów:** Zakaz usuwania testów failing, zakaz obniżania progów asercji, zakaz wprowadzania mocków do kodu produkcyjnego, zakaz modyfikacji expected bez formalnego zatwierdzenia specyfikacji.
12. **Ścisły budżet napraw (3-Cycle Self-Healing):** Algorytm naprawy błędu testu: *Minimalna reprodukcja -> Hipoteza przyczynowa -> Punktowa zmiana -> Asercja*. Maksymalnie 3 próby w pętli z `task-supervisor` w oparciu o `FEEDBACK_PACKET.json`; po 3 cyklach natychmiastowe zamrożenie `BLOCKED_ESCALATED` i eskalacja do człowieka/orchestratora.
13. **Zatwierdzenia operacji krytycznych:** Produkcyjne operacje deploy, migracja bazy danych, kasowanie danych, publikacja paczek, operacje finansowe wymagają odrębnego, jawnego zatwierdzenia człowieka dla konkretnej komendy.
14. **Ochrona tajemnic i PII:** Klucze API, sekrety i dane osobowe pod żadnym pozorem nie trafiają do promptów, commitów, logów ani artefaktów audytu. Logi podlegają automatycznemu redagowaniu (`redact()`).
15. **Weryfikacja skryptów instalacyjnych:** Zakaz uruchamiania nieznanych skryptów instalacyjnych bez uprzedniego audytu kodu. Shell allowlist nie stanowi pełnego sandboxa bezpieczeństwa.
16. **Uczciwe raportowanie końcowe:** Raportuj: cel, diff, faktycznie uruchomione testy, exit code, hash dowodu, zidentyfikowane ryzyka i jeden konkretny następny krok. Zakaz deklarowania "100% production ready" bez twardych dowodów.
17. **Hermetyczna Izolacja Multi-Workspace:** W monorepos i strukturach multi-project (`workspace/*`) każdy podprojekt jest ściśle odizolowanym bytem. Żaden agent, test ani narzędzie nie ma prawa dotykać, badać ani modyfikować sąsiednich podprojektów. Aktywny podprojekt musi być wyznaczony przez `tools/workspace_resolver.py`.
18. **Zero Przedwczesnego Raportowania (Anti-Premature Reporting):** Nigdy nie publikuj raportu końcowego, podsumowania prac ani statusu `✅`, dopóki subagenci działający w tle nie zakończą pracy i ich stan w `manage_subagents` nie osiągnie `idle`/`done`. Wstępny komunikat z pierwszą hipotezą to NIE jest ukończenie zadania. Zakaz stosowania pętli timerów (`schedule`) do odpytywania stanu — czekaj na reaktywne wybudzenie.

---

## 🏛️ STANDARD 7 NIEZMIENNIKÓW DREE (FEATURE ANATOMY)

Każda jednostka funkcjonalna generowana lub modyfikowana w projekcie musi bezwzględnie spełniać:
1. **Interfejs i Kontrakt:** Typowane DTO żądania i odpowiedzi (`@dataclass(frozen=True)` / `interface`).
2. **Walidacja na Granicy Wejścia:** Sprawdzenie poprawności i odrzucenie błędnych danych w `__post_init__`.
3. **Wyjątki Domenowe:** Dedykowany wyjątek domenowy (`DomainError`), brak gołych `except:`.
4. **Czysta Logika SRP:** Funkcje zwięzłe ($\le 40$ linii), deterministyczne, skupione na jednym zadaniu.
5. **Czyste Logowanie / Telemetria:** Brak zaśmiecających `console.log` i surowych `print()`.
6. **Podwójna Suita Testowa (Dual-Test Suite):** Test Happy-Path ORAZ minimum 2 testy negatywne/brzegowe.
7. **Eksport i Rejestracja SSoT:** Jawny eksport w `__all__` oraz wpis w słowniku danych `specs/03_DATA_DICTIONARY.md`.

---

## 🚦 BRAMKI JAKOŚCIOWE I DOWODOWE (G1–G7)

| Bramka | Nazwa | Narzędzie CLI | Weryfikowany Niezmiennik |
|---|---|---|---|
| **G1** | Specyfikacja & DAG | `python .governance/bin/gov.py validate` | Acykliczność grafu zadań, kompletność checklist DREE |
| **G2** | Blokada Specyfikacji | `python .governance/bin/gov.py approve-spec` | SHA-256 specyfikacji zatwierdzony przez człowieka |
| **G3** | Triple Lock Claim | `python .governance/bin/gov.py claim` | Blokada ścieżek, dzierżawa symboli AST i tras routingu API |
| **G4** | Standardy & Szablony | `python .governance/bin/gov.py check-standards` | 7 Niezmienników DREE, SRP $\le$ 40, komponenty CADRE, słownik danych |
| **G5** | Weryfikacja Dowodowa | `python .governance/bin/gov.py run` & `audit-tests` | Exit code 0, dowód w `evidence/`, test mutacyjny Mock-Breaker |
| **G5.2**| Niezależne Review | `python .governance/bin/gov.py review` | Zatwierdzenie przez niezależnego audytora/supervisora (`reviewer != actor`) |
| **G6** | Pre-Merge Interlock | `python .governance/bin/gov.py interlock --cross-worktrees` | Brak kolizji z gałęzią główną i aktywnymi worktrees |
| **G7** | Wydanie Operacyjne | `python .governance/bin/gov.py release` | 100% zadań DONE, zerowa regresja, nienaruszalny `RELEASE_MANIFEST.json` |

---

## 👥 MACIERZ RÓL SUBAGENTÓW (TRÓJWARSTWOWA HIERARCHIA MULTI-SWARM)

### Warstwa 1: Orkiestracja Globalna
- **`project-orchestrator`:** Naczelny koordynator, planowanie acyklicznego DAG, podział na bezkolizyjne fale (Execution Waves), alokacja zasobów Triple Lock, nadzór nad pulą równoległych tandemów (concurrency limit: default 2, max 3), interlock i release.

### Warstwa 2: Lokalny Nadzór Zadań i Audyt
- **`task-supervisor`:** Dedykowany nadzorca pojedynczego zadania w odizolowanym worktree `.worktrees/<task_id>`. Prowadzi pętlę naprawczą z builderem (max 3 cykle), generuje artefakt `FEEDBACK_PACKET.json`, weryfikuje DREE i Mock-Breaker oraz certyfikuje bramkę G5.2.
- **`code-auditor`:** Niezależna globalna recenzja kodu G5.2, audyt mutacyjny Mock-Breaker, analiza wektorów błędów i luk bezpieczeństwa.
- **`qa-verifier` / `qa-sentinel`:** Weryfikacja integralności SQLite, asercje regresyjne CI, testy end-to-end.

### Warstwa 3: Implementacja w Pętli (Self-Healing)
- **`builder-executor`:** Realizacja zadania w izolowanym worktree, 7 niezmienników DREE, montaż szablonów CADRE, konsumpcja wytycznych z `FEEDBACK_PACKET.json`, budżet 3 napraw. Brak uprawnień do samocertyfikacji.

### Role Dodatkowe i Architektoniczne
- **`spec-author`:** Redagowanie PRD, User Stories Gherkin, modelowanie C4, słownik danych `specs/03_DATA_DICTIONARY.md`.
- **`spec-auditor`:** Niezależny audyt specyfikacji, weryfikacja mierzalności kryteriów i checklist DREE przed bramką G2.
- **`release-integrator`:** Scalanie worktrees, Pre-Merge Cross-Interlock, generowanie Macierzy Śledzenia SSoT i certyfikacja G7.
