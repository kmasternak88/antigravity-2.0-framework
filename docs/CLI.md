# CLI — kontrakt i ograniczenia

Uruchamianie: `python3 .governance/bin/gov.py --help`. CWD nie wpływa na ROOT kontrolera (wynika z jego ścieżki). Native hook command w konfiguracji nadal musi odnaleźć skrypt względem cwd środowiska.

| Komenda | Efekt |
|---|---|
| validate | config, ścieżki spec, DAG, dependencies, check argv/timeouts; nie ocenia semantyki produktu |
| doctor | validate + Python/root + jawne NOT_RUN runtime/sandbox |
| spec-hash | SHA256 zawartości spec_files + config.json + tasks.json |
| approve-spec --actor human:owner --reference URL/decision-id | lokalny zapis decyzji o aktualnym digescie; brak weryfikacji tożsamości |
| claim --task T001 --actor agent:builder --session conversationUUID | ACTIVE, TTL, nowe UUID fencing token, snapshot bazowy; dependencje muszą DONE |
| heartbeat --task T001 --token UUID | przedłuża nieprzeterminowany claim, stary token odrzucony |
| run --task T001 --check NAME | subprocess argv shell=False, timeout, log+JSON+exit, source/spec hashes |
| review --task T001 --reviewer agent:other --decision APPROVED/REJECTED --reference REPORT | wymaga aktualnych checks PASS; inny actor label |
| gate --task T001 | aktualne testy, zakres, log hash i independent review dla aktualnego snapshotu |
| finish --task T001 --token UUID | gate + aktualny lease/token →DONE |
| status | spec lock i lokalne stany; nie status całego wdrożenia |

Exit0=powodzenie CLI lub process exit0; exit1=uruchomiony check failed; exit2=odrzucony kontrakt/bramka. Check timeout ma exitCode124; test zmieniający source snapshot ma125 i jest nieważny. Log limit5MiB, nadmiar jawnie oznaczony. Known-secret redaction używa zmiennych środowiska z TOKEN/SECRET/PASSWORD/API_KEY; nie wykrywa wszystkich tajnych danych, więc użytkownik nadal nie może drukować sekretów.

Snapshot wyklucza `.git`, node_modules, caches, build/dist, coverage, e2e outputs i lokalne state/evidence. Nie jest bitowym hashem kontenera ani dowodem powtarzalnego środowiska. Wymagany lockfile i zewnętrzny CI dodają commit/tree/image/toolchain provenance. Symlinki w hashowanym źródle są odrzucane; projekt z symlinkami wymaga jawnie zaprojektowanego adaptera, nie cichego pomijania.

Task checks muszą być prawdziwymi testami. Exit0 dowodzi tylko zakończenia procesu; komenda `echo PASS` nie dowodzi spełnienia wymagania. Niezależny reviewer musi sprawdzić semantykę asercji. Konfiguracja check jest częścią spec lock.

State to lokalny SQLite w `.governance/state`, evidence w `.governance/evidence`; oba ignorowane przez Git. Nie commituj logów z sekretami. Dla durable CI publikuj przefiltrowane artefakty w kontrolowanym storage z retencją. Kopia repo nie kopiuje zaufanej tożsamości ani uprawnień.

Gate zadania wykonuj przed integracją. Późniejsza zmiana dowolnego źródła konserwatywnie unieważnia jego evidence. Po integracji uruchamiaj globalne checks w CI na candidate. Nie próbuj ponownie gateować całej historii zadań na nowym globalnym snapshotie, bo historia nie jest bieżącym dowodem release.
