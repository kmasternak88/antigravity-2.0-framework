# JULES HYBRID ORCHESTRATION ARCHITECTURE (ANTIGRAVITY v8.3)

> **Status:** Production Standard (SSoT)
> **Framework:** Antigravity Ultra v8.3 Omni-Agentic OS
> **Target Integration:** Google Jules Agent via FastMCP Server (`ahaufox/jules-mcp-server`)
> **Architectural Paradigm:** Polyglot Omni-Stack, Evidence-First Dual-Control, Sovereign Dual-Sync Git Pipeline

---

## 1. Executive Summary & Philosophy

Antigravity v8.3 operates as the **Sovereign Engineering Directorate & Auditor** (Tier 1 Global Orchestration & Tier 2 Task Supervision).
Google Jules operates as a **Specialized Cloud Builder-Executor** (Tier 3 Cloud Implementor).

This architecture implements a closed, multi-agent loop with ironclad quality gates (G0–G7), where Jules implements code in the cloud while Antigravity governs specifications, reviews plans before execution, verifies cryptographic evidence, and strictly enforces the **Standard of 7 DREE Invariants** and **Cardinal Rule 12 (3-Cycle Self-Healing Budget)**.

### Universal Polyglot Invariant
Antigravity is completely stack-agnostic. The Antigravity $\leftrightarrow$ Jules loop natively supports:
- **Python:** `@dataclass(frozen=True, slots=True)`, Pydantic v2, pytest / unittest.
- **TypeScript / Node.js:** Zod schemas, immutable readonly interfaces, Vitest / Jest.
- **PHP:** Typed DTOs, PHP 8.2+ readonly classes, Pest / PHPUnit.
- **Go:** Immutable structs, strict error returns, testify / testing.
- **Rust:** Typed structs, Result<T, E>, cargo test.
- **C++:** constexpr, strong typing, GoogleTest.

Contracts frozen in `contracts/` are generated according to the detected project stack prior to Jules session creation.

---

## 2. Three-Tier Multi-Agent Hierarchy

```
+-------------------------------------------------------------------------+
|                       TIER 1: PROJECT-ORCHESTRATOR                      |
|  - Global Kahn DAG (.governance/tasks.json)                             |
|  - Topological Wave Scheduling with Zero-Overlap Invariant               |
|  - Triple Lock Governance (allowed_paths, AST symbols, API routes)      |
|  - Remote Git Branch Management & Pre-Merge Interlock (Gate G6)         |
|  - Operational Release Certification (Gate G7)                          |
+------------------------------------+------------------------------------+
                                     | Dispatches Task
                                     v
+-------------------------------------------------------------------------+
|                        TIER 2: TASK-SUPERVISOR                          |
|  - Isolated LLM Session & Unique GOV_AUDITOR_TOKEN                      |
|  - Automatic Socratic Plan Audit (Allowed Paths, Contracts, DREE)       |
|  - approve_session_plan vs REJECTED_PLAN Loop                           |
|  - Local Worktree Verification (.worktrees/<task_id>)                   |
|  - G4 DREE Invariant Check & G5.1 Mock-Breaker Mutation Audit           |
|  - FEEDBACK_PACKET_<task_id>.json Generation                            |
|  - Independent Gate G5.2 Sign-off (Dual-Control: reviewer != actor)     |
+------------------------------------+------------------------------------+
                                     | MCP Bridge (FastMCP Tools)
                                     v
+-------------------------------------------------------------------------+
|                     TIER 3: CLOUD BUILDER-EXECUTOR                      |
|                             (GOOGLE JULES)                              |
|  - Operates on GitHub Remote Branch: task/<task_id>                     |
|  - Generates Step-by-Step Plan requiring Supervisor approval            |
|  - Implements vertical slices conforming to contracts/                  |
|  - Consumes FEEDBACK_PACKET prompts in <= 3 self-healing cycles         |
|  - Commits directly to remote branch                                    |
|  - STRICTLY FORBIDDEN FROM SELF-CERTIFICATION                           |
+-------------------------------------------------------------------------+
```

---

## 3. Finite State Machine (Execution Lifecycle)

The lifecycle of a task handled by Google Jules follows a deterministic 9-state machine:

```
[INIT]
  |
  +--> Orchestrator verifies Kahn DAG, generates contracts/, freezes G2 Spec Lock.
  v
[BRANCH_PUSHED]
  |
  +--> Antigravity creates branch `task/<task_id>`, commits TASK_BRIEF.md & contracts/,
  |    and pushes to `origin task/<task_id>`.
  v
[SESSION_CREATED]
  |
  +--> Antigravity calls MCP `create_session` with `require_plan_approval=True`
  |    and contextual handoff prompt.
  v
[PLAN_AUDIT] <---------------------------------------------+
  |                                                         |
  +--> Supervisor polls session until AWAITING_PLAN_APPROVAL| Plan Rejected
  |    Supervisor audits plan: allowed_paths, contracts,    | with EARS
  |    DREE invariants.                                     | prompt
  +---------------------------------------------------------+
  |
  v (Plan Approved)
[PLAN_APPROVED]
  |
  +--> Supervisor calls MCP `approve_session_plan(session_id)`.
  v
[POLL_COMPLETION]
  |
  +--> Antigravity awaits Jules completion (`wait_for_session_completion` or periodic activity polling).
  v
[PR_FETCH]
  |
  +--> Antigravity fetches remote commits into local Git Worktree:
  |    `git fetch origin task/<task_id>` into `.worktrees/<task_id>`.
  v
[G4_G5_AUDIT]
  |
  +--> Supervisor runs local checks inside worktree:
  |    - `gov.py check-standards --task <task_id>` (G4 DREE AST verification)
  |    - `gov.py run --task <task_id> --check <check>` (Exit code 0 evidence)
  |    - `gov.py audit-tests --task <task_id>` (G5.1 Mock-Breaker mutation resistance)
  |
  +---------> If failures & Iteration < 3:
  |             Generates FEEDBACK_PACKET_<task_id>.json,
  |             Sends structured prompt via `send_session_message`,
  |             Transitions back to [POLL_COMPLETION].
  |
  +---------> If failures & Iteration == 3:
  |             Freezes task with status `BLOCKED_ESCALATED`,
  |             Records audit log in `state.sqlite`, escalates to Orchestrator/HITL.
  v (All pass)
[G5_2_PASS_AND_FINISH]
  +--> Supervisor signs G5.2 review (`gov.py review --decision APPROVED`).
  +--> Orchestrator runs Pre-Merge Interlock (`gov.py interlock --task <task_id>`).
  +--> Worktree merged, task marked DONE (`gov.py finish --task <task_id>`).
```

---

## 4. Sovereign Dual-Sync Git Pipeline

To eliminate phantom commits and guarantee Evidence-First truth:

1. **Local Worktree Isolation:**
   Every task operates within an isolated local worktree:
   `.worktrees/<task_id>/`
2. **Branch Naming Standard:**
   `task/<task_id>` (e.g. `task/T004-user-auth`).
3. **Upstream Remote Synchronizer:**
   - Antigravity pushes initial context (`TASK_BRIEF.md`, `contracts/`, `specs/`).
   - Jules pulls the branch in Google Cloud sandbox, executes, and pushes commits back to `origin task/<task_id>`.
   - Antigravity pulls remote commits down to `.worktrees/<task_id>` before running any gate audit.
   - Merging to `main` occurs strictly on the local orchestrator side after Gate G6 Cross-Interlock pass.

---

## 5. Automatic Socratic Plan Audit Engine

When Jules enters `AWAITING_PLAN_APPROVAL`, `task-supervisor` intercepts the plan before issuing any approval.

### Audit Invariants:
1. **Allowed Paths Confinement:**
   Does the proposed plan attempt to create or modify files outside `task.allowed_paths`?
   *Violation:* Immediate rejection (`PLAN_REJECTED: PATH_CONFINEMENT_VIOLATION`).
2. **Contract Immutability:**
   Does the plan modify any file in `contracts/`?
   *Violation:* Immediate rejection (`PLAN_REJECTED: CONTRACT_TAMPERING_FORBIDDEN`).
3. **DREE 7 Invariants:**
   Does the plan account for typed DTOs, boundary validation, domain exceptions, SRP ($\le 40$ lines), clean logging, and a dual-test suite?
   *Violation:* Rejection with actionable remediation instructions.

When rejected, Antigravity sends an EARS revision prompt via `send_session_message` and remains in `PLAN_AUDIT` state.

---

## 6. Iron 3-Cycle Self-Healing Budget (Cardinal Rule 12)

If local code audits in `.worktrees/<task_id>` fail:
1. Supervisor outputs `.governance/FEEDBACK_PACKET_<task_id>.json`:
   ```json
   {
     "task_id": "T004",
     "iteration": 1,
     "max_iterations": 3,
     "status": "REJECTED_NEEDS_REVISION",
     "findings": [
       {
         "type": "DREE_SRP_VIOLATION",
         "file": "src/auth_service.py",
         "details": "Function 'authenticate' has 58 lines (max 40 allowed).",
         "actionable_remediation": "Decompose into private helper '_verify_credentials'."
       }
     ],
     "required_action": "Iteration 1/3: Repair indicated violations and commit to branch."
   }
   ```
2. The `jules_bridge` formats this finding into a concise prompt and issues:
   `send_session_message(session_id, prompt)`
3. On iteration 3, if standards are still not met, the task transitions to `BLOCKED_ESCALATED` and halts automatically.

---

## 7. Dual-Control Security Invariant (Rule 9)

- `reviewer != actor`
- Jules operates under identity `agent:jules-builder`.
- Supervisor operates under identity `agent:task-supervisor`.
- Jules session IDs and tokens cannot be reused to approve or review tasks in `gov.py`.
- Any attempt to bypass supervision triggers `DualControlViolationError`.
