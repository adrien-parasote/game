# tests/test_chest_ui.py
"""Unit tests for the Chest UI component."""

import pytest
import pygame
import os
import logging

# Headless mode for tests
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.ui.chest import ChestUI
from src.config import Settings

def make_screen():
    return pygame.Surface((Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT))

def test_initial_state():
    ui = ChestUI()
    assert not ui.is_open
    assert ui._chest_entity is None

def test_open_sets_state():
    ui = ChestUI()
    dummy_entity = object()
    ui.open(dummy_entity)
    assert ui.is_open
    assert ui._chest_entity is dummy_entity

def test_close_resets_state():
    ui = ChestUI()
    ui.open(object())
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
    # Compare surfaces
    assert pygame.image.tobytes(screen, "RGB") == pygame.image.tobytes(before, "RGB")

def test_draw_when_open_and_assets_present(monkeypatch):
    ui = ChestUI()
    
    # Mocking assets
    dummy_bg = pygame.Surface((900, 300))
    dummy_bg.fill((255, 0, 0))
    dummy_slot = pygame.Surface((55, 58))
    dummy_slot.fill((0, 255, 0))
    
    monkeypatch.setattr(ui, "_bg", dummy_bg)
    monkeypatch.setattr(ui, "_slot_img", dummy_slot)
    
    ui.open(object())
    screen = make_screen()
    ui.draw(screen)
    
    # Check if background was blitted (centered at top)
    midx = Settings.WINDOW_WIDTH // 2
    midy = 10 + 15 # center of dummy_bg
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
    """update_hover sets _hovered_slot when mouse is over a slot."""
    ui = ChestUI()
    ui.open(object())
    # _slot_positions are populated after open()
    assert ui._slot_positions, "No slot positions computed"
    first_rect = ui._slot_positions[0]
    ui.update_hover(first_rect.center)
    assert ui._hovered_slot == 0


def test_update_hover_miss():
    """update_hover clears _hovered_slot when mouse is outside all slots."""
    ui = ChestUI()
    ui.open(object())
    ui.update_hover(first_rect.center if False else (0, 0))
    assert ui._hovered_slot is None


def test_hovered_slot_reset_on_close():
    """close() resets _hovered_slot to None."""
    ui = ChestUI()
    ui.open(object())
    ui._hovered_slot = 3
    ui.close()
    assert ui._hovered_slot is None


def test_load_cursor_missing_file(monkeypatch, caplog):
    """_load_cursor returns None and logs a warning when file is missing."""
    ui = ChestUI()
    result = ui._load_cursor("nonexistent_cursor.png")
    assert result is None
    assert any("failed" in rec.message.lower() for rec in caplog.records)


def test_draw_hover_overlay_rendered(monkeypatch):
    """When _hovered_slot is set and hover image exists, hover is drawn on screen."""
    ui = ChestUI()
    dummy_bg = pygame.Surface((900, 300))
    dummy_bg.fill((20, 20, 20))
    dummy_slot = pygame.Surface((49, 49))
    dummy_slot.fill((0, 200, 0))
    dummy_hover = pygame.Surface((49, 49))
    dummy_hover.fill((255, 255, 0))  # Yellow = hover overlay

    monkeypatch.setattr(ui, "_bg", dummy_bg)
    monkeypatch.setattr(ui, "_slot_img", dummy_slot)

    ui.open(object())
    # Set hover image and hovered slot AFTER open() so _compute_layout doesn't overwrite them
    ui._hover_img = dummy_hover
    ui._hovered_slot = 0

    screen = make_screen()
    # Suppress cursor draw side-effects
    monkeypatch.setattr(ui, "_draw_cursor", lambda s: None)
    ui._draw_slots(screen)

    # The hover colour (yellow) must appear at the first slot center
    center = ui._slot_positions[0].center
    pixel = screen.get_at(center)[:3]
    assert pixel == (255, 255, 0), f"Expected yellow hover pixel, got {pixel}"
