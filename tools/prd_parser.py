#!/usr/bin/env python3
"""
Product Requirements Document (PRD) Parser & Spec-Driven Development Transpiler.
Compliant with DREE v8.3 (7 Invariants, SRP <= 40 lines per function, typed DTOs).
"""
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

__all__ = [
    "PRDParseError",
    "PRDValidationError",
    "PRDMetadata",
    "StrategicParameter",
    "FinancialMetric",
    "Persona",
    "Requirement",
    "UserFlow",
    "ErrorScenario",
    "NFRMetric",
    "KPIMetric",
    "TelemetryEvent",
    "RiskItem",
    "ParsedPRD",
    "PRDParser",
]


class PRDParseError(Exception):
    """Raised when PRD document structure is malformed or unparseable."""
    pass


class PRDValidationError(Exception):
    """Raised when PRD violates architectural or governance rules (e.g. MoSCoW > 40%)."""
    pass


@dataclass(frozen=True)
class PRDMetadata:
    doc_id: str
    version: str
    status: str
    architect: str
    lead: str
    is_saas: bool
    is_mobile: bool
    is_iot: bool
    last_updated: str


@dataclass(frozen=True)
class StrategicParameter:
    name: str
    type: str
    value: str


@dataclass(frozen=True)
class FinancialMetric:
    name: str
    value: str


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    description: str

    def __post_init__(self):
        if not self.id:
            raise PRDValidationError("Persona ID cannot be empty")


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    user_story: str
    persona_id: str
    moscow: str
    acceptance_criteria: str
    event_id: str
    complexity: str

    def __post_init__(self):
        if not self.id:
            raise PRDValidationError("Requirement ID cannot be empty")


@dataclass(frozen=True)
class UserFlow:
    id: str
    title: str
    description: str


@dataclass(frozen=True)
class ErrorScenario:
    id: str
    condition: str
    action: str


@dataclass(frozen=True)
class NFRMetric:
    id: str
    category: str
    requirement: str


@dataclass(frozen=True)
class KPIMetric:
    id: str
    name: str
    baseline: str
    target: str


@dataclass(frozen=True)
class TelemetryEvent:
    id: str
    name: str
    trigger: str
    properties: str


@dataclass(frozen=True)
class RiskItem:
    id: str
    description: str
    mitigation: str


@dataclass(frozen=True)
class ParsedPRD:
    metadata: PRDMetadata
    strategy: List[StrategicParameter] = field(default_factory=list)
    financials: List[FinancialMetric] = field(default_factory=list)
    personas: List[Persona] = field(default_factory=list)
    requirements: List[Requirement] = field(default_factory=list)
    flows: List[UserFlow] = field(default_factory=list)
    errors: List[ErrorScenario] = field(default_factory=list)
    nfrs: List[NFRMetric] = field(default_factory=list)
    kpis: List[KPIMetric] = field(default_factory=list)
    events: List[TelemetryEvent] = field(default_factory=list)
    risks: List[RiskItem] = field(default_factory=list)


class PRDParser:
    """Parses modular Markdown PRDs and transpiles to Living Charter specs."""

    def _parse_metadata(self, content: str) -> PRDMetadata:
        doc_id = re.search(r'\*\*ID Dokumentu:\*\*\s*`([^`]+)`', content)
        ver = re.search(r'\*\*Wersja Schematu:\*\*\s*`([^`]+)`', content)
        stat = re.search(r'\*\*Status Dokumentu:\*\*\s*`([^`]+)`', content)
        arch = re.search(r'\*\*Architekt / PM:\*\*\s*`([^`]+)`', content)
        lead = re.search(r'\*\*Lead Inżynieryjny:\*\*\s*`([^`]+)`', content)
        upd = re.search(r'\*\*Data Ostatniej Aktualizacji:\*\*\s*`([^`]+)`', content)

        saas_m = re.search(r'is_SaaS:\s*\[([^\]]+)\]', content)
        mob_m = re.search(r'is_Mobile:\s*\[([^\]]+)\]', content)
        iot_m = re.search(r'is_Hardware_IoT:\s*\[([^\]]+)\]', content)

        return PRDMetadata(
            doc_id=doc_id.group(1) if doc_id else "UNKNOWN",
            version=ver.group(1) if ver else "UNKNOWN",
            status=stat.group(1) if stat else "UNKNOWN",
            architect=arch.group(1) if arch else "UNKNOWN",
            lead=lead.group(1) if lead else "UNKNOWN",
            is_saas="TRUE" in (saas_m.group(1) if saas_m else ""),
            is_mobile="TRUE" in (mob_m.group(1) if mob_m else ""),
            is_iot="TRUE" in (iot_m.group(1) if iot_m else ""),
            last_updated=upd.group(1) if upd else "UNKNOWN"
        )

    def _extract_table_rows(self, section_content: str) -> List[List[str]]:
        rows = []
        for line in section_content.split('\n'):
            line_s = line.strip()
            if not line_s.startswith('|'):
                continue
            if re.match(r'^\|[\s:-]+\|$', line_s) or line_s.startswith('| :---') or line_s.startswith('|:---') or line_s.startswith('| ---'):
                continue
            parts = [p.strip() for p in re.split(r'(?<!\\)\|', line_s)[1:-1]]
            if not parts:
                continue
            first_clean = re.sub(r'[*`]', '', parts[0]).strip().lower()
            if first_clean in ('id', 'kod') or first_clean.startswith('id ') or first_clean.startswith('kod ') or first_clean.startswith('parametr'):
                continue
            rows.append(parts)
        return rows

    def _normalize_acceptance_criteria(self, req_id: str, raw_ac: str) -> str:
        if any(kw in raw_ac.lower() for kw in ["given", "when", "then"]):
            return raw_ac
        return f"Given: requirement {req_id} configured. When: trigger condition met. Then: {raw_ac}"

    def _parse_req_row(self, parts: List[str]) -> Requirement:
        req_id = re.sub(r'[*`]', '', parts[0]).strip()
        title = parts[1].strip()
        if len(parts) > 8:
            user_story = ' | '.join(parts[2:-5]).strip()
            persona_id = re.sub(r'[*`]', '', parts[-5]).strip()
            moscow = re.sub(r'[*`]', '', parts[-4]).strip()
            raw_ac = parts[-3].strip()
            event_id = re.sub(r'[*`]', '', parts[-2]).strip()
            complexity = parts[-1].strip()
        else:
            user_story = parts[2].strip()
            persona_id = re.sub(r'[*`]', '', parts[3]).strip()
            moscow = re.sub(r'[*`]', '', parts[4]).strip()
            raw_ac = parts[5].strip()
            event_id = re.sub(r'[*`]', '', parts[6]).strip() if len(parts) > 6 else ""
            complexity = parts[7].strip() if len(parts) > 7 else "Unknown"

        ac = self._normalize_acceptance_criteria(req_id, raw_ac)
        return Requirement(
            id=req_id, title=title, user_story=user_story,
            persona_id=persona_id, moscow=moscow,
            acceptance_criteria=ac, event_id=event_id,
            complexity=complexity
        )

    def _parse_reqs(self, content: str) -> List[Requirement]:
        reqs = []
        sec = re.search(r'##\s*3\.\s*Zakres\s+Funkcjonalny.*?(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not sec:
            return reqs
        for parts in self._extract_table_rows(sec.group(0)):
            if len(parts) >= 7 and 'REQ-' in parts[0]:
                reqs.append(self._parse_req_row(parts))
        return reqs

    def _parse_personas(self, content: str) -> List[Persona]:
        personas = []
        sec = re.search(r'##\s*2\.\s*Grupa\s+Docelowa.*?(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not sec:
            return personas
        for parts in self._extract_table_rows(sec.group(0)):
            if len(parts) >= 3 and 'PER-' in parts[0]:
                personas.append(Persona(
                    id=re.sub(r'[*`]', '', parts[0]), name=parts[1], description=parts[2]
                ))
        return personas

    def _parse_flows_and_errors(self, content: str) -> Tuple[List[UserFlow], List[ErrorScenario]]:
        flows: List[UserFlow] = []
        errors: List[ErrorScenario] = []
        sec = re.search(r'##\s*4\.\s*Przepływy\s+Użytkownika.*?(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not sec:
            return flows, errors

        text = sec.group(0)
        for line in text.split('\n'):
            flow_m = re.search(r'\(`(FLOW-\d+)`\)', line)
            if flow_m:
                flows.append(UserFlow(id=flow_m.group(1), title=line.strip(), description=""))

        for parts in self._extract_table_rows(text):
            if len(parts) >= 3 and 'ERR-' in parts[0]:
                errors.append(ErrorScenario(
                    id=re.sub(r'[*`]', '', parts[0]),
                    condition=parts[1],
                    action=parts[2]
                ))
        return flows, errors

    def _parse_nfrs(self, content: str) -> List[NFRMetric]:
        nfrs = []
        sec = re.search(r'##\s*5\.\s*Wymagania\s+Niefunkcjonalne.*?(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not sec:
            return nfrs
        for parts in self._extract_table_rows(sec.group(0)):
            if len(parts) >= 3 and 'NFR-' in parts[0]:
                nfrs.append(NFRMetric(id=re.sub(r'[*`]', '', parts[0]), category=parts[1], requirement=parts[2]))
        return nfrs

    def _parse_kpis(self, content: str) -> List[KPIMetric]:
        kpis = []
        sec = re.search(r'###?\s*6\.1\..*?(?=\n###?\s*6\.2|\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not sec:
            return kpis
        for parts in self._extract_table_rows(sec.group(0)):
            if len(parts) >= 4 and not parts[0].startswith('---') and not parts[0].startswith(':--'):
                kpis.append(KPIMetric(id=re.sub(r'[*`]', '', parts[0]), name=parts[1], baseline=parts[2], target=parts[3]))
        return kpis

    def _parse_events(self, content: str) -> List[TelemetryEvent]:
        events = []
        sec = re.search(r'###?\s*6\.2\..*?(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not sec:
            return events
        for parts in self._extract_table_rows(sec.group(0)):
            if len(parts) >= 4 and 'EVT-' in parts[0]:
                events.append(TelemetryEvent(id=re.sub(r'[*`]', '', parts[0]), name=parts[1], trigger=parts[2], properties=parts[3]))
        return events

    def _parse_risks(self, content: str) -> List[RiskItem]:
        risks = []
        sec = re.search(r'###?\s*8\.1\..*?(?=\n###?\s*8\.2|\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not sec:
            return risks
        for parts in self._extract_table_rows(sec.group(0)):
            if len(parts) >= 3 and 'RSK-' in parts[0]:
                risks.append(RiskItem(id=re.sub(r'[*`]', '', parts[0]), description=parts[1], mitigation=parts[4] if len(parts) > 4 else ""))
        return risks

    def parse_markdown(self, content: str) -> ParsedPRD:
        if not isinstance(content, str):
            raise PRDParseError(f"PRD content must be a string, got {type(content).__name__}")

        flows, errors = self._parse_flows_and_errors(content)
        return ParsedPRD(
            metadata=self._parse_metadata(content),
            requirements=self._parse_reqs(content),
            personas=self._parse_personas(content),
            nfrs=self._parse_nfrs(content),
            kpis=self._parse_kpis(content),
            events=self._parse_events(content),
            risks=self._parse_risks(content),
            flows=flows,
            errors=errors,
        )

    def validate_moscow_limit(self, prd: ParsedPRD) -> bool:
        if not prd.requirements:
            return True

        def _is_must(moscow_str: str) -> bool:
            m = moscow_str.upper()
            if 'NOT MUST HAVE' in m or "WON'T HAVE" in m or "WONT HAVE" in m:
                return False
            return bool(re.search(r'\bMUST\s+HAVE\b', m))

        must_have = [r for r in prd.requirements if _is_must(r.moscow)]
        ratio = len(must_have) / len(prd.requirements)
        if ratio > 0.40:
            raise PRDValidationError(f"MUST HAVE requirements exceed 40% ({ratio*100:.1f}%)")
        return True

    def transpile_to_specs(self, prd: ParsedPRD, output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        req_path = output_dir / "01_PRODUCT_REQUIREMENTS.md"
        dict_path = output_dir / "03_DATA_DICTIONARY.md"
        trace_path = output_dir / "05_TRACEABILITY_MATRIX.md"

        req_content = "# Product Requirements\n"
        for r in prd.requirements:
            req_content += f"## {r.id}: {r.title}\n{r.user_story}\n{r.acceptance_criteria}\n"
        req_path.write_text(req_content, encoding='utf-8')

        dict_path.write_text("# Data Dictionary\n", encoding='utf-8')

        trace_content = "# Traceability Matrix\n| REQ | Persona | Event |\n|---|---|---|\n"
        for r in prd.requirements:
            trace_content += f"| {r.id} | {r.persona_id} | {r.event_id} |\n"
        trace_path.write_text(trace_content, encoding='utf-8')

        return {
            "01_PRODUCT_REQUIREMENTS.md": req_path,
            "03_DATA_DICTIONARY.md": dict_path,
            "05_TRACEABILITY_MATRIX.md": trace_path
        }

    def to_dag_task_atoms(self, prd: ParsedPRD) -> List[Dict[str, Any]]:
        atoms = []
        for i, r in enumerate(prd.requirements):
            atoms.append({
                "id": f"task_{r.id}",
                "description": f"Implement {r.title}",
                "allowed_paths": [f"src/features/{r.id.lower()}"],
                "depends_on": [] if i == 0 else [f"task_{prd.requirements[i-1].id}"]
            })
        return atoms
