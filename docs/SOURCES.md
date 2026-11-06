# Źródła i zakres weryfikacji

Data researchu: 2026-10-30. Pierwsze siedem źródeł to oficjalne materiały Antigravity; sześć stron odczytano w całości, workflows potwierdzono wynikiem wyszukiwania. Brak rzeczywistego testu w aplikacji Antigravity w tym środowisku.

- rules: https://antigravity.google/docs/rules/
  - Ustalenie: YAML trigger required; cumulative scoped rules; progressive loading.
- hooks: https://antigravity.google/docs/hooks/
  - Ustalenie: Named hook definitions; PreToolUse camelCase payload; allow/deny/force_ask; stdout JSON.
- subagents: https://antigravity.google/docs/subagents/
  - Ustalenie: tools exact names; model inherit/flash/pro; workspace selected at invocation; parent permissions inherited.
- skills: https://antigravity.google/docs/skills/
  - Ustalenie: SKILL.md name/description; workspace discovery; surface differences.
- settings: https://antigravity.google/docs/settings/
  - Ustalenie: App/CLI/IDE differences; actual sandbox availability; settings managed at documented scope.
- projects: https://antigravity.google/docs/projects/
  - Ustalenie: Git worktree isolation does not isolate non-Git mounted folders.
- workflows: https://antigravity.google/docs/ide/workflows/
  - Ustalenie: IDE workflows separate from persistent rules.
- ssdf: https://csrc.nist.gov/projects/ssdf
  - Ustalenie: Additional primary reference for implementation team; not retrieved during this audit.
- slsa: https://slsa.dev/spec/
  - Ustalenie: Additional reference; not retrieved during this audit.