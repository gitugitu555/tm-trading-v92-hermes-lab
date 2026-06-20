#!/usr/bin/env python3
"""Create a report-only Hermes AI Council Meeting for blocked or ambiguous tasks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hermes_agent_check import inspect_commands  # noqa: E402
from scripts.hermes_invoke_agent import ALLOWED_AGENTS, TaskContext, _find_task, build_prompt  # noqa: E402
from scripts.hermes_lab_guard import EXPECTED_REPO_ROOT, evaluate_guard  # noqa: E402

COUNCIL_ROLES = {
    "vega_orchestrator": {
        "title": "Vega orchestrator brief",
        "brief": "Chair the meeting, summarize task state, synthesize recommendations, and produce a final decision.",
    },
    "opencode_deepseek_flash": {
        "title": "opencode implementation brief",
        "brief": "Give the implementation perspective, explain code-level blockers, and suggest minimal safe patch options.",
    },
    "kilo_nex2_review": {
        "title": "kilo review brief",
        "brief": "Give the review perspective, look for bugs, leakage, unsafe file changes, and bad assumptions.",
    },
    "vibe_strategy": {
        "title": "vibe strategy brief",
        "brief": "Give the strategy perspective, flag overfitting, win-rate traps, weak hypotheses, and unclear direction.",
    },
    "zcode_glm52_research": {
        "title": "zcode research brief",
        "brief": "Give the research perspective, compare the task to project docs and previous decisions.",
    },
}

DECISION_LABELS = [
    "council_continue_current_task",
    "council_retry_with_minimal_patch",
    "council_stop_failed_task",
    "council_rewrite_task_scope",
    "council_create_new_preregistration",
    "council_request_human_decision",
    "council_retire_hypothesis",
    "council_park_until_more_data",
]

DECISION_OPTIONS = [
    "continue_current_task",
    "retry_with_minimal_patch",
    "stop_failed_task",
    "rewrite_task_scope",
    "create_new_preregistration",
    "request_human_decision",
    "retire_hypothesis",
    "park_until_more_data",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-file", default="docs/HERMES_TASK_QUEUE.md")
    parser.add_argument("--trigger-reason", default="unspecified")
    parser.add_argument("--failed-attempt-count", type=int, default=0)
    parser.add_argument("--output-dir", default="reports/hermes_council")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-agents", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _git_value(args: list[str]) -> str:
    completed = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return completed.stdout.strip()


def _available_commands() -> dict[str, dict[str, object]]:
    return {row["name"]: row for row in inspect_commands()}


def _agent_available(agent: str, command_rows: dict[str, dict[str, object]]) -> bool:
    command = ALLOWED_AGENTS[agent]
    if agent == "kilo_nex2_review":
        return bool(command_rows.get("kilo", {}).get("available") or command_rows.get("kilocode", {}).get("available"))
    return bool(command_rows.get(command, {}).get("available"))


def build_council_prompts(task: TaskContext, trigger_reason: str) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for agent, details in COUNCIL_ROLES.items():
        prompts[agent] = build_prompt(
            agent,
            task,
            council_mode=True,
            failure_reason=trigger_reason,
            requested_brief=details["brief"],
        )
    return prompts


def _placeholder_brief(agent: str, available: bool) -> list[str]:
    status = "available" if available else "unavailable"
    return [
        f"### {COUNCIL_ROLES[agent]['title']}",
        "",
        f"- CLI status: {status}",
        "- diagnosis: manual invocation required; no external agent was called in dry-run council mode.",
        "- risks: unresolved until a human or configured local CLI provides this role's brief.",
        "- recommended next action: review the generated council prompt and invoke manually if needed.",
        "- confidence: low",
        "- recommendation: ask human",
        "",
    ]


def _format_list(items: list[str]) -> list[str]:
    if not items:
        return ["- n/a"]
    return [f"- {item}" for item in items]


def _write_report(
    task: TaskContext,
    output_dir: Path,
    trigger_reason: str,
    failed_attempt_count: int,
    guard_result: dict[str, object],
    command_rows: dict[str, dict[str, object]],
    prompts: dict[str, str],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    timestamp_path = timestamp.strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"{task.task_id}_{timestamp_path}_council.md"
    branch = str(guard_result.get("branch") or _git_value(["branch", "--show-current"]))
    current_commit = _git_value(["rev-parse", "HEAD"])
    lines = [
        f"# Hermes AI Council Meeting: {task.task_id}",
        "",
        "## Meeting metadata",
        "",
        f"- task_id: {task.task_id}",
        f"- timestamp: {timestamp.isoformat()}",
        f"- repo_root: {EXPECTED_REPO_ROOT}",
        f"- branch: {branch}",
        f"- current_commit: {current_commit}",
        f"- failed_attempt_count: {failed_attempt_count}",
        f"- trigger_reason: {trigger_reason}",
        f"- guard_status: {'PASS' if guard_result.get('ok') else 'FAIL'}",
        "",
        "## Task state summary",
        "",
        f"- objective: {task.objective}",
        "- allowed files:",
        *_format_list(task.allowed_files),
        "- forbidden files:",
        *_format_list(task.forbidden_files),
        "- current outputs:",
        "- reports/hermes_council/ council report",
        "- failing validations:",
        f"- {task.last_failure_reason or trigger_reason or 'n/a'}",
        "- unexpected diffs:",
        "- none recorded by council dry-run",
        "- unresolved questions:",
        "- whether implementation should continue, stop, or be rescoped",
        "",
        "## Agent briefs",
        "",
    ]
    for agent in COUNCIL_ROLES:
        lines.extend(_placeholder_brief(agent, _agent_available(agent, command_rows)))
        lines.append("<details>")
        lines.append(f"<summary>{agent} council prompt</summary>")
        lines.append("")
        lines.append("```text")
        lines.extend(prompts[agent].splitlines())
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    lines.extend(
        [
            "## Disagreement matrix",
            "",
            "| issue | opencode view | kilo view | vibe view | zcode view | Vega synthesis |",
            "| --- | --- | --- | --- | --- | --- |",
            "| safe next action | manual invocation required | manual invocation required | manual invocation required | manual invocation required | request human decision until briefs are supplied |",
            "| forbidden file risk | stop if touched | stop if touched | stop if strategy scope drifts | stop if historical constraints conflict | do not continue if forbidden files are implicated |",
            "| metrics ambiguity | ask for minimal patch evidence | challenge claimed success | flag win-rate traps | compare to prior docs | council_request_human_decision |",
            "",
            "## Decision options",
            "",
        ]
    )
    lines.extend(f"- {option}" for option in DECISION_OPTIONS)
    lines.extend(
        [
            "",
            "Council decision labels:",
        ]
    )
    lines.extend(f"- {label}" for label in DECISION_LABELS)
    lines.extend(
        [
            "",
            "## Vega final synthesis",
            "",
            "- selected decision label: council_request_human_decision",
            "- rationale: council mode was triggered and external agent briefs were not executed automatically.",
            "- allowed next action: review this report, invoke unavailable or manual agents if needed, then choose an explicit decision label.",
            "- forbidden next actions: edit files in council mode, commit, push, force-push, rewrite history, push to upstream, change workflows, change branch protection, approve alpha, approve paper/live, approve new trading rules, tune thresholds without preregistration.",
            "- human approval is required: true",
            "",
            "Council mode only. Do not edit files. Do not commit. Do not push.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")
    return path


def run_council(
    task_id: str,
    task_file: Path,
    trigger_reason: str,
    failed_attempt_count: int,
    output_dir: Path,
    execute_agents: bool = False,
) -> dict[str, object]:
    guard_result = evaluate_guard(allow_dirty=True, allow_any_root=False)
    task = _find_task(task_file, task_id)
    if task is None:
        return {
            "ok": False,
            "reason": "unknown task_id",
            "task_id": task_id,
            "guard_result": guard_result,
            "report_path": None,
        }
    command_rows = _available_commands()
    prompts = build_council_prompts(task, trigger_reason)
    # External execution remains intentionally conservative for the first council scaffold.
    executed_agents: list[str] = [] if not execute_agents else []
    report_path = _write_report(task, output_dir, trigger_reason, failed_attempt_count, guard_result, command_rows, prompts)
    return {
        "ok": bool(guard_result["ok"]),
        "task_id": task.task_id,
        "report_path": str(report_path),
        "trigger_reason": trigger_reason,
        "failed_attempt_count": failed_attempt_count,
        "guard_result": guard_result,
        "missing_agents": [
            agent
            for agent in COUNCIL_ROLES
            if not _agent_available(agent, command_rows)
        ],
        "executed_agents": executed_agents,
        "prompts": prompts,
        "task": asdict(task),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_council(
        task_id=args.task_id,
        task_file=Path(args.task_file),
        trigger_reason=args.trigger_reason,
        failed_attempt_count=args.failed_attempt_count,
        output_dir=Path(args.output_dir),
        execute_agents=args.execute_agents,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result["ok"]:
            print(f"council_report_path: {result['report_path']}")
        else:
            print(f"council failed safely: {result['reason']}")
            if result.get("report_path"):
                print(f"council_report_path: {result['report_path']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
