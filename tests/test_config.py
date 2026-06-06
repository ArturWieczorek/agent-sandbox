"""Tests for built-in defaults and value validation."""

import pytest

from isolate.config import (
    BUILTIN_DEFAULTS,
    ConfigError,
    validate_cpus,
    validate_memory,
)


def test_builtin_defaults_are_safe():
    # Network on (agents need their API), modest caps, project writable.
    assert BUILTIN_DEFAULTS["network"] is True
    assert BUILTIN_DEFAULTS["memory"] == "4G"
    assert BUILTIN_DEFAULTS["cpus"] == 2
    assert BUILTIN_DEFAULTS["writable"] == ["."]
    assert BUILTIN_DEFAULTS["readable"] == []
    assert BUILTIN_DEFAULTS["home"] == ".isolate-home"


def test_validate_memory_accepts_common_forms():
    for good in ["4G", "512M", "2g", "1.5G", "infinity", None]:
        validate_memory(good)  # should not raise


def test_validate_memory_rejects_garbage():
    for bad in ["4 gigs", "lots", "4GB!", ""]:
        with pytest.raises(ConfigError):
            validate_memory(bad)


def test_validate_cpus_accepts_positive_numbers():
    for good in [1, 2, 0.5, 1.5, None]:
        validate_cpus(good)


def test_validate_cpus_rejects_zero_and_negative():
    for bad in [0, -1, -0.5]:
        with pytest.raises(ConfigError):
            validate_cpus(bad)
