"""The resolved configuration object that drives the sandbox.

`SandboxConfig` is a plain data holder: it is the single, fully-resolved picture
of "what sandbox do we want". The command builders in `sandbox.py` and the
resource wrapper in `resources.py` read from it. Loading and merging config from
files and command-line flags into this object is handled in `profiles.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised when configuration values are invalid, with a clear message."""


# The starting point for every profile. Chosen to be safe and useful out of the
# box: network on (agents need to reach their API), modest CPU/memory caps so a
# runaway agent cannot hog the machine, and only the project directory writable.
BUILTIN_DEFAULTS: dict = {
    "network": True,
    "memory": "4G",
    "cpus": 2,
    "writable": ["."],
    "readable": [],
    "home": ".isolate-home",
}

# A memory value like "4G", "512M", "1.5G", or a plain byte count. We keep this
# loose on purpose; systemd does the final, strict parsing.
_MEMORY_RE = re.compile(r"^\d+(\.\d+)?[KMGTPE]?$", re.IGNORECASE)


def validate_memory(value) -> None:
    """Raise ConfigError if `value` is not a usable memory size.

    None (no cap) and "infinity" are allowed. Plain numbers are treated as a byte
    count. Strings must look like a size such as "4G" or "512M".
    """
    if value is None:
        return
    if isinstance(value, bool):
        raise ConfigError(f"memory must be a size like '4G', not {value!r}")
    if isinstance(value, (int, float)):
        return
    if isinstance(value, str):
        if value.strip().lower() == "infinity":
            return
        if _MEMORY_RE.match(value.strip()):
            return
    raise ConfigError(
        f"memory {value!r} is not a valid size. Use forms like '4G', '512M', "
        f"'1.5G', or 'infinity' for no limit."
    )


def validate_cpus(value) -> None:
    """Raise ConfigError unless `value` is None or a positive number of cores."""
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(
            f"cpus {value!r} is not valid. Use a positive number of cores, "
            f"e.g. 1, 2, or 0.5."
        )


@dataclass
class SandboxConfig:
    """Everything needed to build one sandbox command.

    Paths are already absolute and expanded by the time they reach here.
    """

    project: Path
    """The working directory. Bound read-write and used as the start directory."""

    home_dir: Path
    """A throwaway "fake home" on the host. Bound read-write; HOME points here."""

    ro_system: list[Path]
    """Read-only system directories/files to expose (e.g. /usr, /bin, certs)."""

    writable: list[Path]
    """Paths the sandbox may write to (normally just the project directory)."""

    readable: list[Path]
    """Extra read-only paths to expose (e.g. ~/.gitconfig)."""

    network: bool = True
    """Whether the sandbox shares the host network (needed to reach an LLM API)."""

    memory: str | None = None
    """Memory cap as a systemd value (e.g. "4G"). None means no memory cap."""

    cpus: float | None = None
    """CPU cap in whole cores (e.g. 2 -> CPUQuota=200%). None means no CPU cap."""

    term: str | None = None
    """Value to pass through as TERM so interactive tools render correctly."""

    symlinks: list[tuple[str, str]] = field(default_factory=list)
    """(target, link_path) pairs to recreate inside the sandbox, for merged-/usr
    layouts where /bin, /lib, etc. are symlinks into /usr."""

    command: list[str] = field(default_factory=list)
    """The actual command to run inside the sandbox."""
