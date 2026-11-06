# Model pracy: observe → specify → build → prove → review → integrate → operate

## Zasada główna

Optymalizuj liczbę zaakceptowanych zachowań dostarczonych bez regresji, nie liczbę agentów, komend i dokumentów. Niezależny review redukuje część błędów, ale ten sam model w dwóch rolach może powtarzać ten sam błąd. Dla krytycznej domeny użyj innego recenzenta/modelu i zewnętrznych testów, a ostateczny odbiór pozostaw właścicielowi.

## Profile ryzyka

| Profil | Trigger | Minimalna spec | Weryfikacja i zgody |
|---|---|---|---|
| tiny | docs/style/local reversible change bez kontraktów i auth | cel, zakres, test, rollback | targeted checks + niezależny review; spec approval może obejmować grupę takich zadań |
| standard | nowa funkcja, integracja, API, współdzielony moduł | kontrakty, error paths, stany, DAG, acceptance | unit/integration/contracts; UI e2e gdy dotyczy; review i owner spec approval |
| critical | finanse, dane klientów, authz, migracja prod, destructive, publikacja zewnętrzna | standard + threat model, idempotency/recovery, rollout/rollback, retencja | independent security/domain reviewer, failure injection, staging, protected CI i odrębny human deployment approval |

Profil jest klasyfikacją procesu. CLI nie oceni automatycznie ryzyka domeny. Właściciel konfiguruje check commands i branch protections; zmiana profilu config unieważnia spec approval.

## Bramy

G0 Inventory: odczyt repo/źródeł i capability probe.
G1 Spec ready: mierzalne acceptance, brak niezaakceptowanych blockerów, DAG acyclic.
G2 Spec locked: człowiek zatwierdził digest spec+config+task definitions.
G3 Task active: dependencies DONE, scoped claim i aktualny fencing token.
G4 Verified: wszystkie zadaniowe checks z exit0 dla aktualnego source digest; logi istnieją i hashe zgodne.
G5 Reviewed: reviewer label różny od builder, raport dla tego samego snapshotu. W CI musi to być tożsamość zewnętrzna, nie tylko lokalny string.
G6 Integrated: merge candidate przetestowany ponownie w CI; wcześniejszy review nie dotyczy automatycznie nowego diff.
G7 Released: explicit environment approval, konkretne image/commit/migrations, rollback, postdeploy smoke.

CLI implementuje lokalne G1–G5. G0 jest procedurą discovery, G6/G7 egzekwują zewnętrzne CI/repo/environment controls. Nie przedstawiaj procedury tekstowej jako istniejącej funkcji skryptu.

## Stany lokalne

Definicja zadania bez runtime row=PENDING. Claim→ACTIVE. Finish po gate→DONE. ACTIVE po expires jest logicznie EXPIRED i może zostać przejęte z nowym tokenem. Review APPROVED/REJECTED jest odrębnym rekordem, nie automatycznym przestawieniem task state. BLOCKED/NOT_RUN zapisuj w handoff/report; kontroler nie implementuje osobnej kolejki blocked. Rejestr pochodzenia to lokalny SQLite, nie rozproszony system harmonogramowania.

## Delegacja i worktrees

Domyślnie jeden writer per checkout. Max2 builderów projektu to rekomendowany limit koordynatora, nie maxSubagentDepth w niepotwierdzonym JSON. App `invoke_subagent` dostaje Workspace branch; nie zakładamy, że YAML workspace ustawi izolację. Przy braku funkcji branch użyj manualnego worktree po review komendy Git.

Każdy worktree ma osobny runtime SQLite i evidence. Te lokalne claimy NIE synchronizują worktrees ani hostów. Koordynator rozdziela zadania centralnie, pilnuje kontraktów/lockfile i nie przydziela tego samego ID dwóm aktywnym builderom. Przy wymaganej globalnej blokadzie zastosuj zewnętrzny serwis/kolejkę — nie udawaj distributed lock przez skopiowany plik SQLite. Nie przechowuj SQLite na NFS jako substytutu serwera.

Przy wielu agentach w jednym checkout nawet rozłączne zmiany zmieniają globalny source snapshot i scope diff. Dlatego config max_parallel=1 domyślnie; równoległość uzyskujemy przez worktrees, a nie wspólny katalog z wieloma writerami.

Shared directories non-Git pozostają współdzielone. Przydziel osobne porty, DB/schema, namespace kontenerów i identyfikatory testowych kont. Worktree nie izoluje CPU/RAM, procesów ani uprawnień rodzica.

## Kontekst i budżety

Always-on ograniczamy do AGENTS i jednej krótkiej reguły. Szczegóły aktywowane na żądanie. Handoff ma linki i hashe, nie pełną historię rozmowy. Agent odczytuje kontrakty, zadanie i dotknięte callers, a przy nowym ryzyku rozszerza inventory. Nigdy nie twierdzi „przeczytałem wszystko”, jeśli odczytał fragmenty.

Budżet zadania: max3 cykle tego samego błędu, domyślnie30min pracy przed checkpoint, max2 równoległe builder sessions w projekcie. Po limitach: diagnoza, minimalna reprodukcja, wykonane próby, blokada, proponowane decyzje. Timeout procesu CLI jest twardy; budżet reasoning/cost jest polityką orkiestratora, ponieważ platformowego licznika nie implementujemy.

## Reguły testowania

Testy wynikają z zachowań i ryzyka. Unit dla pure rules, integration dla granic DB/API, contract dla klientów, e2e dla ścieżki użytkownika, fault injection dla recovery, property/concurrency dla niezmienników. Coverage to sygnał, nie dowód poprawności. Nie wymuszamy unit test obok CSS/manifestu, gdy właściwym dowodem jest build/accessibility/integration.

Nie wszystko wymaga browser. API badaj HTTP/DB tests. UI badaj Playwright i opcjonalny /browser; screenshot dowodzi wyglądu w danym momencie, nie stanu zamówienia. Nagrania nie są gwarantowane przez samą deklarację skilla.

## Mierniki

- lead time task ready→integrated;
- procent zadań first-pass bez ponownego otwierania;
- liczba escaped regressions na release;
- czas recovery i odtwarzania;
- liczba stale evidence/review odrzuconych przez gate;
- koszt/latencja delegacji i testów na zaakceptowany acceptance;
- odsetek NOT_RUN dla integracji zewnętrznych;
- liczba zmian governance bez ADR/review, cel0.

Nie przypisuj tych metryk do historii zanim faktycznie je zbierzesz.
