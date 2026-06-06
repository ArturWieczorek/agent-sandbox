"""Integration tests that launch a REAL bubblewrap sandbox.

Everything else in the suite is pure and fast. These tests actually run `bwrap`
to prove the bubble behaves: writes inside the project work, the real system and
home are protected, and the network switch is obeyed.

They are marked `integration` (run the full suite with plain `pytest`, or skip
them with `pytest -m "not integration"`) and auto-skip if `bwrap` is not present.
To keep them focused on isolation rather than systemd, we strip CPU/memory caps
so no systemd scope is involved.
"""

from __future__ import annotations

import dataclasses
import shutil
import subprocess
from pathlib import Path

import pytest

from isolate import profiles, sandbox

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("bwrap") is None, reason="bwrap is not installed"),
]


def run_in_sandbox(project: Path, command: list[str], *, network: bool = False):
    """Resolve a config, build the bwrap command, and run it for real."""
    project.mkdir(parents=True, exist_ok=True)
    config = profiles.resolve(
        command=command,
        profile="default",
        project_dir=project,
        config_paths=[],
        cli_overrides={"network": network},
        real_home=Path.home(),
        term=None,
    )
    # Drop resource caps so these tests do not depend on systemd.
    config = dataclasses.replace(config, memory=None, cpus=None)
    config.home_dir.mkdir(parents=True, exist_ok=True)
    argv = sandbox.build_command(config, systemd_available=False)
    return subprocess.run(argv, capture_output=True, text=True)


def test_can_write_inside_the_project(tmp_path):
    project = tmp_path / "proj"
    result = run_in_sandbox(project, ["bash", "-c", "echo hi > made.txt"])
    assert result.returncode == 0, result.stderr
    assert (project / "made.txt").read_text().strip() == "hi"


def test_system_directories_are_read_only(tmp_path):
    project = tmp_path / "proj"
    result = run_in_sandbox(project, ["bash", "-c", "touch /usr/should-fail"])
    assert result.returncode != 0
    assert "read-only" in result.stderr.lower()


def test_writing_outside_does_not_touch_the_real_host(tmp_path):
    # Writing an unbound path lands on the throwaway in-memory root, never the
    # real host file. We confirm the real /etc was not modified.
    project = tmp_path / "proj"
    run_in_sandbox(project, ["bash", "-c", "touch /etc/isolate-test-marker || true"])
    assert not Path("/etc/isolate-test-marker").exists()


def test_real_home_is_not_visible(tmp_path):
    project = tmp_path / "proj"
    # The fake HOME must be empty: listing it shows no entries.
    result = run_in_sandbox(project, ["bash", "-c", 'ls -A "$HOME" | wc -l'])
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0"


def test_network_off_has_only_loopback(tmp_path):
    project = tmp_path / "proj"
    # /proc/net/dev lists one line per interface. With no shared network, only
    # loopback ("lo") exists, so exactly one interface line contains a colon.
    result = run_in_sandbox(
        project, ["bash", "-c", "grep -c : /proc/net/dev"], network=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"


def test_network_on_exposes_host_interfaces(tmp_path):
    project = tmp_path / "proj"
    result = run_in_sandbox(
        project, ["bash", "-c", "grep -c : /proc/net/dev"], network=True
    )
    assert result.returncode == 0, result.stderr
    # With the host network shared, there is more than just loopback.
    assert int(result.stdout.strip()) > 1
