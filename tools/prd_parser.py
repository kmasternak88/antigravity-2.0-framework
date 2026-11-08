import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

class PRDParseError(Exception): pass
class PRDValidationError(Exception): pass

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
    def _parse_metadata(self, content: str) -> PRDMetadata:
        doc_id = re.search(r'\*\*ID Dokumentu:\*\*\s*`([^`]+)`', content)
        ver = re.search(r'\*\*Wersja Schematu:\*\*\s*`([^`]+)`', content)
        stat = re.search(r'\*\*Status Dokumentu:\*\*\s*`([^`]+)`', content)
        arch = re.search(r'\*\*Architekt / PM:\*\*\s*`([^`]+)`', content)
        lead = re.search(r'\*\*Lead Inżynieryjny:\*\*\s*`([^`]+)`', content)
        upd = re.search(r'\*\*Data Ostatniej Aktualizacji:\*\*\s*`([^`]+)`', content)

        saas = "TRUE" in re.search(r'is_SaaS:\s*\[([^\]]+)\]', content).group(1) if re.search(r'is_SaaS:\s*\[([^\]]+)\]', content) else False
        mobile = "TRUE" in re.search(r'is_Mobile:\s*\[([^\]]+)\]', content).group(1) if re.search(r'is_Mobile:\s*\[([^\]]+)\]', content) else False
        iot = "TRUE" in re.search(r'is_Hardware_IoT:\s*\[([^\]]+)\]', content).group(1) if re.search(r'is_Hardware_IoT:\s*\[([^\]]+)\]', content) else False

        return PRDMetadata(
            doc_id=doc_id.group(1) if doc_id else "UNKNOWN",
            version=ver.group(1) if ver else "UNKNOWN",
            status=stat.group(1) if stat else "UNKNOWN",
            architect=arch.group(1) if arch else "UNKNOWN",
            lead=lead.group(1) if lead else "UNKNOWN",
            is_saas=saas,
            is_mobile=mobile,
            is_iot=iot,
            last_updated=upd.group(1) if upd else "UNKNOWN"
        )

    def _extract_table_rows(self, section_content: str) -> List[List[str]]:
        rows = []
        for line in section_content.split('\n'):
            if line.strip().startswith('|') and not line.strip().startswith('| :---') and not 'ID' in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if parts:
                    rows.append(parts)
        return rows

    def _parse_reqs(self, content: str) -> List[Requirement]:
        reqs = []
        section = re.search(r'## 3\. Zakres Funkcjonalny.*?(?=## 4\.)', content, re.DOTALL)
        if not section:
            return reqs
        for parts in self._extract_table_rows(section.group(0)):
            if len(parts) >= 7 and 'REQ-' in parts[0]:
                req_id = re.sub(r'[*`]', '', parts[0])
                reqs.append(Requirement(
                    id=req_id, title=parts[1], user_story=parts[2],
                    persona_id=parts[3], moscow=parts[4],
                    acceptance_criteria=parts[5], event_id=parts[6],
                    complexity=parts[7] if len(parts)>7 else "Unknown"
                ))
        return reqs

    def _parse_personas(self, content: str) -> List[Persona]:
        personas = []
        section = re.search(r'## 2\. Grupa Docelowa.*?(?=## 3\.)', content, re.DOTALL)
        if not section:
            return personas
        for parts in self._extract_table_rows(section.group(0)):
             if len(parts) >= 3 and 'PER-' in parts[0]:
                  personas.append(Persona(
                      id=re.sub(r'[*`]', '', parts[0]), name=parts[1], description=parts[2]
                  ))
        return personas

    def _parse_flows_and_errors(self, content: str) -> (List[UserFlow], List[ErrorScenario]):
        flows, errors = [], []
        section = re.search(r'## 4\. Przepływy Użytkownika.*?(?=## 5\.)', content, re.DOTALL)
        if section:
             for line in section.group(0).split('\n'):
                 flow_match = re.search(r'\(`(FLOW-\d+)`\)', line)
                 if flow_match:
                     flows.append(UserFlow(id=flow_match.group(1), title=line.strip(), description=""))
                 err_match = re.search(r'ERR-FLOW-', line)
                 if err_match:
                     errors.append(ErrorScenario(id="ERR", condition="Condition", action="Action")) # Placeholder parsing
        return flows, errors

    def _parse_nfrs(self, content: str) -> List[NFRMetric]:
        nfrs = []
        section = re.search(r'## 5\. Wymagania Niefunkcjonalne.*?(?=## 6\.)', content, re.DOTALL)
        if not section: return nfrs
        for parts in self._extract_table_rows(section.group(0)):
            if len(parts) >= 3 and 'NFR-' in parts[0]:
                 nfrs.append(NFRMetric(id=re.sub(r'[*`]', '', parts[0]), category=parts[1], requirement=parts[2]))
        return nfrs

    def _parse_kpis(self, content: str) -> List[KPIMetric]:
        kpis = []
        section = re.search(r'### 6\.1\..*?(?=### 6\.2\.)', content, re.DOTALL)
        if not section: return kpis
        for parts in self._extract_table_rows(section.group(0)):
             if len(parts) >= 4:
                 kpis.append(KPIMetric(id=re.sub(r'[*`]', '', parts[0]), name=parts[1], baseline=parts[2], target=parts[3]))
        return kpis

    def _parse_events(self, content: str) -> List[TelemetryEvent]:
        events = []
        section = re.search(r'### 6\.2\..*?(?=## 7\.)', content, re.DOTALL)
        if not section: return events
        for parts in self._extract_table_rows(section.group(0)):
             if len(parts) >= 4 and 'EVT-' in parts[0]:
                 events.append(TelemetryEvent(id=re.sub(r'[*`]', '', parts[0]), name=parts[1], trigger=parts[2], properties=parts[3]))
        return events

    def _parse_risks(self, content: str) -> List[RiskItem]:
        risks = []
        section = re.search(r'### 8\.1\..*?(?=### 8\.2\.)', content, re.DOTALL)
        if not section: return risks
        for parts in self._extract_table_rows(section.group(0)):
             if len(parts) >= 3 and 'RSK-' in parts[0]:
                  risks.append(RiskItem(id=re.sub(r'[*`]', '', parts[0]), description=parts[1], mitigation=parts[4] if len(parts)>4 else ""))
        return risks

    def parse_markdown(self, content: str) -> ParsedPRD:
        return ParsedPRD(
            metadata=self._parse_metadata(content),
            requirements=self._parse_reqs(content),
            personas=self._parse_personas(content),
            nfrs=self._parse_nfrs(content),
            kpis=self._parse_kpis(content),
            events=self._parse_events(content),
            risks=self._parse_risks(content),
            flows=self._parse_flows_and_errors(content)[0],
            errors=self._parse_flows_and_errors(content)[1],
        )

    def validate_moscow_limit(self, prd: ParsedPRD) -> bool:
        if not prd.requirements:
            return True
        must_have = [r for r in prd.requirements if 'MUST HAVE' in r.moscow.upper()]
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
        req_path.write_text(req_content)

        dict_path.write_text("# Data Dictionary\n")

        trace_content = "# Traceability Matrix\n| REQ | Persona | Event |\n|---|---|---|\n"
        for r in prd.requirements:
            trace_content += f"| {r.id} | {r.persona_id} | {r.event_id} |\n"
        trace_path.write_text(trace_content)

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
