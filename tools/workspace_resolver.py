#!/usr/bin/env python3
"""Antigravity Multi-Workspace & Project Isolation Resolver (v8.0).

Ensures strict boundary isolation between root orchestrator and independent
workspaces in monorepos / multi-project workspaces (e.g. workspace/*).
Prevents cross-project contamination of tasks, memories, governance, and tests.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_MARKERS = (
    '.governance/config.json',
    'package.json',
    'pyproject.toml',
    'Cargo.toml',
    'go.mod',
    '.project-root',
    '.workspace-root'
)


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Finds the top-level repository or workspace collection root."""
    cur = (start or Path(__file__).resolve().parent).resolve()
    if cur.is_file():
        cur = cur.parent

    for candidate in [cur] + list(cur.parents):
        if (candidate / '.git').exists() or (candidate / 'AGENTS.md').is_file():
            return candidate
    return cur


def get_active_workspace(repo_root: Optional[Path] = None) -> Path:
    """Resolves the currently active project workspace using Nearest-Anchor Hierarchy.

    Priority:
    1. Environment variable ANTIGRAVITY_WORKSPACE, GOV_WORKSPACE, or GOV_ROOT
    2. File .active_workspace in repo_root or any parent
    3. Current working directory proximity (if cwd has project markers)
    4. Subproject under workspace/ (e.g. workspace/agentic-payload-core)
    5. Fallback to repo_root
    """
    root = repo_root or find_repo_root()

    # 1. Environment Variables
    for env_var in ('ANTIGRAVITY_WORKSPACE', 'GOV_WORKSPACE', 'GOV_ROOT', 'AGENTIC_WORKSPACE'):
        val = os.environ.get(env_var)
        if val:
            p = Path(val)
            if not p.is_absolute():
                p = root / p
            resolved = p.resolve()
            if resolved.is_dir():
                return resolved

    # 2. .active_workspace Marker file
    for candidate in [Path.cwd(), root] + list(Path.cwd().parents):
        marker = candidate / '.active_workspace'
        if marker.is_file():
            try:
                line = marker.read_text(encoding='utf-8').strip()
                if line:
                    p = Path(line)
                    if not p.is_absolute():
                        p = candidate / p
                    resolved = p.resolve()
                    if resolved.is_dir():
                        return resolved
            except Exception:
                pass

    # 3. Current working directory proximity
    cwd = Path.cwd().resolve()
    cur = cwd
    while cur != cur.parent and cur != root.parent:
        if cur.name in {'.agents', '.governance', 'hooks', 'bin', 'node_modules', '.git'}:
            cur = cur.parent
            continue
        if any((cur / m).exists() for m in PROJECT_MARKERS):
            if cur != root:
                return cur
        cur = cur.parent

    # 4. Default subproject under workspace/ if exists
    ws_dir = root / 'workspace'
    if ws_dir.is_dir():
        # If there's an agentic-payload-core or exactly one workspace, choose it
        core = ws_dir / 'agentic-payload-core'
        if core.is_dir():
            return core.resolve()
        subprojects = [p for p in ws_dir.iterdir() if p.is_dir() and not p.name.startswith('.')]
        if len(subprojects) == 1:
            return subprojects[0].resolve()

    return root


def set_active_workspace(target: str, repo_root: Optional[Path] = None) -> Path:
    """Sets the active workspace marker with boundary validation."""
    root = repo_root or find_repo_root()
    p = Path(target)
    if not p.is_absolute():
        ws_candidate = root / 'workspace' / target
        if ws_candidate.is_dir():
            p = ws_candidate
        else:
            p = root / target
    resolved = p.resolve()
    if not resolved.is_dir():
        raise ValueError(f"Directory does not exist: {resolved}")

    # Boundary check: must be inside root
    if not resolved.is_relative_to(root) and resolved != root:
        raise ValueError(f"Security Violation: Target path {resolved} escapes repository root {root}")

    rel = str(resolved.relative_to(root)) if resolved.is_relative_to(root) else str(resolved)
    marker = root / '.active_workspace'
    marker.write_text(rel + "\n", encoding="utf-8")
    return resolved


def list_workspaces(repo_root: Optional[Path] = None) -> List[Dict]:
    """Returns all detected workspaces within the repository."""
    root = repo_root or find_repo_root()
    projects = []
    ws_dir = root / 'workspace'

    candidates = []
    if ws_dir.is_dir():
        for p in sorted(ws_dir.iterdir()):
            if p.is_dir() and not p.name.startswith('.') and p.name != '__pycache__':
                candidates.append(p)

    for p in candidates:
        has_gov = (p / '.governance').is_dir()
        has_pkg = (p / 'package.json').is_file()
        has_pyproject = (p / 'pyproject.toml').is_file()
        has_agents = (p / 'AGENTS.md').is_file()
        projects.append({
            'name': p.name,
            'path': str(p.resolve()),
            'rel_path': str(p.relative_to(root)),
            'has_governance': has_gov,
            'has_package_json': has_pkg,
            'has_pyproject': has_pyproject,
            'has_agents_md': has_agents
        })
    return projects


def enforce_boundary(target_path: str, workspace_root: Path) -> Path:
    """Validates that target_path does not escape workspace_root."""
    p = Path(target_path)
    if not p.is_absolute():
        p = workspace_root / p
    resolved = p.resolve()
    if not resolved.is_relative_to(workspace_root.resolve()):
        raise RuntimeError(
            f"HERMETIC_BOUNDARY_VIOLATION: Path '{target_path}' escapes active workspace '{workspace_root}'. "
            "Cross-project modifications in multi-project workspaces are strictly forbidden."
        )
    return resolved


def run_in_active_workspace(cmd_args: List[str], repo_root: Optional[Path] = None) -> int:
    """Executes a command inside the active workspace directory."""
    ws = get_active_workspace(repo_root)
    env = os.environ.copy()
    env['GOV_WORKSPACE'] = str(ws)
    env['ANTIGRAVITY_WORKSPACE'] = str(ws)
    env['GOV_ROOT'] = str(ws)
    print(f"[WorkspaceResolver] Executing in active workspace: {ws}")
    print(f"[WorkspaceResolver] Command: {' '.join(cmd_args)}")
    result = subprocess.run(cmd_args, cwd=ws, env=env)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Antigravity Multi-Workspace & Project Isolation Resolver")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("get", help="Print active workspace path")

    set_parser = subparsers.add_parser("set", help="Set active workspace")
    set_parser.add_argument("target", help="Name of workspace folder or relative path")

    subparsers.add_parser("list", help="List all detected workspaces")

    check_parser = subparsers.add_parser("check-boundary", help="Verify path is within active workspace")
    check_parser.add_argument("path", help="Path to verify")

    run_parser = subparsers.add_parser("run", help="Run a command in the active workspace")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command and arguments to execute")

    args = parser.parse_args()

    if args.command == "get" or not args.command:
        ws = get_active_workspace()
        print(str(ws))
    elif args.command == "set":
        ws = set_active_workspace(args.target)
        print(f"Active workspace set to: {ws}")
    elif args.command == "list":
        workspaces = list_workspaces()
        print(json.dumps(workspaces, indent=2))
    elif args.command == "check-boundary":
        ws = get_active_workspace()
        try:
            enforce_boundary(args.path, ws)
            print(f"PASS: {args.path} is within {ws}")
            sys.exit(0)
        except RuntimeError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "run":
        if not args.cmd:
            print("Error: No command specified for run.", file=sys.stderr)
            sys.exit(1)
        sys.exit(run_in_active_workspace(args.cmd))


if __name__ == "__main__":
    main()
