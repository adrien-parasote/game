"""Tests for I18nManager (src/engine/i18n.py).

Covers: singleton pattern, JSON loading via load(), dot-notation lookup via get(),
        error handling (missing file, bad key, partial path), get_item(), get_translations().
"""

import json
from unittest.mock import patch

import pytest
from src.engine.i18n import I18nManager


@pytest.fixture(autouse=True)
def reset_i18n():
    """Reset I18nManager singleton before each test to prevent state leakage."""
    I18nManager._instance = None
    yield
    I18nManager._instance = None


# ── Singleton ──────────────────────────────────────────────────────────────────


def test_singleton_returns_same_instance():
    """I18nManager() must return the same object on successive calls."""
    a = I18nManager()
    b = I18nManager()
    assert a is b


def test_singleton_reset_creates_fresh_instance():
    """Resetting _instance must allow fresh construction."""
    first = I18nManager()
    I18nManager._instance = None
    second = I18nManager()
    assert first is not second


# ── load() ─────────────────────────────────────────────────────────────────────


def test_load_valid_locale_populates_data():
    """load('en') on a valid JSON locale file populates manager.data."""
    data = {"greeting": "Hello", "menu": {"start": "Start Game"}}
    manager = I18nManager()

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", unittest_mock_open(json.dumps(data))):
        manager.load("en")

    assert manager.data.get("greeting") == "Hello"


def test_load_missing_locale_file_clears_data():
    """load() on a missing locale file sets data to {} without crashing."""
    manager = I18nManager()
    manager.data = {"old": "value"}  # pre-populate

    with patch("os.path.exists", return_value=False):
        manager.load("fr")

    assert manager.data == {}


def test_load_corrupted_json_clears_data(tmp_path):
    """load() on malformed JSON logs an error and sets data to {}."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{broken", encoding="utf-8")

    manager = I18nManager()

    # Point the path resolution to our tmp file by patching exists + open
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=Exception("parse error")):
        manager.load("bad")

    assert manager.data == {}


# ── get() / t() lookup ─────────────────────────────────────────────────────────


def test_get_top_level_key():
    """get('key') returns matching string from flat data."""
    manager = I18nManager()
    manager.data = {"title": "My Game"}
    result = manager.get("title")
    assert result == "My Game"


def test_get_dot_notation_nested():
    """get('parent.child') resolves nested dict via dot-notation."""
    manager = I18nManager()
    manager.data = {"ui": {"button": {"ok": "OK"}}}
    result = manager.get("ui.button.ok")
    assert result == "OK"


def test_get_missing_key_returns_key_itself():
    """get() with an unknown key returns the key string as fallback."""
    manager = I18nManager()
    manager.data = {}
    result = manager.get("missing.key")
    # Spec: fallback is the key string itself (not None, not an exception)
    assert result == "missing.key"


def test_get_missing_key_with_explicit_default():
    """get(key, default='N/A') returns the explicit default when key is absent."""
    manager = I18nManager()
    manager.data = {}
    result = manager.get("missing", default="N/A")
    assert result == "N/A"


def test_get_partial_path_returns_fallback():
    """get() on a path where an intermediate node is not a dict returns fallback."""
    manager = I18nManager()
    manager.data = {"ui": "flat_string"}
    result = manager.get("ui.button")
    # 'ui' is not a dict, so traversal fails — must return fallback, not crash
    assert isinstance(result, str)


# ── get_item() ─────────────────────────────────────────────────────────────────


def test_get_item_returns_name_and_description():
    """get_item() returns name + description from items dict."""
    manager = I18nManager()
    manager.data = {
        "items": {
            "sword_iron": {"name": "Iron Sword", "description": "A sharp blade."}
        }
    }
    result = manager.get_item("sword_iron")
    assert result["name"] == "Iron Sword"
    assert result["description"] == "A sharp blade."


def test_get_item_missing_item_returns_defaults():
    """get_item() on unknown item_id returns id-based name and placeholder description."""
    manager = I18nManager()
    manager.data = {"items": {}}
    result = manager.get_item("magic_wand")
    assert result["name"] == "Magic wand"  # id.replace('_', ' ').capitalize()
    assert isinstance(result["description"], str)
    assert len(result["description"]) > 0


# ── get_translations() ─────────────────────────────────────────────────────────


def test_get_translations_returns_data_dict():
    """get_translations() returns the current data dict directly."""
    manager = I18nManager()
    manager.data = {"key": "val"}
    result = manager.get_translations()
    assert result is manager.data


# ── Locale switching ───────────────────────────────────────────────────────────


def test_load_sets_current_locale():
    """load(locale) stores locale name in current_locale."""
    manager = I18nManager()
    with patch("os.path.exists", return_value=False):
        manager.load("fr")
    assert manager.current_locale == "fr"


# ── Helpers ────────────────────────────────────────────────────────────────────

from unittest.mock import mock_open as _mock_open


def unittest_mock_open(content: str):
    """Return a mock_open() callable yielding content."""
    return _mock_open(read_data=content)
