"""Decide which host paths make up the read-only system base of the sandbox.

The sandbox starts as an empty room. For normal programs to run we must hand
them the system's shared libraries and basic config files, all read-only. This
module figures out exactly which directories and files to expose, and handles
the "merged /usr" symlink layout used by modern distros.

It also offers a small safety helper, `find_sensitive`, that spots when a user
has accidentally granted something dangerous (like their whole home folder or
their ~/.ssh keys) so the caller can warn them.
"""

from __future__ import annotations

import os
from pathlib import Path

# Top-level directories that hold binaries and libraries. On merged-/usr systems
# the ones after "usr" are symlinks into it; on older systems they are real.
_SYSTEM_ROOT_ENTRIES = ["usr", "bin", "sbin", "lib", "lib64", "lib32", "libx32"]

# Small, non-secret /etc files and folders programs commonly need: how to resolve
# names, who the users are, and the trust store for TLS certificates. We expose
# only these, never the whole /etc.
_ETC_ENTRIES = [
    "resolv.conf",
    "hosts",
    "host.conf",
    "nsswitch.conf",
    "passwd",
    "group",
    "localtime",
    "ld.so.cache",
    "ld.so.conf",
    "ld.so.conf.d",
    "ssl",
    "pki",
    "ca-certificates",
    "ca-certificates.conf",
    "alternatives",
]

# Folder/file names that almost always hold secrets. Granting these to a sandbox
# defeats the purpose, so we flag them.
_SENSITIVE_NAMES = {
    ".ssh",
    ".gnupg",
    ".pgp",
    ".aws",
    ".kube",
    ".password-store",
    ".secrets",
    ".netrc",
    ".git-credentials",
    ".npmrc",
    ".pypirc",
}


def system_mounts(root: Path = Path("/")) -> tuple[list[Path], list[tuple[str, str]]]:
    """Work out the read-only system base for the sandbox.

    Returns a pair ``(ro_binds, symlinks)`` where:

    - ``ro_binds`` is a list of absolute paths to expose with ``--ro-bind``.
    - ``symlinks`` is a list of ``(target, link_path)`` pairs to recreate inside
      the sandbox with ``--symlink`` (used for merged-/usr links like
      ``/bin -> usr/bin``).

    ``root`` is the host root to inspect; tests pass a fake root so they never
    depend on the real machine.
    """
    ro_binds: list[Path] = []
    symlinks: list[tuple[str, str]] = []

    for entry in _SYSTEM_ROOT_ENTRIES:
        host_path = root / entry
        sandbox_path = "/" + entry
        if not host_path.exists() and not host_path.is_symlink():
            continue
        if host_path.is_symlink():
            # Recreate the same link inside the sandbox instead of binding it,
            # so we never try to mount a directory and its symlink alias twice.
            target = os.readlink(host_path)
            symlinks.append((target, sandbox_path))
        else:
            ro_binds.append(Path(sandbox_path))

    etc = root / "etc"
    if etc.is_dir():
        for name in _ETC_ENTRIES:
            if (etc / name).exists():
                ro_binds.append(Path("/etc") / name)

    return ro_binds, symlinks


def find_sensitive(paths: list[Path], home: Path) -> list[Path]:
    """Return the granted paths that look dangerous to expose.

    A path is flagged if it IS the user's real home directory, or if its name is
    a well-known secret store (e.g. ``.ssh``). The caller can then warn the user
    rather than silently handing secrets to the agent.
    """
    home = home.expanduser()
    flagged: list[Path] = []
    for path in paths:
        resolved = path.expanduser()
        if resolved == home:
            flagged.append(path)
        elif resolved.name in _SENSITIVE_NAMES:
            flagged.append(path)
    return flagged
