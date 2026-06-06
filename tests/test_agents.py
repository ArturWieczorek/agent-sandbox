"""Tests for the known-agent recipes (claude, gemini).

An "agent recipe" works out two things for a known tool: the exact command to run
inside the sandbox, and the read-only paths that must be granted so the tool (and
its runtime) can actually be found. These tests build a fake home with fake binary
files in a temp folder and feed a fake `which`, so nothing depends on the real
machine.
"""

from pathlib import Path

import pytest

from isolate.agents import AgentError, resolve_agent


def test_resolve_claude_builds_command_and_grants(tmp_path):
    home = tmp_path
    binroot = home / ".local" / "share" / "claude" / "versions"
    binroot.mkdir(parents=True)
    real = binroot / "2.1.167"
    real.write_text("#!binary")
    which = lambda name: str(real) if name == "claude" else None

    launch = resolve_agent("claude", extra_args=["--version"], which=which, home=home)

    assert launch.command == [str(real.resolve()), "--version"]
    assert (home / ".local" / "share" / "claude") in launch.reads
    assert launch.writes == []


def test_resolve_claude_login_grants_config(tmp_path):
    home = tmp_path
    real = home / ".local" / "share" / "claude" / "versions" / "x"
    real.parent.mkdir(parents=True)
    real.write_text("x")
    which = lambda name: str(real) if name == "claude" else None

    launch = resolve_agent("claude", extra_args=[], login=True, which=which, home=home)

    assert (home / ".claude") in launch.writes
    assert (home / ".claude.json") in launch.writes


def test_resolve_claude_missing_raises(tmp_path):
    with pytest.raises(AgentError):
        resolve_agent("claude", extra_args=[], which=lambda name: None, home=tmp_path)


def test_resolve_gemini_runs_via_node_and_grants_node_root(tmp_path):
    home = tmp_path
    bindir = home / ".nvm" / "versions" / "node" / "v20" / "bin"
    bindir.mkdir(parents=True)
    node = bindir / "node"
    node.write_text("n")
    gem = bindir / "gemini"
    gem.write_text("g")
    which = lambda name: {"gemini": str(gem), "node": str(node)}.get(name)

    launch = resolve_agent("gemini", extra_args=["chat"], which=which, home=home)

    # Gemini is a node program, so we run it as: node <gemini-script> <args>.
    assert launch.command == [str(node.resolve()), str(gem.resolve()), "chat"]
    # The whole node version directory is granted (covers node + its packages).
    assert (home / ".nvm" / "versions" / "node" / "v20") in launch.reads


def test_resolve_gemini_missing_node_raises(tmp_path):
    home = tmp_path
    gem = tmp_path / "gemini"
    gem.write_text("g")
    which = lambda name: str(gem) if name == "gemini" else None

    with pytest.raises(AgentError):
        resolve_agent("gemini", extra_args=[], which=which, home=home)


def test_resolve_gemini_login_grants_config(tmp_path):
    home = tmp_path
    bindir = home / ".nvm" / "versions" / "node" / "v20" / "bin"
    bindir.mkdir(parents=True)
    (bindir / "node").write_text("n")
    (bindir / "gemini").write_text("g")
    which = lambda name: {
        "gemini": str(bindir / "gemini"),
        "node": str(bindir / "node"),
    }.get(name)

    launch = resolve_agent("gemini", extra_args=[], login=True, which=which, home=home)

    assert (home / ".gemini") in launch.writes


def test_unknown_agent_raises(tmp_path):
    with pytest.raises(AgentError):
        resolve_agent("bard", extra_args=[], which=lambda name: None, home=tmp_path)
