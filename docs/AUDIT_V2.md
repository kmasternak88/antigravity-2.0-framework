# Audyt wejściowego frameworka V2

Przeczytano23 pliki z antigravity-v2-closed-loop-framework: README, settings/hooks,5 agents,3 rules,5 skills i7 templates. Audyt to ocena konkretnych treści, nie test w runtime Google. Źródła platformy: SOURCES.md. Nie klasyfikujemy wspieranych /boost/grill-me/goal/browser/learn jako nieistniejących.

|ID|Plik/obszar|Ustalenie|Zmiana V3|
|---|---|---|---|
|A01|rules/*.md|Brak frontmatter trigger w trzech regułach; obecna oficjalna dokumentacja opisuje ich pomijanie.|Reguły mają trigger:always_on/model_decision/glob i validator.|
|A02|hooks.json|Niezgodny schemat pre_tool_call/post_tool_call i echo bez wymuszenia.|Named definitions, PreToolUse, wejście stdin i decyzje JSON, testowane fixture.|
|A03|settings.json|Auto plus szerokie allow git/npm/npx/python/node; trzy deny nie blokują wykonania dowolnego kodu.|Brak instalowania niezweryfikowanego settings w repo; bezpieczny przykład ustawień CLI i instrukcja UI.|
|A04|agents/*.md|edit_file nie jest na odczytanej liście natywnych narzędzi; potencjalny problem walidacji tools.|Dokładne view_file/write_to_file/replace_file_content/grep_search/run_command.|
|A05|agents/*.md|Hardcoded gemini-3.5-flash, thinkingBudget i workspace we frontmatter bez potwierdzonego schematu.|model inherit/pro, brak pól niesprawdzonych; workspace branch w wywołaniu delegacji.|
|A06|skills/boost-teamwork-build|/teamwork-preview zamiast potwierdzonego /teamwork.|Feature probe i opcjonalne /teamwork, fallback sekwencyjny.|
|A07|templates/CROSS_AUDIT_REPORT.md|APPROVED i zaznaczone checkboxy przed wykonaniem oceny.|Szablony NOT_RUN, ustalenia i check refs; gate wymaga review bieżącego snapshotu.|
|A08|templates/FINAL_VERIFICATION_REPORT.md|Wpisane z góry28 PASS i production ready.|Brak syntetycznych wyników; CLI tworzy surowy dowód po procesie.|
|A09|rules/03-native-primitives-and-evidence|Nieograniczona pętla napraw i obowiązkowe browser dla API.|Budżet3 prób, HTTP integration dla API, browser dla UI, screenshot nie zastępuje asercji.|
|A10|agents/spec-auditor.md|Audytor sam poprawia spec i sam stwierdza brak luk.|Autor poprawia; reviewer ponawia odczyt nowej wersji i nie self-certifies.|
|A11|rules/01-doc-first-governance|Spec Lock to fraza w czacie bez hasha i unieważniania.|Digest plików spec, jawny approval record, zmiana spec unieważnia lock.|
|A12|rules/02-cross-auditing-and-isolation|Worktree przedstawione jako izolacja procesowa i zero context pollution.|Worktree izoluje pliki Git, nie DB, porty, sekrety, uprawnienia, shared folders.|
|A13|README i templates|Brak TTL zadań, lease fencing, state machine, idempotentnych dowodów i merge candidate gate.|SQLite lokalne claimy, states i snapshot-bound checks/review; CI weryfikuje merge candidate.|
|A14|rules/03-native-primitives-and-evidence|/learn może automatycznie zmieniać trwałe rules.|Lessons jako propozycja ADR, test regresyjny i owner review przed nową polityką.|
|A15|skills/doc-first-init|Każdy przypadek wymaga przesłuchania użytkownika i wielkiego PRD.|Tiny/standard/critical; jawne reversible assumptions, pytania tylko o blokujące decyzje.|
|A16|template roadmap|Deklaracja równoległości bez sprawdzania konfliktów plików i kontraktów.|DAG, allowed/protected path scopes, intersekcje claimów, single integrator.|

Zachowano dobre elementy V2: doc-first, cross-review, worktrees, etapowe testowanie i traceability. Zmieniono ich mechanikę i zakres gwarancji.
