"""Tests for plugin.py."""

import ckanext.rvr.plugin as plugin
from ckanext.rvr import helpers


def test_plugin():
    registered = plugin.RvrPlugin().get_helpers()
    assert registered["map_format"] is helpers.map_format
