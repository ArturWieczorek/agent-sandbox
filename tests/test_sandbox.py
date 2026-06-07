"""Tests for the core bubblewrap command builder.

These are pure tests: we hand `build_bwrap_args` a config object and check the
exact argument list it produces. No real sandbox is launched here, so the tests
are fast and deterministic. This is the heart of the TDD loop.
"""

from pathlib import Path

from isolate.config import SandboxConfig
from isolate.sandbox import build_bwrap_args


def has_seq(args, seq):
    """True if `seq` appears as consecutive items inside `args`."""
    n = len(seq)
    return any(list(args[i : i + n]) == list(seq) for i in range(len(args) - n + 1))


def make_config(**overrides):
    base = dict(
        project=Path("/home/user/proj"),
        home_dir=Path("/home/user/proj/.isolate-home"),
        ro_system=[Path("/usr"), Path("/bin")],
        writable=[Path("/home/user/proj")],
        readable=[],
        network=True,
        memory=None,
        cpus=None,
        term="xterm-256color",
        command=["echo", "hi"],
    )
    base.update(overrides)
    return SandboxConfig(**base)


def test_starts_with_bwrap_and_ends_with_command():
    args = build_bwrap_args(make_config())
    assert args[0] == "bwrap"
    # The user command comes last, right after a bare "--" separator.
    assert args[-2:] == ["echo", "hi"]
    assert has_seq(args, ["--", "echo", "hi"])


def test_does_not_mount_whole_root():
    # The biggest safety property: we never bind the entire host disk.
    args = build_bwrap_args(make_config())
    assert not has_seq(args, ["--bind", "/", "/"])
    assert not has_seq(args, ["--ro-bind", "/", "/"])


def test_project_is_mounted_read_write():
    args = build_bwrap_args(make_config())
    assert has_seq(args, ["--bind", "/home/user/proj", "/home/user/proj"])


def test_system_dirs_are_read_only():
    args = build_bwrap_args(make_config())
    assert has_seq(args, ["--ro-bind", "/usr", "/usr"])
    assert has_seq(args, ["--ro-bind", "/bin", "/bin"])


def test_fake_home_is_bound_and_HOME_points_at_it():
    args = build_bwrap_args(make_config())
    home = "/home/user/proj/.isolate-home"
    assert has_seq(args, ["--bind", home, home])
    assert has_seq(args, ["--setenv", "HOME", home])


def test_network_shared_by_default():
    args = build_bwrap_args(make_config(network=True))
    assert "--share-net" in args


def test_network_off_means_no_share_net():
    args = build_bwrap_args(make_config(network=False))
    assert "--share-net" not in args


def test_core_isolation_flags_always_present():
    args = build_bwrap_args(make_config())
    for flag in ["--unshare-all", "--die-with-parent", "--new-session", "--clearenv"]:
        assert flag in args
    assert has_seq(args, ["--proc", "/proc"])
    assert has_seq(args, ["--dev", "/dev"])
    assert has_seq(args, ["--tmpfs", "/tmp"])
    assert has_seq(args, ["--chdir", "/home/user/proj"])


def test_clearenv_then_minimal_env_is_set():
    args = build_bwrap_args(make_config())
    # We wipe the environment, then set only a small safe set.
    assert has_seq(args, ["--setenv", "PATH", "/usr/bin:/bin"])
    assert has_seq(args, ["--setenv", "TERM", "xterm-256color"])


def test_extra_env_vars_are_set_after_clearenv():
    args = build_bwrap_args(
        make_config(env={"CLAUDE_CONFIG_DIR": "/home/u/.claude", "FOO": "bar"})
    )
    assert has_seq(args, ["--setenv", "CLAUDE_CONFIG_DIR", "/home/u/.claude"])
    assert has_seq(args, ["--setenv", "FOO", "bar"])
    # Injected vars must come after the environment is wiped, or they vanish.
    assert args.index("--clearenv") < args.index("CLAUDE_CONFIG_DIR")


def test_no_extra_env_by_default():
    args = build_bwrap_args(make_config())
    assert "CLAUDE_CONFIG_DIR" not in args


def test_extra_readable_paths_are_read_only_binds():
    cfg = make_config(readable=[Path("/home/user/.gitconfig")])
    args = build_bwrap_args(cfg)
    assert has_seq(
        args,
        ["--ro-bind-try", "/home/user/.gitconfig", "/home/user/.gitconfig"],
    )


def test_symlinks_are_emitted_for_merged_usr():
    cfg = make_config(symlinks=[("usr/bin", "/bin"), ("usr/lib", "/lib")])
    args = build_bwrap_args(cfg)
    assert has_seq(args, ["--symlink", "usr/bin", "/bin"])
    assert has_seq(args, ["--symlink", "usr/lib", "/lib"])


def test_extra_writable_paths_are_read_write_binds():
    cfg = make_config(writable=[Path("/home/user/proj"), Path("/data/cache")])
    args = build_bwrap_args(cfg)
    assert has_seq(args, ["--bind", "/data/cache", "/data/cache"])
