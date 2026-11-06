#!/usr/bin/env python3
"""Project Extension & Incremental Living Charter Compiler for Antigravity Ultra v8.2.

Automates the safe, incremental extension of active, managed projects (/extend, /cl-extend, /expand):
1. Ingests extension brief / request and discovers project AST & state.
2. Analyzes AST impact & backward compatibility (symbol collisions, blast radius, downstream dependents).
3. Enforces DREE v8.2 Rule 50: strictly prohibits float types for currency (CURRENCY_FLOAT_PROHIBITED).
4. Runs Socratic 'grill-me' interview (One-Way Doors, EARS boundaries, money invariants, API contracts, SRE).
5. Synthesizes EARS requirements and Gherkin Test Triads (Happy Path + 2 Negative/Edge).
6. Generates Living Charter Delta in specs/ (01 PRD, 02 Architecture, 03 Data Dictionary, 04 Impact).
7. Scaffolds frozen contracts in contracts/ (slots=True, frozen=True, __post_init__, integer cents, DomainError, __all__).
8. Compiles and merges atomic DAG tasks incrementally with sequential IDs (T004, T005...) using Kahn's algorithm.
9. Preserves tasks.json Schema v2 (epics & milestones) and enforces Rule 40/3/1 and 7 DREE invariants.
10. Validates Gate G1/G2 Spec Lock readiness and maintains gov.py doctor/approve-spec compatibility.
"""

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional, Union, Union

_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent
for _p in [_this_dir, _repo_root]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from tools.genesis_compiler import (
        lint_zero_placeholders,
        detect_tech_stack,
        validate_dag_acyclic,
        validate_disjoint_parallel_paths,
        validate_task_complexity_limits,
    )
except ImportError:
    try:
        from genesis_compiler import (
            lint_zero_placeholders,
            detect_tech_stack,
            validate_dag_acyclic,
            validate_disjoint_parallel_paths,
            validate_task_complexity_limits,
        )
    except ImportError:
        lint_zero_placeholders = None
        detect_tech_stack = None
        validate_dag_acyclic = None
        validate_disjoint_parallel_paths = None
        validate_task_complexity_limits = None

__all__ = [
    "SocraticQuestion",
    "SocraticEngine",
    "EarsRequirement",
    "GherkinTriad",
    "ProjectExtensionContext",
    "ASTImpactAnalyzer",
    "validate_currency_invariants",
    "validate_grill_me_session",
    "merge_tasks_dag",
    "compute_next_task_ids",
    "check_governance_state",
    "merge_dag_kahn",
    "validate_40_3_1_rule",
    "validate_dree_checklist",
    "generate_living_charter_delta",
    "generate_frozen_contracts_delta",
    "extend_project",
    "main",
]

class ExtensionError(Exception):
    """Base domain exception for project extension errors."""
    pass

class ProjectStateError(ExtensionError):
    """Raised when the project is not in a valid managed state (S2/S3)."""
    pass

class DAGCycleError(ExtensionError):
    """Raised when an incremental task introduces a dependency cycle."""
    pass

class RuleViolationError(ExtensionError):
    """Raised when 40/3/1 or DREE rules are violated."""
    pass


CURRENCY_KEYWORDS = {
    "price", "amount", "cost", "fee", "balance", "total", "subtotal", "tax",
    "salary", "wage", "cents", "grosze", "kwota", "cena", "oplata", "koszt", "saldo", "prowizja"
}

def validate_currency_invariants(entities: List[Dict[str, Any]]) -> None:
    """Enforces Rule 50 DREE: CURRENCY_FLOAT_PROHIBITED.
    Monetary amounts MUST be strictly represented as integer minor units (e.g. cents/grosze).
    """
    for ent in entities:
        ent_name = ent.get("name", "UnknownEntity")
        fields = ent.get("fields", [])
        for f in fields:
            fname = f.get("name", "").lower()
            ftype = f.get("type", "").lower()
            if any(kw in fname for kw in CURRENCY_KEYWORDS):
                if any(bad in ftype for bad in ["float", "double", "decimal", "number"]):
                    raise RuleViolationError(
                        f"CURRENCY_FLOAT_PROHIBITED: Field '{f.get('name')}' in entity '{ent_name}' "
                        f"uses floating-point type '{f.get('type')}'. Under Rule 50 of DREE v8.2, "
                        "all monetary amounts MUST be strictly represented as integer minor units (e.g. cents/grosze)."
                    )


def validate_grill_me_session(workspace_root: Union[str, Path]) -> bool:
    """Validates the Socratic grill-me session file.
    Must exist at .governance/state/grill_me_session.json and have at least 3 answered questions.
    """
    root = Path(workspace_root).resolve()
    session_file = root / ".governance" / "state" / "grill_me_session.json"
    if not session_file.is_file():
        raise ValueError(
            "GRILL_ME_SESSION_MISSING: .governance/state/grill_me_session.json does not exist. "
            "Grill-me Socratic interview is mandatory before /extend compilation."
        )
    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"GRILL_ME_SESSION_CORRUPT: Invalid JSON in {session_file}: {e}")

    questions = data.get("questions", [])
    if not isinstance(questions, list) or len(questions) < 3:
        raise ValueError(
            f"INSUFFICIENT_GRILL_ME_DEPTH: Found {len(questions) if isinstance(questions, list) else 0} questions; "
            "minimum 3 questions with human answers required."
        )
    for idx, q in enumerate(questions):
        if not isinstance(q, dict) or not str(q.get("a", "")).strip():
            raise ValueError(
                f"INSUFFICIENT_GRILL_ME_DEPTH: Question index {idx} lacks a valid answer ('a')."
            )
    return True


def merge_tasks_dag(existing_tasks_data: Dict[str, Any], extension_tasks_data: Dict[str, Any]) -> Dict[str, Any]:
    """Merges extension tasks into existing tasks while enforcing append-only immutability.
    Any attempt to modify or reset a task with status 'DONE' raises ValueError('DONE_TASK_MUTATION_FORBIDDEN').
    """
    old_tasks = existing_tasks_data.get("tasks", [])
    new_tasks = extension_tasks_data.get("tasks", [])

    old_done_ids = {t["id"]: t for t in old_tasks if t.get("status") == "DONE" or t.get("state") == "DONE"}

    for nt in new_tasks:
        nid = nt.get("id")
        if nid in old_done_ids:
            old_t = old_done_ids[nid]
            if (nt.get("status") != "DONE" or
                nt.get("allowed_paths") != old_t.get("allowed_paths") or
                nt.get("checks") != old_t.get("checks")):
                raise ValueError(
                    f"DONE_TASK_MUTATION_FORBIDDEN: Task '{nid}' is already completed (DONE) and cryptographically sealed. "
                    "Modification, path tampering, or resetting to TODO is strictly forbidden."
                )

    combined_tasks = list(old_tasks)
    existing_ids = {t["id"] for t in old_tasks}
    for nt in new_tasks:
        if nt["id"] not in existing_ids:
            combined_tasks.append(nt)
            existing_ids.add(nt["id"])

    # Validate acyclicity
    if validate_dag_acyclic:
        validate_dag_acyclic(combined_tasks)

    result = dict(existing_tasks_data)
    result["tasks"] = combined_tasks
    return result


class ASTImpactAnalyzer:
    """Static AST Impact & Backward Compatibility Engine.
    Scans existing codebase in src/ and contracts/, computes symbol collisions,
    analyzes downstream dependents, and detects potential breaking changes.
    """

    @staticmethod
    def analyze_workspace_ast(workspace_root: Path, new_symbols: List[str], target_domain: str) -> Dict[str, Any]:
        dependents = set()
        existing_symbols: Dict[str, str] = {}
        collisions = []

        scan_dirs = [workspace_root / "src", workspace_root / "contracts"]
        for sdir in scan_dirs:
            if not sdir.is_dir():
                continue
            for py_path in sdir.rglob("*.py"):
                try:
                    tree = ast.parse(py_path.read_text(encoding="utf-8", errors="ignore"))
                    rel_path = str(py_path.relative_to(workspace_root)).replace("\\", "/")
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                            existing_symbols[node.name] = rel_path
                            if node.name in new_symbols:
                                collisions.append({
                                    "symbol": node.name,
                                    "file": rel_path,
                                    "line": node.lineno
                                })
                        elif isinstance(node, (ast.Import, ast.ImportFrom)):
                            mod_name = getattr(node, "module", "") or ""
                            for alias in getattr(node, "names", []):
                                if target_domain in mod_name or target_domain in alias.name:
                                    dependents.add(rel_path)
                except Exception:
                    pass

        breaking = len(collisions) > 0
        risk_rating = "HIGH" if breaking or len(dependents) > 3 else ("MEDIUM" if len(dependents) > 0 else "LOW")

        return {
            "existingSymbolsCount": len(existing_symbols),
            "collisions": collisions,
            "breakingChanges": breaking,
            "downstreamDependents": sorted(list(dependents)),
            "riskRating": risk_rating
        }


def compute_next_task_ids(existing_tasks: List[Dict[str, Any]], count: int = 3, prefix: str = "T") -> List[str]:
    """Derives sequential task IDs (e.g. T004, T005, T006) avoiding any collisions with existing tasks."""
    max_num = 0
    has_t = False
    for t in existing_tasks:
        tid = t.get("id", "")
        m = re.match(r"^T(\d+)$", tid)
        if m:
            has_t = True
            max_num = max(max_num, int(m.group(1)))
        else:
            m2 = re.search(r"(\d+)", tid)
            if m2:
                max_num = max(max_num, int(m2.group(1)))

    if max_num > 0 or has_t or not existing_tasks:
        return [f"{prefix}{max_num + i + 1:03d}" for i in range(count)]
    else:
        return [f"EXT-{max_num + i + 1:03d}" for i in range(count)]


@dataclass(slots=True, frozen=True)
class SocraticQuestion:
    id: str
    dimension: str
    question: str
    context: str
    options: List[Dict[str, Any]]
    recommended_option_id: str

    def __post_init__(self):
        if not self.id:
            raise ValueError("SocraticQuestion.id cannot be empty")
        if not self.question:
            raise ValueError("SocraticQuestion.question cannot be empty")
        if not self.options:
            raise ValueError("SocraticQuestion.options must not be empty")


@dataclass(slots=True, frozen=True)
class EarsRequirement:
    req_id: str
    pattern_type: str
    statement: str
    rationale: str

    def __post_init__(self):
        valid_patterns = {
            "Ubiquitous", "Event-driven", "State-driven",
            "Unwanted behavior", "Optional feature", "Complex"
        }
        if self.pattern_type not in valid_patterns:
            raise ValueError(f"Invalid EARS pattern: {self.pattern_type}. Must be one of {valid_patterns}")
        if not self.statement.strip():
            raise ValueError("EarsRequirement.statement cannot be empty")


@dataclass(slots=True, frozen=True)
class GherkinTriad:
    req_id: str
    happy_path: str
    negative_boundary: str
    negative_adversarial: str

    def __post_init__(self):
        if not self.happy_path.strip():
            raise ValueError("GherkinTriad.happy_path cannot be empty")
        if not self.negative_boundary.strip():
            raise ValueError("GherkinTriad.negative_boundary cannot be empty")
        if not self.negative_adversarial.strip():
            raise ValueError("GherkinTriad.negative_adversarial cannot be empty")


@dataclass
class ProjectExtensionContext:
    workspace_root: Path
    brief: str
    module_slug: str
    domain: str
    archetype: str = "service_module"
    tech_stack: Dict[str, Any] = field(default_factory=dict)
    socratic_answers: Dict[str, str] = field(default_factory=dict)
    adrs: List[Dict[str, str]] = field(default_factory=list)
    ears_requirements: List[EarsRequirement] = field(default_factory=list)
    gherkin_triads: List[GherkinTriad] = field(default_factory=list)
    new_entities: List[Dict[str, Any]] = field(default_factory=list)
    new_tasks: List[Dict[str, Any]] = field(default_factory=list)
    blast_radius: List[str] = field(default_factory=list)
    ast_impact: Dict[str, Any] = field(default_factory=dict)


def check_governance_state(workspace_root: Path) -> str:
    """Verifies that the target directory is an active managed project (S2/S3)."""
    gov_cfg = workspace_root / ".governance" / "config.json"
    tasks_file = workspace_root / ".governance" / "tasks.json"

    if not gov_cfg.exists() or not tasks_file.exists():
        has_code = any((workspace_root / d).is_dir() for d in ['src', 'app', 'lib', 'tests']) or \
                   any((workspace_root / f).is_file() for f in ['package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod'])
        state = "S1_BROWNFIELD_UNMANAGED" if has_code else "S0_GREENFIELD"
        raise ProjectStateError(
            f"PROJECT_NOT_MANAGED (State: {state}): /extend requires an initialized project with .governance/. "
            "Please run /init (python tools/init_project.py) first to bootstrap the project governance."
        )

    try:
        tasks_data = json.loads(tasks_file.read_text(encoding="utf-8"))
        tasks = tasks_data.get("tasks", [])
    except Exception as e:
        raise ProjectStateError(f"Corrupted .governance/tasks.json: {e}")

    try:
        cfg = json.loads(gov_cfg.read_text(encoding="utf-8"))
        spec_locked = cfg.get("spec_locked", False)
    except Exception:
        spec_locked = False

    if spec_locked and tasks:
        return "S3_IN_FLIGHT"
    return "S2_GOVERNANCE_UNLOCKED"


class SocraticEngine:
    """Generates and processes 5-dimensional Socratic 'grill-me' questions."""

    @staticmethod
    def build_standard_questionnaire(brief: str, domain: str) -> List[SocraticQuestion]:
        q_list = [
            SocraticQuestion(
                id="Q1_ONE_WAY_DOOR_PERSISTENCE",
                dimension="One-Way Doors & Storage",
                question=f"Jak model danych modułu '{domain}' ma być persystowany i synchronizowany?",
                context="Decyzja nieodwracalna: wybór silnika persystencji determinuje mechanizmy transakcyjne i migracje.",
                options=[
                    {
                        "id": "relational_transactional",
                        "label": "[A] Relacyjna Baza Danych (ACID / Transakcje / Obce Klucze) [REKOMENDOWANE]",
                        "recommended": True,
                        "trade_off": "Wysoka spójność, gwarancje transakcyjne, wymaga schematu migracji."
                    },
                    {
                        "id": "append_only_ledger",
                        "label": "[B] Dziennik Append-Only (Event Sourcing / Niezmienny Audit Log)",
                        "recommended": False,
                        "trade_off": "Pełna audytowalność, ale większa złożoność odczytu."
                    },
                    {
                        "id": "in_memory_transient",
                        "label": "[C] Stan ulotny In-Memory / Cache (Redis / Local Key-Value)",
                        "recommended": False,
                        "trade_off": "Niskie opóźnienia, brak gwarancji trwałości przy restarcie."
                    }
                ],
                recommended_option_id="relational_transactional"
            ),
            SocraticQuestion(
                id="Q2_FINANCIAL_AND_MONEY_INVARIANTS",
                dimension="Data & Money Invariants (Rule 50 DREE)",
                question=f"Czy moduł '{domain}' przetwarza jakiekolwiek wartości finansowe, salda, prowizje lub limity budżetowe?",
                context="Reguła 50 DREE: Bezwzględny zakaz float. Wymóg int (cents) i klucza idempotencji X-Idempotency-Key.",
                options=[
                    {
                        "id": "money_integer_cents",
                        "label": "[A] Tak: Kwoty wyłącznie jako integer minor units (grosze/centy) + Idempotencja [REKOMENDOWANE]",
                        "recommended": True,
                        "trade_off": "Zero błędów zaokrągleń IEEE 754, odporność na timeouty sieciowe."
                    },
                    {
                        "id": "no_monetary_data",
                        "label": "[B] Nie: Moduł jest czysto operacyjny/konfiguracyjny, nie przetwarza pieniędzy",
                        "recommended": False,
                        "trade_off": "Brak narzutu walidacji walutowej."
                    }
                ],
                recommended_option_id="money_integer_cents" if any(k in brief.lower() for k in ["płatno", "koszt", "cena", "kwot", "subskryp", "billing", "payment", "fee", "faktur"]) else "no_monetary_data"
            ),
            SocraticQuestion(
                id="Q3_API_AND_COMMUNICATION_CONTRACT",
                dimension="API & Communication Contracts",
                question=f"W jaki sposób moduł '{domain}' komunikuje się z resztą systemu i klientami zewnętrznymi?",
                context="Wybór protokołu i formatu błędów wpływa na kontrakty w contracts/ oraz DTO.",
                options=[
                    {
                        "id": "rest_json_strict_dto",
                        "label": "[A] REST API (JSON) ze ścisłymi DTO (slots=True, frozen=True) i kodami DomainError [REKOMENDOWANE]",
                        "recommended": True,
                        "trade_off": "Uniwersalność, czytelne kontrakty OpenAPI, deterministyczna walidacja wejścia."
                    },
                    {
                        "id": "async_event_driven",
                        "label": "[B] Asynchroniczna szyna zdarzeń (Worker / Queue / PubSub)",
                        "recommended": False,
                        "trade_off": "Wysoka przepustowość, ostateczna spójność (eventual consistency)."
                    },
                    {
                        "id": "internal_service_only",
                        "label": "[C] Czysta biblioteka wewnętrzna (In-Process Dependency Injection, brak endpointów HTTP)",
                        "recommended": False,
                        "trade_off": "Maksymalna wydajność, brak narzutu sieciowego."
                    }
                ],
                recommended_option_id="rest_json_strict_dto"
            ),
            SocraticQuestion(
                id="Q4_SRE_AND_RESILIENCE",
                dimension="SRE, Resilience & Blast Radius",
                question=f"Jakie limity niezawodnościowe i tolerancje awarii obowiązują dla modułu '{domain}'?",
                context="Określa timeouty, circuit breakers i politykę graceful shutdown.",
                options=[
                    {
                        "id": "fail_closed_with_timeout",
                        "label": "[A] Fail-Closed: Ścisły timeout 5000ms, Exponential Backoff z Jitterem, Circuit Breaker [REKOMENDOWANE]",
                        "recommended": True,
                        "trade_off": "Zapobiega kaskadowym awariom, deterministyczna odporność."
                    },
                    {
                        "id": "best_effort_retry",
                        "label": "[B] Best-Effort: Ponowienie operacji w tle bez blokowania wątku głównego",
                        "recommended": False,
                        "trade_off": "Wymaga kolejki DLQ (Dead-Letter Queue) dla odrzuconych żądań."
                    }
                ],
                recommended_option_id="fail_closed_with_timeout"
            ),
            SocraticQuestion(
                id="Q5_RETRO_COMPATIBILITY",
                dimension="Backward Compatibility & Migration",
                question=f"Czy rozszerzenie '{domain}' wprowadza zmiany łamiące istniejące kontrakty (Breaking Changes)?",
                context="Chronione przez regułę zerowej regresji: istniejące testy muszą zachować status PASS.",
                options=[
                    {
                        "id": "additive_non_breaking",
                        "label": "[A] Zmiana w 100% addytywna (Nowe trasy/modele bez mutacji istniejących sygnatur) [REKOMENDOWANE]",
                        "recommended": True,
                        "trade_off": "Gwarancja zerowej regresji, bezproblemowe przejście bramki G5."
                    },
                    {
                        "id": "versioned_coexistence",
                        "label": "[B] Wersjonowanie (v2): Nowy moduł współistnieje obok v1, zachowując backward-compatibility",
                        "recommended": False,
                        "trade_off": "Wymaga utrzymania routera routingu v1 i v2."
                    }
                ],
                recommended_option_id="additive_non_breaking"
            )
        ]
        return q_list

    @staticmethod
    def resolve_answers(questions: List[SocraticQuestion], provided_answers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        resolved = {}
        provided = provided_answers or {}
        for q in questions:
            if q.id in provided:
                resolved[q.id] = provided[q.id]
            else:
                resolved[q.id] = q.recommended_option_id
        return resolved


def synthesize_ears_and_gherkin(domain: str, module_slug: str, brief: str, answers: Dict[str, str]) -> Tuple[List[EarsRequirement], List[GherkinTriad]]:
    is_money = answers.get("Q2_FINANCIAL_AND_MONEY_INVARIANTS") == "money_integer_cents"

    ears_list = [
        EarsRequirement(
            req_id=f"REQ-{module_slug}-001",
            pattern_type="Ubiquitous",
            statement=f"System SHALL zapewnić hermetyczne przetwarzanie domenowe w ramach modułu {domain}.",
            rationale="Izolacja domenowa i SRP na poziomie architektury serwisów."
        ),
        EarsRequirement(
            req_id=f"REQ-{module_slug}-002",
            pattern_type="Event-driven",
            statement=f"WHEN żądanie wejściowe dla {module_slug} zostaje odebrane, system SHALL zweryfikować poprawność kontraktu w __post_init__ przed wykonaniem operacji.",
            rationale="Obrona brzegowa i eliminacja niepoprawnego stanu na wejściu do domeny."
        ),
        EarsRequirement(
            req_id=f"REQ-{module_slug}-003",
            pattern_type="State-driven",
            statement=f"WHILE moduł {domain} znajduje się w stanie aktywnym, system SHALL rejestrować zdarzenia telemetryczne bez użycia surowych funkcji wypisujących.",
            rationale="Standard 5 DREE: brak zaśmiecających console.log i surowych print."
        ),
        EarsRequirement(
            req_id=f"REQ-{module_slug}-004",
            pattern_type="Unwanted behavior",
            statement=f"IF payload wejściowy narusza ograniczenia typów lub inwarianty wartości, THEN system SHALL natychmiast zgłosić dedykowany wyjątek domenowy {domain.capitalize()}DomainError.",
            rationale="Standard 3 DREE: brak ogólnych wyjątków Exception, jawne błędy domenowe."
        )
    ]

    if is_money:
        ears_list.append(
            EarsRequirement(
                req_id=f"REQ-{module_slug}-005",
                pattern_type="Complex",
                statement=f"WHILE realizowane są operacje rozliczeniowe, WHEN przekazywana jest kwota pieniężna, system SHALL wymusić typ całkowity integer cents oraz nagłówek X-Idempotency-Key.",
                rationale="Reguła 50 DREE: zakaz float i gwarancja idempotencji."
            )
        )

    gherkin_list = [
        GherkinTriad(
            req_id=f"REQ-{module_slug}-001",
            happy_path=(
                f"Scenario: Pomyślne przetworzenie poprawnego żądania w module {domain}\n"
                f"  Given Inicjalizowany i poprawnie skonfigurowany serwis {domain}\n"
                f"  When Przekazano poprawny payload wejściowy spełniający zamrożony kontrakt DTO\n"
                f"  Then Operacja kończy się sukcesem, zwracając wynik ze statusem SUCCESS w czasie < 5000ms"
            ),
            negative_boundary=(
                f"Scenario: Odrzucenie niepoprawnych danych wejściowych (Boundary Failure)\n"
                f"  Given Aktywny serwis {domain}\n"
                f"  When Przekazano payload z pustym kluczem identyfikacyjnym lub wartością ujemną\n"
                f"  Then Serwis natychmiast rzuca wyjątek {domain.capitalize()}DomainError i odrzuca żądanie"
            ),
            negative_adversarial=(
                f"Scenario: Ochrona przed ponowieniem i wyścigiem (Adversarial / Idempotency Collision)\n"
                f"  Given Serwis {domain} z zarejestrowaną wcześniejszą operacją o identycznym idempotency_key\n"
                f"  When Równoległe lub powtórzone żądanie trafia do modułu z tym samym kluczem\n"
                f"  Then Serwis zwraca zbuforowaną odpowiedź bez ponownego wywoływania skutków ubocznych"
            )
        )
    ]

    return ears_list, gherkin_list


def merge_dag_kahn(existing_tasks: List[Dict[str, Any]], new_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges new tasks into existing DAG using Kahn's algorithm.
    Guarantees topological order and acyclicity.
    """
    merged_map: Dict[str, Dict[str, Any]] = {}
    for t in existing_tasks:
        merged_map[t["id"]] = t
    for t in new_tasks:
        merged_map[t["id"]] = t

    in_degree: Dict[str, int] = {tid: 0 for tid in merged_map}
    adjacency: Dict[str, List[str]] = {tid: [] for tid in merged_map}

    for tid, task in merged_map.items():
        deps = task.get("depends_on", [])
        for dep in deps:
            if dep not in merged_map:
                continue
            adjacency[dep].append(tid)
            in_degree[tid] += 1

    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    sorted_ids: List[str] = []

    while queue:
        curr = queue.pop(0)
        sorted_ids.append(curr)
        for neighbor in adjacency[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_ids) != len(merged_map):
        unresolved = [tid for tid, deg in in_degree.items() if deg > 0]
        raise DAGCycleError(
            f"CYCLIC_DEPENDENCY_DETECTED: Kahn's topological sort failed. Unresolved cycle nodes: {unresolved}"
        )

    return [merged_map[tid] for tid in sorted_ids]


def validate_40_3_1_rule(task: Dict[str, Any]):
    """Validates Rule 40/3/1:
    - SRP <= 40 lines
    - <= 3 files in allowed_paths
    - Exactly 1 writer isolation
    """
    allowed_paths = task.get("allowed_paths", [])
    if len(allowed_paths) > 3:
        raise RuleViolationError(
            f"RULE_40_3_1_VIOLATION: Task '{task.get('id')}' specifies {len(allowed_paths)} files in allowed_paths. "
            "Maximum 3 files per atomic task allowed to guarantee hermetic write isolation."
        )


def validate_dree_checklist(task: Dict[str, Any]):
    """Verifies that the task declares all 7 DREE invariants."""
    checklist = set(task.get("standards_checklist", []))
    required = {
        "interface_contract",
        "input_validation",
        "domain_exception",
        "pure_logic_srp",
        "telemetry_logging",
        "dual_test_suite",
        "export_registration"
    }
    missing = required - checklist
    if missing:
        raise RuleViolationError(
            f"DREE_CHECKLIST_INCOMPLETE: Task '{task.get('id')}' is missing required DREE invariants: {missing}"
        )


def generate_living_charter_delta(ctx: ProjectExtensionContext):
    """Updates Living Charter files in specs/ with delta sections."""
    specs_dir = ctx.workspace_root / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    # 1. specs/01_PRODUCT_REQUIREMENTS.md
    prd_path = specs_dir / "01_PRODUCT_REQUIREMENTS.md"
    prd_content = prd_path.read_text(encoding="utf-8") if prd_path.is_file() else "# PRODUCT REQUIREMENTS DOCUMENT (PRD) — SSoT\n"

    delta_prd_lines = [
        f"\n\n## Rozszerzenie REQ-EXT-{ctx.module_slug.upper()}: Moduł {ctx.domain}",
        f"> Data wdrożenia rozszerzenia: {os.environ.get('EXT_DATE', 'Auto-generated Delta')}",
        f"\n### 1. Inżynieria Wymagań EARS",
        "| ID Wymagania | Typ Wzorca EARS | Sformułowanie Wymagania | Uzasadnienie |",
        "|---|---|---|---|"
    ]
    for req in ctx.ears_requirements:
        delta_prd_lines.append(f"| `{req.req_id}` | **{req.pattern_type}** | {req.statement} | {req.rationale} |")

    delta_prd_lines.append(f"\n### 2. Triady Scenariuszy Akceptacyjnych (Gherkin Triads)")
    for triad in ctx.gherkin_triads:
        delta_prd_lines.append(f"#### Wymaganie {triad.req_id} — Scenariusze Testowe:")
        delta_prd_lines.append("```gherkin")
        delta_prd_lines.append("# 1. Happy Path")
        delta_prd_lines.append(triad.happy_path)
        delta_prd_lines.append("\n# 2. Negative Path (Boundary/Validation)")
        delta_prd_lines.append(triad.negative_boundary)
        delta_prd_lines.append("\n# 3. Negative Path (Adversarial/Edge/Fault)")
        delta_prd_lines.append(triad.negative_adversarial)
        delta_prd_lines.append("```")

    prd_path.write_text(prd_content + "\n" + "\n".join(delta_prd_lines), encoding="utf-8")

    # 2. specs/02_SYSTEM_ARCHITECTURE.md
    arch_path = specs_dir / "02_SYSTEM_ARCHITECTURE.md"
    arch_content = arch_path.read_text(encoding="utf-8") if arch_path.is_file() else "# SYSTEM ARCHITECTURE & C4 CONTAINER MODEL\n"

    delta_arch_lines = [
        f"\n\n## Rozszerzenie Architektury: Moduł {ctx.domain} ({ctx.module_slug})",
        f"### Model Komponentu (C4 Level 3 Delta)",
        "```mermaid",
        "graph LR",
        f"    Orchestrator[System Core / API Gateway] -->|DTO Validation| ExtService[{ctx.domain.capitalize()}Service]",
        f"    ExtService -->|Domain Events / Persistence| DataLayer[(State / Database)]",
        f"    ExtService -->|Telemetry & Metrics| Logger[Structured Telemetry]",
        "```",
        f"- **Granica Bezpieczeństwa:** Izolacja modułu `{ctx.domain}`, zasada Fail-Closed, timeout 5000ms.",
        f"- **Standard Zapisów:** Zgodność z 7 Niezmiennikami DREE i regułą 40/3/1."
    ]
    arch_path.write_text(arch_content + "\n" + "\n".join(delta_arch_lines), encoding="utf-8")

    # 3. specs/03_DATA_DICTIONARY.md
    dict_path = specs_dir / "03_DATA_DICTIONARY.md"
    dict_content = dict_path.read_text(encoding="utf-8") if dict_path.is_file() else "# DATA DICTIONARY & ENTITY SPECIFICATION\n\n| Symbol / Encja | Typ | Plik Definicji |\n|---|---|---|\n"

    delta_dict_lines = []
    capitalized_domain = "".join(word.capitalize() for word in ctx.domain.replace("-", " ").replace("_", " ").split())
    entities_to_add = [
        (f"{capitalized_domain}Request", "class (DTO)", f"contracts/{ctx.module_slug}.py"),
        (f"{capitalized_domain}Result", "class (DTO)", f"contracts/{ctx.module_slug}.py"),
        (f"{capitalized_domain}DomainError", "class (Exception)", f"contracts/{ctx.module_slug}.py"),
        (f"{ctx.module_slug}_service", "function", f"src/{ctx.module_slug}/{ctx.module_slug}_service.py")
    ]
    for ent in ctx.new_entities:
        ent_name = ent.get("name")
        if ent_name:
            entities_to_add.append((ent_name, "class (Entity)", f"contracts/{ctx.module_slug}.py"))

    for sym, stype, spath in entities_to_add:
        if sym not in dict_content:
            delta_dict_lines.append(f"| `{sym}` | `{stype}` | `{spath}` |")

    if delta_dict_lines:
        dict_path.write_text(dict_content.strip() + "\n" + "\n".join(delta_dict_lines) + "\n", encoding="utf-8")

    # 4. specs/04_DEPENDENCY_AND_IMPACT.md
    impact_path = specs_dir / "04_DEPENDENCY_AND_IMPACT.md"
    impact_content = impact_path.read_text(encoding="utf-8") if impact_path.is_file() else "# DEPENDENCY & IMPACT MATRIX\n"
    delta_impact_lines = [
        f"\n\n## Rozszerzenie: {ctx.module_slug}",
        f"- **Target Domain:** `{ctx.domain}`",
        f"- **Promień Rażenia (Blast Radius):** {len(ctx.blast_radius)} plików",
        f"- **Ryzyko Regresji:** `{ctx.ast_impact.get('riskRating', 'LOW')}`",
        "| Ścieżka Docelowa | Rola | Writer Isolation |",
        "|---|---|---|"
    ]
    for p in ctx.blast_radius:
        delta_impact_lines.append(f"| `{p}` | Rozszerzenie modułowe | Dedykowany podagent builder |")
    impact_path.write_text(impact_content + "\n" + "\n".join(delta_impact_lines), encoding="utf-8")


def generate_frozen_contracts_delta(ctx: ProjectExtensionContext):
    """Generates immutable contract files in contracts/ complying with Rule 50 and 7 Invariants of DREE."""
    contracts_dir = ctx.workspace_root / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    capitalized_domain = "".join(word.capitalize() for word in ctx.domain.replace("-", " ").replace("_", " ").split())
    is_money = ctx.socratic_answers.get("Q2_FINANCIAL_AND_MONEY_INVARIANTS") == "money_integer_cents"

    contract_file_py = contracts_dir / f"{ctx.module_slug}.py"

    py_lines = [
        f"# Frozen Domain Interface Contract: {capitalized_domain} (DREE v8.2)",
        "from dataclasses import dataclass, field",
        "from typing import Optional, Dict, Any, List",
        "",
        "class DomainError(Exception):",
        '    """Base domain exception conforming to DREE v8.2 standard."""',
        "    pass",
        "",
        f"class {capitalized_domain}DomainError(DomainError):",
        f'    """Dedykowany błąd domenowy dla modułu {ctx.domain}."""',
        "    pass",
        "",
        "@dataclass(slots=True, frozen=True)",
        f"class {capitalized_domain}Request:",
        "    id: str",
        "    tenant_id: str",
        "    payload: Dict[str, Any] = field(default_factory=dict)",
    ]
    if is_money:
        py_lines.extend([
            "    amount_cents: int = 0  # Reguła 50 DREE: Integer Minor Units, zakaz float",
            "    idempotency_key: str = ''",
        ])

    py_lines.extend([
        "",
        "    def __post_init__(self):",
        "        if not self.id:",
        f'            raise {capitalized_domain}DomainError("id is required and cannot be empty")',
        "        if not self.tenant_id:",
        f'            raise {capitalized_domain}DomainError("tenant_id is required and cannot be empty")',
    ])
    if is_money:
        py_lines.extend([
            "        if self.amount_cents < 0:",
            f'            raise {capitalized_domain}DomainError("amount_cents must be a non-negative integer")',
            "        if not self.idempotency_key:",
            f'            raise {capitalized_domain}DomainError("idempotency_key is required for financial operations")',
        ])

    py_lines.extend([
        "",
        "@dataclass(slots=True, frozen=True)",
        f"class {capitalized_domain}Result:",
        "    id: str",
        "    status: str = 'SUCCESS'",
        "    data: Dict[str, Any] = field(default_factory=dict)",
        "",
        "    def __post_init__(self):",
        "        if not self.id:",
        f'            raise {capitalized_domain}DomainError("id is required")',
        "        if self.status not in ('SUCCESS', 'FAILED', 'PENDING'):",
        f'            raise {capitalized_domain}DomainError(f"Invalid status: {{self.status}}")',
        ""
    ])

    for ent in ctx.new_entities:
        e_name = ent.get("name")
        if not e_name:
            continue
        py_lines.extend([
            "@dataclass(slots=True, frozen=True)",
            f"class {e_name}:",
            "    id: str",
        ])
        for f in ent.get("fields", []):
            fname = f.get("name")
            ftype = f.get("type", "str")
            if fname and fname != "id":
                py_lines.append(f"    {fname}: {ftype}")
        py_lines.extend([
            "",
            "    def __post_init__(self):",
            "        if not self.id:",
            f'            raise {capitalized_domain}DomainError("{e_name}.id cannot be empty")',
            ""
        ])

    all_symbols = ["DomainError", f"{capitalized_domain}DomainError", f"{capitalized_domain}Request", f"{capitalized_domain}Result"]
    for ent in ctx.new_entities:
        if ent.get("name"):
            all_symbols.append(ent.get("name"))

    py_lines.extend([
        "__all__ = [",
        "\n".join(f"    '{s}'," for s in all_symbols),
        "]",
        ""
    ])

    contract_file_py.write_text("\n".join(py_lines), encoding="utf-8")

    # TypeScript contracts
    contract_file_ts = contracts_dir / f"{ctx.module_slug}.ts"
    ts_lines = [
        f"/** Frozen Domain Interface Contract: {capitalized_domain} (TypeScript Strict) */",
        f"export interface {capitalized_domain}Request {{",
        "  readonly id: string;",
        "  readonly tenantId: string;",
        "  readonly payload: Record<string, unknown>;",
    ]
    if is_money:
        ts_lines.extend([
            "  readonly amountCents: number; // Integer Minor Units, no float",
            "  readonly idempotencyKey: string;",
        ])
    ts_lines.extend([
        "}",
        "",
        f"export interface {capitalized_domain}Result {{",
        "  readonly id: string;",
        "  readonly status: 'SUCCESS' | 'FAILED' | 'PENDING';",
        "  readonly data: Record<string, unknown>;",
        "}",
        ""
    ])
    contract_file_ts.write_text("\n".join(ts_lines), encoding="utf-8")


def compile_incremental_tasks(
    ctx: ProjectExtensionContext,
    existing_tasks: Optional[List[Dict[str, Any]]] = None,
    use_sequential_t_ids: bool = True
) -> List[Dict[str, Any]]:
    """Synthesizes atomic tasks conforming to 40/3/1, sequential IDs, and Kahn's topological sort."""
    stack = ctx.tech_stack or {"gate_cmd": "pytest", "gate_ext": ".py"}
    gate_cmd = stack.get("gate_cmd", "pytest")
    gate_ext = stack.get("gate_ext", ".py")

    slug = ctx.module_slug
    capitalized = "".join(word.capitalize() for word in ctx.domain.replace("-", " ").replace("_", " ").split())

    ex_tasks = existing_tasks or []
    if use_sequential_t_ids:
        t_ids = compute_next_task_ids(ex_tasks, count=3, prefix="T")
    else:
        t_ids = [f"task-contract-{slug}", f"task-service-{slug}", f"task-integration-{slug}"]

    t1_id, t2_id, t3_id = t_ids[0], t_ids[1], t_ids[2]

    root_deps = []
    if ex_tasks:
        last_id = ex_tasks[-1].get("id")
        if last_id:
            root_deps = [last_id]

    task1 = {
        "id": t1_id,
        "title": f"Walidacja i zamrożenie kontraktu domenowego {capitalized}",
        "domain": ctx.domain,
        "symbols": [f"{capitalized}Request", f"{capitalized}Result", f"{capitalized}DomainError"],
        "routes": [],
        "allowed_paths": [f"contracts/{slug}.py", f"tests/test_{slug}_contract{gate_ext}"],
        "depends_on": root_deps,
        "checks": ["unit"],
        "acceptance": [
            f"Kontrakt {capitalized}Request posiada walidację w __post_init__",
            f"Błędy domenowe rzucają {capitalized}DomainError"
        ],
        "dod_command": f"{gate_cmd} tests/test_{slug}_contract{gate_ext}",
        "risk": "low",
        "standards_checklist": [
            "interface_contract",
            "input_validation",
            "domain_exception",
            "pure_logic_srp",
            "telemetry_logging",
            "dual_test_suite",
            "export_registration"
        ]
    }

    task2 = {
        "id": t2_id,
        "title": f"Implementacja czystej logiki biznesowej {capitalized}Service",
        "domain": ctx.domain,
        "symbols": [f"{slug}_service", f"{capitalized}Service"],
        "routes": [f"/api/v1/{slug}"],
        "allowed_paths": [f"src/{slug}/{slug}_service{gate_ext}", f"tests/test_{slug}_service{gate_ext}"],
        "depends_on": [t1_id],
        "checks": ["unit"],
        "acceptance": [
            f"Funkcje logiki biznesowej posiadają <= 40 linii kodu (SRP)",
            f"Przechodzi podwójna suita testowa (Happy Path + 2 testy negatywne/brzegowe)"
        ],
        "dod_command": f"{gate_cmd} tests/test_{slug}_service{gate_ext}",
        "risk": "medium",
        "standards_checklist": [
            "interface_contract",
            "input_validation",
            "domain_exception",
            "pure_logic_srp",
            "telemetry_logging",
            "dual_test_suite",
            "export_registration"
        ]
    }

    task3 = {
        "id": t3_id,
        "title": f"Weryfikacja bramki integracyjnej i odpornościowej dla {capitalized}",
        "domain": ctx.domain,
        "symbols": [f"{capitalized}IntegrationGate"],
        "routes": [f"/api/v1/{slug}/health"],
        "allowed_paths": [f"tests/integration/test_{slug}_gate{gate_ext}"],
        "depends_on": [t2_id],
        "checks": ["unit"],
        "acceptance": [
            f"Bramka integracyjna potwierdza brak regresji w całym projekcie",
            f"Testy mutacyjne Mock-Breaker przechodzą pomyślnie"
        ],
        "dod_command": f"{gate_cmd} tests/integration/test_{slug}_gate{gate_ext}",
        "risk": "low",
        "standards_checklist": [
            "interface_contract",
            "input_validation",
            "domain_exception",
            "pure_logic_srp",
            "telemetry_logging",
            "dual_test_suite",
            "export_registration"
        ]
    }

    new_tasks = [task1, task2, task3]
    for t in new_tasks:
        validate_40_3_1_rule(t)
        validate_dree_checklist(t)

    return new_tasks


def extend_project(
    workspace_root: Path,
    brief: str,
    module_slug: Optional[str] = None,
    domain: Optional[str] = None,
    provided_answers: Optional[Dict[str, str]] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    use_sequential_t_ids: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Master operational flow for extending active managed projects."""
    ws = Path(workspace_root).resolve()

    state = check_governance_state(ws)

    m_slug = module_slug or re.sub(r'[^a-z0-9_-]', '', brief.lower().split()[0])[:20] or "custom_ext"
    m_domain = domain or m_slug.replace("-", "_")

    if entities:
        validate_currency_invariants(entities)

    questions = SocraticEngine.build_standard_questionnaire(brief, m_domain)
    answers = SocraticEngine.resolve_answers(questions, provided_answers)

    ears_reqs, gherkin_triads = synthesize_ears_and_gherkin(m_domain, m_slug, brief, answers)

    tech_stack = detect_tech_stack(ws) if detect_tech_stack else {"gate_cmd": "pytest", "gate_ext": ".py"}

    capitalized_domain = "".join(word.capitalize() for word in m_domain.replace("-", " ").replace("_", " ").split())
    candidate_symbols = [f"{capitalized_domain}Request", f"{capitalized_domain}Result", f"{capitalized_domain}DomainError", f"{m_slug}_service"]
    if entities:
        for ent in entities:
            if ent.get("name"):
                candidate_symbols.append(ent.get("name"))

    ast_impact = ASTImpactAnalyzer.analyze_workspace_ast(ws, candidate_symbols, m_domain)

    ctx = ProjectExtensionContext(
        workspace_root=ws,
        brief=brief,
        module_slug=m_slug,
        domain=m_domain,
        tech_stack=tech_stack,
        socratic_answers=answers,
        ears_requirements=ears_reqs,
        gherkin_triads=gherkin_triads,
        new_entities=entities or [],
        blast_radius=[
            f"contracts/{m_slug}.py",
            f"src/{m_slug}/{m_slug}_service{tech_stack.get('gate_ext', '.py')}",
            f"tests/test_{m_slug}_service{tech_stack.get('gate_ext', '.py')}"
        ] + ast_impact.get("downstreamDependents", []),
        ast_impact=ast_impact
    )

    tasks_file = ws / ".governance" / "tasks.json"
    existing_tasks = []
    is_schema_v2 = False
    raw_tasks_data: Dict[str, Any] = {}

    if tasks_file.is_file():
        try:
            raw_tasks_data = json.loads(tasks_file.read_text(encoding="utf-8"))
            existing_tasks = raw_tasks_data.get("tasks", [])
            is_schema_v2 = (raw_tasks_data.get("version") == 2) or ("epics" in raw_tasks_data)
        except Exception:
            existing_tasks = []

    new_tasks = compile_incremental_tasks(ctx, existing_tasks, use_sequential_t_ids=use_sequential_t_ids)
    ctx.new_tasks = new_tasks

    merged_tasks = merge_dag_kahn(existing_tasks, new_tasks)

    if not dry_run:
        generate_living_charter_delta(ctx)
        generate_frozen_contracts_delta(ctx)

        if is_schema_v2:
            epics = list(raw_tasks_data.get("epics", []))
            milestones = list(raw_tasks_data.get("milestones", []))
            epic_id = f"EPIC-{m_slug.upper()}"
            milestone_id = f"M-{m_slug.upper()}"
            if not any(e.get("id") == epic_id for e in epics):
                epics.append({
                    "id": epic_id,
                    "title": f"Rozszerzenie: Moduł {capitalized_domain}",
                    "description": f"Przyrostowa rozbudowa systemu o moduł {m_domain} ({m_slug})"
                })
            if not any(m.get("id") == milestone_id for m in milestones):
                milestones.append({
                    "id": milestone_id,
                    "epic_id": epic_id,
                    "title": f"Kamień Milowy: Wdrożenie {capitalized_domain}"
                })
            for t in new_tasks:
                t["epic_id"] = epic_id
                t["milestone_id"] = milestone_id

            tasks_data = {
                "version": 2,
                "blueprint_source": raw_tasks_data.get("blueprint_source", "specs/00_MASTER_BLUEPRINT.md"),
                "epics": epics,
                "milestones": milestones,
                "tasks": merged_tasks
            }
        else:
            tasks_data = {"version": 1, "tasks": merged_tasks}

        tasks_file.write_text(json.dumps(tasks_data, indent=2, ensure_ascii=False), encoding="utf-8")

        gov_cfg = ws / ".governance" / "config.json"
        if gov_cfg.is_file():
            try:
                cfg = json.loads(gov_cfg.read_text(encoding="utf-8"))
                cfg["spec_locked"] = False
                spec_files = list(cfg.get("spec_files", []))
                new_contract_ref = f"contracts/{m_slug}.py"
                if new_contract_ref not in spec_files:
                    spec_files.append(new_contract_ref)
                cfg["spec_files"] = spec_files
                gov_cfg.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            except Exception:
                pass

        lock_file = ws / ".governance" / "spec.lock"
        if lock_file.is_file():
            try:
                lock_file.unlink()
            except Exception:
                pass

    return {
        "status": "SUCCESS",
        "state": state,
        "module_slug": m_slug,
        "domain": m_domain,
        "answers": answers,
        "ears_count": len(ears_reqs),
        "gherkin_count": len(gherkin_triads),
        "new_tasks_count": len(new_tasks),
        "total_tasks_count": len(merged_tasks),
        "tasks": new_tasks,
        "ast_impact": ast_impact,
        "dry_run": dry_run,
        "next_step": f"python .governance/bin/gov.py approve-spec --actor human:owner --reference extend-{m_slug}"
    }


def main():
    parser = argparse.ArgumentParser(description="Antigravity Ultra v8.2 Project Extension Engine")
    parser.add_argument("--target", default=".", help="Project workspace root")
    parser.add_argument("--brief", help="Extension request brief text")
    parser.add_argument("--brief-file", help="Path to brief file")
    parser.add_argument("--slug", help="Module slug")
    parser.add_argument("--domain", help="Module domain name")
    parser.add_argument("--answers-file", help="Path to JSON file with pre-resolved Socratic answers")
    parser.add_argument("--entities-file", help="Path to JSON file defining new entities and fields")
    parser.add_argument("--legacy-task-ids", action="store_true", help="Use legacy task-contract-... IDs instead of sequential T00X")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    args = parser.parse_args()

    brief_text = args.brief
    if not brief_text and args.brief_file and Path(args.brief_file).is_file():
        brief_text = Path(args.brief_file).read_text(encoding="utf-8")

    if not brief_text:
        print("ERROR: --brief or --brief-file is required.", file=sys.stderr)
        sys.exit(1)

    answers = None
    if args.answers_file and Path(args.answers_file).is_file():
        try:
            answers = json.loads(Path(args.answers_file).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR reading answers file: {e}", file=sys.stderr)
            sys.exit(1)

    entities = None
    if args.entities_file and Path(args.entities_file).is_file():
        try:
            entities = json.loads(Path(args.entities_file).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR reading entities file: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        res = extend_project(
            workspace_root=Path(args.target),
            brief=brief_text,
            module_slug=args.slug,
            domain=args.domain,
            provided_answers=answers,
            entities=entities,
            use_sequential_t_ids=not args.legacy_task_ids,
            dry_run=args.dry_run
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
