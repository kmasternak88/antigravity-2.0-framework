---
name: cl-jules
description: "Orkiestracja i nadzór hybrydowej pętli Google Jules Agent via FastMCP (Tier 3 Cloud Builder) pod kontrolą Antigravity v8.3."
tools:
  - run_command
  - view_file
---

# /cl-jules — Hybrydowa Orkiestracja Google Jules Agent (Antigravity v8.3)

Uruchamia i nadzoruje wykonanie zadań lub fal DAG z wykorzystaniem chmurowego wykonawcy **Google Jules** za pośrednictwem serwera FastMCP (`ahaufox/jules-mcp-server`).

## Kluczowe Inwarianty i Bramki Dowodowe
1. **Sovereign Dual-Sync:**
   - Antigravity zamraża specyfikację i kontrakty (`contracts/`) na bramce G2.
   - Antigravity pushuje gałąź roboczą `task/<task_id>` z plikiem `TASK_BRIEF.md`.
2. **Sokratejski Audyt Planu (Plan Approval Gate):**
   - Jules tworzy plan z `require_plan_approval=True`.
   - Supervisor weryfikuje plan pod kątem:
     - `allowed_paths` (brak modyfikacji plików poza zakresem).
     - Nienaruszalności `contracts/` (blokada modyfikacji zamrożonych interfejsów).
     - Standardu 7 Niezmienników DREE (SRP $\le 40$, DTO, walidacja, testy brzegowe).
   - W przypadku niezgodności plan jest odrzucany promptem naprawczym przed zatwierdzeniem.
3. **Pętla Samonaprawcza (3-Cycle Self-Healing, Reguła 12):**
   - Po commicie Julesa kod jest pobierany (`git fetch`) do `.worktrees/<task_id>`.
   - W przypadku niezaliczonych bramek G4/G5 generowany jest `FEEDBACK_PACKET_<task_id>.json`.
   - Adapter przesyła ustrukturyzowany prompt do sesji Julesa przez `send_session_message`.
   - Po 3 cyklach proces zostaje zamrożony ze statusem `BLOCKED_ESCALATED`.
4. **Dual-Control (Reguła 9):**
   - Jules (`agent:jules-builder`) NIGDY nie certyfikuje ani nie recenzuje własnego kodu. Niezależny `task-supervisor` certyfikuje bramkę G5.2.

## Użycie CLI

### Weryfikacja połączenia i źródeł:
```powershell
python tools/jules_bridge.py --ping
```

### Uruchomienie pojedynczego zadania z egzekutorem Jules:
```powershell
python tools/subagent_workflow.py --task <TASK_ID> --executor jules
```

### Uruchomienie fali równoległej w swarmie:
```powershell
python tools/subagent_workflow.py --swarm --executor jules --concurrency 2
```
