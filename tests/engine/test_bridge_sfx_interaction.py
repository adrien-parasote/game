"""RED tests — Bridge SFX : _resolve_sfx helper in InteractionManager.

Spec: docs/specs/bridge-sfx-spec.md
Tests: UT-010 → UT-015
"""

from unittest.mock import MagicMock

import pygame
import pytest

from src.engine.interaction import InteractionManager


class _SfxEntity(pygame.sprite.Sprite):
    """Minimal sprite with SFX attrs and toggleable is_on for integration tests."""

    def __init__(self, element_id, sfx="", sfx_open="", sfx_close="", is_on=True):
        super().__init__()
        self.element_id = element_id
        self.sfx = sfx
        self.sfx_open = sfx_open
        self.sfx_close = sfx_close
        self.is_on = is_on
        self.target_id = None
        self.rect = pygame.Rect(0, 0, 32, 32)

    def interact(self, player=None):
        pass  # is_on already set to desired post-toggle state in test

def _make_entity(sfx="", sfx_open="", sfx_close="", is_on=True):
    """Build a minimal mock entity with SFX attributes."""
    entity = MagicMock()
    entity.sfx = sfx
    entity.sfx_open = sfx_open
    entity.sfx_close = sfx_close
    entity.is_on = is_on
    return entity


class TestResolveSfx:
    """BRIDGE-U-007 → BRIDGE-U-012 — _resolve_sfx() directional SFX selection logic."""

    @pytest.mark.tc("BRIDGE-U-007")
    def test_sfx_open_used_when_on(self):
        """BRIDGE-U-007: _resolve_sfx returns sfx_open when is_on=True and sfx_open is set."""
        entity = _make_entity(sfx_open="o", sfx="g", is_on=True)
        result = InteractionManager._resolve_sfx(entity)
        assert result == "o"

    @pytest.mark.tc("BRIDGE-U-008")
    def test_sfx_close_used_when_off(self):
        """BRIDGE-U-008: _resolve_sfx returns sfx_close when is_on=False and sfx_close is set."""
        entity = _make_entity(sfx_close="c", sfx="g", is_on=False)
        result = InteractionManager._resolve_sfx(entity)
        assert result == "c"

    @pytest.mark.tc("BRIDGE-U-009")
    def test_fallback_to_sfx_when_sfx_open_empty_and_on(self):
        """BRIDGE-U-009: _resolve_sfx falls back to sfx when sfx_open is '' and is_on=True."""
        entity = _make_entity(sfx_open="", sfx="g", is_on=True)
        result = InteractionManager._resolve_sfx(entity)
        assert result == "g"

    @pytest.mark.tc("BRIDGE-U-010")
    def test_fallback_to_sfx_when_sfx_close_empty_and_off(self):
        """BRIDGE-U-010: _resolve_sfx falls back to sfx when sfx_close is '' and is_on=False."""
        entity = _make_entity(sfx_close="", sfx="g", is_on=False)
        result = InteractionManager._resolve_sfx(entity)
        assert result == "g"

    @pytest.mark.tc("BRIDGE-U-011")
    def test_returns_empty_when_all_sfx_empty(self):
        """BRIDGE-U-011: _resolve_sfx returns '' when sfx, sfx_open, sfx_close are all empty."""
        entity = _make_entity(sfx="", sfx_open="", sfx_close="", is_on=True)
        result = InteractionManager._resolve_sfx(entity)
        assert result == ""

    @pytest.mark.tc("BRIDGE-U-012")
    def test_legacy_entity_without_sfx_open_close_uses_sfx(self):
        """BRIDGE-U-012: Entities without sfx_open/sfx_close fall back to sfx (rétrocompat)."""
        entity = MagicMock(spec=["sfx", "is_on"])
        entity.sfx = "01-lever"
        entity.is_on = True
        result = InteractionManager._resolve_sfx(entity)
        assert result == "01-lever"


class TestResolveSfxIntegration:
    """BRIDGE-I-001 → BRIDGE-I-002 — _resolve_sfx used in _trigger_object_interaction and toggle_entity_by_id."""

    @pytest.mark.tc("BRIDGE-I-001")
    def test_trigger_object_plays_sfx_open_when_toggled_on(self):
        """BRIDGE-I-001: Bridge toggled ON via toggle_entity_by_id plays sfx_open."""
        game = MagicMock()

        bridge = _SfxEntity(
            "drawbridge",
            sfx_open="bridge_open",
            sfx_close="bridge_close",
            is_on=True,  # post-toggle state
        )

        game.interactives = pygame.sprite.Group(bridge)
        game.npcs = pygame.sprite.Group()

        im = InteractionManager(game)
        im.toggle_entity_by_id("drawbridge")

        game.audio_manager.play_sfx.assert_called_once_with(
            "bridge_open", "drawbridge"
        )

    @pytest.mark.tc("BRIDGE-I-002")
    def test_trigger_object_plays_sfx_close_when_toggled_off(self):
        """BRIDGE-I-002: Bridge toggled OFF via toggle_entity_by_id plays sfx_close."""
        game = MagicMock()

        bridge = _SfxEntity(
            "drawbridge",
            sfx_open="bridge_open",
            sfx_close="bridge_close",
            is_on=False,  # post-toggle state
        )

        game.interactives = pygame.sprite.Group(bridge)
        game.npcs = pygame.sprite.Group()

        im = InteractionManager(game)
        im.toggle_entity_by_id("drawbridge")

        game.audio_manager.play_sfx.assert_called_once_with(
            "bridge_close", "drawbridge"
        )

    def test_legacy_sfx_still_plays_via_toggle(self):
        """Regression: lever with only sfx still plays sfx via toggle_entity_by_id."""
        game = MagicMock()

        lever = _SfxEntity("lever_1", sfx="01-lever", is_on=True)

        game.interactives = pygame.sprite.Group(lever)
        game.npcs = pygame.sprite.Group()

        im = InteractionManager(game)
        im.toggle_entity_by_id("lever_1")

        game.audio_manager.play_sfx.assert_called_once_with(
            "01-lever", "lever_1"
        )

    def test_no_sfx_played_when_all_empty(self):
        """Regression: entity with all sfx empty → audio_manager.play_sfx not called."""
        game = MagicMock()

        obj = _SfxEntity("silent_obj", sfx="", sfx_open="", sfx_close="", is_on=True)

        game.interactives = pygame.sprite.Group(obj)
        game.npcs = pygame.sprite.Group()

        im = InteractionManager(game)
        im.toggle_entity_by_id("silent_obj")

        game.audio_manager.play_sfx.assert_not_called()

# assert True (legacy bypass)

# assert True (legacy bypass)

# assert True (legacy bypass)
