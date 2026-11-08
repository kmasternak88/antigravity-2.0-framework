---
name: cl-impact
description: "Semantic AST Impact & Blast Radius Engine dla Antigravity Ultra v8.3. Oblicza drzewo wywołań, wykrywa zależności między plikami i wskazuje downstream dependents oraz wymagane testy regresyjne."
version: 5.1.0
---

# /cl-impact — Semantic AST Impact & Blast Radius Engine

Komenda `/cl-impact` pozwala agentom i deweloperom przewidzieć pełny wpływ planowanej zmiany w kodzie na cały projekt przed dotknięciem implementacji.

## Użycie CLI

### 1. Analiza wpływu pliku
```powershell
python .governance/bin/gov.py impact --file src/services/auth.py
```

### 2. Analiza wpływu konkretnego symbolu (klasy / funkcji)
```powershell
python .governance/bin/gov.py impact --symbol AuthService
```

## Wyjście Operacyjne
Polecenie zwraca ustrukturyzowany JSON z sekcjami:
* `directSymbols`: symbole zdefiniowane w pliku źródłowym
* `downstreamDependents`: lista plików w projekcie importujących lub wywołujących te symbole
* `affectedChecks`: testy i suity walidacyjne pokrywające moduły zależne
* `riskRating`: ocena ryzyka (`LOW`, `MEDIUM`, `HIGH`)

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
