# cl-implementation-plan

## Description
Integrates with the DAG state and deployment engine `tools/jules_bridge.py` to orchestrate rollout.

## Usage
`/cl-implementation-plan` connects the validated PRD to the `.governance/tasks.json` and triggers deployment execution.

## Flow
1. Evaluates `.agents/templates/IMPLEMENTATION_PLAN.md`.
2. Connects with `tools/jules_bridge.py --deployment` to start executing the deployment strategy.
3. Monitors Rollback triggers and Smoke Test Matrix.
