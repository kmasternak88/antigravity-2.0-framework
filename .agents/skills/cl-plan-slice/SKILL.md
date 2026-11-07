---
name: cl-plan-slice
description: "Dzieli zatwierdzony zakres na małe zadania w acyklicznym grafie DAG, optymalizuje fale wykonawcze (Execution Waves) pod kątem bezkolizyjnej pracy wieloagentowej w tandemach i przydziela izolację worktree."
version: 8.3.0
---

# /cl-plan-slice — Multi-Agent Task Decomposition, Parallel Waves & DREE Invariants

Protokół dekompozycji wymagań biznesowych na atomowe plastry pionowe (*Vertical Slices*) zoptymalizowane pod kątem równoległej pracy wieloagentowej w tandemach `[task-supervisor + builder-executor]`.

## Zasady Planowania Wieloagentowego (Bramka G1)

1. **Struktura Zadania w `.governance/tasks.json`:**
   Każde zadanie `T###` musi posiadać:
   - `id`: unikalny identyfikator (np. `T001`).
   - `title`: precyzyjny opis celu biznesowego.
   - `depends_on`: lista id zadań, które muszą osiągnąć stan `DONE`.
   - `allowed_paths`: ścisłe granice zapisu dla subagenta (np. `["src/billing", "tests/billing"]`).
   - `checks`: lista checków weryfikacyjnych ze zdefiniowanym limitem timeout.
   - `acceptance`: identyfikatory kryteriów z Living Charteru (`AC-*`).
   - `risk`: profil ryzyka (`tiny`, `standard`, `critical`).
   - `standards_checklist`: **obowiązkowa niepusta lista standardów DREE** (`CONTRACT_DEFINED`, `DOMAIN_EXCEPTION_DEFINED`, `INPUT_VALIDATED`, `CLEAN_CODE_SRP`, `ZERO_CONSOLE`, `DUAL_TESTS_CREATED`, `DATA_DICTIONARY_SYNCED`).

2. **Dekompozycja na Bezkolizyjne Fale Wykonawcze (Parallel Execution Waves):**
   - Wszystkie zadania podlegają kategoryzacji do fal wykonawczych:
     $$\text{Wave } k = \{ T_i \mid \forall_{d \in \text{depends\_on}(T_i)} \; d \in \bigcup_{j < k} \text{Wave } j \}$$
   - **Twardy Warunek Zero-Overlap wewnątrz fali:**
     Dla każdych dwóch zadań $T_A, T_B$ w tej samej fali:
     $$\text{allowed\_paths}(T_A) \cap \text{allowed\_paths}(T_B) = \emptyset$$
     oraz brak nakładających się dzierżaw symboli AST w `symbol_leases`.
   - W przypadku wykrycia kolizji zasobów, zadanie $T_B$ zostaje automatycznie zepchnięte do kolejnej fali (sekwencjonowanie wymuszone bezpieczeństwem).

3. **Limit Współbieżności i Architektura Tandemów:**
   - Domyślny limit równoległości w fali wynosi **2 tandemy jednocześnie** (4 subagenci równolegle), z bezwzględnym twardym sufitem **max 3 tandemy**.
   - Każde zadanie w fali otrzymuje dedykowany worktree `.worktrees/<task_id>` oraz unikalną parę sesji `[task-supervisor, builder-executor]`.

4. **Analiza Zasięgu i Wpływu (Blast Radius):**
   - Przed sfinalizowaniem planu uruchom analizę wpływu dla każdego planowanego pliku:
     ```bash
     python .governance/bin/gov.py impact --file <path>
     ```
   - Zidentyfikuj moduły zależne i dodaj ich testy regresyjne do sprawdzanych checków zadania.

5. **Weryfikacja Determinizmu Grafu:**
   - Sprawdź acykliczność, kompletność checklist i brak cykli Kahna:
     ```bash
     python .governance/bin/gov.py validate
     ```
   - Każde naruszenie (cykl w DAG, pusta checklista standardów, brakujące checki) natychmiast blokuje przejście do Bramki G2.

Wyjście: wygenerowany, bezkolizyjny graf zadań zoptymalizowany pod wykonanie równoległe w `ParallelSwarmOrchestrator`.
