"""Tests for the `isolate doctor` preflight checks.

Each check is a small function that takes its "probe" (how it looks at the world)
as an argument, so tests can feed it fake answers and never depend on the real
machine. We check that good and bad situations are reported correctly and that
required failures make the command exit non-zero.
"""

from isolate.doctor import (
    Check,
    check_bwrap,
    check_systemd,
    check_user_namespaces,
    format_report,
    overall_status,
)


def test_check_bwrap_found():
    c = check_bwrap(which=lambda name: "/usr/bin/bwrap")
    assert c.ok is True
    assert c.required is True


def test_check_bwrap_missing_has_fix():
    c = check_bwrap(which=lambda name: None)
    assert c.ok is False
    assert c.fix and "install" in c.fix


def test_user_namespaces_enabled():
    c = check_user_namespaces(read_sysctl=lambda name: "1")
    assert c.ok is True


def test_user_namespaces_disabled_has_fix():
    c = check_user_namespaces(read_sysctl=lambda name: "0")
    assert c.ok is False
    assert "sysctl" in c.fix


def test_systemd_is_optional():
    c = check_systemd(available_fn=lambda: False)
    assert c.ok is False
    assert c.required is False


def test_format_report_marks_pass_and_fail_and_shows_fix():
    report = format_report(
        [
            Check("alpha", True, True, "all good"),
            Check("beta", False, True, "broken", fix="do the thing"),
        ]
    )
    assert "PASS" in report
    assert "FAIL" in report
    assert "do the thing" in report


def test_overall_status_fails_only_on_required_failures():
    # A required check failing -> non-zero exit.
    assert overall_status([Check("a", False, True, "x")]) == 1
    # An optional check failing -> still success.
    assert (
        overall_status(
            [Check("a", True, True, "x"), Check("b", False, False, "opt")]
        )
        == 0
    )
