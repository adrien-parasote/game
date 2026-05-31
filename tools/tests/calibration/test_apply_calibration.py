"""Tests for calibration/apply_calibration.py.

Covers the two pure functions _extract and _inject which contain
all the business logic. main() is an integration-only CLI entry
point and is explicitly excluded from unit coverage.
"""

from __future__ import annotations

import pytest

from calibration.apply_calibration import _extract, _inject


# ---------------------------------------------------------------------------
# _extract — extracts a variable assignment block (list) from content
# ---------------------------------------------------------------------------


class TestExtract:
    def test_extracts_single_line_list(self):
        content = "BACKGROUND_LIGHTS = [(10, 20, 30)]"
        result = _extract(content, "BACKGROUND_LIGHTS")
        assert result == "BACKGROUND_LIGHTS = [(10, 20, 30)]"

    def test_extracts_multiline_list(self):
        content = (
            "BACKGROUND_LIGHTS = [\n"
            "    (100, 200, 45),  # lanterne\n"
            "    (300, 400, 28),  # fenêtre\n"
            "]\n"
        )
        result = _extract(content, "BACKGROUND_LIGHTS")
        assert result is not None
        assert "BACKGROUND_LIGHTS" in result
        assert "(100, 200, 45)" in result
        assert "(300, 400, 28)" in result

    def test_returns_none_when_variable_missing(self):
        content = "MUSHROOM_LIGHTS = [(1, 2, 3)]"
        result = _extract(content, "BACKGROUND_LIGHTS")
        assert result is None

    def test_extracts_correct_variable_when_multiple_present(self):
        content = (
            "BACKGROUND_LIGHTS = [(10, 20, 30)]\n"
            "MUSHROOM_LIGHTS = [(50, 60, 22, (70, 220, 200))]\n"
        )
        bg = _extract(content, "BACKGROUND_LIGHTS")
        mush = _extract(content, "MUSHROOM_LIGHTS")
        assert bg is not None and "BACKGROUND_LIGHTS" in bg
        assert mush is not None and "MUSHROOM_LIGHTS" in mush

    def test_extracts_empty_list(self):
        content = "BACKGROUND_LIGHTS = []"
        result = _extract(content, "BACKGROUND_LIGHTS")
        assert result == "BACKGROUND_LIGHTS = []"

    def test_handles_extra_whitespace_around_equals(self):
        content = "BACKGROUND_LIGHTS  =  [(1, 2, 3)]"
        result = _extract(content, "BACKGROUND_LIGHTS")
        assert result is not None
        assert "(1, 2, 3)" in result


# ---------------------------------------------------------------------------
# _inject — replaces or appends a variable block in constants content
# ---------------------------------------------------------------------------


class TestInject:
    def test_replaces_existing_variable(self):
        constants = "BACKGROUND_LIGHTS = [(0, 0, 0)]\nSOME_OTHER = 42\n"
        new_block = "BACKGROUND_LIGHTS = [(100, 200, 45)]"
        result = _inject(constants, "BACKGROUND_LIGHTS", new_block)
        assert "BACKGROUND_LIGHTS = [(100, 200, 45)]" in result
        assert "(0, 0, 0)" not in result
        assert "SOME_OTHER = 42" in result

    def test_appends_when_variable_not_found(self):
        constants = "SOME_CONSTANT = 99\n"
        new_block = "BACKGROUND_LIGHTS = [(10, 20, 30)]"
        result = _inject(constants, "BACKGROUND_LIGHTS", new_block)
        assert "BACKGROUND_LIGHTS = [(10, 20, 30)]" in result
        assert "SOME_CONSTANT = 99" in result

    def test_replaces_multiline_list(self):
        constants = (
            "BACKGROUND_LIGHTS = [\n"
            "    (0, 0, 45),\n"
            "]\n"
            "SOME_OTHER = True\n"
        )
        new_block = "BACKGROUND_LIGHTS = [(100, 200, 45), (300, 400, 28)]"
        result = _inject(constants, "BACKGROUND_LIGHTS", new_block)
        assert "(100, 200, 45)" in result
        assert "(0, 0, 45)" not in result
        assert "SOME_OTHER = True" in result

    def test_inject_does_not_duplicate_variable(self):
        constants = "BACKGROUND_LIGHTS = [(1, 2, 3)]\n"
        new_block = "BACKGROUND_LIGHTS = [(9, 9, 9)]"
        result = _inject(constants, "BACKGROUND_LIGHTS", new_block)
        # Only one assignment should remain
        assert result.count("BACKGROUND_LIGHTS") == 1

    def test_inject_mushroom_lights_independently(self):
        constants = (
            "BACKGROUND_LIGHTS = [(10, 20, 45)]\n"
            "MUSHROOM_LIGHTS = [(5, 5, 22)]\n"
        )
        new_mush = "MUSHROOM_LIGHTS = [(100, 200, 22, (70, 220, 200))]"
        result = _inject(constants, "MUSHROOM_LIGHTS", new_mush)
        assert "(100, 200, 22" in result
        assert "(5, 5, 22)" not in result
        # BACKGROUND_LIGHTS untouched
        assert "BACKGROUND_LIGHTS = [(10, 20, 45)]" in result
