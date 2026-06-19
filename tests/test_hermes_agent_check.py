from __future__ import annotations

import json

import scripts.hermes_agent_check as check


def test_command_detection_handles_missing_commands(monkeypatch):
    monkeypatch.setattr(check, "_command_path", lambda command: None if command == "hermes" else f"/usr/bin/{command}")
    rows = check.inspect_commands()
    hermes_row = next(row for row in rows if row["name"] == "hermes")
    git_row = next(row for row in rows if row["name"] == "git")
    assert hermes_row["available"] is False
    assert git_row["available"] is True


def test_output_does_not_contain_environment_variables_or_api_key_like_values(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_API_KEY", "sk-test-1234567890abcdef")
    monkeypatch.setattr(check, "_command_path", lambda command: None)
    monkeypatch.setattr(check, "_version_from_command", lambda command, path: None)
    check.main([])
    output = capsys.readouterr().out
    assert "FAKE_API_KEY" not in output
    assert "sk-test-1234567890abcdef" not in output


def test_json_output_has_each_expected_agent_role(monkeypatch, capsys):
    monkeypatch.setattr(check, "_command_path", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(check, "_version_from_command", lambda command, path: None)
    check.main(["--json"])
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["roles"]) == {
        "vega_orchestrator",
        "opencode_deepseek_flash",
        "kilo_nex2_review",
        "vibe_strategy",
        "zcode_glm52_research",
    }


def test_role_map_includes_opencode_kilo_vibe_zcode_hermes():
    assert check.ROLE_MAP["vega_orchestrator"]["preferred_command"] == "hermes"
    assert check.ROLE_MAP["opencode_deepseek_flash"]["preferred_command"] == "opencode"
    assert check.ROLE_MAP["kilo_nex2_review"]["preferred_command_options"] == ["kilo", "kilocode"]
    assert check.ROLE_MAP["vibe_strategy"]["preferred_command"] == "vibe"
    assert check.ROLE_MAP["zcode_glm52_research"]["preferred_command"] == "zcode"
