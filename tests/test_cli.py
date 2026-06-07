"""Tests for command-line parsing and the top-level `main` entry point.

We avoid launching a real sandbox by always using `--dry-run`, which prints the
command it WOULD run instead of running it. That keeps these tests fast and safe.
"""

from pathlib import Path

from isolate import agents, cli
from isolate.cli import build_arg_parser, build_overrides, main, split_command


def test_split_command_at_double_dash():
    left, cmd = split_command(["run", "--no-network", "--", "claude", "-p", "hi"])
    assert left == ["run", "--no-network"]
    assert cmd == ["claude", "-p", "hi"]


def test_split_command_without_double_dash():
    left, cmd = split_command(["doctor"])
    assert left == ["doctor"]
    assert cmd == []


def test_overrides_no_network_is_false():
    args = build_arg_parser().parse_args(["run", "--no-network"])
    assert build_overrides(args)["network"] is False


def test_overrides_network_unset_is_none():
    args = build_arg_parser().parse_args(["run"])
    assert build_overrides(args)["network"] is None


def test_overrides_memory_cpus_and_allowlists():
    args = build_arg_parser().parse_args(
        [
            "run",
            "--memory",
            "8G",
            "--cpus",
            "4",
            "--allow-write",
            "/data",
            "--allow-read",
            "/ref",
        ]
    )
    ov = build_overrides(args)
    assert ov["memory"] == "8G"
    assert ov["cpus"] == 4.0
    assert ov["allow_write"] == ["/data"]
    assert ov["allow_read"] == ["/ref"]


def test_main_dry_run_prints_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--no-network", "--dry-run", "--", "echo", "hi"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "bwrap" in out
    assert "--share-net" not in out  # network was turned off
    assert "echo" in out


def test_main_dry_run_does_not_create_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["run", "--dry-run", "--", "echo", "hi"])
    # Dry run must not touch the filesystem (no fake home created).
    assert not (tmp_path / ".isolate-home").exists()


def test_main_run_without_command_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--dry-run"])
    assert rc != 0


def test_main_unknown_profile_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--profile", "ghost", "--dry-run", "--", "echo", "hi"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "profile" in err.lower()


def test_agent_unknown_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--agent", "bard", "--dry-run"])
    assert rc != 0
    assert "agent" in capsys.readouterr().err.lower()


def test_agent_dry_run_uses_command_and_merges_grants(tmp_path, monkeypatch, capsys):
    # Fake the agent recipe so the test does not depend on a real agent install.
    monkeypatch.chdir(tmp_path)
    fake = agents.AgentLaunch(
        command=["/opt/claude/bin/claude", "--version"],
        reads=[Path("/opt/claude")],
        writes=[],
    )
    monkeypatch.setattr(cli.agents, "resolve_agent", lambda *a, **k: fake)

    rc = main(["run", "--agent", "claude", "--no-network", "--dry-run", "--", "--version"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "/opt/claude/bin/claude" in out  # the agent command is what runs
    assert "/opt/claude" in out  # the read grant was mounted into the sandbox


def test_env_flag_parsed_into_dict():
    args = build_arg_parser().parse_args(["run", "--env", "FOO=bar", "--env", "BAZ=qux"])
    assert build_overrides(args)["env"] == {"FOO": "bar", "BAZ": "qux"}


def test_env_flag_keeps_equals_in_value():
    args = build_arg_parser().parse_args(["run", "--env", "URL=https://a=b"])
    assert build_overrides(args)["env"] == {"URL": "https://a=b"}


def test_env_flag_without_equals_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--env", "NOEQUALS", "--dry-run", "--", "echo", "hi"])
    assert rc != 0
    assert "env" in capsys.readouterr().err.lower()


def test_agent_login_dry_run_injects_config_env(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake = agents.AgentLaunch(
        command=["/opt/claude/bin/claude"],
        reads=[],
        writes=[Path("/home/u/.claude")],
        env={"CLAUDE_CONFIG_DIR": "/home/u/.claude"},
    )
    monkeypatch.setattr(cli.agents, "resolve_agent", lambda *a, **k: fake)

    rc = main(["run", "--agent", "claude", "--login", "--dry-run"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "--setenv CLAUDE_CONFIG_DIR /home/u/.claude" in out
    assert "/home/u/.claude" in out  # config dir granted writable too


def test_agent_does_not_require_command_after_dashes(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake = agents.AgentLaunch(command=["/opt/claude/bin/claude"], reads=[], writes=[])
    monkeypatch.setattr(cli.agents, "resolve_agent", lambda *a, **k: fake)

    rc = main(["run", "--agent", "claude", "--dry-run"])
    assert rc == 0
    assert "/opt/claude/bin/claude" in capsys.readouterr().out
