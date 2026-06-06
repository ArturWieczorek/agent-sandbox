"""Add CPU and memory caps to a sandbox using a systemd user scope.

Bubblewrap isolates *what* a program can see and touch. It does not limit *how
much* CPU or memory it can use. To add those caps we launch the whole sandbox
inside a transient systemd "scope", which is just a friendly front-end to a
Linux cgroup (the kernel feature that meters resources).

Real life analogy: bubblewrap gives the agent its own room; the systemd scope is
the meal plan that says "you get this much food and no more", so one greedy guest
cannot eat the whole kitchen and starve everyone else (your other apps).

If systemd is not available, we simply skip the caps and let the caller warn the
user. The sandbox itself still works; it just runs without resource limits.
"""

from __future__ import annotations

import os
import shutil

from .config import SandboxConfig

# A sane default cap on the number of processes/threads inside the scope, to stop
# a fork bomb. Applied whenever we create a scope at all.
_DEFAULT_TASKS_MAX = "512"


def cpus_to_quota(cpus: float) -> str:
    """Turn a core count into a systemd CPUQuota string.

    systemd expresses CPU limits as a percentage where 100% means one full core.
    So 2 cores -> "200%", half a core -> "50%". Whole numbers stay whole.
    """
    value = cpus * 100
    if value == int(value):
        return f"{int(value)}%"
    return f"{value:g}%"


def limits_requested(config: SandboxConfig) -> bool:
    """True if the config asks for any CPU or memory cap."""
    return config.memory is not None or config.cpus is not None


def systemd_scope_args(config: SandboxConfig) -> list[str]:
    """Build the `systemd-run --user --scope ... --` prefix for `config`.

    Returns an empty list when no caps were requested. The returned prefix ends
    with a bare "--" so the sandbox command can be appended directly after it.
    """
    if not limits_requested(config):
        return []

    args = ["systemd-run", "--user", "--scope", "--quiet"]
    if config.memory is not None:
        args += ["-p", f"MemoryMax={config.memory}"]
    if config.cpus is not None:
        args += ["-p", f"CPUQuota={cpus_to_quota(config.cpus)}"]
    args += ["-p", f"TasksMax={_DEFAULT_TASKS_MAX}"]
    args += ["--"]
    return args


def is_systemd_available() -> bool:
    """Best-effort check that a systemd user scope can be created here.

    We need the `systemd-run` binary and a running user session bus (signalled by
    XDG_RUNTIME_DIR). `isolate doctor` does a stronger live check; this quick test
    is enough to decide whether to attempt resource limits.
    """
    if shutil.which("systemd-run") is None:
        return False
    return bool(os.environ.get("XDG_RUNTIME_DIR"))
