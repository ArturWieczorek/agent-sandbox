"""Tests for loading config files, merging profiles, and resolving a config.

These tests build small YAML files in a temp folder and check the layering rules:
built-in defaults, then the user file, then the project file, then CLI flags,
with later layers winning. They also check that a profile turns into a correct,
fully-resolved SandboxConfig (absolute paths, fake home, system whitelist).
"""

from pathlib import Path

import pytest

from isolate.config import ConfigError
from isolate.profiles import (
    UnknownProfileError,
    apply_cli_overrides,
    load_profiles,
    resolve,
    resolve_profile_dict,
)


def write_yaml(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


# A fake system layout for resolution tests, so we never touch the real machine.
def fake_system_mounts(root=Path("/")):
    return ([Path("/usr"), Path("/etc/resolv.conf")], [("usr/bin", "/bin")])


def test_load_profiles_merges_user_then_project(tmp_path):
    user = write_yaml(
        tmp_path / "user.yml",
        "profiles:\n  default:\n    memory: 8G\n    cpus: 4\n",
    )
    project = write_yaml(
        tmp_path / "project.yml",
        "profiles:\n  default:\n    cpus: 1\n",
    )
    merged = load_profiles([user, project])
    # Project overrides cpus; user-only memory survives.
    assert merged["default"]["cpus"] == 1
    assert merged["default"]["memory"] == "8G"


def test_load_profiles_skips_missing_files(tmp_path):
    project = write_yaml(
        tmp_path / "project.yml", "profiles:\n  default:\n    network: false\n"
    )
    merged = load_profiles([tmp_path / "does-not-exist.yml", project])
    assert merged["default"]["network"] is False


def test_resolve_profile_dict_starts_from_builtin_defaults(tmp_path):
    # No files: the default profile is just the built-in defaults.
    d = resolve_profile_dict("default", [])
    assert d["memory"] == "4G"
    assert d["network"] is True


def test_unknown_profile_raises(tmp_path):
    with pytest.raises(UnknownProfileError):
        resolve_profile_dict("nope", [])


def test_named_profile_from_file_overrides_builtin(tmp_path):
    f = write_yaml(
        tmp_path / "c.yml",
        "profiles:\n  readonly:\n    network: false\n    writable: []\n",
    )
    d = resolve_profile_dict("readonly", [f])
    assert d["network"] is False
    assert d["writable"] == []
    # Untouched keys still come from built-in defaults.
    assert d["home"] == ".isolate-home"


def test_apply_cli_overrides_scalars_and_list_append():
    base = {"network": True, "memory": "4G", "writable": ["."], "readable": []}
    out = apply_cli_overrides(
        base,
        {
            "network": False,
            "memory": "1G",
            "allow_write": ["/data"],
            "allow_read": ["/ref"],
        },
    )
    assert out["network"] is False  # scalar replaced
    assert out["memory"] == "1G"
    assert out["writable"] == [".", "/data"]  # list appended, not replaced
    assert out["readable"] == ["/ref"]


def test_apply_cli_overrides_ignores_none_values():
    base = {"network": True, "memory": "4G", "writable": ["."], "readable": []}
    out = apply_cli_overrides(base, {"memory": None, "network": None})
    assert out["memory"] == "4G"
    assert out["network"] is True


def test_apply_cli_overrides_merges_env():
    base = {"network": True, "writable": ["."], "readable": [], "env": {"A": "1"}}
    out = apply_cli_overrides(base, {"env": {"B": "2", "A": "9"}})
    assert out["env"] == {"A": "9", "B": "2"}  # override wins on conflict


def test_resolve_sets_env_from_overrides(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    cfg = resolve(
        command=["x"],
        profile="default",
        project_dir=project,
        config_paths=[],
        cli_overrides={"env": {"CLAUDE_CONFIG_DIR": "/h/.claude"}},
        real_home=tmp_path,
        term=None,
        system_mounts_fn=fake_system_mounts,
    )
    assert cfg.env == {"CLAUDE_CONFIG_DIR": "/h/.claude"}


def test_resolve_produces_absolute_paths_and_fake_home(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    cfg = resolve(
        command=["claude"],
        profile="default",
        project_dir=project,
        config_paths=[],
        cli_overrides={},
        real_home=tmp_path / "home",
        term="xterm",
        system_mounts_fn=fake_system_mounts,
    )
    # Project bound writable as an absolute path.
    assert project.resolve() in [p.resolve() for p in cfg.writable]
    # Fake home lives inside the project and is separate from the real home.
    assert cfg.home_dir == (project / ".isolate-home").resolve()
    assert cfg.home_dir != (tmp_path / "home")
    # System whitelist and symlinks came from the injected layout.
    assert Path("/usr") in cfg.ro_system
    assert ("usr/bin", "/bin") in cfg.symlinks
    assert cfg.command == ["claude"]
    assert cfg.network is True


def test_resolve_expands_tilde_in_readable(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    real_home = tmp_path / "home"
    real_home.mkdir()
    cfg = resolve(
        command=["x"],
        profile="default",
        project_dir=project,
        config_paths=[],
        cli_overrides={"allow_read": ["~/.gitconfig"]},
        real_home=real_home,
        term=None,
        system_mounts_fn=fake_system_mounts,
    )
    assert (real_home / ".gitconfig") in cfg.readable


def test_resolve_rejects_bad_memory(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(ConfigError):
        resolve(
            command=["x"],
            profile="default",
            project_dir=project,
            config_paths=[],
            cli_overrides={"memory": "loads"},
            real_home=tmp_path,
            term=None,
            system_mounts_fn=fake_system_mounts,
        )
