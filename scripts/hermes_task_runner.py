#!/usr/bin/env python3
"""Run one Hermes task in a conservative dry-run loop."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hermes_invoke_agent import ALLOWED_AGENTS, TaskContext, _find_task, build_prompt  # noqa: E402
from scripts.hermes_lab_guard import EXPECTED_REPO_ROOT, evaluate_guard  # noqa: E402

TASK_QUEUE_PATH = Path("docs/HERMES_TASK_QUEUE.md")
RUN_REPORT_DIR = Path("reports/hermes_runs")


@dataclass(frozen=True)
class RunReport:
    timestamp: str
    repo_root: str
    branch: str
    remotes: dict[str, str]
    task: dict[str, object]
    assigned_agents: list[str]
    allowed_files: list[str]
    forbidden_files: list[str]
    validation_commands: list[str]
    guard_result: dict[str, object]
    branch_matches_task: bool
    dry_run_prompt: str
    next_steps: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--agent")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _load_task(task_id: str | None) -> TaskContext | None:
    return _find_task(TASK_QUEUE_PATH, task_id)


def _remote_map() -> dict[str, str]:
    import subprocess

    remotes: dict[str, str] = {}
    for remote in ("origin", "upstream"):
        completed = subprocess.run(
            ["git", "remote", "get-url", remote],
            capture_output=True,
            text=True,
            check=False,
        )
        remotes[remote] = completed.stdout.strip()
    return remotes


def _write_report(task_id: str, report: RunReport) -> Path:
    RUN_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = RUN_REPORT_DIR / f"{task_id}.md"
    lines = [
        f"# Hermes Run Report: {task_id}",
        "",
        f"- timestamp: {report.timestamp}",
        f"- repo_root: {report.repo_root}",
        f"- branch: {report.branch}",
        f"- branch_matches_task: {str(report.branch_matches_task).lower()}",
        "- remotes:",
    ]
    for name, url in report.remotes.items():
        lines.append(f"  - {name}: {url}")
    lines.extend(
        [
            "- selected_task:",
            f"  - task_id: {report.task['task_id']}",
            f"  - title: {report.task['title']}",
            f"  - status: {report.task['status']}",
            f"  - branch_name: {report.task['branch_name']}",
            f"  - objective: {report.task['objective']}",
            "- assigned_agents:",
        ]
    )
    lines.extend(f"  - {item}" for item in report.assigned_agents)
    lines.append("- allowed_files:")
    lines.extend(f"  - {item}" for item in report.allowed_files)
    lines.append("- forbidden_files:")
    lines.extend(f"  - {item}" for item in report.forbidden_files)
    lines.append("- validation_commands:")
    lines.extend(f"  - {item}" for item in report.validation_commands)
    lines.append("- guard_result:")
    for key, value in report.guard_result.items():
        lines.append(f"  - {key}: {value}")
    lines.append("- dry_run_prompt:")
    for line in report.dry_run_prompt.splitlines():
        lines.append(f"  {line}")
    lines.append("- next_steps:")
    lines.extend(f"  - {item}" for item in report.next_steps)
    path.write_text("\n".join(lines) + "\n")
    return path


def _task_payload(task: TaskContext | None) -> dict[str, object]:
    if task is None:
        return {}
    return asdict(task)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    task = _load_task(args.task_id)
    if task is None:
        raise SystemExit("No matching pending task found")
    assigned_agent = args.agent or "vega_orchestrator"
    if assigned_agent not in ALLOWED_AGENTS:
        raise SystemExit(f"Unknown agent: {assigned_agent}")
    guard_result = evaluate_guard(allow_dirty=args.allow_dirty or args.execute, allow_any_root=False)
    branch = guard_result["branch"] or ""
    branch_matches_task = branch == task.branch_name
    prompt = build_prompt(assigned_agent, task)
    next_steps = [
        "Review the dry-run prompt before any execution.",
        "Run validation commands only after explicit approval.",
        "Never push to upstream.",
    ]
    report = RunReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        repo_root=str(EXPECTED_REPO_ROOT),
        branch=branch,
        remotes=_remote_map(),
        task=_task_payload(task),
        assigned_agents=[
            "vega_orchestrator",
            "opencode_deepseek_flash",
            "kilo_nex2_review",
            "zcode_glm52_research",
            "vibe_strategy",
        ],
        allowed_files=task.allowed_files,
        forbidden_files=task.forbidden_files,
        validation_commands=task.validation_commands,
        guard_result=guard_result,
        branch_matches_task=branch_matches_task,
        dry_run_prompt=prompt,
        next_steps=next_steps,
    )
    report_path = _write_report(task.task_id, report)
    payload = {
        "ok": bool(guard_result["ok"]),
        "task_id": task.task_id,
        "report_path": str(report_path),
        "branch_matches_task": branch_matches_task,
        "dry_run": not args.execute,
        "prompt": prompt,
        "next_steps": next_steps,
        "guard_result": guard_result,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"task_id: {task.task_id}")
        print(f"report_path: {report_path}")
        print(f"branch_matches_task: {str(branch_matches_task).lower()}")
        print(prompt)
        print("")
        print("next_steps:")
        for step in next_steps:
            print(f"- {step}")
    return 0 if guard_result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
