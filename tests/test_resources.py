"""Tests for the CPU/memory resource-limit wrapper.

Bubblewrap builds the safe room, but it does not cap how much CPU or memory the
program inside can eat. We add those caps by launching the whole sandbox inside a
systemd "scope" (a cgroup). These tests check we build the right systemd-run
prefix, and that if systemd is missing we degrade gracefully instead of crashing.
"""

from pathlib import Path

from isolate.config import SandboxConfig
from isolate.resources import (
    cpus_to_quota,
    limits_requested,
    systemd_scope_args,
)
from isolate.sandbox import build_command


def has_seq(args, seq):
    n = len(seq)
    return any(list(args[i : i + n]) == list(seq) for i in range(len(args) - n + 1))


def make_config(**overrides):
    base = dict(
        project=Path("/p"),
        home_dir=Path("/p/.isolate-home"),
        ro_system=[Path("/usr")],
        writable=[Path("/p")],
        readable=[],
        network=True,
        memory=None,
        cpus=None,
        term=None,
        command=["echo", "hi"],
    )
    base.update(overrides)
    return SandboxConfig(**base)


def test_cpus_to_quota_whole_and_fractional():
    assert cpus_to_quota(2) == "200%"
    assert cpus_to_quota(1) == "100%"
    assert cpus_to_quota(0.5) == "50%"
    assert cpus_to_quota(1.5) == "150%"


def test_limits_requested_is_false_when_no_caps():
    assert limits_requested(make_config()) is False


def test_limits_requested_is_true_with_memory_or_cpus():
    assert limits_requested(make_config(memory="4G")) is True
    assert limits_requested(make_config(cpus=2)) is True


def test_no_scope_args_when_no_limits():
    assert systemd_scope_args(make_config()) == []


def test_scope_args_have_memory_and_cpu_and_tasks():
    args = systemd_scope_args(make_config(memory="4G", cpus=2))
    assert args[0] == "systemd-run"
    assert "--user" in args
    assert "--scope" in args
    assert has_seq(args, ["-p", "MemoryMax=4G"])
    assert has_seq(args, ["-p", "CPUQuota=200%"])
    assert has_seq(args, ["-p", "TasksMax=512"])
    # The prefix must end with a bare "--" so the sandbox command follows.
    assert args[-1] == "--"


def test_scope_args_with_only_memory_has_no_cpu_quota():
    args = systemd_scope_args(make_config(memory="2G"))
    assert has_seq(args, ["-p", "MemoryMax=2G"])
    assert not any(a.startswith("CPUQuota=") for a in args)


def test_build_command_prepends_scope_when_systemd_available():
    cfg = make_config(memory="4G", cpus=2)
    argv = build_command(cfg, systemd_available=True)
    assert argv[0] == "systemd-run"
    # bwrap still appears, after the systemd "--" separator.
    assert "bwrap" in argv
    assert has_seq(argv, ["--", "bwrap"])


def test_build_command_skips_scope_when_systemd_missing():
    # Graceful fallback: limits were asked for, but systemd is not available.
    cfg = make_config(memory="4G", cpus=2)
    argv = build_command(cfg, systemd_available=False)
    assert argv[0] == "bwrap"
    assert "systemd-run" not in argv


def test_build_command_is_bwrap_only_when_no_limits():
    argv = build_command(make_config(), systemd_available=True)
    assert argv[0] == "bwrap"
    assert "systemd-run" not in argv
