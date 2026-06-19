from __future__ import annotations

from pathlib import Path

import pytest

import scripts.hermes_council_meeting as council
from scripts.hermes_invoke_agent import TaskContext


def _task() -> TaskContext:
    return TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="research/task",
        objective="Objective",
        context="Context",
        allowed_files=["scripts/example.py"],
        forbidden_files=["/home/tokio/tm-trading-v92-core/**", ".github/workflows/**"],
        validation_commands=["pytest -q"],
        failed_attempt_count=2,
        last_failure_reason="same test failed twice",
        council_after_failed_attempts=2,
    )


def _guard(tmp_path: Path) -> dict[str, object]:
    return {
        "ok": True,
        "repo_root": str(tmp_path),
        "branch": "infra/hermes-vega-agent-orchestration",
        "origin_url": "origin",
        "upstream_url": "upstream",
        "dirty": False,
        "suspicious_files_present": [],
        "failures": [],
    }


def test_council_report_is_created_under_reports_hermes_council(monkeypatch, tmp_path):
    monkeypatch.setattr(council, "evaluate_guard", lambda allow_dirty, allow_any_root: _guard(tmp_path))
    monkeypatch.setattr(council, "_find_task", lambda task_file, task_id: _task())
    monkeypatch.setattr(council, "inspect_commands", lambda: [])
    monkeypatch.setattr(council, "_git_value", lambda args: "commit")
    result = council.run_council(
        "TASK-001",
        tmp_path / "queue.md",
        "human_requested",
        2,
        tmp_path / "reports" / "hermes_council",
    )
    assert result["ok"] is True
    assert str(result["report_path"]).startswith(str(tmp_path / "reports" / "hermes_council"))
    assert Path(result["report_path"]).exists()


def test_council_mode_does_not_commit_or_push(monkeypatch, tmp_path):
    monkeypatch.setattr(council, "evaluate_guard", lambda allow_dirty, allow_any_root: _guard(tmp_path))
    monkeypatch.setattr(council, "_find_task", lambda task_file, task_id: _task())
    monkeypatch.setattr(council, "inspect_commands", lambda: [])
    calls = []

    def fake_git_value(args):
        calls.append(args)
        return "commit"

    monkeypatch.setattr(council, "_git_value", fake_git_value)
    council.run_council("TASK-001", tmp_path / "queue.md", "human_requested", 0, tmp_path)
    assert ["commit"] not in calls
    assert ["push"] not in calls


def test_generated_prompts_include_no_edit_commit_push_warning():
    prompts = council.build_council_prompts(_task(), "human_requested")
    assert prompts
    for prompt in prompts.values():
        assert "Do not edit files. Do not commit. Do not push." in prompt


def test_unknown_task_id_fails_safely(monkeypatch, tmp_path):
    monkeypatch.setattr(council, "evaluate_guard", lambda allow_dirty, allow_any_root: _guard(tmp_path))
    monkeypatch.setattr(council, "_find_task", lambda task_file, task_id: None)
    result = council.run_council("UNKNOWN", tmp_path / "queue.md", "human_requested", 0, tmp_path)
    assert result["ok"] is False
    assert result["reason"] == "unknown task_id"
    assert result["report_path"] is None


def test_missing_agent_cli_does_not_fail_whole_council(monkeypatch, tmp_path):
    monkeypatch.setattr(council, "evaluate_guard", lambda allow_dirty, allow_any_root: _guard(tmp_path))
    monkeypatch.setattr(council, "_find_task", lambda task_file, task_id: _task())
    monkeypatch.setattr(council, "inspect_commands", lambda: [{"name": "hermes", "available": True, "path": "/bin/hermes", "version": None}])
    monkeypatch.setattr(council, "_git_value", lambda args: "commit")
    result = council.run_council("TASK-001", tmp_path / "queue.md", "human_requested", 1, tmp_path)
    assert result["ok"] is True
    assert "opencode_deepseek_flash" in result["missing_agents"]


@pytest.mark.parametrize("needle", ["human_requested", "failed_attempt_count: 3"])
def test_trigger_reason_and_failed_attempt_count_are_recorded(monkeypatch, tmp_path, needle):
    monkeypatch.setattr(council, "evaluate_guard", lambda allow_dirty, allow_any_root: _guard(tmp_path))
    monkeypatch.setattr(council, "_find_task", lambda task_file, task_id: _task())
    monkeypatch.setattr(council, "inspect_commands", lambda: [])
    monkeypatch.setattr(council, "_git_value", lambda args: "commit")
    result = council.run_council("TASK-001", tmp_path / "queue.md", "human_requested", 3, tmp_path)
    assert needle in Path(result["report_path"]).read_text()


def test_decision_labels_repo_boundary_and_safety_are_present(monkeypatch, tmp_path):
    monkeypatch.setattr(council, "evaluate_guard", lambda allow_dirty, allow_any_root: _guard(tmp_path))
    monkeypatch.setattr(council, "_find_task", lambda task_file, task_id: _task())
    monkeypatch.setattr(council, "inspect_commands", lambda: [])
    monkeypatch.setattr(council, "_git_value", lambda args: "commit")
    result = council.run_council("TASK-001", tmp_path / "queue.md", "human_requested", 2, tmp_path)
    text = Path(result["report_path"]).read_text()
    assert "council_continue_current_task" in text
    assert "/home/tokio/tm-trading-v92-hermes-lab" in text
    assert "push to upstream" in text
    assert "force-push" in text
    assert "allowed next action: review this report" in text


def test_report_contains_all_required_sections(monkeypatch, tmp_path):
    monkeypatch.setattr(council, "evaluate_guard", lambda allow_dirty, allow_any_root: _guard(tmp_path))
    monkeypatch.setattr(council, "_find_task", lambda task_file, task_id: _task())
    monkeypatch.setattr(council, "inspect_commands", lambda: [])
    monkeypatch.setattr(council, "_git_value", lambda args: "commit")
    result = council.run_council("TASK-001", tmp_path / "queue.md", "human_requested", 2, tmp_path)
    text = Path(result["report_path"]).read_text()
    for heading in [
        "## Meeting metadata",
        "## Task state summary",
        "## Agent briefs",
        "## Disagreement matrix",
        "## Decision options",
        "## Vega final synthesis",
    ]:
        assert heading in text
