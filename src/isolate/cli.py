"""The command-line interface: `isolate run ...` and `isolate doctor`.

This module only wires things together. It parses what you typed, asks the other
modules to build the sandbox command, and then either prints it (`--dry-run`) or
launches it. The interesting logic lives in `profiles`, `sandbox`, `resources`,
`paths`, and `doctor`; keeping `cli` thin makes all of those easy to test.
"""

from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path

from . import agents, paths, profiles, resources, sandbox
from .config import ConfigError
from .doctor import doctor_main


def split_command(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split argv at the first bare "--" into (isolate args, inner command).

    Everything before "--" configures isolate; everything after is the program to
    run inside the sandbox. If there is no "--", the command part is empty.
    """
    if "--" in argv:
        index = argv.index("--")
        return argv[:index], argv[index + 1 :]
    return argv, []


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the isolate CLI."""
    parser = argparse.ArgumentParser(
        prog="isolate",
        description="Run a command inside a safe bubblewrap sandbox.",
    )
    subparsers = parser.add_subparsers(dest="cmd_name")

    run = subparsers.add_parser(
        "run", help="run a command inside the sandbox (put the command after --)"
    )
    run.add_argument(
        "--profile", default="default", help="named profile to use (default: default)"
    )
    run.add_argument(
        "--agent",
        default=None,
        metavar="NAME",
        help="run a known agent (claude or gemini); auto-grants the paths it needs",
    )
    run.add_argument(
        "--login",
        action="store_true",
        help="with --agent, also share the agent's saved login/config from your "
        "home (no re-login, but wider access)",
    )

    network = run.add_mutually_exclusive_group()
    network.add_argument(
        "--network",
        dest="network",
        action="store_true",
        default=None,
        help="allow network access (the default)",
    )
    network.add_argument(
        "--no-network",
        dest="network",
        action="store_false",
        help="block all network access (air-gapped run)",
    )

    run.add_argument("--memory", default=None, help="memory cap, e.g. 4G or 512M")
    run.add_argument(
        "--cpus", type=float, default=None, help="CPU cap in cores, e.g. 2 or 0.5"
    )
    run.add_argument("--home", default=None, help="path to use as the fake home")
    run.add_argument(
        "--allow-write",
        action="append",
        default=None,
        metavar="PATH",
        help="extra path the sandbox may write to (repeatable)",
    )
    run.add_argument(
        "--allow-read",
        action="append",
        default=None,
        metavar="PATH",
        help="extra path the sandbox may read (repeatable)",
    )
    run.add_argument(
        "--config", default=None, help="extra config file to layer on top"
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="print the command that would run, without running it",
    )

    subparsers.add_parser("doctor", help="check the machine has what is needed")
    return parser


def build_overrides(args: argparse.Namespace) -> dict:
    """Turn parsed run-flags into the overrides dict the resolver expects."""
    return {
        "network": args.network,
        "memory": args.memory,
        "cpus": args.cpus,
        "home": args.home,
        "allow_write": args.allow_write,
        "allow_read": args.allow_read,
    }


def default_config_paths(real_home: Path, project_dir: Path) -> list[Path]:
    """The config files we read, in increasing priority order."""
    return [
        real_home / ".config" / "isolate" / "config.yml",
        project_dir / ".isolate.yml",
    ]


def _exec(argv: list[str]) -> int:
    """Replace this process with the sandbox command (best for terminal apps)."""
    try:
        os.execvp(argv[0], argv)
    except FileNotFoundError:
        print(f"error: '{argv[0]}' was not found on PATH", file=sys.stderr)
        return 127
    return 0  # unreachable on success; execvp never returns


def _run(args: argparse.Namespace, command: list[str]) -> int:
    overrides = build_overrides(args)
    inner_command = command

    if args.agent:
        # A known agent: work out the real command and the paths it needs, then
        # fold those grants into the overrides. Any words after -- are passed
        # through to the agent as extra arguments.
        try:
            launch = agents.resolve_agent(
                args.agent, extra_args=command, login=args.login
            )
        except agents.AgentError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        inner_command = launch.command
        overrides["allow_read"] = (overrides.get("allow_read") or []) + [
            str(p) for p in launch.reads
        ]
        if launch.writes:
            overrides["allow_write"] = (overrides.get("allow_write") or []) + [
                str(p) for p in launch.writes
            ]
    elif not command:
        print(
            "error: no command given. Put the command after --, "
            "for example: isolate run -- claude (or use --agent claude)",
            file=sys.stderr,
        )
        return 2

    project_dir = Path.cwd()
    real_home = Path.home()
    config_paths = default_config_paths(real_home, project_dir)
    if args.config:
        config_paths.append(Path(args.config))

    try:
        config = profiles.resolve(
            command=inner_command,
            profile=args.profile,
            project_dir=project_dir,
            config_paths=config_paths,
            cli_overrides=overrides,
            real_home=real_home,
            term=os.environ.get("TERM"),
        )
    except ConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    # Warn (do not block) if the user granted something that usually holds secrets.
    for flagged in paths.find_sensitive(config.writable + config.readable, real_home):
        print(
            f"warning: you granted access to {flagged}, which may expose secrets "
            f"to the sandboxed command",
            file=sys.stderr,
        )

    systemd_available = resources.is_systemd_available()
    if resources.limits_requested(config) and not systemd_available:
        print(
            "warning: systemd user scope is unavailable; running without "
            "CPU/memory limits",
            file=sys.stderr,
        )

    argv = sandbox.build_command(config, systemd_available=systemd_available)

    if args.dry_run:
        print(shlex.join(argv))
        return 0

    # Only now, when we are actually launching, do we touch the filesystem.
    config.home_dir.mkdir(parents=True, exist_ok=True)
    return _exec(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    left, command = split_command(argv)

    parser = build_arg_parser()
    try:
        args = parser.parse_args(left)
    except SystemExit as exit_error:  # argparse calls sys.exit on bad input
        return int(exit_error.code) if exit_error.code is not None else 0

    if args.cmd_name == "doctor":
        return doctor_main()
    if args.cmd_name == "run":
        return _run(args, command)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
