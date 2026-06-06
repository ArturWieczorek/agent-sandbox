"""Preflight checks: does this machine have what the sandbox needs?

`isolate doctor` runs a short health check, like a car's dashboard lights before
a drive. Each check answers one question, says whether it passed, and if not
tells you the exact command to fix it. Required checks must pass for the sandbox
to work at all; optional ones (like systemd) only affect extra features.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from . import resources


@dataclass
class Check:
    """The result of one health check."""

    name: str
    ok: bool
    required: bool
    detail: str
    fix: str | None = None


def _read_sysctl(name: str) -> str | None:
    """Read a kernel sysctl value via /proc/sys, or None if it does not exist."""
    path = Path("/proc/sys") / name
    try:
        return path.read_text()
    except OSError:
        return None


def check_bwrap(which=shutil.which) -> Check:
    """The sandbox cannot exist without the bubblewrap binary."""
    path = which("bwrap")
    if path:
        return Check("bubblewrap", True, True, f"found at {path}")
    return Check(
        "bubblewrap",
        False,
        True,
        "the 'bwrap' command was not found",
        fix="install it, e.g. on Ubuntu: sudo apt install bubblewrap",
    )


def check_user_namespaces(read_sysctl=_read_sysctl) -> Check:
    """Bubblewrap builds the sandbox using unprivileged user namespaces."""
    clone = read_sysctl("kernel/unprivileged_userns_clone")
    if clone is not None and clone.strip() == "0":
        return Check(
            "user namespaces",
            False,
            True,
            "unprivileged user namespaces are disabled",
            fix="sudo sysctl -w kernel.unprivileged_userns_clone=1",
        )
    return Check("user namespaces", True, True, "unprivileged user namespaces allowed")


def check_systemd(available_fn=resources.is_systemd_available) -> Check:
    """Optional: needed only for CPU/memory limits via a systemd scope."""
    if available_fn():
        return Check(
            "systemd user scope",
            True,
            False,
            "available, so CPU and memory limits will be enforced",
        )
    return Check(
        "systemd user scope",
        False,
        False,
        "not available, so the sandbox runs without CPU/memory limits",
    )


def all_checks() -> list[Check]:
    """Run every check against the real machine."""
    return [check_bwrap(), check_user_namespaces(), check_systemd()]


def overall_status(checks: list[Check]) -> int:
    """Return 0 if all REQUIRED checks passed, else 1."""
    return 0 if all(c.ok for c in checks if c.required) else 1


def format_report(checks: list[Check]) -> str:
    """Render the checks as a friendly, aligned text report."""
    lines = []
    for c in checks:
        marker = "PASS" if c.ok else "FAIL"
        tag = "" if c.required else " (optional)"
        lines.append(f"[{marker}] {c.name}{tag}: {c.detail}")
        if not c.ok and c.fix:
            lines.append(f"        fix: {c.fix}")
    status = "All good." if overall_status(checks) == 0 else "Something required is missing (see above)."
    lines.append("")
    lines.append(status)
    return "\n".join(lines)


def doctor_main() -> int:
    """Run all checks, print the report, and return an exit code."""
    checks = all_checks()
    print(format_report(checks))
    return overall_status(checks)
