"""Tests for command-line parsing and the top-level `main` entry point.

We avoid launching a real sandbox by always using `--dry-run`, which prints the
command it WOULD run instead of running it. That keeps these tests fast and safe.
"""

from isolate.cli import build_arg_parser, build_overrides, main, split_command


def test_split_command_at_double_dash():
    left, cmd = split_command(["run", "--no-network", "--", "claude", "-p", "hi"])
    assert left == ["run", "--no-network"]
    assert cmd == ["claude", "-p", "hi"]


def test_split_command_without_double_dash():
    left, cmd = split_command(["doctor"])
    assert left == ["doctor"]
    assert cmd == []


def test_overrides_no_network_is_false():
    args = build_arg_parser().parse_args(["run", "--no-network"])
    assert build_overrides(args)["network"] is False


def test_overrides_network_unset_is_none():
    args = build_arg_parser().parse_args(["run"])
    assert build_overrides(args)["network"] is None


def test_overrides_memory_cpus_and_allowlists():
    args = build_arg_parser().parse_args(
        [
            "run",
            "--memory",
            "8G",
            "--cpus",
            "4",
            "--allow-write",
            "/data",
            "--allow-read",
            "/ref",
        ]
    )
    ov = build_overrides(args)
    assert ov["memory"] == "8G"
    assert ov["cpus"] == 4.0
    assert ov["allow_write"] == ["/data"]
    assert ov["allow_read"] == ["/ref"]


def test_main_dry_run_prints_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--no-network", "--dry-run", "--", "echo", "hi"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "bwrap" in out
    assert "--share-net" not in out  # network was turned off
    assert "echo" in out


def test_main_dry_run_does_not_create_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["run", "--dry-run", "--", "echo", "hi"])
    # Dry run must not touch the filesystem (no fake home created).
    assert not (tmp_path / ".isolate-home").exists()


def test_main_run_without_command_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--dry-run"])
    assert rc != 0


def test_main_unknown_profile_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--profile", "ghost", "--dry-run", "--", "echo", "hi"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "profile" in err.lower()
