"""A first trivial test so the suite is green from the very first commit."""

import isolate


def test_package_has_version():
    assert isolate.__version__ == "0.1.0"
