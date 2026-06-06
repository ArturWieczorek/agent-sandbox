"""Tests for the system whitelist and symlink handling.

Modern Linux distros (including this Ubuntu) use "merged /usr": /bin, /sbin,
/lib, /lib64 are symlinks pointing into /usr. If we naively bind both /usr and
/bin, bwrap can fail or double-mount. So we bind the real directories and
recreate the symlinks instead. These tests build a tiny fake root in a temp
folder so we can check both layouts without touching the real system.
"""

from pathlib import Path

from isolate.paths import find_sensitive, system_mounts


def test_symlinked_bin_becomes_a_symlink_not_a_bind(tmp_path):
    # Simulate merged-/usr: /bin is a symlink to usr/bin.
    (tmp_path / "usr" / "bin").mkdir(parents=True)
    (tmp_path / "bin").symlink_to("usr/bin")

    ro_binds, symlinks = system_mounts(root=tmp_path)

    assert Path("/usr") in ro_binds
    assert ("usr/bin", "/bin") in symlinks
    # /bin must NOT also be a bind, or bwrap would try to mount it twice.
    assert Path("/bin") not in ro_binds


def test_real_bin_directory_is_bound_read_only(tmp_path):
    # Older layout: /bin is a real directory of its own.
    (tmp_path / "usr").mkdir()
    (tmp_path / "bin").mkdir()

    ro_binds, symlinks = system_mounts(root=tmp_path)

    assert Path("/bin") in ro_binds
    assert all(link != "/bin" for _, link in symlinks)


def test_selected_etc_files_included_when_present(tmp_path):
    (tmp_path / "usr").mkdir()
    etc = tmp_path / "etc"
    etc.mkdir()
    (etc / "resolv.conf").write_text("nameserver 1.1.1.1\n")

    ro_binds, _ = system_mounts(root=tmp_path)

    assert Path("/etc/resolv.conf") in ro_binds


def test_missing_etc_files_are_skipped(tmp_path):
    (tmp_path / "usr").mkdir()  # no /etc at all

    ro_binds, _ = system_mounts(root=tmp_path)

    assert Path("/etc/resolv.conf") not in ro_binds


def test_find_sensitive_flags_ssh_and_home(tmp_path):
    home = tmp_path / "me"
    (home / ".ssh").mkdir(parents=True)
    granted = [home, home / ".ssh", home / "project"]

    flagged = find_sensitive(granted, home=home)

    assert (home / ".ssh") in flagged  # the secret folder is flagged
    assert home in flagged  # granting the whole home is flagged
    assert (home / "project") not in flagged  # an ordinary project is fine
