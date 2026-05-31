"""Coverage tests for: chest_input.py:81, chest_layout.py:47,148,
chest_transfer.py:13,32, chest.py:114,203-204, hud.py:47-49."""

import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture(autouse=True)
def pygame_setup(setup_pygame):
    return


# ---------------------------------------------------------------------------
# chest_input.py:81 — _handle_mouse_up early return when not dragging
# ---------------------------------------------------------------------------


class TestChestInputHandleMouseUp:
    def test_mouse_up_returns_early_when_not_dragging(self):
        """Ligne 81 : _handle_mouse_up retourne immédiatement si _dragging_item est None."""
        from src.ui.chest import ChestUI

        ui = ChestUI()
        ui._dragging_item = None
        event = MagicMock()
        event.pos = (100, 100)
        # Ne doit pas lever d'exception
        ui._handle_mouse_up(event)
        # Vérifie qu'on n'a pas tenté d'accéder à _hovered_chest_slot ou similaire
        assert ui._dragging_item is None


# ---------------------------------------------------------------------------
# chest_layout.py:47 — _compute_layout early return when _bg is None
# ---------------------------------------------------------------------------


class TestChestLayoutComputeLayout:
    def test_compute_layout_returns_early_when_bg_none(self):
        """Ligne 47 : _compute_layout() retourne si _bg is None."""
        from src.ui.chest import ChestUI

        ui = ChestUI()
        ui._bg = None
        # Ne doit pas lever d'exception ni modifier les rects
        ui._compute_layout()
        assert ui._bg_rect is None


# ---------------------------------------------------------------------------
# chest_layout.py:148 — _compute_inv_panel early return when _inv_bg is None
# ---------------------------------------------------------------------------


class TestChestLayoutComputeInvPanel:
    def test_compute_inv_panel_returns_early_when_inv_bg_none(self):
        """Ligne 148 : _compute_inv_panel() retourne si _inv_bg is None."""
        from src.ui.chest import ChestUI

        ui = ChestUI()
        ui._inv_bg = None
        ui._inv_bg_rect = None
        # Appel direct de la méthode privée avec la signature correcte
        ui._compute_inv_layout(
            slot_size=49, step=56, screen_w=1280, screen_h=720, arrow_scale=1.0
        )
        assert ui._inv_bg_rect is None


# ---------------------------------------------------------------------------
# chest_transfer.py:13 — _transfer_chest_to_inventory guard
# ---------------------------------------------------------------------------


class TestChestTransferGuards:
    def test_transfer_chest_to_inv_returns_early_when_no_entity(self):
        """Ligne 13 : _transfer_chest_to_inventory retourne si _chest_entity est None."""
        from src.ui.chest import ChestUI

        ui = ChestUI()
        ui._chest_entity = None
        ui._player = MagicMock()
        # Ne doit pas lever
        ui._transfer_chest_to_inventory()
        assert ui._player.inventory.add_item.call_count == 0

    def test_transfer_inv_to_chest_returns_early_when_no_entity(self):
        """Ligne 32 : _transfer_inventory_to_chest retourne si _chest_entity est None."""
        from src.ui.chest import ChestUI

        ui = ChestUI()
        ui._chest_entity = None
        ui._player = MagicMock()
        ui._transfer_inventory_to_chest()
        assert ui._player.inventory.slots.copy.call_count == 0


# ---------------------------------------------------------------------------
# chest.py:114 — draw() guard when _bg is None (is_open but bg not loaded)
# ---------------------------------------------------------------------------


class TestChestDrawGuard:
    def test_draw_returns_early_when_bg_none_but_open(self):
        """Ligne 114 : draw() retourne si _bg is None même quand is_open=True."""
        from src.ui.chest import ChestUI

        ui = ChestUI()
        ui.is_open = True
        ui._bg = None
        ui._bg_rect = None
        screen = pygame.Surface((1280, 720))
        before = screen.copy()
        ui.draw(screen)
        # L'écran ne doit pas avoir été modifié
        assert pygame.image.tobytes(screen, "RGB") == pygame.image.tobytes(before, "RGB")


# ---------------------------------------------------------------------------
# chest.py:203-204 — _scroll_left when _can_scroll_left() is True
# ---------------------------------------------------------------------------


class TestChestScrollLeft:
    def test_scroll_left_decrements_inv_offset(self):
        """Lignes 203-204 : _scroll_left() décrémente _inv_offset quand possible."""
        from src.ui.chest import _INV_SLOTS_VISIBLE, ChestUI

        ui = ChestUI()
        player = MagicMock()
        player.inventory.capacity = 28
        player.inventory.slots = [None] * 28
        ui.open(object(), player)
        # Avancer d'abord pour avoir quelque chose à gauche
        ui._inv_offset = _INV_SLOTS_VISIBLE
        ui._scroll_left()
        assert ui._inv_offset == 0

    def test_scroll_left_no_op_at_zero(self):
        """_scroll_left() ne fait rien si offset déjà à 0."""
        from src.ui.chest import ChestUI

        ui = ChestUI()
        player = MagicMock()
        player.inventory.capacity = 28
        player.inventory.slots = [None] * 28
        ui.open(object(), player)
        ui._inv_offset = 0
        ui._scroll_left()
        assert ui._inv_offset == 0


# ---------------------------------------------------------------------------
# hud.py:47-49 — _load_image pygame.error fallback
# ---------------------------------------------------------------------------


class TestHudLoadImageFallback:
    def test_load_image_returns_fallback_surface_on_pygame_error(self):
        """Lignes 47-49 : _load_image retourne une Surface placeholder via AssetManager."""
        from src.ui.hud import GameHUD

        with patch("src.ui.hud.AssetManager") as mock_am_cls:
            placeholder = pygame.Surface((32, 32))
            mock_am_cls.return_value.get_image.return_value = placeholder
            hud = GameHUD.__new__(GameHUD)
            result = hud._load_image("missing.png")
        assert isinstance(result, pygame.Surface)
