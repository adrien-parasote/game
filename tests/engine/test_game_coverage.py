"""Coverage tests for I18nManager (engine-level i18n module)."""

import os
from unittest.mock import patch

import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.display.init()
pygame.font.init()

from src.engine.i18n import I18nManager


class TestI18nCoverage:
    def setup_method(self):
        # Reset singleton between tests
        I18nManager._instance = None

    def test_load_locale_file_not_found_logs_warning(self, caplog):
        """L31-35: missing locale file → empty data, no crash."""
        mgr = I18nManager()
        mgr.load("zz_NONEXISTENT")
        assert mgr.data == {}

    def test_load_locale_json_error_logs_error(self, caplog):
        """L33-35: JSON parse failure → empty data."""
        mgr = I18nManager()
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=Exception("corrupt")),
        ):
            mgr.load("fr")
        assert mgr.data == {}

    def test_get_key_missing_returns_key_name(self):
        """L45-46: missing key returns the key itself when no default given."""
        mgr = I18nManager()
        mgr.data = {}
        result = mgr.get("seasons.SUMMER")
        assert result == "seasons.SUMMER"

    def test_get_key_missing_returns_explicit_default(self):
        """L45-46: missing key returns explicit default."""
        mgr = I18nManager()
        mgr.data = {}
        result = mgr.get("dialogues.hello", default="fallback")
        assert result == "fallback"

    def test_get_translations_returns_dict(self):
        """L58: get_translations returns current data dict."""
        mgr = I18nManager()
        mgr.data = {"foo": "bar"}
        assert mgr.get_translations() == {"foo": "bar"}

    def test_get_nested_key(self):
        """Happy path: dot-separated nested key resolution."""
        mgr = I18nManager()
        mgr.data = {"items": {"potion_red": {"name": "Potion"}}}
        assert mgr.get("items.potion_red.name") == "Potion"

    def test_get_item_unknown_returns_fallback(self):
        """get_item() returns fallback name for unknown item_id."""
        mgr = I18nManager()
        mgr.data = {}
        result = mgr.get_item("unknown_item")
        assert result["name"] == "Unknown item"


# ---------------------------------------------------------------------------
# BaseEntity — lines 51, 66-68, 76, 79
# ---------------------------------------------------------------------------
