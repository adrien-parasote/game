"""
TitleScreen — Main menu UI with state machine.
Spec: docs/specs/game-flow-spec.md#22-srcuititle_screenpy-new
"""

import logging
from pathlib import Path

import pygame

from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.game_events import GameEvent, GameEventType
from src.engine.i18n import I18nManager
from src.engine.save_manager import SaveManager
from src.ui.save_menu import SaveMenuOverlay
from src.ui.title_screen_constants import (
    _MENU_DIR,
    _MENU_ITEM_DEFAULTS,
    _MENU_ITEM_KEYS,
    _UI_DIR,
    BACK_BTN_FONT_SIZE,
    BACK_BTN_H,
    BACK_BTN_OFFSET_X,
    BACK_BTN_OFFSET_Y,
    BACK_BTN_W,
    BACK_BTN_X,
    BACK_BTN_Y,
    LOGO_MAIN_COLOR,
    LOGO_MAIN_FONT_SIZE,
    LOGO_MAIN_HALO,
    LOGO_Y,
    LOGO_ZONE_W,
    MENU_FONT_PATH,
    MENU_ITEM_FONT_SIZE,
    MENU_ITEM_OFFSET_X,
    MENU_ITEM_OFFSET_Y,
    MENU_ITEM_SPACING,
    MENU_ITEM_X,
    MENU_ITEM_Y_START,
    OVERLAY_ALPHA,
)
from src.ui.title_screen_draw import TitleDrawMixin
from src.ui.title_screen_lights import TitleLightsMixin
from src.ui.ui_colors import COLOR_BLACK


class TitleScreen(TitleLightsMixin, TitleDrawMixin):
    """Main menu screen — background, logo, cursor.

    Light halo logic provided by TitleLightsMixin.
    Text rendering provided by TitleDrawMixin.
    """

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self.state = "MAIN_MENU"  # "MAIN_MENU" | "LOAD_MENU"
        self._hovered_item: int | None = None
        self._i18n = I18nManager()
        self._light_time = 0.0

        sw, sh = screen.get_size()
        self._sw = sw
        self._sh = sh
        # Scale factors: BACKGROUND_LIGHTS coords are in logical 1280×720 space
        self._light_scale_x = sw / 1280.0
        self._light_scale_y = sh / 720.0
        logging.debug(
            f"TitleScreen: surface={sw}x{sh}, light_scale=({self._light_scale_x:.3f}, {self._light_scale_y:.3f})"
        )

        self._load_menu = SaveMenuOverlay(
            screen, save_manager, self._i18n.get("save_menu.title_load", "Load Game")
        )

        self._load_assets()
        self._compute_layout()

    # ── Asset helpers ──────────────────────────────────────────────────────────

    def _load_asset(self, filename: str) -> pygame.Surface:
        path = str(Path(_MENU_DIR) / filename)
        return AssetManager().get_image(path, fallback=True)

    def _load_cursor(self, filename: str) -> pygame.Surface:
        """Load cursor from UI assets directory, scaled to CURSOR_SIZE."""
        path = str(Path(_UI_DIR) / filename)
        raw = AssetManager().get_image(path, fallback=True)
        target_h = Settings.CURSOR_SIZE
        ratio = target_h / 535
        target_w = int(309 * ratio)
        return pygame.transform.smoothscale(raw, (target_w, target_h))

    def _scale(self, surf: pygame.Surface, target_w: int) -> pygame.Surface:
        """Scale proportionally to target_w."""
        sw, sh = surf.get_size()
        return pygame.transform.smoothscale(surf, (target_w, int(sh * target_w / sw)))

    # ── Assets & layout ────────────────────────────────────────────────────────

    def _load_assets(self) -> None:
        # Background — native 1280x720
        bg_raw = self._load_asset("01-menu_background.png")
        self._bg = pygame.transform.smoothscale(bg_raw, (self._sw, self._sh))

        # Fonts
        try:
            self._title_font = pygame.font.Font(MENU_FONT_PATH, LOGO_MAIN_FONT_SIZE)
        except OSError:
            self._title_font = pygame.font.SysFont(None, LOGO_MAIN_FONT_SIZE)

        # Semi-transparent overlay
        self._overlay = pygame.Surface((self._sw, self._sh))
        self._overlay.set_alpha(OVERLAY_ALPHA)
        self._overlay.fill(COLOR_BLACK)

        # Fonts
        try:
            am = __import__("src.engine.asset_manager", fromlist=["AssetManager"]).AssetManager()
            self._font = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
            self._font_small = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        except Exception:
            self._font = pygame.font.SysFont(None, 32)
            self._font_small = pygame.font.SysFont(None, 24)

        # Custom cursor
        self._pointer_img = self._load_cursor("05-pointer.png")
        self._pointer_select_img = self._load_cursor("06-pointer_select.png")
        pygame.mouse.set_visible(False)

        # Scroll title + menu item fonts — Cormorant Garamond, cached at init
        try:
            self._menu_item_font = pygame.font.Font(MENU_FONT_PATH, MENU_ITEM_FONT_SIZE)
        except OSError:
            logging.warning("TitleScreen: Cormorant Garamond not found, falling back to Noble font")
            self._menu_item_font = self._font

        # Options back button — 01-menu_back_cursor.png
        back_raw = self._load_asset("01-menu_back_cursor.png")
        self._back_btn = pygame.transform.smoothscale(back_raw, (BACK_BTN_W, BACK_BTN_H))
        self._back_btn_hover = pygame.transform.smoothscale(
            back_raw, (BACK_BTN_W + 4, BACK_BTN_H + 4)
        )
        # Label font (Cormorant Garamond, small — cached at init)
        try:
            self._back_label_font = pygame.font.Font(MENU_FONT_PATH, BACK_BTN_FONT_SIZE)
        except OSError:
            self._back_label_font = self._font_small

        # P1+P2: Pre-scale halo surfaces into buckets — delegated to TitleLightsMixin
        self._init_light_halos()

        # P3: Blur cache — invalidated when hovered item changes
        self._blur_cache: dict[int | None, pygame.Surface] = {}
        self._prev_hovered_item: int | None = None

        # P3: Pre-render idle menu label surfaces — avoids font.render() per frame
        self._menu_label_surfaces: list[pygame.Surface] = [
            self._render_engraved(self._i18n.get(key, default=default))
            for key, default in zip(_MENU_ITEM_KEYS, _MENU_ITEM_DEFAULTS, strict=False)
        ]

    def _compute_layout(self) -> None:
        """Compute menu item rects, save slot rects, and back button rect."""
        # Menu item click zones (centred on MENU_ITEM_X)
        item_w = 280
        item_h = 48
        self.menu_item_rects: list[pygame.Rect] = []
        for i in range(len(_MENU_ITEM_KEYS)):
            cx = MENU_ITEM_X + MENU_ITEM_OFFSET_X
            cy = MENU_ITEM_Y_START + MENU_ITEM_OFFSET_Y + i * MENU_ITEM_SPACING
            self.menu_item_rects.append(
                pygame.Rect(cx - item_w // 2, cy - item_h // 2, item_w, item_h)
            )
        # Back button rect (OPTIONS state) — covers text + icon
        # Layout: [text] <gap> [icon]  all centred on (bcx, bcy)
        # We don't know text width at layout time, so we use a generous fixed width
        bcx = BACK_BTN_X + BACK_BTN_OFFSET_X
        bcy = BACK_BTN_Y + BACK_BTN_OFFSET_Y
        back_total_w = 120  # conservative estimate: text (~70px) + gap + icon (28px)
        self.back_btn_rect = pygame.Rect(
            bcx - back_total_w // 2, bcy - BACK_BTN_H // 2, back_total_w, max(BACK_BTN_H, 28)
        )
        self._back_hovered: bool = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.Event) -> GameEvent | None:
        if self.state == "LOAD_MENU":
            return self._handle_load_menu(event)
        if self.state == "OPTIONS":
            return self._handle_options(event)
        return self._handle_main_menu(event)

    def update(self, dt: float) -> None:
        self._light_time += dt

        mouse_pos = pygame.mouse.get_pos()
        if self.state == "MAIN_MENU":
            self._hovered_item: int | None = None
            for i, rect in enumerate(self.menu_item_rects):
                if rect.collidepoint(mouse_pos):
                    self._hovered_item = i
                    break
        elif self.state == "LOAD_MENU":
            self._load_menu.update(dt)
        elif self.state == "OPTIONS":
            self._back_hovered = self.back_btn_rect.collidepoint(mouse_pos)

    def draw(self) -> None:
        self._screen.blit(self._bg, (0, 0))

        # P1+P2: Draw light halos (delegated to TitleLightsMixin)
        self._draw_background_lights()
        self._draw_mushroom_lights()

        title_text = self._i18n.get("menu.main_title", "L'Éveil de l'Héritier")  # Proper noun — game title stays in French
        self._blit_halo_text(
            title_text, LOGO_ZONE_W // 2, LOGO_Y, self._title_font, LOGO_MAIN_COLOR, LOGO_MAIN_HALO
        )

        if self.state == "MAIN_MENU":
            self._draw_menu_items()
        elif self.state == "LOAD_MENU":
            self._load_menu.draw()
        elif self.state == "OPTIONS":
            self._draw_options_overlay()

        self._draw_cursor()

    # ── Load overlay ───────────────────────────────────────────────────────────

    def _refresh_slots(self) -> None:
        """Reload slot data from SaveManager (call when entering LOAD_MENU)."""
        self._load_menu.refresh()

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _handle_main_menu(self, event: pygame.Event) -> GameEvent | None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        for i, rect in enumerate(self.menu_item_rects):
            if not rect.collidepoint(event.pos):
                continue
            actions = [
                GameEvent.new_game,  # 0 — Nouvelle Partie
                self._enter_load_menu,  # 1 — Charger
                self._enter_options,  # 2 — Options
                GameEvent.quit,  # 3 — Quitter
            ]
            return actions[i]()
        return None

    def _enter_load_menu(self) -> None:
        self.state = "LOAD_MENU"
        self._refresh_slots()

    def _enter_options(self) -> None:
        self.state = "OPTIONS"

    def _handle_options(self, event: pygame.Event) -> GameEvent | None:
        """ESC or click on back button → MAIN_MENU."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "MAIN_MENU"
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn_rect.collidepoint(event.pos):
                self.state = "MAIN_MENU"
        return None

    def _handle_load_menu(self, event: pygame.Event) -> GameEvent | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "MAIN_MENU"
            return None

        if self._load_menu.is_back_clicked(event):
            self.state = "MAIN_MENU"
            return None

        slot_idx = self._load_menu.get_clicked_slot(event)
        if slot_idx is not None:
            # check if there is data
            if self._load_menu._slots_info[slot_idx] is not None:
                return GameEvent(type=GameEventType.LOAD_REQUESTED, slot_id=slot_idx + 1)
        return None
