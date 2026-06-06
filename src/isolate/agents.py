"""Recipes for running known AI agents inside the sandbox.

The agents you run (Claude Code, the Gemini CLI) live under your home folder,
which the sandbox never mounts. So a bare `isolate run -- claude` cannot find
them. This module knows, for each supported agent, two things:

1. the exact command to run inside the sandbox, and
2. the small set of read-only paths to grant so the agent (and its runtime) is
   visible.

That lets the CLI offer a simple `isolate run --agent claude` instead of making
you remember the grant flags by hand.

Real life picture: it is like a coat-check ticket for a known guest. Instead of
describing the guest's coat every time, you say "the usual for Claude" and the
attendant fetches exactly the right items.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path


class AgentError(Exception):
    """Raised when a requested agent is unknown or not installed."""


@dataclass
class AgentLaunch:
    """The result of resolving an agent: what to run and what to grant."""

    command: list[str]
    """The full command to run inside the sandbox (resolved binary plus args)."""

    reads: list[Path]
    """Read-only paths to grant so the agent and its runtime can be found."""

    writes: list[Path] = field(default_factory=list)
    """Extra writable paths (only used with login mode, for the agent's config)."""


def _dedup(paths: list[Path]) -> list[Path]:
    """Drop duplicates while keeping the first-seen order."""
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def resolve_agent(
    name: str,
    *,
    extra_args: list[str],
    login: bool = False,
    which=shutil.which,
    home: Path | None = None,
) -> AgentLaunch:
    """Resolve a known agent by name into an AgentLaunch.

    `extra_args` are passed through to the agent. `login` opts in to sharing the
    agent's saved login/config from your home (wider access, but no re-login).
    `which` and `home` are injectable so tests never touch the real machine.
    """
    home = Path(home) if home is not None else Path.home()
    key = name.lower()
    if key == "claude":
        return _resolve_claude(extra_args, login, which, home)
    if key == "gemini":
        return _resolve_gemini(extra_args, login, which, home)
    raise AgentError(f"Unknown agent {name!r}. Known agents: claude, gemini.")


def _resolve_claude(extra_args, login, which, home) -> AgentLaunch:
    launcher = which("claude")
    if not launcher:
        raise AgentError(
            "claude was not found on your PATH. Install Claude Code first, "
            "then try again."
        )
    real = Path(launcher).resolve()
    # Claude is a self-contained binary kept under ~/.local/share/claude. Grant
    # that whole folder (covers every installed version) plus the resolved binary
    # in case it lives elsewhere. Missing paths are skipped safely at mount time.
    reads = _dedup([home / ".local" / "share" / "claude", real])
    writes = [home / ".claude", home / ".claude.json"] if login else []
    return AgentLaunch(command=[str(real), *extra_args], reads=reads, writes=writes)


def _resolve_gemini(extra_args, login, which, home) -> AgentLaunch:
    gem = which("gemini")
    if not gem:
        raise AgentError(
            "gemini was not found on your PATH. Install the Gemini CLI first, "
            "then try again."
        )
    node = which("node")
    if not node:
        raise AgentError(
            "node was not found, but the Gemini CLI needs Node.js to run. "
            "Install Node.js (or make sure it is on your PATH)."
        )
    gem_real = Path(gem).resolve()
    node_real = Path(node).resolve()
    reads = []
    # If node sits in a "<prefix>/bin" layout (true for nvm and most installs),
    # grant the whole <prefix>. That covers the node runtime AND the globally
    # installed gemini package under <prefix>/lib/node_modules.
    if node_real.parent.name == "bin":
        reads.append(node_real.parent.parent)
    reads += [node_real, gem_real]
    writes = [home / ".gemini"] if login else []
    # Run gemini explicitly through node so we do not depend on a shebang or on
    # node being on PATH inside the sandbox.
    return AgentLaunch(
        command=[str(node_real), str(gem_real), *extra_args],
        reads=_dedup(reads),
        writes=writes,
    )
