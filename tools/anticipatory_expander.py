#!/usr/bin/env python3
"""Anticipatory Archetype Expander for Antigravity v8.5.

Predicts the 80% hidden iceberg of production requirements (Idempotency, Security,
Resilience, DB, SRE, Config, A11y, Adverse Tests) and binds mandatory skills and tools
to tasks, eliminating AI blind spots before coding begins.
Adheres strictly to the 7 DREE Invariants and SRP <= 40 lines.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("anticipatory_expander")

__all__ = [
    "AnticipatoryExpansionError",
    "UnknownArchetypeError",
    "AnticipatedRequirement",
    "ArchetypeDefinition",
    "ExpansionResult",
    "AnticipatoryExpander",
    "main",
]


class AnticipatoryExpansionError(Exception):
    """Base exception for anticipatory expansion errors."""


class UnknownArchetypeError(AnticipatoryExpansionError):
    """Raised when an unrecognized archetype key is referenced."""


@dataclass(frozen=True)
class AnticipatedRequirement:
    """Represents a predicted hidden production requirement."""

    code: str
    title: str
    description: str
    vector: str  # One of the 8 production vectors
    required_skills: Tuple[str, ...]
    required_tools: Tuple[str, ...]
    acceptance_criteria: str

    def __post_init__(self) -> None:
        if not self.code or not self.code.strip():
            raise AnticipatoryExpansionError("Requirement code cannot be empty")
        if not self.title or not self.title.strip():
            raise AnticipatoryExpansionError("Requirement title cannot be empty")
        if not self.vector or not self.vector.strip():
            raise AnticipatoryExpansionError("Production vector cannot be empty")


@dataclass(frozen=True)
class ArchetypeDefinition:
    """Defines an engineering archetype and its baseline production requirements."""

    name: str
    description: str
    keywords: Tuple[str, ...]
    requirements: Tuple[AnticipatedRequirement, ...]

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise AnticipatoryExpansionError("Archetype name cannot be empty")
        if not self.requirements:
            raise AnticipatoryExpansionError(f"Archetype '{self.name}' must define requirements")


@dataclass(frozen=True)
class ExpansionResult:
    """Summary of anticipated requirements expansion."""

    detected_archetypes: Tuple[str, ...]
    added_requirements: Tuple[AnticipatedRequirement, ...]
    total_added: int
    profile: str

    def __post_init__(self) -> None:
        if self.total_added < 0:
            raise AnticipatoryExpansionError("total_added cannot be negative")


class AnticipatoryExpander:
    """Orchestrates archetypal analysis and proactive tool binding."""

    ARCHETYPES: Dict[str, ArchetypeDefinition] = {
        "BILLING_CHECKOUT": ArchetypeDefinition(
            name="Billing & Checkout",
            description="Payment gateways, checkout funnels, invoicing, subscriptions",
            keywords=(
                "payment", "billing", "checkout", "stripe", "invoice", "subscription",
                "order", "cart", "płatnoś", "faktur", "subskrypc", "zamówien", "koszyk",
            ),
            requirements=(
                AnticipatedRequirement(
                    code="REQ-IDEMP-01",
                    title="Idempotency-Key & Replay Defense",
                    description="Guarantees single execution for concurrent payment or charge calls",
                    vector="IDEMPOTENCY",
                    required_skills=("clean-code", "database-design"),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given duplicate Idempotency-Key When charge is sent Then returns cached 200 without second charge",
                ),
                AnticipatedRequirement(
                    code="REQ-CURR-01",
                    title="Currency Strict Integer Cents Representation",
                    description="Prohibits floating-point numbers for financial amounts (Rule 50 DREE)",
                    vector="INTEGRITY",
                    required_skills=("clean-code",),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given financial transaction When monetary amount stored Then stored as integer cents without float",
                ),
            ),
        ),
        "AUTH_IDENTITY": ArchetypeDefinition(
            name="Authentication & Identity",
            description="Login, registration, token refresh, sessions, OAuth, RBAC",
            keywords=(
                "auth", "login", "oauth", "jwt", "session", "user", "permission",
                "rbac", "password", "autoryzac", "uwierzyteln", "użytkown",
            ),
            requirements=(
                AnticipatedRequirement(
                    code="REQ-AUTH-RATE-01",
                    title="Rate Limiting & Brute-Force Lockout",
                    description="Restricts consecutive failed login attempts per IP/user",
                    vector="SECURITY",
                    required_skills=("wp-security-guardrails", "adversarial-resilience"),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given 5 consecutive failed login attempts When 6th attempt made Then returns HTTP 429 Too Many Requests",
                ),
                AnticipatedRequirement(
                    code="REQ-AUTH-SAFE-01",
                    title="Timing-Safe Password & Secret Verification",
                    description="Prevents side-channel timing attacks during hash comparisons",
                    vector="SECURITY",
                    required_skills=("clean-code", "wp-security-guardrails"),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given credential verification When string compare executed Then uses constant-time compare algorithm",
                ),
            ),
        ),
        "API_MICROSERVICE": ArchetypeDefinition(
            name="API & Microservice Router",
            description="REST, GraphQL, or RPC backend service endpoints and routing",
            keywords=("api", "endpoint", "rest", "graphql", "microservice", "router", "controller"),
            requirements=(
                AnticipatedRequirement(
                    code="REQ-API-HEALTH-01",
                    title="Healthcheck & Readiness Probes (/healthz, /readyz)",
                    description="Standardized orchestration liveness and readiness endpoints",
                    vector="SRE_OBSERVABILITY",
                    required_skills=("nodejs-best-practices", "clean-code"),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given GET /healthz request When system dependencies active Then returns HTTP 200 with JSON status UP",
                ),
                AnticipatedRequirement(
                    code="REQ-API-CID-01",
                    title="Structured Correlation-ID & Request Tracing",
                    description="Injects and logs unique X-Correlation-ID across all downstream calls",
                    vector="SRE_OBSERVABILITY",
                    required_skills=("clean-code",),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given incoming HTTP request When missing X-Correlation-ID Then generates UUID and attaches to response",
                ),
            ),
        ),
        "FRONTEND_UI": ArchetypeDefinition(
            name="Frontend UI & Dashboard",
            description="Interactive components, single-page apps, dashboards, client forms",
            keywords=("ui", "frontend", "component", "screen", "dashboard", "react", "vue", "template", "view"),
            requirements=(
                AnticipatedRequirement(
                    code="REQ-UI-STATES-01",
                    title="Quad Edge-States (Loading, Empty, Error, Success)",
                    description="Mandates explicit UI states eliminating blank or broken views",
                    vector="UX_EDGE_STATES",
                    required_skills=("better-interface", "ui-design-direction"),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given empty data set When view renders Then displays user-friendly empty state with call-to-action",
                ),
                AnticipatedRequirement(
                    code="REQ-UI-A11Y-01",
                    title="EAA 2025 / WCAG 2.1 AA 48px Touch Targets & Contrast",
                    description="Accessibility compliance with minimum 48x48dp interactive areas",
                    vector="ACCESSIBILITY",
                    required_skills=("a11y-audit", "better-interface"),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given interactive buttons When measured on mobile Then bounding box >= 48px and contrast ratio >= 4.5:1",
                ),
            ),
        ),
        "ASYNC_WORKER": ArchetypeDefinition(
            name="Async Worker & Event Queue",
            description="Background jobs, Celery, BullMQ, Kafka, RabbitMQ consumers",
            keywords=("worker", "queue", "kafka", "rabbitmq", "celery", "job", "consumer", "background"),
            requirements=(
                AnticipatedRequirement(
                    code="REQ-QUEUE-DLQ-01",
                    title="Dead-Letter Queue (DLQ) & Poison Pill Isolation",
                    description="Routes permanently failing messages to DLQ after max retries",
                    vector="RESILIENCE",
                    required_skills=("self-healing-agents", "clean-code"),
                    required_tools=("gov.py check-standards",),
                    acceptance_criteria="Given unparseable payload When processed 3 times Then routed to DLQ without blocking worker queue",
                ),
            ),
        ),
    }

    @classmethod
    def detect_archetypes(cls, text: str) -> List[ArchetypeDefinition]:
        """Detects relevant engineering archetypes from brief, PRD, or code snippet."""
        lower_text = text.lower()
        detected: List[ArchetypeDefinition] = []
        for arch in cls.ARCHETYPES.values():
            if any(kw in lower_text for kw in arch.keywords):
                detected.append(arch)
        return detected

    @classmethod
    def expand_requirements(
        cls,
        brief_text: str,
        existing_codes: Optional[Set[str]] = None,
        profile: str = "production",
    ) -> ExpansionResult:
        """Expands user brief with hidden production requirements based on detected archetypes."""
        if not brief_text or not brief_text.strip():
            raise AnticipatoryExpansionError("brief_text cannot be empty")
        detected = cls.detect_archetypes(brief_text)
        known_codes = existing_codes or set()
        added: List[AnticipatedRequirement] = []
        if profile.lower() != "lean":
            for arch in detected:
                for req in arch.requirements:
                    if req.code not in known_codes:
                        added.append(req)
                        known_codes.add(req.code)
        return ExpansionResult(
            detected_archetypes=tuple(a.name for a in detected),
            added_requirements=tuple(added),
            total_added=len(added),
            profile=profile,
        )

    @classmethod
    def _match_skills_for_task(cls, text_blob: str) -> Tuple[List[str], List[str]]:
        skills: List[str] = ["clean-code"]
        tools: List[str] = ["gov.py check-standards"]
        lower = text_blob.lower()
        if any(k in lower for k in ("ui", "frontend", "component", "screen", "page", "react", "vue", "html", "css")):
            skills.extend(["better-interface", "a11y-audit", "ui-design-direction"])
        if any(k in lower for k in ("auth", "security", "token", "password", "crypto", "login")):
            skills.extend(["wp-security-guardrails", "adversarial-resilience"])
        if any(k in lower for k in ("db", "database", "sql", "sqlite", "postgres", "billing", "payment")):
            skills.extend(["database-design"])
        if any(k in lower for k in ("api", "endpoint", "rest", "router", "service")):
            skills.extend(["api-patterns"])
        dedup_skills = sorted(list(set(skills)))
        return dedup_skills, tools

    @classmethod
    def enrich_tasks_with_skills_and_tools(cls, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Injects required_skills and required_tools into task definitions."""
        enriched: List[Dict[str, Any]] = []
        for t in tasks:
            task_copy = dict(t)
            blob = f"{task_copy.get('id', '')} {task_copy.get('title', '')} {' '.join(task_copy.get('allowed_paths', []))}"
            skills, tools = cls._match_skills_for_task(blob)
            existing_skills = task_copy.get("required_skills", [])
            existing_tools = task_copy.get("required_tools", [])
            task_copy["required_skills"] = sorted(list(set(existing_skills + skills)))
            task_copy["required_tools"] = sorted(list(set(existing_tools + tools)))
            enriched.append(task_copy)
        return enriched


def main() -> int:
    """CLI Entry point for anticipatory_expander."""
    parser = argparse.ArgumentParser(description="Antigravity Anticipatory Archetype Expander v8.5")
    parser.add_argument("--brief", "-b", help="Raw brief or requirements text")
    parser.add_argument("--file", "-f", help="Path to input text file (e.g. PRD or brief)")
    parser.add_argument("--profile", "-p", default="production", choices=["lean", "production", "mission-critical"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    text = args.brief
    if args.file:
        p = Path(args.file).resolve()
        if p.is_file():
            text = p.read_text(encoding="utf-8")
    if not text:
        logger.error("Must provide either --brief or --file")
        return 1
    try:
        res = AnticipatoryExpander.expand_requirements(text, profile=args.profile)
        logger.info("Detected %d archetypes: %s", len(res.detected_archetypes), ", ".join(res.detected_archetypes))
        logger.info("Anticipated %d hidden production requirements (profile: %s):", res.total_added, res.profile)
        for req in res.added_requirements:
            logger.info("  * [%s] (%s) %s -> %s", req.code, req.vector, req.title, req.acceptance_criteria)
        return 0
    except Exception as exc:
        logger.error("Anticipatory expansion failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
