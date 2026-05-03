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

_FONT_PATH = "assets/fonts/cormorant-garamond-regular.ttf"

OVERLAY_ALPHA = 160

# Panel — 02-panel_background.png (600x600 → 480x480)
PANEL_W = 480
PANEL_H = 480

# Inner content area offsets from panel edges (gear decorations)
INNER_TOP = 60        # px from panel top to inner stone area
INNER_BOTTOM = 60     # px from panel bottom to inner stone area

# Layout offsets from panel top
PAUSE_TITLE_OFFSET = 105    # y du titre depuis le haut du panel
ITEM_Y_START_OFFSET = 170  # y du 1er item depuis le haut du panel
ITEM_SPACING = 60          # espacement vertical entre items

# Font sizes
PAUSE_TITLE_FONT_SIZE = 42
PAUSE_ITEM_FONT_SIZE = 32

# Couleurs — identiques au TitleScreen
ENGRAVE_TEXT   = (58, 85, 92)
ENGRAVE_SHADOW = (12, 20, 23)
ENGRAVE_LIGHT  = (75, 105, 112)
HOVER_COLOR    = (255, 235, 180)
TITLE_COLOR    = (220, 195, 140)

_BUTTON_LABELS = ["Menu Principal", "Reprendre", "Sauvegarder"]



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

        # Fonts — Cormorant Garamond (title + items), Noble fallback
        try:
            self._title_font = pygame.font.Font(_FONT_PATH, PAUSE_TITLE_FONT_SIZE)
            self._item_font  = pygame.font.Font(_FONT_PATH, PAUSE_ITEM_FONT_SIZE)
        except OSError:
            self._title_font = pygame.font.SysFont(None, 42)
            self._item_font  = pygame.font.SysFont(None, 32)
        try:
            am = __import__(
                "src.engine.asset_manager", fromlist=["AssetManager"]
            ).AssetManager()
            self._font_small = am.get_font(
                Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE
            )
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
            PANEL_W, PANEL_H,
        )
        # Click zones: centred horizontally, spaced vertically from ITEM_Y_START_OFFSET
        btn_w, btn_h = 280, 50
        x = panel_rect.centerx - btn_w // 2
        self.button_rects: list[pygame.Rect] = [
            pygame.Rect(
                x,
                panel_rect.top + ITEM_Y_START_OFFSET + i * ITEM_SPACING,
                btn_w, btn_h,
            )
            for i in range(len(_BUTTON_LABELS))
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
        panel_rect = pygame.Rect(
            self._sw // 2 - PANEL_W // 2,
            self._sh // 2 - PANEL_H // 2,
            PANEL_W, PANEL_H,
        )

        self._screen.blit(self._overlay, (0, 0))
        self._screen.blit(self._panel, panel_rect)

        # Title — Cormorant Garamond, doré, centré en haut du panel
        title = self._title_font.render("PAUSE", True, TITLE_COLOR)
        self._screen.blit(
            title,
            title.get_rect(midtop=(panel_rect.centerx, panel_rect.top + PAUSE_TITLE_OFFSET)),
        )

        # Menu items — engraved idle, golden hover
        for i, (rect, label) in enumerate(zip(self.button_rects, _BUTTON_LABELS)):
            cx = rect.centerx
            cy = rect.centery
            if self._hovered_btn == i:
                surf = self._item_font.render(label, True, HOVER_COLOR)
                self._screen.blit(surf, surf.get_rect(center=(cx, cy)))
            else:
                self._blit_engraved(label, cx, cy)

        if self._confirm_timer > 0:
            msg = self._font_small.render(
                "Partie sauvegardée !", True, (180, 220, 150)
            )
            self._screen.blit(
                msg, msg.get_rect(midbottom=(panel_rect.centerx, panel_rect.bottom - 25))
            )

        self._draw_cursor()

    def _blit_engraved(self, label: str, cx: int, cy: int) -> None:
        """3-pass stone engraving: shadow | light | text. Matches TitleScreen effect."""
        shadow = self._item_font.render(label, True, ENGRAVE_SHADOW)
        light  = self._item_font.render(label, True, ENGRAVE_LIGHT)
        text   = self._item_font.render(label, True, ENGRAVE_TEXT)
        r = text.get_rect(center=(cx, cy))
        self._screen.blit(shadow, r.move(1, 2))
        self._screen.blit(light,  r.move(-1, -1))
        self._screen.blit(text,   r)

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
            return GameEvent.goto_title()
        if index == 1:
            return GameEvent.resume()
        if index == 2:
            return GameEvent(type=GameEventType.PAUSE_REQUESTED)  # signal save
        return None
