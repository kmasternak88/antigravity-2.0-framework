---
name: cl-market-discovery
description: "Autonomiczny silnik analizy rynkowej, inżynierii wstecznej konkurencji i adaptacyjnego wywiadu HITL (Context Hygiene DAG) w Antigravity Ultra v8.2+."
version: 8.2.1
---

# /cl-market-discovery — Autonomous Market Discovery & Inception Engine

Protokół deterministycznej dekonstrukcji rynku, inżynierii wstecznej rozwiązań wiodących oraz przeprowadzenia ustrukturyzowanego wywiadu z człowiekiem przed rozpoczęciem generowania kodu.

## Przepływ Pracy (Context Hygiene DAG)

```
[/init "Pomysł" --deep-discovery]
        │
        ▼
[KROK 0: Web & Competitor Deep Sweep] (Subagenty na izolowanych worktree)
        │ Output: .governance/discovery/raw_competitor_dumps.json
        ▼
[KROK 1: Matrix & Architectural Synthesis] (Kompresja faktograficzna)
        │ Output: .governance/discovery/COMPETITIVE_MATRIX.json
        ▼
[KROK 2: Adaptive HITL Interview] (Pytania oparte na zidentyfikowanych trade-offach)
        │ Wejście od użytkownika: .governance/discovery/USER_DECISIONS.json
        ▼
[KROK 3: Deterministic Blueprint & Spec Compilation]
        │ Output: specs/blueprints/system.blueprint.json (walidowany przez system.blueprint.schema.json)
        │ Output: specs/01_PRODUCT_REQUIREMENTS.md do 05_TRACEABILITY_MATRIX.md
        │ Output: contracts/ (modele domenowe, OpenAPI 3.1.0, typy TS/PHP)
        ▼
[KROK 4: Hand-off do Genesis / Builder-Executor]
```

## Wywołanie CLI

```bash
# Uruchomienie pełnego cyklu Discovery z wywiadem interaktywnym
python tools/init_project.py --target . --brief "Stwórz najlepszy plugin SEO dla wp/woo" --deep-discovery

# Uruchomienie w trybie nieinteraktywnym (CI/CD) ze z góry zdefiniowanymi decyzjami
python tools/init_project.py --target . --brief "Stwórz najlepszy plugin SEO dla wp/woo" --deep-discovery --non-interactive --decisions .governance/discovery/USER_DECISIONS.json
```

## Niezmienniki Rygoru Jakościowego (DoD)
1. Analiza minimum 3 czołowych rozwiązań rynkowych (reprezentowana w `COMPETITIVE_MATRIX.json`).
2. Sformatowana ankieta decyzyjna (5–7 pytań) z rekomendacjami i kompromisami.
3. Pełen komplet zwalidowanych artefaktów: `specs/blueprints/system.blueprint.json`, `specs/01` do `05`, kontrakty `contracts/` oraz zsynchronizowany `specs/03_DATA_DICTIONARY.md`.
4. Rejestracja punktów kontrolnych w `.governance/state/state.sqlite` w tabelach `discovery_runs` i `discovery_checkpoints`.
