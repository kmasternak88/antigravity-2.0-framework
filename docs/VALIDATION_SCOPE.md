# Co sprawdzono podczas wygenerowania paczki

1. Framework V2: odczyt23 plików projektowych i audyt w AUDIT_V2.md.
2. Oficjalne Antigravity docs: rules/hooks/subagents/skills/settings/projects odczytane przez fetch, workflows znalezione w wyszukiwaniu. Date w SOURCES.md.
3. Wykonane w Python sandbox: unit/integration selftests lokalnego gov, procesy subprocess, SQLite claims, spec invalidation, source/log hashes, review gates, hook payload fixtures i installer collision behavior.
4. Static native config check: frontmatter, names i hook schema zgodne z odczytaną dokumentacją.
5. Niewykonane: start App/CLI/IDE Antigravity, rzeczywisty native hook discovery/permissions, sandbox denial na systemie użytkownika, /boost/teamwork/browser, GitHub hosting protections, testy budowanego produktu.

Raport wykonania w TEST_RESULTS.json i TEST_RESULTS.log. Wynik testów frameworka nie jest certyfikacją produktu ani dowodem pełnej zgodności wszystkich wersji platformy. Zmiana konfiguracji/kodu wymaga ponownego testu.
