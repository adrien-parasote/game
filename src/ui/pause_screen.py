"""
PauseScreen — Overlay pause menu on top of the running game.
Spec: docs/specs/game-flow-spec.md#24-srcuipause_screenpy-new
"""
import logging
import os
import pygame
from src.config import Settings
from src.engine.game_events import GameEvent, GameEventType
from src.engine.save_manager import SaveManager

_MENU_DIR = os.path.join("assets", "images", "menu")
_UI_DIR = os.path.join("assets", "images", "ui")

BTN_W_SRC = 341
BTN_H_SRC = 182
BTN_W_DST = 400
BTN_H_DST = 86
BTN_SPACING = 70

OVERLAY_ALPHA = 160

_BUTTON_LABELS = ["Reprendre", "Sauvegarder", "Menu Principal"]


class PauseScreen:
    """Semi-transparent overlay with 3 pause actions."""

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self._hovered_btn: int | None = None
        self._confirm_timer: float = 0.0  # >0 → show "Sauvegardé !" for 2s

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

        # Fonts
        try:
            am = __import__(
                "src.engine.asset_manager", fromlist=["AssetManager"]
            ).AssetManager()
            self._font = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
            self._font_small = am.get_font(
                Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE
            )
        except Exception:
            self._font = pygame.font.SysFont(None, 32)
            self._font_small = pygame.font.SysFont(None, 24)

        # Custom cursor
        self._pointer_img = self._load_cursor("05-pointer.png")
        self._pointer_select_img = self._load_cursor("06-pointer_select.png")

    def _compute_layout(self) -> None:
        n = len(_BUTTON_LABELS)
        zone_h = (n - 1) * BTN_SPACING + BTN_H_DST
        panel_rect = self._panel.get_rect(center=(self._sw // 2, self._sh // 2))
        y_start = panel_rect.centery - zone_h // 2 + 40
        x = (self._sw - BTN_W_DST) // 2

        self.button_rects: list[pygame.Rect] = [
            pygame.Rect(x, y_start + i * BTN_SPACING, BTN_W_DST, BTN_H_DST)
            for i in range(n)
        ]

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.Event) -> GameEvent | None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        for i, rect in enumerate(self.button_rects):
            if rect.collidepoint(event.pos):
                return self._on_button_click(i)
        return None

    def update(self, dt: float) -> None:
        if self._confirm_timer > 0:
            self._confirm_timer -= dt

        mouse_pos = pygame.mouse.get_pos()
        self._hovered_btn = None
        for i, rect in enumerate(self.button_rects):
            if rect.collidepoint(mouse_pos):
                self._hovered_btn = i
                break

    def draw(self) -> None:
        self._screen.blit(self._overlay, (0, 0))
        panel_rect = self._panel.get_rect(center=(self._sw // 2, self._sh // 2))
        self._screen.blit(self._panel, panel_rect)

        title = self._font.render("PAUSE", True, (220, 200, 150))
        self._screen.blit(
            title, title.get_rect(midtop=(panel_rect.centerx, panel_rect.top + 30))
        )

        for i, (rect, label) in enumerate(zip(self.button_rects, _BUTTON_LABELS)):
            color = (255, 235, 180) if self._hovered_btn == i else (220, 200, 150)
            text = self._font.render(label, True, color)
            self._screen.blit(text, text.get_rect(center=rect.center))

        if self._confirm_timer > 0:
            msg = self._font_small.render("Partie sauvegardée !", True, (180, 220, 150))
            self._screen.blit(msg, msg.get_rect(midbottom=(self._sw // 2, panel_rect.bottom - 20)))

        self._draw_cursor()

    def notify_save_result(self, success: bool) -> None:
        """Call after a save attempt to show confirmation for 2 seconds."""
        if success:
            self._confirm_timer = 2.0

    def _draw_cursor(self) -> None:
        """Draw custom cursor on top of everything."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        self._screen.blit(img, mouse_pos)

    # ── Button actions ────────────────────────────────────────────────────────

    def _on_button_click(self, index: int) -> GameEvent | None:
        if index == 0:
            return GameEvent.resume()
        if index == 1:
            return GameEvent(type=GameEventType.PAUSE_REQUESTED)  # signal save
        if index == 2:
            return GameEvent.goto_title()
        return None
