# Antigravity Ultra Evidence-Driven Framework v8.3 (Omni-Agentic OS, CADRE & DREE Engine)

Kompletny system operacyjny dla autonomicznych zespołów agentów AI (**Omni-Agentic OS**) dedykowany dla środowiska **Antigravity 2.0** (oraz kompatybilny z Cursor, Claude Code, Copilot). 

Zapewnia bezbłędne wdrożenia nowych projektów (*Greenfield S0/S1*) oraz bezpieczną, inkrementalną rozbudowę systemów już działających (*Brownfield Managed S2/S3*) dzięki kryptograficznym bramkom dowodowym, atomowym pakietom handoffu, silnikowi egzekwowania reguł projektowych **DREE (Design Rule & Architectural Invariant Enforcement)**, sokratejskiemu wywiadowi **Grill-Me** oraz testom mutacyjnym **Mock-Breaker**.

---

## 🚀 Filarowe Mechanizmy Antigravity Ultra v8.2

### Filar I: Autonomiczny Potok Greenfield & Inception (`/init`, `/cl-genesis`)
* **Kognitywne Inception & Stress-Testing (`/cl-inception`):** Automatyczny podział na decyzje odwracalne (*Two-Way Doors*, podejmowane autonomicznie) oraz nieodwracalne (*One-Way Doors*, eskalowane do człowieka).
* **Multi-Agent Genesis Blueprint Compiler (`tools/genesis_compiler.py`):** Zamienia surowy pomysł lub PRD w kompletny, 7-fazowy Master Blueprint bez halucynacji.
* **Living Charter Architecture (`specs/`):** Generuje nienaruszalną, żywą dokumentację:
  * `specs/01_PRODUCT_REQUIREMENTS.md` (Wymagania PRD w składni EARS)
  * `specs/02_SYSTEM_ARCHITECTURE.md` (Architektura C4 i topologia DAG)
  * `specs/03_DATA_DICTIONARY.md` (Słownik Danych SSoT)
  * `contracts/` (Zamrożone interfejsy i modele I/O)

### Filar II: Inkrementalna Rozbudowa Aktywnych Projektów (`/extend`, `/grill-me`)
* **Sokratejski Wywiad Inżynieryjny (`/grill-me`):** Natywne pytania eliminujące dwuznaczności w modelach biznesowych, SLA, limitach SRE i interfejsach.
* **Delta Living Charter & Contract Scaffolding:** Bezpieczna rozbudowa specyfikacji bez naruszania historycznych decyzji.
* **Append-Only Kahn DAG (`tools/extend_project.py`):** Scalanie nowych zadań z istniejącym grafem `.governance/tasks.json` z zachowaniem acykliczności Kahna i sekwencyjnych identyfikatorów (`T004`, `T005`...). Blokada mutacji ukończonych zadań (`DONE_TASK_MUTATION_FORBIDDEN`).

### Filar III: DREE Engine — 7 Niezmienników Kompletnej Funkcji
Każda nowa jednostka kodu tworzona przez agentów musi bezwzględnie spełniać:
1. *Contract-First:* dane wejściowe/wyjściowe w `dataclass(frozen=True, slots=True)` lub interfejsie TS.
2. *Boundary Validation:* walidacja formatu i typów w `__post_init__`.
3. *Domain Exceptions:* dedykowany wyjątek domenowy (`DomainError`), zakaz surowego `except:`.
4. *Clean Code (SRP):* maksymalnie 40 linii kodu na funkcję.
5. *Zero Console / Telemetria:* zakaz surowych `print()` i `console.log`.
6. *Dual Test Suite:* test Happy-Path + minimum 2 testy negatywne/brzegowe.
7. *SSoT & Spec Sync:* rejestracja w `__all__` oraz aktualizacja `specs/03_DATA_DICTIONARY.md`.
* **Reguła 50 DREE (Zero Float Invariant):** Bezwzględny zakaz stosowania typów zmiennoprzecinkowych (`float`, `double`) dla operacji finansowych i walutowych — wymuszone jednostki podrzędne (`amount_cents: int`).

### Filar IV: Omni-Agentic OS & Izolacja Środowisk Roboczych
* **Hermetyczna Izolacja Multi-Workspace:** Resolver `tools/workspace_resolver.py` gwarantuje, że agenci operują wyłącznie w granicach aktywnego podprojektu.
* **Git Worktree Isolation (`gov.py worktree`):** Każdy subagent operuje w osobnym worktree, chroniąc gałąź główną przed kolizjami zapisu.
* **Semantic Blast Radius Engine (`gov.py impact`):** Analizuje drzewo wywołań AST i wyznacza moduły zależne (*downstream dependents*) oraz powiązane testy.

### Filar V: Mock-Breaker, Semantic Interlock & Operational Release
* **Anti-Tautology Mock-Breaker (`gov.py audit-tests`):** Wstrzykuje syntetyczne mutacje i weryfikuje, czy testy wykrywają usterki (eliminacja testów pozornych pisanych przez LLM).
* **Pre-Merge Semantic Interlock (`gov.py interlock`):** Weryfikuje brak kolizji symboli w AST przed scaleniem worktree do gałęzi głównej.
* **Operational Release Gate (`gov.py release`):** Generuje kryptograficznie zweryfikowany manifest `.governance/RELEASE_MANIFEST.json` potwierdzający stan `G7_PASS_OPERATIONAL_RELEASE`.

---

## 🛡️ Architektura Bramek Dowodowych (G0 - G7)

```
[G0: Discovery & Doctor] ➔ [G1/G2: Spec Validation & Lock] ➔ [G3: Claim & Worktree]
                                                                     │
[G7: Release & SSoT]   ◀─── [G6: Interlock & Merge] ◀─── [G4/G5: DREE, Tests & Review]
```

| Bramka | Nazwa | Narzędzie | Warunek Przejścia |
|:---:|:---|:---|:---|
| **G0** | Discovery & Doctor | `gov.py doctor` & `discover` | Integralność bazy sprawna, zindeksowana topologia, wygenerowany Living Charter. |
| **G1** | Spec Validation | `gov.py validate` | Acykliczny DAG, checklisty standardów DREE dla każdego zadania. |
| **G2** | Spec Lock | `gov.py approve-spec` | Kryptograficzny SHA-256 Spec Lock zatwierdzony przez operatora. |
| **G3** | Task Claim | `gov.py claim` & `worktree` | Wydany unikalny fencing token, utworzone dedykowane środowisko worktree. |
| **G4** | Evidence & DREE | `gov.py check-standards` & `run` | 0 naruszeń AST standardów 7 niezmienników, realny przebieg testów (exit code 0). |
| **G5** | Adversarial Review | `gov.py audit-tests` & `review` | Test mutacyjny Mock-Breaker zaliczony, niezależny przegląd G5 zatwierdzony. |
| **G6** | Pre-Merge Interlock | `gov.py interlock` & `worktree merge` | Brak kolizji symboli w AST, bezkonfliktowe scalenie worktree, stan zadania `DONE`. |
| **G7** | Operational Release | `gov.py release` & `trace-matrix` | 100% zadań DONE, zerowa regresja, nienaruszalny manifest `RELEASE_MANIFEST.json`. |

---

## 📦 Globalna Instalacja Turnkey

W celu jednoczesnej rejestracji wszystkich skilli, agentów, reguł i komend w ekosystemie Antigravity 2.0 uruchom:

```powershell
python install_to_antigravity.py
```

Skrypt przeprowadzi automatyczną sanityzację środowiska, usunie luźne duplikaty, zaindeksuje wtyczkę `ag-kit` i uruchomi suitę 144 testów jednostkowych i odpornościowych.

---

## 📄 Licencja

MIT License. Copyright (c) 2026 Antigravity Framework Team.
