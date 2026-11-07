# JULES MCP SERVER SETUP & INTEGRATION GUIDE

> **Framework:** Antigravity Ultra v8.3 Omni-Agentic OS
> **Server:** FastMCP Jules Server (`ahaufox/jules-mcp-server`)
> **Protocol:** Model Context Protocol (FastMCP Python / stdio / SSE)

---

## 1. Prerequisites & Environment Setup

The Jules MCP bridge interacts with Google Jules via the `jules-mcp-server`.

### Requirements:
- Python 3.10+ (Python 3.13 recommended for standalone `uv` server run)
- `JULES_API_KEY`: API key for Google Jules
- Git configured with push access to upstream repository (GitHub)

### Setting API Key (SecretShield Compliance):
Never hardcode API keys in any code file, commit, or log artifact. Set it in your local environment or `.env` file (which is git-ignored):

```bash
# Linux / macOS
export JULES_API_KEY="your-jules-api-key"

# Windows PowerShell
$Env:JULES_API_KEY = "your-jules-api-key"
```

---

## 2. FastMCP Server Configuration (`mcp_config.json`)

Configure Antigravity to connect to `jules-mcp-server`:

### Option A: Local Virtual Environment (`uv` / `python`)
```json
{
  "mcpServers": {
    "jules": {
      "command": "python",
      "args": ["-m", "jules_mcp"],
      "cwd": "/path/to/jules-mcp-server",
      "env": {
        "JULES_API_KEY": "${JULES_API_KEY}"
      }
    }
  }
}
```

### Option B: Docker Container
```json
{
  "mcpServers": {
    "jules": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "JULES_API_KEY",
        "jules-mcp"
      ]
    }
  }
}
```

---

## 3. Connectivity Verification

Antigravity includes a verification utility inside `tools/jules_bridge.py`:

```bash
# Verify connection to Jules MCP Server and list available GitHub sources
python tools/jules_bridge.py --ping
```

Expected Output:
```json
{
  "status": "OK",
  "mcp_server": "jules",
  "api_key_configured": true,
  "sources_count": 3,
  "sources": [
    "sources/github/owner/repo"
  ]
}
```

---

## 4. Operational Commands & Workflow

### Executing a Single Task via Jules
```bash
python tools/subagent_workflow.py --task T004 --executor jules
```

### Executing Swarm Wave via Jules
```bash
python tools/subagent_workflow.py --swarm --executor jules --concurrency 2
```

### Manual Plan Review / Supervision CLI
```bash
# Inspect pending session plan
python tools/jules_bridge.py --session sessions/12345 --inspect-plan

# Approve plan manually if required
python tools/jules_bridge.py --session sessions/12345 --approve-plan
```
