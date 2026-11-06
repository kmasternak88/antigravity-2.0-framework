#!/usr/bin/env python3
"""Ingestion Node & Input Maturity Score (IMS) Parser for Antigravity Framework v8.1.

Ingests raw ideas, prompts, or PRD markdown files, computes the Input Maturity Score (IMS),
identifies domain archetypes, entities, operations, actors, and classifies the project into:
- RAW_SEED (IMS <= 0.35): Autonomous ADR resolution with standard production profiles.
- PARTIAL_SPEC (0.35 < IMS <= 0.70): Formulates max 3 One-Way Door questions while generating complete draft.
- COMPREHENSIVE_PRD (IMS > 0.70): Deconstructs normative RFC 2119 requirements.
"""
import argparse, json, os, re, sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

__all__ = [
    "IngestionContext",
    "IngestionParser",
    "FORBIDDEN_ENTITY_WORDS",
    "ARCHETYPE_DEFAULT_ENTITIES",
    "FIVE_INVARIANT_VECTORS",
    "main",
]

FIVE_INVARIANT_VECTORS = [
    "ONE_WAY_DOORS_STORAGE",
    "FINANCIAL_MONEY_INVARIANTS",
    "RESILIENCE_AND_UNWANTED_EARS",
    "SRE_RESOURCE_LIMITS",
    "PANEL_PERMISSIONS_WCAG",
]

FORBIDDEN_ENTITY_WORDS = {
    # Markdown & framework structure keywords
    "faza", "system", "projekt", "plan", "opis", "wymagania", "master", "blueprint",
    "dekonstrukcja", "domeny", "przypadki", "brzegowe", "architektura", "danych",
    "zarzadzanie", "zarządzanie", "stanem", "kontrakty", "komunikacyjne", "walidacja",
    "bezpieczenstwo", "bezpieczeństwo", "odpornosc", "odporność", "obserwowalnosc",
    "obserwowalność", "stos", "technologiczny", "konfiguracja", "drzewo", "plikow",
    "plików", "atomowy", "implementacji", "strategia", "testowania", "kontroli",
    "jakosci", "jakości", "weryfikacja", "matrix", "epic", "epik", "milestone",
    "sprint", "task", "zadanie", "kryterium", "odbioru", "zaleznosci", "zależności",
    "pliki", "docelowe", "kontekst", "wejsciowy", "wejściowy", "header", "introduction",
    "overview", "standard", "rfc2119", "dree", "genesis", "living", "charter",
    "traceability", "action", "actions", "component", "components", "feature", "features",
    "moduł", "moduły", "warstwa", "warstwy", "endpoint", "endpointy", "tabela", "tabele",
    "model", "modele", "encja", "encje", "serwis", "serwisy", "usługa", "usługi",
    # Grammar stopwords
    "about", "after", "again", "against", "before", "being", "between", "during",
    "further", "having", "itself", "myself", "ourselves", "themselves", "through",
    "under", "until", "where", "which", "while", "would", "should", "could",
    "oraz", "albo", "takze", "także", "przez", "przy", "jest", "jego", "będzie",
    "będą", "jako", "który", "która", "które", "może", "mogą", "tylko", "więc",
    "jeśli", "kiedy", "gdzie", "czym", "przed", "poza", "razem"
}

ARCHETYPE_DEFAULT_ENTITIES = {
    "fintech_transaction_ledger": ["TransactionRecord", "LedgerAccount", "AuditEntry"],
    "cli_system_tool": ["CliCommand", "ExecutionContext", "SystemConfig"],
    "realtime_telemetry_broker": ["TelemetryEvent", "SensorDevice", "MetricReading"],
    "data_pipeline_etl": ["PipelineJob", "DataSet", "RecordBatch"],
    "multi_tenant_saas": ["TenantAccount", "UserProfile", "SubscriptionRecord"],
    "enterprise_rest_api": ["DomainEntity", "UserProfile", "AuditRecord"],
}

FORBIDDEN_AMBIGUITY_REGEX = re.compile(
    r'\b(?:do ustalenia|w zależności od potrzeb|itd\.?|itp\.?|np\.?|//\s*TODO|/\*\s*TODO|TODO:|zabezpiecz odpowiednio|dowolny|jakis|jakikolwiek|szybki|wydajny|prosty)\b',
    re.IGNORECASE
)

PRD_FILENAME_PATTERNS = [
    re.compile(r'.*(prd|spec|requirements|brief|rfc|design).*\.md$', re.IGNORECASE),
    re.compile(r'^README\.md$', re.IGNORECASE)
]

@dataclass
class IngestionContext:
    source_type: str  # 'file', 'brief', 'auto_discovered', 'stdin'
    source_path: Optional[str] = None
    raw_content: str = ""
    archetype: str = "generic_backend"
    actors: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    nfrs: List[str] = field(default_factory=list)
    ambiguity_penalties: int = 0
    ims_score: float = 0.0
    classification: str = "RAW_SEED"  # RAW_SEED | PARTIAL_SPEC | COMPREHENSIVE_PRD
    one_way_door_questions: List[str] = field(default_factory=list)
    autonomous_adrs: List[Dict[str, str]] = field(default_factory=list)
    grill_me_required: bool = True
    grounded_invariants: List[str] = field(default_factory=list)
    missing_invariants: List[str] = field(default_factory=list)
    grill_me_bypass_reason: Optional[str] = None

class IngestionParser:
    @staticmethod
    def auto_discover_prd(workspace_root: Path) -> Optional[Path]:
        """Scan workspace for likely PRD or spec markdown files."""
        candidates = []
        for p in workspace_root.glob("*.md"):
            if p.is_file():
                for pat in PRD_FILENAME_PATTERNS:
                    if pat.match(p.name):
                        candidates.append(p)
                        break
        # Also check docs/ and specs/
        for sub in ["docs", "specs", "specification"]:
            sub_dir = workspace_root / sub
            if sub_dir.is_dir():
                for p in sub_dir.glob("*.md"):
                    if p.is_file():
                        candidates.append(p)

        # Sort by priority: explicit 'prd' or 'spec' over 'README.md'
        def score_candidate(path: Path) -> int:
            name = path.name.lower()
            if "prd" in name: return 100
            if "spec" in name and "blueprint" not in name: return 80
            if "requirements" in name: return 70
            if "brief" in name: return 60
            if "readme" in name: return 10
            return 20

        candidates.sort(key=score_candidate, reverse=True)
        return candidates[0] if candidates else None

    @classmethod
    def parse_input(cls, input_str_or_path: Optional[str], workspace_root: Optional[Path] = None) -> IngestionContext:
        ws = workspace_root or Path.cwd().resolve()
        ctx = IngestionContext(source_type="brief")

        # 1. Check if input points to an existing file
        if input_str_or_path:
            is_file = False
            if "\n" not in input_str_or_path and len(input_str_or_path) < 260:
                try:
                    target_p = Path(input_str_or_path)
                    if not target_p.is_absolute():
                        target_p = (ws / target_p).resolve()
                    if target_p.is_file():
                        is_file = True
                        ctx.source_type = "file"
                        ctx.source_path = str(target_p)
                        ctx.raw_content = target_p.read_text(encoding="utf-8")
                except (OSError, ValueError):
                    is_file = False

            if not is_file:
                ctx.source_type = "brief"
                ctx.raw_content = input_str_or_path
        else:
            # Try auto-discovery in workspace
            discovered = cls.auto_discover_prd(ws)
            if discovered:
                ctx.source_type = "auto_discovered"
                ctx.source_path = str(discovered)
                ctx.raw_content = discovered.read_text(encoding="utf-8")
            else:
                ctx.source_type = "stdin"
                ctx.raw_content = sys.stdin.read() if not sys.stdin.isatty() else ""

        ctx.raw_content = ctx.raw_content.strip()
        if not ctx.raw_content:
            ctx.ims_score = 0.0
            ctx.classification = "RAW_SEED"
            return ctx

        cls._analyze_content(ctx)
        return ctx

    @classmethod
    def _analyze_content(cls, ctx: IngestionContext):
        content = ctx.raw_content
        lines = content.splitlines()

        # 1. Archetype detection
        content_lower = content.lower()
        if any(w in content_lower for w in ["płatnoś", "payment", "ledger", "stripe", "escrow", "faktura", "billing"]):
            ctx.archetype = "fintech_transaction_ledger"
        elif any(w in content_lower for w in ["cli", "terminal", "command line", "komenda", "narzędzie cli"]):
            ctx.archetype = "cli_system_tool"
        elif any(w in content_lower for w in ["saas", "subskrypcj", "dashboard", "b2b", "portal", "tenan"]):
            ctx.archetype = "multi_tenant_saas"
        elif any(w in content_lower for w in ["crawler", "scraper", "etl", "scraping", "indeksow"]):
            ctx.archetype = "data_pipeline_etl"
        elif any(w in content_lower for w in ["iot", "sensor", "telemetria", "broker", "mqtt", "websocket"]):
            ctx.archetype = "realtime_telemetry_broker"
        else:
            ctx.archetype = "enterprise_rest_api"

        # 2. Extract Actors / Roles
        actor_matches = re.findall(r'(?:jako|rola|aktor|user|admin|operator|klient|użytkownik|developer|audytor)\s+([A-Za-z0-9_-]+)', content, re.IGNORECASE)
        ctx.actors = sorted(list(set([a.capitalize() for a in actor_matches if len(a) > 2])))
        if not ctx.actors:
            if "admin" in content_lower: ctx.actors.append("Administrator")
            ctx.actors.append("StandardUser")
            ctx.actors.append("SystemWorker")

        # 3. Extract Entities (Nouns)
        entity_matches = re.findall(r'(?:tabela|model|encja|entity|zasób|agregat|tabeli|modelu)\s+[`"]?([A-Za-z0-9_-]+)[`"]?', content, re.IGNORECASE)
        clean_entities = [
            e.capitalize() for e in entity_matches
            if len(e) > 2 and e.lower() not in FORBIDDEN_ENTITY_WORDS and not e.isdigit()
        ]
        ctx.entities = sorted(list(set(clean_entities)))
        if not ctx.entities:
            # Fallback based on archetype - clean without junk
            ctx.entities = list(ARCHETYPE_DEFAULT_ENTITIES.get(ctx.archetype, ARCHETYPE_DEFAULT_ENTITIES["enterprise_rest_api"]))

        # 4. Extract Operations / Flows
        op_matches = re.findall(r'(?:tworzenie|rejestracja|dodawanie|pobieranie|aktualizacja|usuwanie|anulowanie|przetwarzanie|generowanie|walidacja)\s+([^\n,.;]+)', content, re.IGNORECASE)
        ctx.operations = [op.strip() for op in op_matches[:10] if len(op.strip()) > 3]

        # 5. Extract NFRs
        nfr_patterns = [
            r'(\b\d+\s*(?:ms|s|sekund|minut|rps|tps)\b)',
            r'(\b99\.\d+%\b)',
            r'(rate\s*limit[^\n,.;]*)',
            r'(jwt|oauth|mtls|argon2|bcrypt|sha256)',
            r'(acid|transakcj|idempotent[^\n,.;]*)'
        ]
        for pat in nfr_patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            for m in matches:
                ctx.nfrs.append(m.strip())
        ctx.nfrs = sorted(list(set(ctx.nfrs)))

        # 6. Ambiguity Penalty
        ambiguity_matches = FORBIDDEN_AMBIGUITY_REGEX.findall(content)
        ctx.ambiguity_penalties = len(ambiguity_matches)

        # 7. Compute IMS Score
        c_actors = min(1.0, len(ctx.actors) / 2.0)
        c_data = min(1.0, len(ctx.entities) / 3.0)
        c_ops = min(1.0, len(ctx.operations) / 4.0)
        c_nfr = min(1.0, len(ctx.nfrs) / 2.0)
        penalty = min(0.40, ctx.ambiguity_penalties * 0.05)

        raw_ims = (0.25 * c_actors) + (0.25 * c_data) + (0.25 * c_ops) + (0.25 * c_nfr) - penalty
        ctx.ims_score = max(0.0, min(1.0, round(raw_ims, 3)))

        # 8. Classification
        if ctx.ims_score <= 0.35 or len(content) < 250:
            ctx.classification = "RAW_SEED"
            cls._populate_autonomous_adrs(ctx)
        elif ctx.ims_score <= 0.70:
            ctx.classification = "PARTIAL_SPEC"
            cls._populate_one_way_door_questions(ctx)
            cls._populate_autonomous_adrs(ctx)
        else:
            ctx.classification = "COMPREHENSIVE_PRD"

        # 9. Evaluate Adaptive Socratic Flow & 5 Invariant Vectors
        cls._evaluate_invariant_vectors(ctx)

    @classmethod
    def _populate_autonomous_adrs(cls, ctx: IngestionContext):
        """Formulate deterministic architectural decision records tailored to domain archetype."""
        if ctx.archetype == "fintech_transaction_ledger":
            adr2 = {
                "id": "ADR-002",
                "title": "Zasada Przechowywania Wartości Pieniężnych (Zero-Float Policy)",
                "decision": "Wyłącznie liczby całkowite w jednostkach podrzędnych (integer minor: grosze lub centy)",
                "rationale": "Wyeliminowanie błędów zaokrągleń IEEE 754 w operacjach finansowych i księgowych."
            }
        elif ctx.archetype == "cli_system_tool":
            adr2 = {
                "id": "ADR-002",
                "title": "Standard Determinizmu i Standardowych Strumieni I/O (POSIX CLI Standard)",
                "decision": "Zwracanie kodów wyjścia 0 dla sukcesu i >0 dla błędów, separacja stdout i stderr, brak efektów ubocznych przy flagach informacyjnych",
                "rationale": "Zgodność z potokami Uniksa (UNIX philosophy) i bezproblemowa kompozycja w skryptach powłoki."
            }
        elif ctx.archetype == "realtime_telemetry_broker":
            adr2 = {
                "id": "ADR-002",
                "title": "Obsługa Strumieni i Kontrola Przepływu (Backpressure Policy)",
                "decision": "Asynchroniczne buforowanie z mechanizmem backpressure i odpornością na skoki ruchu (bursts)",
                "rationale": "Zapobieganie wyciekom pamięci (OOM) przy przeciążeniu brokerów telemetrycznych."
            }
        elif ctx.archetype == "data_pipeline_etl":
            adr2 = {
                "id": "ADR-002",
                "title": "Atomowość Wsadowa i Idempotentny Replay (Checkpointing & DLQ)",
                "decision": "Zapis postępu w punktach kontrolnych (checkpoints) oraz przekierowanie błędnych rekordów do Dead-Letter Queue (DLQ)",
                "rationale": "Zapewnienie semantyki exactly-once lub at-least-once bez utraty danych."
            }
        else:
            adr2 = {
                "id": "ADR-002",
                "title": "Izolacja Danych i Walidacja Granic Domenowych (Zero-Trust Boundaries)",
                "decision": "Rygorystyczna walidacja schematów na wejściu i logiczna separacja przestrzeni danych podmiotów",
                "rationale": "Zapobieganie atakom injection, zanieczyszczeniu stanu oraz wyciekom danych między podmiotami."
            }

        ctx.autonomous_adrs = [
            {
                "id": "ADR-001",
                "title": "Baza Danych i Magazyn Stanu Trwałego",
                "decision": "PostgreSQL 16 (lub SQLite z trybem WAL dla narzędzi jednoużytkownikowych / CLI)",
                "rationale": "Pełne wsparcie dla transakcji ACID, blokad wierszowych (SELECT FOR UPDATE) oraz typów UUIDv7."
            },
            adr2,
            {
                "id": "ADR-003",
                "title": "Uwierzytelnianie i Identyfikacja Podmiotów",
                "decision": "Krótkożyjące asymetryczne tokeny JWT (RS256/EdDSA) + Refresh Token z rotacją i unieważnieniem w Redis",
                "rationale": "Bezstanowa weryfikacja brzegowa, zgodność z modelem Zero-Trust i ochrona przed replay-attacks."
            },
            {
                "id": "ADR-004",
                "title": "Idempotentność Mutacji Stanu",
                "decision": "Wymóg nagłówka X-Idempotency-Key (UUIDv7) dla każdej operacji POST/PUT z czasem retencji 24h",
                "rationale": "Odporność na duplikację zleceń, timeouty sieciowe oraz samorzutne powtórzenia klienta."
            }
        ]

    @staticmethod
    def generate_data_dictionary_content(entities: List[str], archetype: str) -> str:
        """Generates clean specs/03_DATA_DICTIONARY.md synchronized with extracted domain entities."""
        lines = [
            "# DATA DICTIONARY & ENTITY SPECIFICATION",
            "> Auto-generated by Antigravity Ultra v8.1 Ingestion Engine (Lock 5 Clean-Slate)",
            "",
            f"**Archetyp:** `{archetype}` | **Data generacji:** `2026-11-03`",
            "",
            "## 1. Zindeksowane Encje Domenowe i Kontrakty SSoT",
            "| Symbol / Encja | Typ | Plik Definicji | Opis Domenowy |",
            "|---|---|---|---|"
        ]
        for ent in entities:
            lines.append(f"| `{ent}` | `class (dataclass)` | `contracts/models.py` | Główna encja domenowa ({ent}) |")
            lines.append(f"| `{ent}Error` | `class (Exception)` | `contracts/models.py` | Wyjątek domenowy dla encji {ent} |")
            lines.append(f"| `I{ent}Service` | `interface / protocol` | `contracts/models.py` | Interfejs serwisowy dla {ent} |")
        return "\n".join(lines) + "\n"

    @classmethod
    def _populate_one_way_door_questions(cls, ctx: IngestionContext):
        """Formulate max 3 critical One-Way Door questions with pre-baked options."""
        ctx.one_way_door_questions = [
            "1. [ARCHITEKTURA TENANCY]: Czy projekt ma działać w modelu Single-Tenant (izolowana instancja per klient) czy Multi-Tenant (wspólna baza z tenant_id)? [Domyślnie: Multi-Tenant ze schematem logicznym]",
            "2. [MODEL INTEGRACJI]: Czy synchronizacja z zewnętrznymi usługami ma zachodzić synchronicznie (blokujące API), czy przez asynchroniczną kolejkę zdarzeniową (Outbox Pattern / Redis Stream)? [Domyślnie: Outbox Pattern]",
            "3. [RYGORYSTYCZNY REGULATOR]: Czy system podlega pod specyficzne regulacje (takie jak RODO/GDPR, KNF, HIPAA), wymagające natychmiastowego szyfrowania w spoczynku i prawa do bycia zapomnianym? [Domyślnie: Standard GDPR-compliant audit trail]"
        ]

    @classmethod
    def _evaluate_invariant_vectors(cls, ctx: IngestionContext):
        """Adaptive Socratic Flow: check whether the input explicitly grounds the 5 Invariant Vectors.
        If all 5 vectors are grounded, Grill-Me can be safely bypassed.
        """
        c_lower = ctx.raw_content.lower()

        grounded = []
        missing = []

        # 1. One-Way Doors & Storage
        if any(w in c_lower for w in ["postgresql", "sqlite", "mysql", "hpos", "database", "baza danych", "tabela", "relacyjn", "dynamodb", "mongodb"]):
            grounded.append("ONE_WAY_DOORS_STORAGE")
        else:
            missing.append("ONE_WAY_DOORS_STORAGE")

        # 2. Financial / Money Invariants (Rule 50 DREE)
        has_money_concept = any(w in c_lower for w in ["płatno", "payment", "cena", "kwota", "cents", "grosze", "stripe", "billing", "subskryp", "faktur"])
        if has_money_concept:
            if any(w in c_lower for w in ["cents", "grosze", "minor units", "integer cents", "zero-float", "amount_cents", "bez float"]):
                grounded.append("FINANCIAL_MONEY_INVARIANTS")
            else:
                missing.append("FINANCIAL_MONEY_INVARIANTS")
        else:
            # Domain does not involve money -> trivially satisfied
            grounded.append("FINANCIAL_MONEY_INVARIANTS")

        # 3. Resilience & Unwanted Behavior (EARS Unwanted / Failures)
        if any(w in c_lower for w in ["if ", "jeśli", "failure", "awaria", "timeout", "retry", "circuit breaker", "domainerror", "błąd", "error", "unwanted"]):
            grounded.append("RESILIENCE_AND_UNWANTED_EARS")
        else:
            missing.append("RESILIENCE_AND_UNWANTED_EARS")

        # 4. SRE & Resource Limits
        if any(w in c_lower for w in ["ms", "timeout", "limit", "rps", "tps", "pamięć", "memory", "rate limit", "5000ms"]):
            grounded.append("SRE_RESOURCE_LIMITS")
        else:
            missing.append("SRE_RESOURCE_LIMITS")

        # 5. Panel / Permissions / WCAG / Roles
        if any(w in c_lower for w in ["admin", "dashboard", "panel", "rola", "role", "wcag", "uprawnien", "rbac", "permissions", "capabilities", "current_user_can"]):
            grounded.append("PANEL_PERMISSIONS_WCAG")
        else:
            missing.append("PANEL_PERMISSIONS_WCAG")

        ctx.grounded_invariants = grounded
        ctx.missing_invariants = missing

        if len(missing) == 0 and ctx.ims_score > 0.70:
            ctx.grill_me_required = False
            ctx.grill_me_bypass_reason = "Grill-Me Bypassed: All 5 Invariant Vectors explicitly grounded in input PRD"
        else:
            ctx.grill_me_required = True
            ctx.grill_me_bypass_reason = None

def main():
    parser = argparse.ArgumentParser(description="Ingestion Node & IMS Parser v8.1")
    parser.add_argument("input", nargs="?", help="Input brief text or path to markdown file")
    parser.add_argument("--prd", help="Explicit path to PRD markdown file")
    parser.add_argument("--brief", help="Raw brief text")
    parser.add_argument("--workspace", "-w", help="Workspace root directory")
    parser.add_argument("--auto", action="store_true", help="Auto-discover PRD in workspace")
    parser.add_argument("--json", action="store_true", help="Output JSON context")
    args = parser.parse_args()

    ws = Path(args.workspace).resolve() if args.workspace else Path.cwd().resolve()
    target_input = args.prd or args.brief or args.input

    ctx = IngestionParser.parse_input(target_input, ws)

    if args.json:
        print(json.dumps(asdict(ctx), indent=2, ensure_ascii=False))
    else:
        print(f"\n=======================================================")
        print(f"   INGESTION PARSER v8.1 — RAPORT DOJRZAŁOŚCI WEJŚCIA   ")
        print(f"=======================================================\n")
        print(f"Źródło:          {ctx.source_type} ({ctx.source_path or 'tekst w pamięci'})")
        print(f"Długość:         {len(ctx.raw_content)} znaków")
        print(f"Archetyp:        {ctx.archetype}")
        print(f"Wskaźnik IMS:    {ctx.ims_score} / 1.000")
        print(f"Klasyfikacja:    {ctx.classification}")
        print(f"Wykryte Encje:   {', '.join(ctx.entities) if ctx.entities else 'brak'}")
        print(f"Aktorzy/Role:    {', '.join(ctx.actors) if ctx.actors else 'brak'}")
        print(f"Kary Nieostrości: {ctx.ambiguity_penalties} tokenów")

        if ctx.classification == "RAW_SEED":
            print(f"\n[TRYB RAW_SEED] Zastosowano autonomiczne rozstrzygnięcia inżynierskie (ADR):")
            for adr in ctx.autonomous_adrs:
                print(f"  * {adr['id']} ({adr['title']}): {adr['decision']}")
        elif ctx.classification == "PARTIAL_SPEC":
            print(f"\n[TRYB PARTIAL_SPEC] Sformułowano pytania o decyzje nieodwracalne (One-Way Doors):")
            for q in ctx.one_way_door_questions:
                print(f"  {q}")
        else:
            print(f"\n[TRYB COMPREHENSIVE_PRD] Gotowy do bezpośredniej dekompozycji normatywnej RFC 2119.")
        print()

if __name__ == '__main__':
    main()
