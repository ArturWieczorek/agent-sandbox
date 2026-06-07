"""Turn config files, a chosen profile, and CLI flags into a SandboxConfig.

Think of building the final config like making a sandwich in layers, where each
later layer can change what the one below put down:

1. Built-in defaults (the base bread).
2. The user's global config file (~/.config/isolate/config.yml).
3. The project's local .isolate.yml.
4. The flags typed on the command line (the top, wins ties).

A "profile" is just a named bundle of these settings (for example a "readonly"
profile). After merging the layers we resolve every path to an absolute one,
pick the throwaway home folder, and attach the read-only system whitelist.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from . import paths as paths_module
from .config import (
    BUILTIN_DEFAULTS,
    ConfigError,
    SandboxConfig,
    validate_cpus,
    validate_memory,
)


class UnknownProfileError(ConfigError):
    """Raised when a profile name is requested that no config file defines."""


def load_profiles(config_paths: list[Path]) -> dict[str, dict]:
    """Read the given YAML files in order and merge their `profiles` sections.

    Missing files are skipped quietly. Later files win on a per-key basis, so a
    project file can override one setting from the user's global file without
    repeating the rest.
    """
    merged: dict[str, dict] = {}
    for raw_path in config_paths:
        if raw_path is None:
            continue
        path = Path(raw_path)
        if not path.is_file():
            continue
        data = yaml.safe_load(path.read_text()) or {}
        profiles = data.get("profiles") or {}
        for name, settings in profiles.items():
            dest = merged.setdefault(name, {})
            dest.update(settings or {})
    return merged


def resolve_profile_dict(name: str, config_paths: list[Path]) -> dict:
    """Merge built-in defaults with the named profile from the config files.

    The "default" profile always exists (it is the built-in defaults even with no
    files). Any other name must be defined in at least one config file, otherwise
    we raise a clear UnknownProfileError.
    """
    file_profiles = load_profiles(config_paths)
    if name != "default" and name not in file_profiles:
        known = ", ".join(sorted(["default", *file_profiles])) or "default"
        raise UnknownProfileError(
            f"Unknown profile {name!r}. Known profiles: {known}."
        )
    result = copy.deepcopy(BUILTIN_DEFAULTS)
    result.update(file_profiles.get(name, {}))
    return result


def apply_cli_overrides(profile_dict: dict, overrides: dict) -> dict:
    """Apply command-line flags on top of a profile dict.

    Scalar flags (network, memory, cpus, home) replace the profile value when
    given. The list flags (allow_write, allow_read) ADD to the profile's lists
    rather than replacing them, so "isolate run --allow-write /data" widens the
    grant instead of throwing away the project directory.
    """
    out = dict(profile_dict)
    for key in ("network", "memory", "cpus", "home"):
        if overrides.get(key) is not None:
            out[key] = overrides[key]
    extra_write = overrides.get("allow_write")
    if extra_write:
        out["writable"] = list(out.get("writable", [])) + list(extra_write)
    extra_read = overrides.get("allow_read")
    if extra_read:
        out["readable"] = list(out.get("readable", [])) + list(extra_read)
    env_override = overrides.get("env")
    if env_override:
        out["env"] = {**out.get("env", {}), **env_override}
    return out


def _expand(path_like: str, *, project_dir: Path, real_home: Path) -> Path:
    """Resolve one configured path to an absolute path.

    A leading ~ means the user's real home. A relative path is taken relative to
    the project directory. The result is made absolute (but not required to
    exist, since we may be granting a path the agent will create).
    """
    text = str(path_like)
    if text == "~":
        return real_home.resolve()
    if text.startswith("~/"):
        return (real_home / text[2:]).resolve()
    path = Path(text)
    if not path.is_absolute():
        path = project_dir / path
    return path.resolve()


def resolve(
    *,
    command: list[str],
    profile: str,
    project_dir: Path,
    config_paths: list[Path],
    cli_overrides: dict,
    real_home: Path,
    term: str | None,
    system_mounts_fn=None,
) -> SandboxConfig:
    """Produce the final, fully-resolved SandboxConfig.

    `system_mounts_fn` is injectable so tests can supply a fake system layout.
    """
    if system_mounts_fn is None:
        system_mounts_fn = paths_module.system_mounts

    profile_dict = resolve_profile_dict(profile, config_paths)
    profile_dict = apply_cli_overrides(profile_dict, cli_overrides or {})

    validate_memory(profile_dict.get("memory"))
    validate_cpus(profile_dict.get("cpus"))

    project_dir = Path(project_dir).resolve()
    real_home = Path(real_home)

    writable = [
        _expand(p, project_dir=project_dir, real_home=real_home)
        for p in profile_dict.get("writable", [])
    ]
    readable = [
        _expand(p, project_dir=project_dir, real_home=real_home)
        for p in profile_dict.get("readable", [])
    ]
    home_dir = _expand(
        profile_dict.get("home", ".isolate-home"),
        project_dir=project_dir,
        real_home=real_home,
    )

    ro_system, symlinks = system_mounts_fn()

    return SandboxConfig(
        project=project_dir,
        home_dir=home_dir,
        ro_system=ro_system,
        writable=writable,
        readable=readable,
        network=bool(profile_dict.get("network", True)),
        memory=profile_dict.get("memory"),
        cpus=profile_dict.get("cpus"),
        term=term,
        command=list(command),
        symlinks=symlinks,
        env=dict(profile_dict.get("env", {})),
    )
