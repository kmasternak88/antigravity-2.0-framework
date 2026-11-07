# Raport Techniczny: Analiza Promptu Autonomous Execution Engine i Rekomendacje dla Frameworka Antigravity

**Status:** REKOMENDACJA ARCHITEKTONICZNA (RFC / ENHANCEMENT PROPOSAL)
**Wersja bazowa frameworka:** Antigravity Ultra v8.2 (Omni-Agentic OS, CADRE & DREE Engine)
**Data:** 2026-11-03
**Autor:** Principal LLMOps & Antigravity Architecture Specialist

---

## 1. Wstęp i Cel Opracowania

Niniejszy raport stanowi formalną dekompozycję oraz inżynierską analizę promptu systemowego:
`[SYSTEM INSTRUCTION: AUTONOMOUS EXECUTION ENGINE] (Google Antigravity 2.0 Integration)`.

### Główny cel biznesowo-techniczny
Umożliwienie **całkowicie deterministycznej transpilacji abstrakcyjnego konceptu biznesowego (surowego pomysłu użytkownika) w działający, zweryfikowany i gotowy do wdrożenia projekt programistyczny**, przy:
1. **Maksymalnej redukcji halucynacji** agentów AI (zasada Evidence-First i Zero-Tautology),
2. **Proaktywnym przewidywaniu potrzeb użytkownika** (autonomiczne domykanie brakujących wymagań domenowych bez konieczności ciągłego dopytywania o drobiazgi),
3. **Bezinwazyjności wdrożenia** – zachowaniu istniejących, sprawdzonych fundamentów Antigravity Ultra v8.2 (bramki G0–G7, silnik DREE, Living Charter w `specs/`, izolacja Git Worktree, stan SSoT w SQLite) i wzbogaceniu ich jedynie o te mechanizmy, które wnoszą realną wartość.

---

## 2. Analiza Porównawcza: Co już posiadamy vs Co wnosi Prompt

| Obszar / Krok z Promptu | Stan obecny w Antigravity Ultra v8.2 | Propozycja z Promptu | Ocena i Rekomendacja |
|---|---|---|---|
| **Krok A-01: Agent Blueprint & Linter** | Mamy `tools/genesis_compiler.py` z linterem `lint_zero_placeholders` i walidacją faz 1–7. | Wymóg lintera pre-save w hooku edytora oraz fallback do `.agents/history/`. | **WDROŻYĆ (Adaptacja):** Dodać hook/kopię migawkową do `.agents/history/` przy kompilacji blueprintu. Zabezpiecza przed utratą kontekstu przy błędzie składni. |
| **Krok A-02: Rusztowanie katalogów** | Mamy `tools/init_project.py` i `genesis_compiler.py`, tworzące `specs/`, `contracts/`, `.governance/`. | Tworzenie `.agents/agents/` i `.agents/skills/`. | **JUŻ POSIADAMY:** Drzewo `.agents/` jest standardem w repozytorium. |
| **Krok A-03: Model Selection & Thinking Level** | Modele są przypisane domyślnie w agentach `.agents/agents/*.md`. | Jawny parametr `thinking_level: High/Max` (Argon) dla Orchestratora i Gemini Flash dla workerów. | **WDROŻYĆ (Lekkie):** Dodanie krotki metadanych `thinking_level` w nagłówkach agentów i `.governance/config.json`. |
| **Krok A-04: Guardrails (PII & Injection)** | Reguła 14 w `AGENTS.md` (zakaz PII, maskowanie sekretów, Zero-Trust). | Wstrzykiwanie filtrów regex i odrzucanie prompt-injection. | **JUŻ POSIADAMY / UTRZYMAĆ:** Posiadamy reguły w `.agents/rules/40-security-and-tools.md`. |
| **Krok A-05: Subagenci i Git Worktrees** | Pełne wsparcie: `gov.py worktree`, `gov.py claim`, fencing tokeny, zasada 1 writer na plik. | Podział MECE, osobne Git Worktrees dla podagentów. | **PEŁNA ZGODNOŚĆ:** Jeden z filarów v8.2. |
| **Krok A-06: Pakiety Skills (`SKILL.md` + `/scripts`)** | Skille w `.agents/skills/*/SKILL.md` z procedurami i wywołaniami CLI. | Sformalizowany kontrakt pól `SKILL.md`: Description, Input Schema, Output Schema, scripts/. | **WDROŻYĆ (Standaryzacja):** Ujednolicić kontrakt metadanych `SKILL.md` z jawnym schematem wejścia/wyjścia JSON. |
| **Krok A-07: Odporność MCP (Timeout 3s + Mock Fallback)** | Narzędzia wywoływane lokalnie przez CLI/Python. Brak formalnego kontraktu degradacji MCP. | HTTP Timeout = 3000ms, serwer MCP przełącza się w `Degraded Local Mode` (statyczne makiety). | **BARDZO WARTO WDROŻYĆ:** Kluczowe dla determinizmu. Zapobiega wiszeniu agentów na zewnętrznych API. |
| **Krok A-08: Structured Output Enforcement** | DREE Niezmiennik 1: `dataclass(frozen=True)` i interfejsy TS. Brak wymuszenia biblioteką runtime Pydantic/Instructor. | Wymuszenie Pydantic/Instructor na wyjściu modeli LLM. | **WDROŻYĆ (Doprecyzowanie):** Generator kontraktów Pydantic dla operacji LLM/agentowych w `contracts/`. |
| **Krok A-09: Implementation Plan Artifact** | Living Charter (`specs/01..07_*.md`) oraz `tasks.json` z macierzą śledzenia. | Bogaty wizualnie artefakt w kartach podglądu Antigravity. | **ZGODNE:** Living Charter pełni rolę SSoT. |
| **Krok A-10: Stan i sesja (Redis vs SQLite)** | Stan zarządzany hermetycznie w lokalnym `.governance/state/state.sqlite` (transakcje ACID, blokady). | Wymóg Redis z SLA < 5ms dla rozproszonych blokad i sesji. | **ODRZUCIĆ / ADAPTOWAĆ JAKO OPCJĘ:** Zastąpienie SQLite Redisem zniszczyłoby offline-first i prostotę frameworka. SQLite w trybie WAL w zupełności spełnia SLA < 2ms lokalnie. Redis dopuszczalny tylko jako opcjonalny adapter chmurowy. |
| **Krok A-11: Pętla LLM-as-a-Judge (Ragas/Phoenix)** | Mock-Breaker (`gov.py audit-tests`), testy mutacyjne, zasada podwójnej suity testowej. | Ewaluacja jakości odpowiedzi (Correctness, Faithfulness, Context Precision $\ge 0.90$) + pętla strojenia promptów (Prompt Tuning Loop z negatywnymi przykładami). | **BARDZO WARTO WDROŻYĆ:** Automatyczna pętla wstrzykiwania negatywnych przykładów (Few-Shot Failure Injection) po wykryciu halucynacji/błędu testu. |
| **Krok A-12 & A-13: CI/CD i Serverless Push** | `tools/ci_checks.py`, manifest wydania `RELEASE_MANIFEST.json` w bramce G7. | Automatyczny push do repozytorium i serverless deploy. | **ZACHOWAĆ OBOSTRZENIA:** Zgodnie z Regułą 13 AGENTS.md, operacje deploy/push wymagają świadomej autoryzacji człowieka. |

---

## 3. Wyselekcjonowane Krotki i Logiki do Bezinwazyjnego Wdrożenia

Wybrano 4 kluczowe ulepszenia, które **nie burzą istniejącego przepływu zadań (DAG)**, ale bezpośrednio podnoszą autonomię i odporność agentów na halucynacje.

---

### Ulepszenie 1: Pętla Ewaluacyjna LLM-as-a-Judge oraz Samonaprawa Promptów (Few-Shot Negative Injection)

#### 1. Logika Biznesowa i Matematyczna (Prompt Tuning Loop)
Gdy agent generuje kod lub plan, a testy mutacyjne (Mock-Breaker) lub bramka G4/G5 zwrócą błąd, zamiast generycznego "napraw to", silnik oblicza wskaźniki ewaluacyjne i rejestruje krotkę negatywną. Jeżeli wskaźnik semantyczny spadnie poniżej progu ($0.90$), wygenerowany przypadek błędu jest automatycznie transpilowany do reguły **"Czego NIE robić" (Negative Example)** i wstrzykiwany do kontekstu agenta wykonawczego.

#### 2. Krotka Danych / Schemat Kontraktu (Pydantic / TypedDict)
```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal

@dataclass(frozen=True, slots=True)
class EvaluationMetricTuple:
    """Krotka metryk jakościowych LLM-as-a-Judge (skala 0.0 - 1.0)."""
    correctness: float       # Poprawność faktograficzna / zgodność ze specyfikacją
    faithfulness: float      # Brak halucynacji względem dostarczonego kontekstu
    context_precision: float # Relewantność wyciągniętych informacji
    threshold: float = 0.90  # Twardy próg zaliczenia DoD

    @property
    def is_passing(self) -> bool:
        return (
            self.correctness >= self.threshold and
            self.faithfulness >= self.threshold and
            self.context_precision >= self.threshold
        )

@dataclass(frozen=True, slots=True)
class NegativeFewShotExample:
    """Krotka negatywnego przykładu wstrzykiwanego do kontekstu po porażce."""
    failure_id: str
    task_id: str
    failing_input: str
    hallucinated_or_flawed_output: str
    root_cause_analysis: str
    explicit_anti_rule: str  # Np. "NIGDY nie używaj typu float w polach kwotowych"
    timestamp_utc: str
```

#### 3. Algorytm Logiki Wykonawczej
```
JEŚLI wynik testu zadania == FAIL LUB evaluation_metrics.is_passing == FALSE:
    1. Wyodrębnij minimalną różnicę (diff) błędu oraz zidentyfikowaną halucynację.
    2. Sformatuj krotkę NegativeFewShotExample.
    3. Zapisz krotkę do pliku .governance/evidence/tuning/{task_id}_failure.json.
    4. Wstrzyknij sekcję:
       "### UWAGA: POPRZEDNI BŁĄD (NEGATIVE CONSTRAINT):
        Wejście: {failing_input}
        Błędne wyjście: {flawed_output}
        ZAKAZ: {explicit_anti_rule}"
       do pliku tymczasowego kontekstu subagenta builder-executor.
    5. Zwiększ licznik prób (maksymalnie 3 cykle self-healingu zgodnie z Regułą 12).
```

---

### Ulepszenie 2: Odporność Narzędzi MCP – Limit Czasu (3000ms) i Automatyczna Degradacja do Makiet (Degraded Local Mode)

#### 1. Uzasadnienie
Jednym z głównych powodów zawieszania się agentów autonomicznych jest brak odpowiedzi z zewnętrznych serwerów MCP (narzędzi bazodanowych, zewnętrznych API, systemów wyszukiwania). Wprowadzenie deterministycznego przełącznika na lokalne makiety gwarantuje, że proces budowy projektu nigdy nie zablokuje się z powodu awarii sieci.

#### 2. Krotka Konfiguracyjna Serwera MCP (`mcp-resilience-schema.json`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MCPResiliencePolicy",
  "type": "object",
  "properties": {
    "server_name": { "type": "string" },
    "timeout_ms": { "type": "integer", "default": 3000 },
    "retry_count": { "type": "integer", "default": 1 },
    "degraded_fallback_mode": {
      "type": "string",
      "enum": ["STATIC_MOCK", "LOCAL_CACHE", "FAIL_FAST_ABORT"],
      "default": "STATIC_MOCK"
    },
    "mock_payload_path": { "type": "string" }
  },
  "required": ["server_name", "timeout_ms", "degraded_fallback_mode"]
}
```

#### 3. Logika Działania (Fallback Orchestration)
```python
def execute_mcp_call(tool_name: str, payload: dict, policy: MCPResiliencePolicy) -> dict:
    try:
        # Twardy timeout 3000ms na poziomie socketu/procesu
        return call_remote_mcp(tool_name, payload, timeout=policy.timeout_ms / 1000.0)
    except (TimeoutError, ConnectionError) as exc:
        if policy.degraded_fallback_mode == "STATIC_MOCK":
            log_warning(f"MCP server '{policy.server_name}' timed out (>3000ms). Falling back to Degraded Local Mode.")
            return load_static_mock_fixture(policy.mock_payload_path, tool_name)
        raise exc
```

---

### Ulepszenie 3: Pre-Save Blueprint Linter z Historią Migawek (`.agents/history/`)

#### 1. Uzasadnienie
Krok A-01 i Mitygacja A-01 słusznie zauważają, że błędy składniowe w generowanym pliku blueprintu/manifestu potrafią uszkodzić cały stan projektu. Nasz `genesis_compiler.py` doskonale waliduje niezmienniki, ale warto dodać mechanizm automatycznego zapisu migawki przed kompilacją oraz przywracania ostatniej znanej poprawnej wersji w przypadku błędu.

#### 2. Krotka Stanu Migawki (Snapshot Manifest)
```python
@dataclass(frozen=True, slots=True)
class BlueprintSnapshot:
    snapshot_id: str         # Np. "SNAP-20261103-143000-A01"
    source_file: str         # "specs/00_MASTER_BLUEPRINT.md"
    content_sha256: str      # Hash zawartości
    is_valid_dag: bool       # Czy przeszło validate_dag_acyclic
    backup_path: str         # ".agents/history/00_MASTER_BLUEPRINT.md.{timestamp}.bak"
    created_at: str
```

#### 3. Logika Rollbacku (Krok A-01 Mitygacja)
1. Przed zapisaniem lub nadpisaniem pliku blueprintu, bieżący plik jest kopiowany do `.agents/history/`.
2. Uruchamiany jest parser i linter faz (`lint_zero_placeholders`, `validate_dag_acyclic`).
3. W przypadku rzucenia wyjątku (`ValueError`):
   - Błąd jest logowany do raportu,
   - Stan w `specs/` jest automatycznie przywracany z `.agents/history/`,
   - Agent otrzymuje precyzyjny raport błędu z numerem linii bez uszkadzania drzewa roboczego.

---

### Ulepszenie 4: Standaryzacja Kontraktu Narzędzi Agenta (`SKILL.md`)

#### 1. Uzasadnienie
W celu uniknięcia halucynacji dotyczących dostępnych parametrów narzędzi, każdy pakiet w `.agents/skills/` powinien posiadać zwalidowany blok Frontmatter / Schema definiujący dokładne wejście i wyjście.

#### 2. Krotka Metadanych Umiejętności (Skill Metadata Tuple)
```yaml
---
name: "db_query_executor"
version: "1.1.0"
description: "Deterministyczne odpytywanie bazy SQLite w trybie tylko do odczytu z limitem 100 rekordów."
thinking_level: "High"
timeout_ms: 3000
input_schema:
  type: "object"
  required: ["query", "database_path"]
  properties:
    query: { "type": "string", "pattern": "^SELECT\\b" }
    database_path: { "type": "string" }
output_schema:
  type: "object"
  required: ["row_count", "rows", "execution_time_ms"]
  properties:
    row_count: { "type": "integer" }
    rows: { "type": "array" }
    execution_time_ms: { "type": "number" }
executable: "scripts/run.py"
---
```

---

## 4. Czego ŚWIADOMIE NIE Wdrażamy i Dlaczego (Anti-Patterns)

1. **Wymóg klastra Redis jako warunku sine-qua-non (Krok A-10):**
   - *Dlaczego odrzucamy:* Wymóg zewnętrznego serwera Redis w każdym lokalnym środowisku programisty narusza zasadę hermetyczności i działania bez zbędnej konfiguracji (*zero friction*). Nasz silnik oparty o bazę SQLite w `.governance/state/state.sqlite` z trybem WAL w środowisku lokalnym oferuje latencję rzędu mikrosekund (< 1ms) i pełną atomowość transakcji ACID. Redis powinien pozostać jedynie opcją konfiguracyjną dla wdrożeń chmurowych.

2. **Pominięcie Sokratejskiego Wywiadu (Grill-Me / Inception):**
   - *Dlaczego modyfikujemy:* W dostarczonym prompcie agent natychmiast przechodzi od pomysłu do generowania planu (Krok A-01), co przy lakonicznych zapytaniach prowadzi do halucynowania brakujących założeń biznesowych. W naszym podejściu zachowujemy mechanizm wyliczania wskaźnika **IMS (Input Maturity Score)**: jeśli pomysł jest lakoniczny (RAW_SEED), agent autonomicznie stosuje standardowe profile architektoniczne (ADR), a w przypadku wątpliwości kluczowych zadaje maksymalnie 3 pytania o decyzje nieodwracalne (*One-Way Doors*).

3. **Niekontrolowany push na produkcję i do Git bez bramki człowieka (Krok A-13):**
   - *Dlaczego odrzucamy:* Zgodnie z kardynalną regułą 13 `AGENTS.md`, operacje deployu i migracji produkcyjnych wymagają jawnego potwierdzenia operatora. Agent przygotowuje paczkę wydania (bramka G7) i manifest weryfikacyjny, ale nie wykonuje ślepego pusha.

---

## 5. Podsumowanie i Rekomendowany Plan Działań

Wdrożenie powyższych 4 logik pozwoli na:
- **0 wiszących procesów** dzięki timeoutom 3000ms i degradacji MCP do statycznych makiet,
- **Brak regresji i halucynacji** dzięki weryfikacji metryk $\ge 0.90$ i wstrzykiwaniu negatywnych przykładów w pętli Prompt Tuning,
- **Odporność na błędy składni** dzięki automatycznym migawkom `.agents/history/`,
- **Pełną zgodność z filozofią Antigravity Ultra v8.2** bez konieczności rewolucji i przebudowy sprawdzonych komponentów.
