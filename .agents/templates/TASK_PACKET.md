# Pakiet Delegacji Zadania (Antigravity Ultra v5.1)

```xml
<task_packet version="5.1.0">
  <metadata>
    <task_id>{taskId}</task_id>
    <task_title>{taskTitle}</task_title>
    <risk_profile>{riskRating}</risk_profile>
    <actor>{actorId}</actor>
    <fencing_token>{fencingToken}</fencing_token>
    <spec_digest>{specDigest}</spec_digest>
  </metadata>

  <isolation>
    <worktree_path>.worktrees/{taskId}</worktree_path>
    <allowed_paths>
      {allowedPaths}
    </allowed_paths>
    <read_only_contracts>
      {readOnlyFiles}
    </read_only_contracts>
  </isolation>

  <blast_radius>
    <direct_targets>{directTargets}</direct_targets>
    <downstream_dependents>{downstreamDependents}</downstream_dependents>
    <affected_checks>{affectedChecks}</affected_checks>
  </blast_radius>

  <standards_checklist profile="{standardsProfile}">
    <rule id="1" name="CONTRACT_FIRST">Wszystkie wejścia/wyjścia zdefiniowane w dataclass(frozen=True) lub interfejsie TS.</rule>
    <rule id="2" name="BOUNDARY_VALIDATION">Walidacja formatu i zakresu argumentów na wejściu do funkcji/metody.</rule>
    <rule id="3" name="DOMAIN_EXCEPTIONS">Zakaz surowego 'except:' oraz 'except Exception: pass'. Dedykowane błędy domenowe.</rule>
    <rule id="4" name="CLEAN_CODE_SRP">Maksymalnie 40 linii kodu na funkcję. Czysta pojedyncza odpowiedzialność (SRP).</rule>
    <rule id="5" name="TELEMETRY_AND_ZERO_CONSOLE">Zakaz print() i console.log. Ustrukturyzowane logowanie telemetryczne.</rule>
    <rule id="6" name="DUAL_TEST_SUITE">Obowiązkowy zestaw testów: min. 1 Happy-Path + min. 1 Negative Edge-Case (asercja błędu).</rule>
    <rule id="7" name="SPEC_AND_EXPORTS_SYNC">Rejestracja w __all__ oraz aktualizacja specs/03_DATA_DICTIONARY.md.</rule>
  </standards_checklist>

  <acceptance_criteria>
    {acceptanceCriteria}
  </acceptance_criteria>

  <verification_checks>
    {checks}
  </verification_checks>
</task_packet>
```
