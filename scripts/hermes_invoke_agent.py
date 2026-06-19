#!/usr/bin/env python3
"""Build safe self-contained prompts for local Hermes/Vega worker CLIs."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hermes_lab_guard import EXPECTED_REPO_ROOT, evaluate_guard  # noqa: E402

ALLOWED_AGENTS = {
    "vega_orchestrator": "hermes",
    "opencode_deepseek_flash": "opencode",
    "kilo_nex2_review": "kilo",
    "vibe_strategy": "vibe",
    "zcode_glm52_research": "zcode",
}


@dataclass(frozen=True)
class TaskContext:
    task_id: str
    title: str
    status: str
    branch_name: str
    objective: str
    context: str
    allowed_files: list[str]
    forbidden_files: list[str]
    validation_commands: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--task-file", default="docs/HERMES_TASK_QUEUE.md")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _load_task_queue(task_file: Path) -> list[TaskContext]:
    if not task_file.exists():
        return []
    tasks: list[TaskContext] = []
    current: dict[str, object] | None = None
    section: str | None = None
    buffer: list[str] = []
    for raw_line in task_file.read_text().splitlines():
        line = raw_line.rstrip()
        if line.startswith("## TASK-"):
            if current is not None:
                current["context"] = "\n".join(buffer).strip()
                tasks.append(
                    TaskContext(
                        task_id=str(current["task_id"]),
                        title=str(current["title"]),
                        status=str(current["status"]),
                        branch_name=str(current["branch_name"]),
                        objective=str(current["objective"]),
                        context=str(current["context"]),
                        allowed_files=list(current["allowed_files"]),
                        forbidden_files=list(current["forbidden_files"]),
                        validation_commands=list(current["validation_commands"]),
                    )
                )
            current = {
                "task_id": line.removeprefix("## ").strip(),
                "title": "",
                "status": "",
                "branch_name": "",
                "objective": "",
                "context": "",
                "allowed_files": [],
                "forbidden_files": [],
                "validation_commands": [],
            }
            section = None
            buffer = []
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("Title:"):
            current["title"] = stripped.split("Title:", 1)[1].strip()
            continue
        if stripped.startswith("Status:"):
            current["status"] = stripped.split("Status:", 1)[1].strip()
            continue
        if stripped.startswith("Branch:"):
            current["branch_name"] = stripped.split("Branch:", 1)[1].strip()
            continue
        if stripped.startswith("Objective:"):
            current["objective"] = stripped.split("Objective:", 1)[1].strip()
            continue
        if stripped == "Context:":
            section = "context"
            buffer = []
            continue
        if stripped == "Allowed files:":
            section = "allowed_files"
            continue
        if stripped == "Forbidden files:":
            section = "forbidden_files"
            continue
        if stripped == "Validation commands:":
            section = "validation_commands"
            continue
        if section == "context" and stripped:
            buffer.append(raw_line)
            continue
        if section in {"allowed_files", "forbidden_files", "validation_commands"}:
            if stripped.startswith("- "):
                value = stripped[2:].strip()
                current[section].append(value)
            continue
    if current is not None:
        current["context"] = "\n".join(buffer).strip()
        tasks.append(
            TaskContext(
                task_id=str(current["task_id"]),
                title=str(current["title"]),
                status=str(current["status"]),
                branch_name=str(current["branch_name"]),
                objective=str(current["objective"]),
                context=str(current["context"]),
                allowed_files=list(current["allowed_files"]),
                forbidden_files=list(current["forbidden_files"]),
                validation_commands=list(current["validation_commands"]),
            )
        )
    return tasks


def _find_task(task_file: Path, task_id: str | None) -> TaskContext | None:
    tasks = _load_task_queue(task_file)
    if task_id is not None:
        for task in tasks:
            if task.task_id == task_id:
                return task
        return None
    for task in tasks:
        if task.status.lower() == "pending":
            return task
    return None


def build_prompt(agent: str, task: TaskContext | None, task_file: Path | None = None) -> str:
    if agent not in ALLOWED_AGENTS:
        raise ValueError(f"Unknown agent: {agent}")
    command = ALLOWED_AGENTS[agent]
    lines = [
        f"Agent: {agent}",
        f"Command: {command}",
        f"Repository boundary: {EXPECTED_REPO_ROOT}",
        "Active repo: /home/tokio/tm-trading-v92-hermes-lab",
        "Checkpoint repo: /home/tokio/tm-trading-v92-core",
        "Push remote: origin only",
        "Forbidden remote: upstream",
        "No force-push, no history rewrite, no workflow changes, no branch protection changes, no secrets.",
    ]
    if task is not None:
        lines.extend(
            [
                f"Task id: {task.task_id}",
                f"Task title: {task.title}",
                f"Task branch: {task.branch_name}",
                f"Task status: {task.status}",
                "Objective:",
                task.objective,
                "Context:",
                task.context or "n/a",
                "Allowed files:",
            ]
        )
        lines.extend(f"- {value}" for value in task.allowed_files)
        lines.append("Forbidden files:")
        lines.extend(f"- {value}" for value in task.forbidden_files)
        lines.append("Validation commands:")
        lines.extend(f"- {value}" for value in task.validation_commands)
    else:
        lines.append("No task context was loaded.")
    lines.extend(
        [
            "Instruction:",
            "Operate only inside the lab repo. Treat all prompts as stateless and self-contained.",
            "Never suggest pushing to upstream.",
        ]
    )
    return "\n".join(lines)


def _intended_command(agent: str) -> list[str]:
    command = ALLOWED_AGENTS[agent]
    path = subprocess.run(
        ["bash", "-lc", f"command -v {shlex.quote(command)}"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if not path:
        return [command]
    return [path]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.agent not in ALLOWED_AGENTS:
        raise SystemExit(f"Unknown agent: {args.agent}")
    task_path = Path(args.task_file)
    task = _find_task(task_path, args.task_id)
    prompt = build_prompt(args.agent, task)
    intended_command = _intended_command(args.agent)
    guard_result = evaluate_guard(allow_dirty=args.allow_dirty, allow_any_root=False)
    if args.execute and not guard_result["ok"]:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "guard failed",
                        "guard": guard_result,
                        "prompt": prompt,
                        "intended_command": intended_command,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print("guard failed; execution refused")
            print(prompt)
        return 1
    payload = {
        "ok": True,
        "execute_requested": args.execute,
        "manual_invocation_required": True,
        "agent": args.agent,
        "task_id": task.task_id if task else None,
        "intended_command": intended_command,
        "prompt": prompt,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(prompt)
        print("")
        print("manual invocation required")
        print(f"intended command: {' '.join(intended_command)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
