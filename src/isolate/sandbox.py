"""Build the bubblewrap (`bwrap`) command from a resolved config.

This module is deliberately pure: `build_bwrap_args` takes a `SandboxConfig` and
returns a list of strings (the argv). It launches nothing and touches no files,
which makes it trivial to test.

The shape of the produced command follows the "whitelist / default-deny" model:
nothing from the host is visible unless we explicitly bind it in. The whole host
disk is never mounted, so the agent cannot read the real home directory or its
secrets.
"""

from __future__ import annotations

from . import resources
from .config import SandboxConfig


def build_bwrap_args(config: SandboxConfig) -> list[str]:
    """Return the full `bwrap ... -- <command>` argument list for `config`."""
    args: list[str] = ["bwrap"]

    # 1. Read-only system files: the libraries and binaries the command needs to
    #    run, exposed read-only so the command can use them but never change them.
    for path in config.ro_system:
        args += ["--ro-bind", str(path), str(path)]

    # 1b. Recreate merged-/usr symlinks (e.g. /bin -> usr/bin) inside the sandbox
    #     instead of binding both, which would be a double mount.
    for target, link_path in config.symlinks:
        args += ["--symlink", target, link_path]

    # 2. Virtual filesystems every normal program expects. /proc and /dev are
    #    fresh (isolated) ones, and /tmp is a private in-memory scratch space.
    args += ["--proc", "/proc"]
    args += ["--dev", "/dev"]
    args += ["--tmpfs", "/tmp"]

    # 3. Writable paths: the project directory and any extra grants. These are
    #    the only places on the host the command can change.
    for path in config.writable:
        args += ["--bind", str(path), str(path)]

    # 4. The throwaway fake home. HOME (set below) points here, so the command
    #    sees an empty, safe home instead of the user's real one.
    home = str(config.home_dir)
    args += ["--bind", home, home]

    # 5. Extra read-only grants (e.g. ~/.gitconfig). "-try" means "skip quietly
    #    if it does not exist" so a missing optional file is never a hard error.
    for path in config.readable:
        args += ["--ro-bind-try", str(path), str(path)]

    # 6. Start the command inside the project directory.
    args += ["--chdir", str(config.project)]

    # 7. Namespaces: isolate everything (processes, hostname, IPC, network, ...).
    #    bubblewrap also drops all Linux capabilities inside this new namespace.
    args += ["--unshare-all"]
    #    Re-share only the network when allowed, so the agent can reach its API.
    if config.network:
        args += ["--share-net"]

    # 8. Safety extras: die together with the launcher (no orphaned sandbox), and
    #    start a brand new terminal session (blocks TIOCSTI keystroke injection).
    args += ["--die-with-parent"]
    args += ["--new-session"]

    # 9. Environment: wipe everything inherited, then set only a small safe set.
    args += ["--clearenv"]
    args += ["--setenv", "HOME", home]
    args += ["--setenv", "PATH", "/usr/bin:/bin"]
    if config.term:
        args += ["--setenv", "TERM", config.term]

    # 10. Finally, the command to run, after a bare "--" so bwrap stops parsing
    #     its own options and treats the rest as the program plus its arguments.
    args += ["--", *config.command]

    return args


def build_command(config: SandboxConfig, *, systemd_available: bool) -> list[str]:
    """Build the final argv to actually run.

    This is the bubblewrap command, optionally wrapped in a systemd scope that
    applies CPU/memory caps. If caps were requested but systemd is not available,
    we drop the caps and return the bare bubblewrap command (a safe fallback).
    """
    bwrap_args = build_bwrap_args(config)
    if resources.limits_requested(config) and systemd_available:
        return resources.systemd_scope_args(config) + bwrap_args
    return bwrap_args
