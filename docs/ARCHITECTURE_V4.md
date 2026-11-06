> [!NOTE]
> Dokumentacja historyczna wersji v4.0. Aktualna specyfikacja systemu operacyjnego agentów znajduje się w [docs/ARCHITECTURE_V5.md](ARCHITECTURE_V5.md) (Antigravity Ultra v5.1).

# DOKUMENTACJA ARCHITEKTONICZNA: ANTIGRAVITY ULTRA (v4.0)
### Pełna specyfikacja Agentic OS dla środowiska Antigravity 2.0

## 1. Wprowadzenie i Cele Architektoniczne
Antigravity Ultra v4.0 to autonomiczny system operacyjny dla zespołów agentów AI, rozwiązujący krytyczne ograniczenia modeli LLM:
* **Halucynacje i dryf kontekstu:** eliminowane przez podejście Contract-First i schematy OpenAPI/TypeScript.
* **Modyfikacje poza zakresem:** blokowane na poziomie jądra hooków przez `native_guard.py` i pakiety Handoff.
* **Niekończące się pętle błędów:** eliminowane przez 3-cyklową maszynę stanów samoleczenia z automatycznym rollbackiem i eskalacją do człowieka.
* **Regresje w kodzie produkcyjnym:** eliminowane przez deterministyczny harness Golden Master z dynamicznym maskowaniem.

---

## 2. Diagram Przepływu Greenfield (S0)
```mermaid
flowchart TD
    Idea["Surowy Pomysł Użytkownika"] --> Inception["/cl-inception: Wykrywanie One-Way Doors"]
    Inception --> HumanApproval["Zatwierdzenie 3 Decyzji Blokujących"]
    HumanApproval --> Scaffolding["gov.py scaffold-contracts: OpenAPI + TS + Pydantic"]
    Scaffolding --> DAGPlan["gov.py validate: Acykliczny Graf Zadań (DAG)"]
    DAGPlan --> SpecLock["gov.py approve-spec (Bramka G2)"]
    SpecLock --> ParallelWorkers["Wykonanie przez Subagentów z Izolacją Handoff"]
```

---

## 3. Diagram Przepływu Brownfield (S1)
```mermaid
flowchart TD
    ExistingCode["Istniejący Projekt"] --> Discovery["gov.py discover --deep: AST + Trasy + Modele"]
    Discovery --> LivingSpec["specs/RECONSTRUCTED_SPEC.md + Fragility Score"]
    LivingSpec --> GoldenRecord["gov.py golden-record: Zamrożenie Baseline Zachowań"]
    GoldenRecord --> RefactorTask["gov.py package-handoff: Izolowane Zadanie"]
    RefactorTask --> Execution["Implementacja z Native Guard allowedToWrite"]
    Execution --> GoldenAssert["gov.py golden-assert: Weryfikacja Zero-Regresji"]
    GoldenAssert --> ReviewIntegrate["Bramki G5 (Review) i G6 (Integrate)"]
```

---

## 4. Specyfikacja 3-Cyklowej Pętli Samoleczenia
```mermaid
stateDiagram-v2
    [*] --> TestFailure
    TestFailure --> Cycle1: Minimalna Reprodukcja
    Cycle1 --> Cycle2: Hipoteza i Zmiana w 1 miejscu
    Cycle2 --> Cycle3: Weryfikacja Skutków Ubocznych
    Cycle3 --> Passed: Test OK
    Passed --> [*]
    Cycle3 --> Exceeded: Błąd po 3 cyklach
    Exceeded --> Rollback: Automatyczny Rollback Plików
    Rollback --> Freeze: Stan BLOCKED w SQLite
    Freeze --> EscalationReport: Wygenerowanie ESC_T00X.md
    EscalationReport --> [*]
```

---

## 5. Standard Pakietyzacji Handoffu (JSON Schema)
Pakiet `.governance/handoffs/<task_id>.json` posiada ścisłą strukturę:
```json
{
  "taskId": "T001",
  "taskName": "Nazwa zadania",
  "specDigest": "sha256...",
  "targetFiles": {
    "readOnly": ["contracts/types.ts", ".specify/specs/02_ARCHITECTURE.md"],
    "allowedToWrite": ["src/modules/auth.ts"]
  },
  "acceptanceCriteria": [
    {
      "id": "AC-01",
      "assertion": "Warunek akceptacyjny",
      "testCommand": "python -m unittest tests/test_auth.py"
    }
  ],
  "mockContext": {
    "mockServerUrl": "http://127.0.0.1:4010",
    "governanceProfile": "standard"
  },
  "executionBudget": {
    "maxAttemptCycles": 3,
    "timeoutSeconds": 1800
  }
}
```

Wszystkie operacje zapisu są weryfikowane przez hook `native_guard.py` w czasie rzeczywistym przed dotknięciem dysku.
