"""Regression tests for format helpers used by plugin registration and search."""

import pytest

from ckanext.rvr import helpers
from ckanext.rvr.profiles import EU_FILE_TYPE_PREFIX


@pytest.mark.parametrize("value, expected", [
    (None, ""),
    ("", ""),
    ("csv", "CSV"),
    ("json-ld", "JSON-LD"),
    (EU_FILE_TYPE_PREFIX + "JSON_LD", "JSON-LD"),
])
def test_map_format(value, expected):
    assert helpers.map_format(value) == expected


@pytest.mark.parametrize("value, expected", [
    ("CSV", {"CSV", EU_FILE_TYPE_PREFIX + "CSV"}),
    ("JSON-LD", {"JSON-LD", EU_FILE_TYPE_PREFIX + "JSON_LD"}),
    (EU_FILE_TYPE_PREFIX + "CSV", {"CSV", EU_FILE_TYPE_PREFIX + "CSV"}),
    (EU_FILE_TYPE_PREFIX + "JSON_LD", {"JSON-LD", EU_FILE_TYPE_PREFIX + "JSON_LD"}),
])
def test_get_format_aliases(value, expected):
    assert set(helpers.get_format_aliases(value)) == expected
