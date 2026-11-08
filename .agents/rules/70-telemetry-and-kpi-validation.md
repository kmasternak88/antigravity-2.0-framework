---
rule_id: 70-telemetry-and-kpi-validation
trigger: post_launch
status: active
---
# Post-Launch Telemetry & KPI Validation Rule

## Rule ID
70-telemetry-and-kpi-validation

## Status
ACTIVE

## Invariant
No release can be considered 100% complete strictly on a business level without configured telemetry events as defined in PRD Section 6.2 (`EVT-XXX`).

## Post-Launch Procedure
1. **Event Verification:** Ensure synthetic event emissions work in staging/canary environments.
2. **KPI Measurement Comparison:** Compare the measured values of defined KPIs against Baseline and Target values from the PRD KPI Table (e.g., MTTR, NRR, latency).
3. **Learning Loop:** Register deviations and conclusions in the `.agents/learning_inbox/` adhering to the G-LEARN v8.3 standard.
