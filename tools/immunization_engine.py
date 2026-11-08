#!/usr/bin/env python3
"""Cross-Task Error Immunization Buffer for Antigravity v8.4.

Distills actionable negative constraints from FEEDBACK_PACKET.json and injects them
into upcoming subagent handoff prompts, preventing repeat errors across execution waves.
Adheres strictly to the 7 DREE Invariants and SRP <= 40 lines.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("immunization_engine")

__all__ = [
    "ImmunizationError",
    "InvalidFeedbackPacketError",
    "ImmunizationRule",
    "ImmunizationState",
    "ImmunizationResult",
    "ImmunizationEngine",
    "main",
]


class ImmunizationError(Exception):
    """Base exception for immunization engine errors."""


class InvalidFeedbackPacketError(ImmunizationError):
    """Raised when FEEDBACK_PACKET structure is invalid or corrupt."""


@dataclass(frozen=True)
class ImmunizationRule:
    """Represents a single synthesized prevention rule (negative constraint)."""

    rule_id: str
    target_module: str
    error_category: str
    negative_constraint: str
    recommended_fix: str
    timestamp: float
    ttl_seconds: int = 86400

    def __post_init__(self) -> None:
        if not self.rule_id or not self.rule_id.strip():
            raise InvalidFeedbackPacketError("rule_id cannot be empty")
        if not self.negative_constraint or not self.negative_constraint.strip():
            raise InvalidFeedbackPacketError("negative_constraint cannot be empty")
        if self.ttl_seconds <= 0:
            raise InvalidFeedbackPacketError("ttl_seconds must be positive")

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Checks if rule validity has exceeded TTL."""
        now = current_time or time.time()
        return (now - self.timestamp) > self.ttl_seconds


@dataclass(frozen=True)
class ImmunizationState:
    """Snapshot of active immunization rules for a project."""

    project_id: str
    version: str
    rules: Tuple[ImmunizationRule, ...]

    def __post_init__(self) -> None:
        if not self.project_id or not self.project_id.strip():
            raise InvalidFeedbackPacketError("project_id cannot be empty")


@dataclass(frozen=True)
class ImmunizationResult:
    """Summary of immunization operation."""

    status: str
    rules_count: int
    state_path: str

    def __post_init__(self) -> None:
        if self.rules_count < 0:
            raise InvalidFeedbackPacketError("rules_count cannot be negative")


class ImmunizationEngine:
    """Processes feedback packets and manages active prompt immunization."""

    RULE_TEMPLATES = {
        "SRP_VIOLATION": ("Nigdy nie przekraczaj limitu 40 linii na funkcję.", "Zastosuj podział na mniejsze funkcje pomocnicze."),
        "MOCK_TAUTOLOGY": ("Nigdy nie twórz pozornych testów z asercją na mockowaną wartość.", "Weryfikuj stan wyjściowy lub realne zachowanie domeny."),
        "IMPORT_ERROR": ("Nigdy nie używaj niesprawdzonych importów spoza kontraktu.", "Sprawdź pliki w contracts/ i używaj ścisłych aliasów."),
        "SYNTAX_ERROR": ("Nigdy nie generuj nieskompilowanego kodu.", "Wykonaj statyczną weryfikację AST przed zapisem."),
        "TYPE_ERROR": ("Nigdy nie mieszaj niekompatybilnych typów (np. float dla kwot walutowych).", "Używaj wyłącznie integer cents lub Decimal."),
        "SCHEMA_MISMATCH": ("Nigdy nie modyfikuj zamrożonych pól kontraktu DTO.", "Dostosuj implementację do interfejsu lub zainicjuj procedurę RFC."),
    }

    @classmethod
    def _create_rule(cls, finding: Dict[str, Any], project_id: str) -> ImmunizationRule:
        cat = str(finding.get("category", "GENERAL")).upper()
        target = str(finding.get("file", finding.get("target", "all")))
        msg = str(finding.get("message", "Naruszenie standardu"))
        neg_default, fix_default = cls.RULE_TEMPLATES.get(
            cat,
            ("Nigdy nie ignoruj wykrytych naruszeń standardu.", "Popraw kod zgodnie z wytycznymi audytora.")
        )
        neg_constraint = f"INVARIANT [{Path(target).name}]: {neg_default} Szegóły błędu: {msg}"
        fix_advice = str(finding.get("remediation", fix_default))
        rule_hash = uuid.uuid5(uuid.NAMESPACE_DNS, f"{project_id}_{target}_{cat}_{msg}").hex[:8].upper()
        return ImmunizationRule(
            rule_id=f"IMM-{rule_hash}",
            target_module=target,
            error_category=cat,
            negative_constraint=neg_constraint,
            recommended_fix=fix_advice,
            timestamp=time.time(),
        )

    @classmethod
    def distill_from_packet(cls, packet_data: Dict[str, Any], project_id: str = "default") -> List[ImmunizationRule]:
        """Distills immunization rules from feedback packet findings."""
        findings = packet_data.get("findings", [])
        if not isinstance(findings, list):
            raise InvalidFeedbackPacketError("Feedback packet 'findings' must be a list")
        rules: List[ImmunizationRule] = []
        for finding in findings:
            if isinstance(finding, dict):
                rules.append(cls._create_rule(finding, project_id))
        return rules

    @classmethod
    def save_rules(cls, rules: List[ImmunizationRule], state_file: Path, project_id: str = "default") -> ImmunizationResult:
        """Saves immunization rules into JSON state file."""
        state_file.parent.mkdir(parents=True, exist_ok=True)
        raw_list = [
            {
                "rule_id": r.rule_id,
                "target_module": r.target_module,
                "error_category": r.error_category,
                "negative_constraint": r.negative_constraint,
                "recommended_fix": r.recommended_fix,
                "timestamp": r.timestamp,
                "ttl_seconds": r.ttl_seconds,
            }
            for r in rules
        ]
        payload = {"project_id": project_id, "version": "8.4.0", "rules": raw_list}
        state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return ImmunizationResult(status="SAVED", rules_count=len(rules), state_path=str(state_file))

    @classmethod
    def load_rules(cls, state_file: Path) -> List[ImmunizationRule]:
        """Loads and returns unexpired immunization rules from state file."""
        if not state_file.is_file():
            return []
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            raw_rules = data.get("rules", [])
            rules: List[ImmunizationRule] = []
            now = time.time()
            for r in raw_rules:
                rule = ImmunizationRule(
                    rule_id=str(r["rule_id"]),
                    target_module=str(r["target_module"]),
                    error_category=str(r["error_category"]),
                    negative_constraint=str(r["negative_constraint"]),
                    recommended_fix=str(r["recommended_fix"]),
                    timestamp=float(r["timestamp"]),
                    ttl_seconds=int(r.get("ttl_seconds", 86400)),
                )
                if not rule.is_expired(now):
                    rules.append(rule)
            return rules
        except Exception as exc:
            logger.warning("Failed to load immunization rules from %s: %s", state_file, exc)
            return []

    @classmethod
    def filter_rules_for_target(cls, rules: List[ImmunizationRule], target_paths: List[str]) -> List[ImmunizationRule]:
        """Filters rules relevant to the target paths or marked for all modules."""
        if not target_paths:
            return rules[:5]
        target_basenames = {Path(p).name for p in target_paths}
        selected: List[ImmunizationRule] = []
        for r in rules:
            if r.target_module.lower() in {"all", "*"} or Path(r.target_module).name in target_basenames:
                selected.append(r)
        return selected if selected else rules[:3]

    @classmethod
    def format_prompt_injection(cls, rules: List[ImmunizationRule]) -> str:
        """Formats active rules as an XML guardrail block for agent prompts."""
        if not rules:
            return ""
        lines = [
            "<cross_task_immunization_guardrails>",
            "  <!-- Aktywne reguły zapobiegawcze z poprzednich cykli naprawczych (Self-Healing Memory) -->",
        ]
        for r in rules:
            lines.append(f'  <rule id="{r.rule_id}" category="{r.error_category}">')
            lines.append(f"    <negative_constraint>{r.negative_constraint}</negative_constraint>")
            lines.append(f"    <recommended_fix>{r.recommended_fix}</recommended_fix>")
            lines.append("  </rule>")
        lines.append("</cross_task_immunization_guardrails>")
        return "\n".join(lines)


def main() -> int:
    """CLI Entry point for immunization_engine."""
    parser = argparse.ArgumentParser(description="Antigravity Cross-Task Error Immunization Engine v8.4")
    parser.add_argument("action", choices=["distill", "inject", "list"], help="Action to execute")
    parser.add_argument("--packet", "-p", default="FEEDBACK_PACKET.json", help="Path to FEEDBACK_PACKET.json")
    parser.add_argument("--state", "-s", default=".governance/state/immunization.json", help="State file path")
    parser.add_argument("--paths", default="", help="Comma-separated target paths for prompt injection")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    state_p = Path(args.state).resolve()
    if args.action == "distill":
        p_path = Path(args.packet).resolve()
        if not p_path.is_file():
            logger.error("Feedback packet not found: %s", p_path)
            return 1
        data = json.loads(p_path.read_text(encoding="utf-8"))
        rules = ImmunizationEngine.distill_from_packet(data)
        existing = ImmunizationEngine.load_rules(state_p)
        merged = {r.rule_id: r for r in (existing + rules)}.values()
        res = ImmunizationEngine.save_rules(list(merged), state_p)
        logger.info("Distilled and saved %d rules into %s", res.rules_count, res.state_path)
        return 0
    elif args.action == "inject":
        rules = ImmunizationEngine.load_rules(state_p)
        paths = [p.strip() for p in args.paths.split(",") if p.strip()]
        filtered = ImmunizationEngine.filter_rules_for_target(rules, paths)
        prompt_block = ImmunizationEngine.format_prompt_injection(filtered)
        sys.stdout.write(prompt_block + "\n")
        return 0
    elif args.action == "list":
        rules = ImmunizationEngine.load_rules(state_p)
        logger.info("Found %d active immunization rules in %s", len(rules), state_p)
        for r in rules:
            logger.info("  * [%s] %s -> %s", r.rule_id, r.error_category, r.negative_constraint)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
