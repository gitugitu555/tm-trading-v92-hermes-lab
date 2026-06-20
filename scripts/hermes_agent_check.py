#!/usr/bin/env python3
"""Detect locally installed CLI agents without touching secrets."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path

COMMANDS = ["hermes", "opencode", "kilo", "kilocode", "vibe", "zcode", "gh", "git", "python3", "uv"]

ROLE_MAP = {
    "vega_orchestrator": {
        "preferred_command": "hermes",
        "role": "task orchestration and run summarization",
    },
    "opencode_deepseek_flash": {
        "preferred_command": "opencode",
        "role": "fast implementation using DeepSeek V4 Flash Free if configured in the local tool",
    },
    "kilo_nex2_review": {
        "preferred_command_options": ["kilo", "kilocode"],
        "role": "code review and verification using Nex 2 Pro Free if configured in the local tool",
    },
    "vibe_strategy": {
        "preferred_command": "vibe",
        "role": "deep thinking, strategy discussion, qualitative analysis",
    },
    "zcode_glm52_research": {
        "preferred_command": "zcode",
        "role": "GLM 5.2 research and large-context analysis if configured in the local tool",
    },
}

DEFAULT_INVOCATION_MODE = "direct_cli"

HERMES_DELEGATE_AGENTS = {
    "opencode_deepseek_flash": {"command": "opencode", "delegate_name": "opencode"},
    "kilo_nex2_review": {"command": "kilo", "alternate_command": "kilocode", "delegate_name": "kilo"},
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _command_path(command: str) -> str | None:
    completed = subprocess.run(
        ["bash", "-lc", f"command -v {shlex.quote(command)}"],
        capture_output=True,
        text=True,
        check=False,
    )
    path = completed.stdout.strip()
    return path or None


def _version_from_command(command: str, path: str | None) -> str | None:
    if not path:
        return None
    candidates = [
        [path, "--version"],
        [path, "version"],
    ]
    for candidate in candidates:
        try:
            completed = subprocess.run(candidate, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return None
        if completed.returncode == 0:
            output = (completed.stdout or completed.stderr).strip().splitlines()
            if output:
                return output[0].strip()
    return None


def inspect_commands() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for command in COMMANDS:
        path = _command_path(command)
        rows.append(
            {
                "name": command,
                "available": path is not None,
                "path": path,
                "version": _version_from_command(command, path),
            }
        )
    return rows


def build_agent_inventory() -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    direct_commands = {row["name"]: row for row in inspect_commands()}
    for role, info in ROLE_MAP.items():
        preferred = info.get("preferred_command")
        preferred_options = info.get("preferred_command_options")
        if preferred:
            command = preferred
            available = direct_commands.get(command, {}).get("available", False)
        elif preferred_options:
            command = preferred_options[0]
            available = any(direct_commands.get(opt, {}).get("available", False) for opt in preferred_options)
        else:
            command = None
            available = False

        if role in HERMES_DELEGATE_AGENTS:
            invocation_mode = "hermes_delegate"
            delegate_info = HERMES_DELEGATE_AGENTS[role]
            delegate_name = delegate_info.get("delegate_name")
            hermes_available = direct_commands.get("hermes", {}).get("available", False)
            if available:
                state = "direct_cli_available"
                overall_available = True
            elif hermes_available:
                state = "available_via_hermes_delegate"
                overall_available = True
            else:
                state = "hermes_delegate_configured"
                overall_available = False
        else:
            invocation_mode = DEFAULT_INVOCATION_MODE
            delegate_name = None
            if available:
                state = "direct_cli_available"
                overall_available = True
            else:
                state = "unavailable"
                overall_available = False

        inventory[role] = {
            "preferred_command": command,
            "invocation_mode": invocation_mode,
            "delegate_name": delegate_name,
            "direct_cli_available": available,
            "hermes_delegate_configured": invocation_mode == "hermes_delegate",
            "available_via_hermes_delegate": (invocation_mode == "hermes_delegate" and not available and direct_commands.get("hermes", {}).get("available", False)),
            "state": state,
            "available": overall_available,
        }
    return inventory


def _markdown_summary(commands: list[dict[str, object]], inventory: dict[str, dict[str, object]]) -> str:
    lines = ["# Hermes Agent Check", ""]
    lines.append("## Command Inventory")
    lines.append("")
    lines.append("| command | available | path | version |")
    lines.append("| --- | --- | --- | --- |")
    for row in commands:
        lines.append(
            "| {name} | {available} | {path} | {version} |".format(
                name=row["name"],
                available=str(row["available"]).lower(),
                path=row["path"] or "",
                version=row["version"] or "",
            )
        )
    lines.append("")
    lines.append("## Agent Inventory")
    lines.append("")
    lines.append("| agent | command | invocation_mode | state | available |")
    lines.append("| --- | --- | --- | --- | --- |")
    for role, info in inventory.items():
        lines.append(
            "| {role} | {command} | {mode} | {state} | {available} |".format(
                role=role,
                command=info.get("preferred_command", ""),
                mode=info.get("invocation_mode", ""),
                state=info.get("state", ""),
                available=str(info.get("available", False)).lower(),
            )
        )
    lines.append("")
    lines.append("## Role Map")
    lines.append("")
    for role, details in ROLE_MAP.items():
        lines.append(f"- {role}:")
        for key, value in details.items():
            if isinstance(value, list):
                lines.append(f"  - {key}: {', '.join(value)}")
            else:
                lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


def build_result() -> dict[str, object]:
    commands = inspect_commands()
    inventory = build_agent_inventory()
    return {"commands": commands, "inventory": inventory, "roles": ROLE_MAP}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    commands = inspect_commands()
    inventory = build_agent_inventory()
    if args.json:
        print(json.dumps({"commands": commands, "inventory": inventory, "roles": ROLE_MAP}, indent=2, sort_keys=True))
    else:
        print(_markdown_summary(commands, inventory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
