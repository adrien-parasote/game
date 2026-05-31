"""
PauseScreen — Overlay pause menu on top of the running game.
Spec: game/docs/specs/game-flow-spec.md#24-srcuipause_screenpy-new
"""

from pathlib import Path

import pygame
from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.game_events import GameEvent, GameEventType
from src.engine.i18n import I18nManager
from src.engine.save_manager import SaveManager
from src.ui.pause_screen_constants import (
    _BUTTON_DEFAULTS,
    _BUTTON_KEYS,
    _FONT_PATH,
    _MENU_DIR,
    _UI_DIR,
    CONFIRM_DISPLAY_SECONDS,
    CONFIRM_MSG_MARGIN_BOTTOM,
    CURSOR_RAW_H,
    CURSOR_RAW_W,
    ENGRAVE_LIGHT,
    ENGRAVE_SHADOW,
    ENGRAVE_TEXT,
    FALLBACK_SURF_SIZE,
    HALO_BLUR_PADDING,
    HALO_BLUR_RADIUS,
    HOVER_HALO_COLOR,
    HOVER_TEXT_COLOR,
    ITEM_SPACING,
    ITEM_Y_START_OFFSET,
    OVERLAY_ALPHA,
    PANEL_FALLBACK_BORDER,
    PANEL_FALLBACK_FILL,
    PANEL_H,
    PANEL_W,
    PAUSE_BTN_H,
    PAUSE_BTN_W,
    PAUSE_ITEM_FONT_SIZE,
    PAUSE_SUCCESS_FONT_SIZE,
    PAUSE_TITLE_FONT_SIZE,
    PAUSE_TITLE_OFFSET,
    SUCCESS_COLOR,
    TITLE_COLOR,
)
from src.ui.save_menu import SaveMenuOverlay
from src.ui.ui_colors import COLOR_BLACK


class PauseScreen:
    """Semi-transparent overlay with 3 pause actions."""

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self._hovered_btn: int | None = None
        self._confirm_timer: float = 0.0  # >0 → show "Saved!" feedback
        self.state = "MAIN"  # "MAIN" or "SAVE_MENU"
        self._i18n = I18nManager()
        self._save_menu = SaveMenuOverlay(
            screen, save_manager, self._i18n.get("pause_menu.save", "Save Game")
        )

        sw, sh = screen.get_size()
        self._sw = sw
        self._sh = sh

        self._load_assets()
        self._compute_layout()

    def _load_asset(self, filename: str) -> pygame.Surface:
        path = str(Path(_MENU_DIR) / filename)
        return AssetManager().get_image(path, fallback=True)

    def _load_cursor(self, filename: str) -> pygame.Surface:
        """Load cursor from UI assets, scaled to CURSOR_SIZE."""
        path = str(Path(_UI_DIR) / filename)
        raw = AssetManager().get_image(path, fallback=True)
        target_h = Settings.CURSOR_SIZE
        ratio = target_h / CURSOR_RAW_H
        target_w = int(CURSOR_RAW_W * ratio)
        return pygame.transform.smoothscale(raw, (target_w, target_h))

    def _load_assets(self) -> None:
        # Semi-transparent overlay
        self._overlay = pygame.Surface((self._sw, self._sh))
        self._overlay.set_alpha(OVERLAY_ALPHA)
        self._overlay.fill(COLOR_BLACK)

        # Panel background — 02-panel_background.png (600x600 RGBA → scaled)
        panel_raw = self._load_asset("02-panel_background.png")
        if panel_raw.get_size() != (FALLBACK_SURF_SIZE, FALLBACK_SURF_SIZE):
            self._panel = pygame.transform.smoothscale(panel_raw, (PANEL_W, PANEL_H))
        else:
            # Fallback: programmatic surface
            self._panel = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
            self._panel.fill(PANEL_FALLBACK_FILL)
            pygame.draw.rect(self._panel, PANEL_FALLBACK_BORDER, self._panel.get_rect(), 2)

        try:
            self._title_font = pygame.font.Font(_FONT_PATH, PAUSE_TITLE_FONT_SIZE)
            self._item_font = pygame.font.Font(_FONT_PATH, PAUSE_ITEM_FONT_SIZE)
            self._success_font = pygame.font.Font(_FONT_PATH, PAUSE_SUCCESS_FONT_SIZE)
        except OSError:
            self._title_font = pygame.font.SysFont(None, PAUSE_TITLE_FONT_SIZE)
            self._item_font = pygame.font.SysFont(None, PAUSE_ITEM_FONT_SIZE)
            self._success_font = pygame.font.SysFont(None, PAUSE_SUCCESS_FONT_SIZE)
        try:
            am = __import__("src.engine.asset_manager", fromlist=["AssetManager"]).AssetManager()
            self._font_small = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        except Exception:
            self._font_small = pygame.font.SysFont(None, 24)

        # Custom cursor
        self._pointer_img = self._load_cursor("05-pointer.png")
        self._pointer_select_img = self._load_cursor("06-pointer_select.png")

        # Pre-render button label surfaces (idle + hover) — zero allocs in draw()
        self._rendered_idle: list[pygame.Surface] = []
        self._rendered_hover: list[pygame.Surface] = []
        for key, default in zip(_BUTTON_KEYS, _BUTTON_DEFAULTS, strict=False):
            label = self._i18n.get(key, default)
            self._rendered_idle.append(self._make_engraved_surface(label))
            self._rendered_hover.append(self._make_halo_surface(label))

    def _make_engraved_surface(self, label: str) -> pygame.Surface:
        """Pre-render 3-pass stone engraving to a single composite surface."""
        shadow = self._item_font.render(label, True, ENGRAVE_SHADOW)
        light = self._item_font.render(label, True, ENGRAVE_LIGHT)
        text = self._item_font.render(label, True, ENGRAVE_TEXT)
        w = text.get_width() + 2
        h = text.get_height() + 2
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.blit(shadow, (0, 0))
        out.blit(light, (2, 2))
        out.blit(text, (1, 1))
        return out

    def _make_halo_surface(self, label: str) -> pygame.Surface:
        """Pre-render halo glow + main text to a composite surface."""
        base = self._item_font.render(label, True, HOVER_HALO_COLOR)
        w, h = base.get_size()
        pad = HALO_BLUR_PADDING
        padded = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        padded.blit(base, (pad, pad))
        out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        try:
            blurred = pygame.transform.gaussian_blur(padded, HALO_BLUR_RADIUS)
            out.blit(blurred, (0, 0))
            out.blit(blurred, (0, 0))
            out.blit(blurred, (0, 0))
        except AttributeError:
            # Fallback for standard pygame (no gaussian_blur)
            base.set_alpha(80)
            offsets = [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, -4), (0, 4), (-4, 0), (4, 0)]
            for dx, dy in offsets:
                out.blit(base, (pad + dx, pad + dy))
        main = self._item_font.render(label, True, HOVER_TEXT_COLOR)
        out.blit(main, (pad, pad))
        return out

    def _compute_layout(self) -> None:
        """Button rects aligned to the inner stone area of the panel."""
        panel_rect = pygame.Rect(
            self._sw // 2 - PANEL_W // 2,
            self._sh // 2 - PANEL_H // 2,
            PANEL_W,
            PANEL_H,
        )
        btn_w, btn_h = PAUSE_BTN_W, PAUSE_BTN_H
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

        # Title — Cormorant Garamond, golden, centered at top of panel
        title_text = self._i18n.get("pause_menu.title", "PAUSE")
        title = self._title_font.render(title_text, True, TITLE_COLOR)
        self._screen.blit(
            title,
            title.get_rect(midtop=(panel_rect.centerx, panel_rect.top + PAUSE_TITLE_OFFSET)),
        )

        # Menu items — blit pre-rendered cached surfaces
        for i, (rect, surf_idle, surf_hover) in enumerate(
            zip(self.button_rects, self._rendered_idle, self._rendered_hover, strict=False)
        ):
            surf = surf_hover if self._hovered_btn == i else surf_idle
            self._screen.blit(surf, surf.get_rect(center=rect.center))

        if self._confirm_timer > 0:
            success_text = self._i18n.get("pause_menu.saved_success", "Game saved!")
            msg = self._success_font.render(success_text, True, SUCCESS_COLOR)
            alpha = int(min(255, (self._confirm_timer / CONFIRM_DISPLAY_SECONDS) * 255))
            msg.set_alpha(alpha)
            self._screen.blit(
                msg,
                msg.get_rect(midbottom=(self._sw // 2, self._sh - CONFIRM_MSG_MARGIN_BOTTOM)),
            )

        self._draw_cursor()

    def notify_save_result(self, success: bool) -> None:
        """Call after a save attempt to show confirmation for CONFIRM_DISPLAY_SECONDS."""
        if success:
            self._confirm_timer = CONFIRM_DISPLAY_SECONDS
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
