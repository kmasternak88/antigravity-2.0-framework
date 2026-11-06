# Threat model i granice gwarancji

## Aktywa

Repo kodu, secrets, dane klientów, system użytkownika, konta zewnętrzne MCP, CI release, evidence integrity, approved scope.

## Zagrożenia i kontrole

- Prompt injection przez README/issue/WWW/test logs: untrusted data policy i brak automatycznej eskalacji uprawnień.
- Shell escape przez szerokie allow python/node/npm: hook force_ask plus sandbox i najmniejsze uprawnienia; nie próbujemy parsować całego shell jako bezpiecznego AST.
- Agent modyfikuje hook/config/testy: protected governance paths, owner code review, CODEOWNERS i chronione CI. Lokalny hook sam w sobie nie jest niezależną granicą.
- Fałszywy PASS: wykonanie procesu, source/log hashes, current review, CI rerun. Lokalny autor z dostępem do DB może sfałszować wszystko; potrzebna zewnętrzna attestacja.
- Podszycie pod human/reviewer: actor labels są bookkeeping, nie auth. Critical: zewnętrzne PR review i environment approval z prawdziwymi kontami i separation of duties.
- Worktree shared resources: izolowane DB/ports/containers/secrets; brak dostępu do produkcyjnych kont.
- Secret exfiltration: nie przekazuj sekretów do kontekstu, allowlist sieci, redaction, prywatne artefakty i retencja.
- Supply chain: pin versions/digests, review install scripts, SCA/SBOM dla produktu, aktualizacje jako osobne zadania.
- Zewnętrzny MCP write: dokładny target/payload i jawna zgoda. Zatwierdzenie spec nie uprawnia do wysłania wiadomości, zakupu lub zmiany produkcyjnych danych.
- Ominięcie Git hook przez --no-verify: local hook opcjonalny pomocniczy; prawdziwa kontrola to protected server-side CI/review.

## Nie obiecujemy

Pełnego wyeliminowania błędów, matematycznej kompletności PRD, kryptograficznej tożsamości reviewerów w lokalnym SQLite, izolacji procesowej przez Git worktree ani dowodu bezpieczeństwa z screenshotów. Stop hook nie jest pętlą wymuszającą „aż do skutku”; operator zawsze może zatrzymać agenta.
