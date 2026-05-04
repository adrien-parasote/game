"""
PauseScreen — Overlay pause menu on top of the running game.
Spec: docs/specs/game-flow-spec.md#24-srcuipause_screenpy-new
"""

import logging
import os

import pygame

from src.config import Settings
from src.engine.game_events import GameEvent, GameEventType
from src.engine.i18n import I18nManager
from src.engine.save_manager import SaveManager
from src.ui.pause_screen_constants import (
    _BUTTON_DEFAULTS,
    _BUTTON_KEYS,
    _FONT_PATH,
    _MENU_DIR,
    _UI_DIR,
    ENGRAVE_LIGHT,
    ENGRAVE_SHADOW,
    ENGRAVE_TEXT,
    ITEM_SPACING,
    ITEM_Y_START_OFFSET,
    OVERLAY_ALPHA,
    PANEL_H,
    PANEL_W,
    PAUSE_ITEM_FONT_SIZE,
    PAUSE_TITLE_FONT_SIZE,
    PAUSE_TITLE_OFFSET,
    TITLE_COLOR,
)
from src.ui.save_menu import SaveMenuOverlay


class PauseScreen:
    """Semi-transparent overlay with 3 pause actions."""

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self._hovered_btn: int | None = None
        self._confirm_timer: float = 0.0  # >0 → show "Saved!" feedback for 2s
        self.state = "MAIN"  # "MAIN" or "SAVE_MENU"
        self._i18n = I18nManager()
        self._save_menu = SaveMenuOverlay(
            screen, save_manager, self._i18n.get("pause_menu.save", "Sauvegarder la partie")
        )

        sw, sh = screen.get_size()
        self._sw = sw
        self._sh = sh

        self._load_assets()
        self._compute_layout()

    def _load_asset(self, filename: str) -> pygame.Surface:
        path = os.path.join(_MENU_DIR, filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"PauseScreen: Could not load {filename}: {e}")
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 255))
            return surf

    def _load_cursor(self, filename: str) -> pygame.Surface:
        """Load cursor from UI assets, scaled to CURSOR_SIZE."""
        path = os.path.join(_UI_DIR, filename)
        try:
            raw = pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"PauseScreen: Could not load cursor {filename}: {e}")
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 255))
            return surf
        target_h = Settings.CURSOR_SIZE
        ratio = target_h / 535
        target_w = int(309 * ratio)
        return pygame.transform.smoothscale(raw, (target_w, target_h))

    def _load_assets(self) -> None:
        # Semi-transparent overlay
        self._overlay = pygame.Surface((self._sw, self._sh))
        self._overlay.set_alpha(OVERLAY_ALPHA)
        self._overlay.fill((0, 0, 0))

        # Panel background — 02-panel_background.png (600x600 RGBA → scaled)
        panel_raw = self._load_asset("02-panel_background.png")
        if panel_raw.get_size() != (32, 32):  # not the error fallback
            self._panel = pygame.transform.smoothscale(panel_raw, (480, 480))
        else:
            # Fallback: programmatic surface
            self._panel = pygame.Surface((480, 480), pygame.SRCALPHA)
            self._panel.fill((10, 18, 22, 210))
            pygame.draw.rect(self._panel, (60, 80, 85), self._panel.get_rect(), 2)

        try:
            self._title_font = pygame.font.Font(_FONT_PATH, PAUSE_TITLE_FONT_SIZE)
            self._item_font = pygame.font.Font(_FONT_PATH, PAUSE_ITEM_FONT_SIZE)
            self._success_font = pygame.font.Font(_FONT_PATH, 26)
        except OSError:
            self._title_font = pygame.font.SysFont(None, 42)
            self._item_font = pygame.font.SysFont(None, 32)
            self._success_font = pygame.font.SysFont(None, 26)
        try:
            am = __import__("src.engine.asset_manager", fromlist=["AssetManager"]).AssetManager()
            self._font_small = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        except Exception:
            self._font_small = pygame.font.SysFont(None, 24)

        # Custom cursor
        self._pointer_img = self._load_cursor("05-pointer.png")
        self._pointer_select_img = self._load_cursor("06-pointer_select.png")

    def _compute_layout(self) -> None:
        """Button rects aligned to the inner stone area of the panel."""
        panel_rect = pygame.Rect(
            self._sw // 2 - PANEL_W // 2,
            self._sh // 2 - PANEL_H // 2,
            PANEL_W,
            PANEL_H,
        )
        # Click zones: centred horizontally, spaced vertically from ITEM_Y_START_OFFSET
        btn_w, btn_h = 280, 50
        x = panel_rect.centerx - btn_w // 2
        self.button_rects = []
        for i in range(len(_BUTTON_KEYS)):
            self.button_rects.append(
                pygame.Rect(
                    x,
                    panel_rect.top + ITEM_Y_START_OFFSET + i * ITEM_SPACING,
                    btn_w,
                    btn_h,
                )
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.Event) -> GameEvent | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.state == "SAVE_MENU":
                self.state = "MAIN"
                return None

        if self.state == "SAVE_MENU":
            if self._save_menu.is_back_clicked(event):
                self.state = "MAIN"
                return None
            slot_idx = self._save_menu.get_clicked_slot(event)
            if slot_idx is not None:
                # Emit save-requested event for the given slot (1-indexed)
                return GameEvent(type=GameEventType.SAVE_REQUESTED, slot_id=slot_idx + 1)
            return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        for i, rect in enumerate(self.button_rects):
            if rect.collidepoint(event.pos):
                return self._on_button_click(i)
        return None

    def update(self, dt: float) -> None:
        if self._confirm_timer > 0:
            self._confirm_timer -= dt

        if self.state == "SAVE_MENU":
            self._save_menu.update(dt)
            return

        mouse_pos = pygame.mouse.get_pos()
        self._hovered_btn = None
        for i, rect in enumerate(self.button_rects):
            if rect.collidepoint(mouse_pos):
                self._hovered_btn = i
                break

    def draw(self) -> None:
        # Background dark overlay
        self._screen.blit(self._overlay, (0, 0))

        if self.state == "SAVE_MENU":
            self._save_menu.draw()
            self._draw_cursor()
            return

        panel_rect = pygame.Rect(
            self._sw // 2 - PANEL_W // 2,
            self._sh // 2 - PANEL_H // 2,
            PANEL_W,
            PANEL_H,
        )

        self._screen.blit(self._panel, panel_rect)

        # Title — Cormorant Garamond, golden, centered at the top of the panel
        title_text = self._i18n.get("pause_menu.title", "PAUSE")
        title = self._title_font.render(title_text, True, TITLE_COLOR)
        self._screen.blit(
            title,
            title.get_rect(midtop=(panel_rect.centerx, panel_rect.top + PAUSE_TITLE_OFFSET)),
        )

        # Menu items — engraved idle, golden hover
        for i, (rect, key, default) in enumerate(
            zip(self.button_rects, _BUTTON_KEYS, _BUTTON_DEFAULTS, strict=False)
        ):
            label = self._i18n.get(key, default)
            cx = rect.centerx
            cy = rect.centery
            if self._hovered_btn == i:
                # Text is light sky blue, Halo is intense bright blue
                self._blit_halo_text(
                    label, cx, cy, self._item_font, (180, 230, 255), (40, 120, 255)
                )
            else:
                self._blit_engraved(label, cx, cy)

        if self._confirm_timer > 0:
            success_text = self._i18n.get("pause_menu.saved_success", "Partie sauvegardée !")
            msg = self._success_font.render(success_text, True, (180, 220, 150))
            # Apply alpha fade out: timer goes from 2.0 to 0.0
            alpha = int(min(255, (self._confirm_timer / 2.0) * 255))
            msg.set_alpha(alpha)
            self._screen.blit(msg, msg.get_rect(midbottom=(self._sw // 2, self._sh - 40)))

        self._draw_cursor()

    def _blit_halo_text(
        self,
        label: str,
        cx: int,
        cy: int,
        font: pygame.font.Font,
        text_color: tuple[int, int, int],
        halo_color: tuple[int, int, int],
    ) -> None:
        """Draw text with a soft, spreading glowing halo effect."""
        base_surf = font.render(label, True, halo_color)
        w, h = base_surf.get_size()

        # Create a padded surface so the blur doesn't clip
        pad = 24
        padded = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        padded.blit(base_surf, (pad, pad))

        try:
            # Use pygame-ce's fast gaussian_blur
            blurred = pygame.transform.gaussian_blur(padded, 8)
            blurred.set_alpha(255)

            # Blit 3 times for a very strong, dense center glow that is highly visible
            rect = blurred.get_rect(center=(cx, cy))
            self._screen.blit(blurred, rect)
            self._screen.blit(blurred, rect)
            self._screen.blit(blurred, rect)
        except AttributeError:
            # Fallback if standard pygame is used
            base_surf.set_alpha(80)
            offsets = [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, -4), (0, 4), (-4, 0), (4, 0)]
            for dx, dy in offsets:
                self._screen.blit(base_surf, base_surf.get_rect(center=(cx + dx, cy + dy)))

        main_surf = font.render(label, True, text_color)
        self._screen.blit(main_surf, main_surf.get_rect(center=(cx, cy)))

    def _blit_engraved(self, label: str, cx: int, cy: int) -> None:
        """3-pass stone engraving: shadow | light | text. Matches TitleScreen effect."""
        shadow = self._item_font.render(label, True, ENGRAVE_SHADOW)
        light = self._item_font.render(label, True, ENGRAVE_LIGHT)
        text = self._item_font.render(label, True, ENGRAVE_TEXT)
        r = text.get_rect(center=(cx, cy))
        self._screen.blit(shadow, r.move(-1, -1))
        self._screen.blit(light, r.move(1, 1))
        self._screen.blit(text, r)

    def notify_save_result(self, success: bool) -> None:
        """Call after a save attempt to show confirmation for 2 seconds."""
        if success:
            self._confirm_timer = 2.0
            self.state = "MAIN"

    def _draw_cursor(self) -> None:
        """Draw custom cursor on top of everything."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        self._screen.blit(img, mouse_pos)

    # ── Button actions ────────────────────────────────────────────────────────

    def _on_button_click(self, index: int) -> GameEvent | None:
        if index == 0:
            return GameEvent.goto_title()
        if index == 1:
            return GameEvent.resume()
        if index == 2:
            # Switch state to save menu
            self.state = "SAVE_MENU"
            self._save_menu.refresh()
            return None
        return None
