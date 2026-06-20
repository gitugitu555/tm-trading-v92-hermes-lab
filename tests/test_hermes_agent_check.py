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


def test_delegate_agents_have_hermes_delegate_mode():
    inventory = check.build_agent_inventory()
    assert inventory["opencode_deepseek_flash"]["invocation_mode"] == "hermes_delegate"
    assert inventory["kilo_nex2_review"]["invocation_mode"] == "hermes_delegate"
    assert inventory["vega_orchestrator"]["invocation_mode"] == "direct_cli"
    assert inventory["vibe_strategy"]["invocation_mode"] == "direct_cli"
    assert inventory["zcode_glm52_research"]["invocation_mode"] == "direct_cli"


def test_delegate_agent_marked_available_when_hermes_present_but_command_missing(monkeypatch):
    monkeypatch.setattr(check, "inspect_commands", lambda: [
        {"name": "hermes", "available": True, "path": "/usr/bin/hermes", "version": "1.0"},
        {"name": "opencode", "available": False, "path": None, "version": None},
    ])
    inventory = check.build_agent_inventory()
    opencode = inventory["opencode_deepseek_flash"]
    assert opencode["state"] == "available_via_hermes_delegate"
    assert opencode["available"] is True
    assert opencode["direct_cli_available"] is False
    assert opencode["hermes_delegate_configured"] is True


def test_delegate_agent_marked_unavailable_when_hermes_and_command_both_missing(monkeypatch):
    monkeypatch.setattr(check, "inspect_commands", lambda: [
        {"name": "hermes", "available": False, "path": None, "version": None},
        {"name": "opencode", "available": False, "path": None, "version": None},
    ])
    inventory = check.build_agent_inventory()
    opencode = inventory["opencode_deepseek_flash"]
    assert opencode["state"] == "hermes_delegate_configured"
    assert opencode["available"] is False
    assert opencode["direct_cli_available"] is False


def test_direct_cli_agent_state_when_available(monkeypatch):
    monkeypatch.setattr(check, "inspect_commands", lambda: [
        {"name": "hermes", "available": True, "path": "/usr/bin/hermes", "version": "1.0"},
        {"name": "vibe", "available": True, "path": "/usr/bin/vibe", "version": "2.0"},
    ])
    inventory = check.build_agent_inventory()
    vibe = inventory["vibe_strategy"]
    assert vibe["state"] == "direct_cli_available"
    assert vibe["available"] is True
    assert vibe["direct_cli_available"] is True


def test_direct_cli_agent_state_when_unavailable(monkeypatch):
    monkeypatch.setattr(check, "inspect_commands", lambda: [
        {"name": "hermes", "available": True, "path": "/usr/bin/hermes", "version": "1.0"},
        {"name": "vibe", "available": False, "path": None, "version": None},
    ])
    inventory = check.build_agent_inventory()
    vibe = inventory["vibe_strategy"]
    assert vibe["state"] == "unavailable"
    assert vibe["available"] is False
    assert vibe["direct_cli_available"] is False


def test_inventory_does_not_use_su_or_sudo(monkeypatch):
    import subprocess as _subprocess
    calls = []
    original_run = _subprocess.run

    def capture_run(cmd, **kwargs):
        calls.append(" ".join(str(c) for c in cmd))
        return original_run(cmd, **kwargs)

    monkeypatch.setattr(_subprocess, "run", capture_run)
    check.build_agent_inventory()
    for call in calls:
        assert "su " not in call
        assert "sudo" not in call


def test_inventory_never_inspects_secrets_or_env(monkeypatch):
    import os
    monkeypatch.setenv("FAKE_API_KEY", "sk-test-secret")
    inventory = check.build_agent_inventory()
    for role, info in inventory.items():
        assert "sk-test-secret" not in str(info)
        assert "FAKE_API_KEY" not in str(info)


def test_inventory_json_has_inventory_key(monkeypatch, capsys):
    monkeypatch.setattr(check, "inspect_commands", lambda: [
        {"name": "hermes", "available": True, "path": "/usr/bin/hermes", "version": "1.0"},
    ])
    check.main(["--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "inventory" in payload
    assert "commands" in payload
    assert "roles" in payload
