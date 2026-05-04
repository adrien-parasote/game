"""
TitleScreen — Main menu UI with state machine.
Spec: docs/specs/game-flow-spec.md#22-srcuititle_screenpy-new
"""
import logging
import os
import math
import pygame
from src.config import Settings
from src.engine.game_events import GameEvent, GameEventType
from src.engine.save_manager import SaveManager
from src.ui.save_menu import SaveMenuOverlay
from src.engine.i18n import I18nManager
from src.ui.title_screen_constants import *
from src.ui.title_screen_constants import _MENU_DIR, _UI_DIR, _MENU_ITEM_KEYS, _MENU_ITEM_DEFAULTS, LOGO_MAIN_FONT_SIZE, LOGO_MAIN_COLOR, LOGO_MAIN_HALO, MENU_HOVER_COLOR, MENU_HOVER_HALO, BACKGROUND_LIGHTS, BG_LIGHT_COLOR, HALO_DEBUG

class TitleScreen:
    """Main menu screen — background, logo, cursor. Menu to be added."""

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self.state = "MAIN_MENU"          # "MAIN_MENU" | "LOAD_MENU"
        self._hovered_item: int | None = None
        self._i18n = I18nManager()
        self._light_time = 0.0

        sw, sh = screen.get_size()
        self._sw = sw
        self._sh = sh
        # Scale factors: BACKGROUND_LIGHTS coords are in logical 1280×720 space
        self._light_scale_x = sw / 1280.0
        self._light_scale_y = sh / 720.0
        logging.debug(f"TitleScreen: surface={sw}x{sh}, light_scale=({self._light_scale_x:.3f}, {self._light_scale_y:.3f})")
        
        self._load_menu = SaveMenuOverlay(screen, save_manager, self._i18n.get("save_menu.title_load", "Charger une partie"))

        self._load_assets()
        self._compute_layout()

    # ── Asset helpers ──────────────────────────────────────────────────────────

    def _load_asset(self, filename: str) -> pygame.Surface:
        path = os.path.join(_MENU_DIR, filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"TitleScreen: Could not load {filename}: {e}")
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 255))
            return surf

    def _load_cursor(self, filename: str) -> pygame.Surface:
        """Load cursor from UI assets directory, scaled to CURSOR_SIZE."""
        path = os.path.join(_UI_DIR, filename)
        try:
            raw = pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"TitleScreen: Could not load cursor {filename}: {e}")
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 255))
            return surf
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
        self._overlay.fill((0, 0, 0))

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
            self._back_label_font = pygame.font.Font(
                MENU_FONT_PATH, BACK_BTN_FONT_SIZE
            )
        except OSError:
            self._back_label_font = self._font_small

        # Pre-generate one halo surface per distinct radius — same technique as SaveSlotUI
        # Black surface: invisible in BLEND_RGB_ADD mode
        self._light_halos: dict[int, pygame.Surface] = {}
        for r in {entry[2] for entry in BACKGROUND_LIGHTS}:
            surf = pygame.Surface((r * 2, r * 2))
            surf.fill((0, 0, 0))
            for ri in range(r, 0, -1):
                intensity = (1.0 - (ri / r)) ** 2
                color = (
                    int(BG_LIGHT_COLOR[0] * intensity),
                    int(BG_LIGHT_COLOR[1] * intensity),
                    int(BG_LIGHT_COLOR[2] * intensity),
                )
                pygame.draw.circle(surf, color, (r, r), ri)
            self._light_halos[r] = surf

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
        back_total_w = 120   # conservative estimate: text (~70px) + gap + icon (28px)
        self.back_btn_rect = pygame.Rect(
            bcx - back_total_w // 2, bcy - BACK_BTN_H // 2,
            back_total_w, max(BACK_BTN_H, 28)
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

        # Draw animated background lights
        for i, (lx, ly, hr) in enumerate(BACKGROUND_LIGHTS):
            # Map from logical 1280×720 space to actual surface space
            sx = int(lx * self._light_scale_x)
            sy = int(ly * self._light_scale_y)
            scaled_r = int(hr * (self._light_scale_x + self._light_scale_y) / 2)

            # Candle-like flicker: slow, low-amplitude breathing
            flicker = (
                math.sin(self._light_time * 0.4 + i * 1.1) * 0.06 +
                math.sin(self._light_time * 0.9 + i * 2.3) * 0.04
            ) + 0.92
            flicker = max(0.80, min(1.0, flicker))

            # Use the radius bucket from _light_halos, scaled to surface size
            halo_surf = self._light_halos[hr]
            display_scale = flicker * (scaled_r / hr)
            rendered = pygame.transform.rotozoom(halo_surf, 0, display_scale)
            offset = rendered.get_width() // 2
            self._screen.blit(rendered, (sx - offset, sy - offset), special_flags=pygame.BLEND_RGB_ADD)

            if HALO_DEBUG:
                pygame.draw.line(self._screen, (255, 0, 0), (sx - 10, sy), (sx + 10, sy), 1)
                pygame.draw.line(self._screen, (255, 0, 0), (sx, sy - 10), (sx, sy + 10), 1)
                pygame.draw.circle(self._screen, (255, 0, 0), (sx, sy), 4)

        title_text = self._i18n.get("menu.main_title", "L'Éveil de l'Héritier")
        self._blit_halo_text(
            title_text, 
            LOGO_ZONE_W // 2, 
            LOGO_Y, 
            self._title_font, 
            LOGO_MAIN_COLOR, 
            LOGO_MAIN_HALO
        )

        if self.state == "MAIN_MENU":
            self._draw_menu_items()
        elif self.state == "LOAD_MENU":
            self._load_menu.draw()
        elif self.state == "OPTIONS":
            self._draw_options_overlay()

        self._draw_cursor()

    def _draw_menu_items(self) -> None:
        """Render menu items: engraved stone effect idle, golden on hover."""
        for i, (key, default) in enumerate(zip(_MENU_ITEM_KEYS, _MENU_ITEM_DEFAULTS)):
            label = self._i18n.get(key, default=default)
            cx = MENU_ITEM_X + MENU_ITEM_OFFSET_X
            cy = MENU_ITEM_Y_START + MENU_ITEM_OFFSET_Y + i * MENU_ITEM_SPACING
            if self._hovered_item == i:
                self._blit_halo_text(label, cx, cy, self._menu_item_font, MENU_HOVER_COLOR, MENU_HOVER_HALO)
            else:
                self._blit_engraved(label, cx, cy)

    def _blit_halo_text(
        self, label: str, cx: int, cy: int,
        font: pygame.font.Font,
        text_color: tuple[int, int, int],
        halo_color: tuple[int, int, int]
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

    def _blit_engraved(
        self, label: str, cx: int, cy: int,
        font: pygame.font.Font | None = None
    ) -> None:
        """3-pass engraved-in-stone text effect.

        Pass 1 — shadow (bottom-right): simulates the dark background of the engraving.
        Pass 2 — highlight (top-left): simulates light on the upper edge.
        Pass 3 — main text: slightly lighter than the stone.
        Uses self._menu_item_font by default; pass a custom font to override.
        """
        f = font if font is not None else self._menu_item_font
        shadow = f.render(label, True, MENU_ENGRAVE_SHADOW)
        light  = f.render(label, True, MENU_ENGRAVE_LIGHT)
        text   = f.render(label, True, MENU_ENGRAVE_TEXT)
        r = text.get_rect(center=(cx, cy))
        self._screen.blit(shadow, r.move(1, 2))
        self._screen.blit(light,  r.move(-1, -1))
        self._screen.blit(text,   r)

    # ── Load overlay ───────────────────────────────────────────────────────────

    def _refresh_slots(self) -> None:
        """Reload slot data from SaveManager (call when entering LOAD_MENU)."""
        self._load_menu.refresh()

    def _draw_cursor(self) -> None:
        """Draw custom cursor on top of everything."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        self._screen.blit(img, mouse_pos)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _handle_main_menu(self, event: pygame.Event) -> GameEvent | None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        for i, rect in enumerate(self.menu_item_rects):
            if not rect.collidepoint(event.pos):
                continue
            actions = [
                GameEvent.new_game,     # 0 — Nouvelle Partie
                self._enter_load_menu, # 1 — Charger
                self._enter_options,   # 2 — Options
                GameEvent.quit,        # 3 — Quitter
            ]
            return actions[i]()
        return None

    def _enter_load_menu(self) -> None:
        self.state = "LOAD_MENU"
        self._refresh_slots()

    def _enter_options(self) -> None:
        self.state = "OPTIONS"

    def _handle_options(self, event: pygame.Event) -> GameEvent | None:
        """ESC ou clic sur le bouton retour → MAIN_MENU."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "MAIN_MENU"
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn_rect.collidepoint(event.pos):
                self.state = "MAIN_MENU"
        return None

    def _draw_options_overlay(self) -> None:
        """Draw options panel: 'Retour' label (engraved/golden) + back icon."""
        label = self._i18n.get(BACK_BTN_LABEL_KEY, default=BACK_BTN_LABEL_DEFAULT)
        cx = BACK_BTN_X + BACK_BTN_OFFSET_X
        cy = BACK_BTN_Y + BACK_BTN_OFFSET_Y

        # Render icon (hover = slightly larger)
        btn = self._back_btn_hover if self._back_hovered else self._back_btn
        icon_w = btn.get_width()

        # Measure label width for layout (use engraved text surface)
        label_surf_measure = self._back_label_font.render(label, True, (0, 0, 0))
        label_w = label_surf_measure.get_width()

        # Total width: icon + gap + label  — centred on (cx, cy)
        total_w = icon_w + BACK_BTN_GAP + label_w
        left_x = cx - total_w // 2

        # Draw icon left
        icon_r = btn.get_rect(midleft=(left_x, cy))
        self._screen.blit(btn, icon_r)

        # Draw label right of icon: engraved at rest, golden on hover
        label_cx = left_x + icon_w + BACK_BTN_GAP + label_w // 2
        if self._back_hovered:
            self._blit_halo_text(label, label_cx, cy, self._back_label_font, MENU_HOVER_COLOR, MENU_HOVER_HALO)
        else:
            self._blit_engraved(label, label_cx, cy, font=self._back_label_font)

    def _handle_load_menu(self, event: pygame.Event) -> GameEvent | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "MAIN_MENU"
            return None

        slot_idx = self._load_menu.get_clicked_slot(event)
        if slot_idx is not None:
            # check if there is data
            if self._load_menu._slots_info[slot_idx] is not None:
                return GameEvent(type=GameEventType.LOAD_REQUESTED, slot_id=slot_idx + 1)
        return None
