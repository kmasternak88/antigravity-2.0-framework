---
name: cl-inception
description: "Greenfield Idea Inception & Stress-Testing Loop dla Antigravity Ultra v8.3. Przekształca surowy pomysł w ścisłe kontrakty, konfiguruje profile standardów projektowych DREE, identyfikuje One-Way Doors i generuje acykliczny plan DAG."
version: 5.1.0
---

# /cl-inception — Greenfield Inception & Contract-First Engine

Komenda `/cl-inception` przeprowadza agenta i człowieka przez rygorystyczny, 5-fazowy proces powstawania nowego projektu, eliminując halucynacje, niespójności i dług technologiczny przed napisaniem jakiegokolwiek kodu biznesowego.

```
[Surowy Pomysł]
       ↓
(1. Idea Inception & Stress-Testing) → [Odwracalne vs Nieodwracalne Decyzje]
       ↓
(2. Contract-First Schema Engine)   → [OpenAPI / TypeSpec / DB Schema / Mocki]
       ↓
(3. DREE Standards Configuration)   → [.governance/standards.json: Profile & 7 Niezmienników]
       ↓
(4. Deterministic Slice Planner)    → [Acykliczny Graf DAG + Checklisty Standardów]
       ↓
(5. Agent Handoff Packet Synthesizer)→ [Izolowane Zadania + Scaffold-First Priming]
```

---

## 🛡️ PROTOKÓŁ KROK PO KROKU

### Krok 1: Wykrywanie One-Way Doors (Decyzje Nieodwracalne)
Framework zadaje maksymalnie **3 zwięzłe pytania** dotyczące wyłącznie decyzji nieodwracalnych:
1. **Model Danych:** Architektura danych i transakcyjność (np. relacyjna PostgreSQL vs schemaless, multi-tenancy).
2. **Autoryzacja i Integracje:** Zewnętrzne API, metody logowania, limity budżetowe.
3. **SLA i Skala:** Wymogi opóźnień, wolumen danych, środowisko wykonawcze.

> **Reguła Decyzji Odwracalnych (Two-Way Doors):** Wszystkie niekrytyczne decyzje (wybór biblioteki do logowania, kolorystyka, lintery) podejmujesz **samodzielnie** i zapisujesz w `specs/REVERSIBLE_DECISIONS.md`.

### Krok 2: Generowanie Kontraktów (`gov.py scaffold-contracts`)
Przed utworzeniem kodu biznesowego uruchom:
```powershell
python .governance/bin/gov.py scaffold-contracts
```
Spowoduje to wygenerowanie:
* `contracts/types.ts` — ścisłe interfejsy TypeScript
* `contracts/models.py` — schematy Python dataclasses/Pydantic
* `contracts/openapi.json` — specyfikacja OpenAPI 3.1 dla tras API

### Krok 3: Konfiguracja Standardów Projektowych DREE (`.governance/standards.json`)
Wybierz profil rygoru dla projektu:
* `tiny`: Szybkie prototypy, narzędzia wewnętrzne (max 60 linii).
* `standard`: Produkcyjne aplikacje webowe / serwisy (max 40 linii, pełne typowanie, dual tests).
* `critical`: Finanse, autoryzacja, healthcare (max 25 linii, restrykcyjna walidacja).

### Krok 4: Generowanie Acyklicznego Grafu Zadań (DAG)
1. Zdefiniuj atomowe zadania w `.governance/tasks.json`.
2. Każde zadanie musi posiadać:
   - `id`: Identyfikator (`T001`, `T002`, ...)
   - `depends_on`: Zależności poprzedzające
   - `allowed_paths`: Ściśle wyizolowane ścieżki zapisu
   - `checks`: Maszynowe skrypty testowe
   - `acceptance`: Mierzalne asercje
   - `standards_checklist`: Lista kryteriów standardu 7 niezmienników
3. Zweryfikuj acykliczność i checklisty standardów:
```powershell
python .governance/bin/gov.py validate
```

### Krok 5: Zablokowanie Specyfikacji (Spec Lock - Bramka G2)
Poproś człowieka o zatwierdzenie specyfikacji i zarejestruj cryptographic hash:
```powershell
python .governance/bin/gov.py spec-hash
python .governance/bin/gov.py approve-spec --actor human:owner --reference "Initial approved spec"
```
Po zablokowaniu specyfikacji uruchamiaj podagentów za pomocą `gov.py scaffold-unit` i `gov.py package-handoff`.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
