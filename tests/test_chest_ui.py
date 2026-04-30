# tests/test_chest_ui.py
"""Unit tests for the Chest UI component."""

import pytest
import pygame
import os
import logging
from unittest.mock import MagicMock

# Headless mode for tests
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.ui.chest import ChestUI
from src.config import Settings


def make_screen():
    return pygame.Surface((Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT))


def make_player(capacity=28):
    """Create a mock player with an inventory of given capacity."""
    player = MagicMock()
    player.inventory = MagicMock()
    player.inventory.capacity = capacity
    player.inventory.slots = [None] * capacity
    return player


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------

def test_initial_state():
    ui = ChestUI()
    assert not ui.is_open
    assert ui._chest_entity is None


def test_open_sets_state():
    ui = ChestUI()
    dummy_entity = object()
    player = make_player()
    ui.open(dummy_entity, player)
    assert ui.is_open
    assert ui._chest_entity is dummy_entity


def test_close_resets_state():
    ui = ChestUI()
    ui.open(object(), make_player())
    ui.close()
    assert not ui.is_open
    assert ui._chest_entity is None


def test_close_when_already_closed_is_idempotent():
    ui = ChestUI()
    ui.close()
    assert not ui.is_open


def test_draw_noop_when_closed(monkeypatch):
    ui = ChestUI()
    screen = make_screen()
    before = screen.copy()
    ui.draw(screen)
    assert pygame.image.tobytes(screen, "RGB") == pygame.image.tobytes(before, "RGB")


def test_draw_when_open_and_assets_present(monkeypatch):
    ui = ChestUI()
    dummy_bg = pygame.Surface((900, 300))
    dummy_bg.fill((255, 0, 0))
    dummy_slot = pygame.Surface((55, 58))
    dummy_slot.fill((0, 255, 0))
    monkeypatch.setattr(ui, "_bg", dummy_bg)
    monkeypatch.setattr(ui, "_slot_img", dummy_slot)
    ui.open(object(), make_player())
    screen = make_screen()
    ui.draw(screen)
    midx = Settings.WINDOW_WIDTH // 2
    midy = 10 + 15
    assert screen.get_at((midx, midy))[:3] == (255, 0, 0)


def test_load_background_missing_file(monkeypatch, caplog):
    ui = ChestUI()
    monkeypatch.setattr("src.ui.chest.ASSET_CHEST_BG", "nonexistent.png")
    result = ui._load_background()
    assert result is None
    assert any("failed" in rec.message.lower() for rec in caplog.records)


def test_load_slot_image_missing_file(monkeypatch, caplog):
    ui = ChestUI()
    monkeypatch.setattr("src.ui.chest.ASSET_SLOT_IMG", "nonexistent.png")
    result = ui._load_slot_image()
    assert result is None
    assert any("failed" in rec.message.lower() for rec in caplog.records)


def test_update_hover_hit():
    """update_hover sets _hovered_chest_slot when mouse is over a chest slot."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._slot_positions, "No slot positions computed"
    first_rect = ui._slot_positions[0]
    ui.update_hover(first_rect.center)
    assert ui._hovered_chest_slot == 0


def test_update_hover_miss():
    """update_hover clears _hovered_chest_slot when mouse is outside all slots."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui.update_hover((0, 0))
    assert ui._hovered_chest_slot is None


def test_hovered_slot_reset_on_close():
    """close() resets _hovered_chest_slot to None."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._hovered_chest_slot = 3
    ui.close()
    assert ui._hovered_chest_slot is None


def test_load_cursor_missing_file(monkeypatch, caplog):
    ui = ChestUI()
    result = ui._load_cursor("nonexistent_cursor.png")
    assert result is None
    assert any("failed" in rec.message.lower() for rec in caplog.records)


def test_draw_hover_overlay_rendered(monkeypatch):
    """When _hovered_chest_slot is set and hover image exists, hover is drawn."""
    ui = ChestUI()
    dummy_bg = pygame.Surface((900, 300))
    dummy_bg.fill((20, 20, 20))
    dummy_slot = pygame.Surface((49, 49))
    dummy_slot.fill((0, 200, 0))
    dummy_hover = pygame.Surface((49, 49))
    dummy_hover.fill((255, 255, 0))
    monkeypatch.setattr(ui, "_bg", dummy_bg)
    monkeypatch.setattr(ui, "_slot_img", dummy_slot)
    ui.open(object(), make_player())
    ui._hover_img = dummy_hover
    ui._hovered_chest_slot = 0
    screen = make_screen()
    monkeypatch.setattr(ui, "_draw_cursor", lambda s: None)
    ui._draw_slots(screen)
    center = ui._slot_positions[0].center
    pixel = screen.get_at(center)[:3]
    assert pixel == (255, 255, 0), f"Expected yellow hover pixel, got {pixel}"


# --- Chest arrow button tests ---

def test_arrow_rects_computed_after_open():
    ui = ChestUI()
    assert ui._arrow_up_rect is None
    assert ui._arrow_down_rect is None
    ui.open(object(), make_player())
    assert ui._arrow_up_rect is not None
    assert ui._arrow_down_rect is not None


def test_arrow_up_rect_is_left_of_down():
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._arrow_up_rect.left < ui._arrow_down_rect.left


def test_update_hover_chest_arrows():
    """update_hover sets _hovered_chest_arrow when mouse is over chest arrow buttons."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui.update_hover(ui._arrow_up_rect.center)
    assert ui._hovered_chest_arrow == "up"
    assert ui._hovered_chest_slot is None
    ui.update_hover(ui._arrow_down_rect.center)
    assert ui._hovered_chest_arrow == "down"
    ui.update_hover((0, 0))
    assert ui._hovered_chest_arrow is None


def test_hovered_arrow_reset_on_close():
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._hovered_chest_arrow = "up"
    ui.close()
    assert ui._hovered_chest_arrow is None


def test_draw_arrow_hover_overlay_rendered(monkeypatch):
    ui = ChestUI()
    ui.open(object(), make_player())
    up_hover = pygame.Surface((30, 30))
    up_hover.fill((255, 0, 0))
    down_hover = pygame.Surface((30, 30))
    down_hover.fill((0, 0, 255))
    ui._arrow_down_hover_img = down_hover
    ui._arrow_up_hover_img = up_hover
    screen = make_screen()
    ui._hovered_chest_arrow = "up"
    ui._draw_arrow_hovers(screen)
    pixel = screen.get_at(ui._arrow_up_rect.center)[:3]
    assert pixel == (0, 0, 255), f"Expected blue hover overlay in RED zone, got {pixel}"
    screen.fill((0, 0, 0))
    ui._hovered_chest_arrow = "down"
    ui._draw_arrow_hovers(screen)
    pixel = screen.get_at(ui._arrow_down_rect.center)[:3]
    assert pixel == (255, 0, 0), f"Expected red hover overlay in BLUE zone, got {pixel}"


# ---------------------------------------------------------------------------
# NEW: Dual-panel tests (Player Inventory panel)
# ---------------------------------------------------------------------------

def test_open_with_player_stores_player():
    """open(entity, player) stores the player reference."""
    ui = ChestUI()
    player = make_player()
    ui.open(object(), player)
    assert ui._player is player


def test_open_resets_inv_offset():
    """open() always resets the inventory offset to 0."""
    ui = ChestUI()
    ui._inv_offset = 5
    ui.open(object(), make_player())
    assert ui._inv_offset == 0


def test_close_resets_inv_state():
    """close() resets all inventory panel state."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._inv_offset = 3
    ui._hovered_inv_slot = 5
    ui._hovered_inv_arrow = "right"
    ui.close()
    assert ui._inv_offset == 0
    assert ui._hovered_inv_slot is None
    assert ui._hovered_inv_arrow is None
    assert ui._player is None


def test_inv_bg_rect_computed_after_open():
    """open() must compute _inv_bg_rect at bottom of screen."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._inv_bg_rect is not None
    # Should be flush to bottom of screen
    assert ui._inv_bg_rect.bottom == Settings.WINDOW_HEIGHT


def test_inv_slot_positions_computed_after_open():
    """open() must populate _inv_slot_positions with exactly _INV_SLOTS_VISIBLE entries."""
    from src.ui.chest import _INV_SLOTS_VISIBLE
    ui = ChestUI()
    ui.open(object(), make_player())
    assert len(ui._inv_slot_positions) == _INV_SLOTS_VISIBLE


def test_update_hover_inv_slot():
    """update_hover sets _hovered_inv_slot when mouse is over a player inventory slot."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._inv_slot_positions, "No inv slot positions computed"
    first = ui._inv_slot_positions[0]
    ui.update_hover(first.center)
    assert ui._hovered_inv_slot == 0
    assert ui._hovered_chest_slot is None


def test_update_hover_chest_slot_when_mouse_in_chest():
    """update_hover sets _hovered_chest_slot and clears inv state when in chest grid."""
    ui = ChestUI()
    ui.open(object(), make_player())
    chest_first = ui._slot_positions[0]
    ui.update_hover(chest_first.center)
    assert ui._hovered_chest_slot == 0
    assert ui._hovered_inv_slot is None


def test_inv_offset_advance_on_right_click():
    """handle_event jumps _inv_offset by a full page when right arrow is clicked."""
    from src.ui.chest import _INV_SLOTS_VISIBLE
    ui = ChestUI()
    player = make_player(capacity=28)
    ui.open(object(), player)
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = ui._inv_arrow_right_rect.center
    ui.handle_event(event)
    # Full page jump: offset = 0 + 18 = 18, clamped to capacity-1 = 27 → 18
    assert ui._inv_offset == _INV_SLOTS_VISIBLE


def test_inv_offset_no_overflow():
    """handle_event does not advance _inv_offset beyond max_offset (right arrow at max)."""
    from src.ui.chest import _INV_SLOTS_VISIBLE
    ui = ChestUI()
    player = make_player(capacity=28)
    ui.open(object(), player)
    max_offset = 28 - _INV_SLOTS_VISIBLE
    ui._inv_offset = max_offset
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = ui._inv_arrow_right_rect.center
    ui.handle_event(event)
    assert ui._inv_offset == max_offset  # already at limit — no change


def test_inv_offset_no_underflow():
    """handle_event does not go below 0 when clicking left arrow."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._inv_offset = 0
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = ui._inv_arrow_left_rect.center
    ui.handle_event(event)
    assert ui._inv_offset == 0


def test_inv_bg_full_screen_width():
    """Inventory background should span the full screen width."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._inv_bg_rect.width == Settings.WINDOW_WIDTH
