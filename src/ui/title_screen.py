"""
TitleScreen — Main menu UI with state machine.
Spec: docs/specs/game-flow-spec.md#22-srcuititle_screenpy-new
"""
import logging
import os
import pygame
from src.config import Settings
from src.engine.game_events import GameEvent, GameEventType
from src.engine.save_manager import SaveManager, SlotInfo

# ── Asset constants ────────────────────────────────────────────────────────────
_MENU_DIR = os.path.join("assets", "images", "menu")
_UI_DIR = os.path.join("assets", "images", "ui")

# Logo composite: 5 separate alpha-transparent PNGs assembled at runtime
# Source sizes (px): main_title=790x138, moon=69x71, gear=94x95,
#                   separator=676x11, subtitle=531x55
LOGO_MAIN_W = 640          # main title scaled width
LOGO_ACCENT_H = 58         # moon/gear icon height
LOGO_SEP_W = 380           # separator width
LOGO_SUB_W = 380           # subtitle width
LOGO_Y = 30                # top of logo block on screen
LOGO_GAP = 6               # vertical gap between elements
# Fine-tune moon/gear position (px, relative to default centred placement)
MOON_OFFSET_X = 25         # >0 → right,  <0 → left
MOON_OFFSET_Y = 55         # >0 → down,   <0 → up
GEAR_OFFSET_X = -25        # >0 → right,  <0 → left
GEAR_OFFSET_Y = 55         # >0 → down,   <0 → up

# Save slot spritesheet (04-save_slot.png 1024x1024, 2 states stacked)
SLOT_H_SRC = 512
SLOT_W_DST = 800
SLOT_H_DST = 120
SLOT_SPACING = 140
SLOT_PANEL_Y_START = 140   # inside the load panel overlay

# Semi-transparent overlay for load screen
OVERLAY_ALPHA = 180

# Scroll edge overlays (295x720 — shown on left/right edges)
SCROLL_W = 295             # width of scroll image
SCROLL_ZONE_W = 295        # mouse hover zone width on each side


class TitleScreen:
    """Main menu screen — background, logo, cursor. Menu to be added."""

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self.state = "MAIN_MENU"          # "MAIN_MENU" | "LOAD_MENU"
        self._slots: list[SlotInfo | None] = [None, None, None]
        self._hovered_slot: int | None = None
        self._hovered_scroll: str | None = None   # None | 'left' | 'right'

        sw, sh = screen.get_size()
        self._sw = sw
        self._sh = sh

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

    def _build_logo_composite(self) -> pygame.Surface:
        """Assemble 5 alpha-transparent logo parts into one surface."""
        main = self._scale(self._load_asset("00-title_logo_main_title.png"), LOGO_MAIN_W)

        moon_raw = self._load_asset("00-title_logo_moon.png")
        mw, mh = moon_raw.get_size()
        moon = pygame.transform.smoothscale(moon_raw, (int(mw * LOGO_ACCENT_H / mh), LOGO_ACCENT_H))

        gear_raw = self._load_asset("00-title_logo_gear.png")
        gw, gh = gear_raw.get_size()
        gear = pygame.transform.smoothscale(gear_raw, (int(gw * LOGO_ACCENT_H / gh), LOGO_ACCENT_H))

        sep = self._scale(self._load_asset("00-title_logo_separator.png"), LOGO_SEP_W)
        sub = self._scale(self._load_asset("00-title_logo_subtitle.png"), LOGO_SUB_W)

        main_w, main_h = main.get_size()
        _, sep_h = sep.get_size()
        _, sub_h = sub.get_size()
        moon_w, moon_h = moon.get_size()
        gear_w, _ = gear.get_size()

        comp_w = main_w + moon_w + gear_w + 8
        comp_h = main_h + LOGO_GAP + sep_h + LOGO_GAP + sub_h
        comp = pygame.Surface((comp_w, comp_h), pygame.SRCALPHA)

        moon_base_y = (main_h - moon_h) // 2
        main_x = moon_w + 4
        comp.blit(moon, (0 + MOON_OFFSET_X, moon_base_y + MOON_OFFSET_Y))
        comp.blit(main, (main_x, 0))
        comp.blit(gear, (main_x + main_w + 4 + GEAR_OFFSET_X, moon_base_y + GEAR_OFFSET_Y))

        sep_x = (comp_w - LOGO_SEP_W) // 2
        sep_y = main_h + LOGO_GAP
        comp.blit(sep, (sep_x, sep_y))

        sub_x = (comp_w - LOGO_SUB_W) // 2
        comp.blit(sub, (sub_x, sep_y + sep_h + LOGO_GAP))

        return comp

    # ── Assets & layout ────────────────────────────────────────────────────────

    def _load_assets(self) -> None:
        # Background — native 1280x720
        bg_raw = self._load_asset("01-menu_background.png")
        self._bg = pygame.transform.smoothscale(bg_raw, (self._sw, self._sh))

        # Logo composite
        self._logo_surf = self._build_logo_composite()

        # Save slot spritesheet — 2 states stacked vertically
        slot_sheet = self._load_asset("04-save_slot.png")
        slot_states: dict[str, pygame.Surface] = {}
        for i, state in enumerate(["idle", "hover"]):
            raw = slot_sheet.subsurface(pygame.Rect(0, i * SLOT_H_SRC, 1024, SLOT_H_SRC))
            slot_states[state] = pygame.transform.smoothscale(raw, (SLOT_W_DST, SLOT_H_DST))
        self._slot_states = slot_states

        # Load overlay panel
        panel_raw = self._load_asset("03-panel_background.png")
        self._panel_load = pygame.transform.smoothscale(panel_raw, (900, 480))

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

        # Scroll edge hover overlay (01-menu_scroll_on.png, 295x720)
        # "off" state is baked into the background — only load hover image
        self._scroll_on = pygame.transform.smoothscale(
            self._load_asset("01-menu_scroll_on.png"), (SCROLL_W, self._sh)
        )
        self._scroll_on_r = pygame.transform.flip(self._scroll_on, True, False)

    def _compute_layout(self) -> None:
        """Compute save slot rects for the load overlay."""
        ov_x = self._sw // 2 - 450
        ov_y = self._sh // 2 - 240
        self.slot_rects: list[pygame.Rect] = []
        for i in range(3):
            sx = ov_x + 450 - SLOT_W_DST // 2
            sy = ov_y + SLOT_PANEL_Y_START + i * SLOT_SPACING
            self.slot_rects.append(pygame.Rect(sx, sy, SLOT_W_DST, SLOT_H_DST))

    # ── Public API ─────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.Event) -> GameEvent | None:
        if self.state == "LOAD_MENU":
            return self._handle_load_menu(event)
        return self._handle_main_menu(event)

    def update(self, dt: float) -> None:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Track scroll edge hover
        if mouse_x < SCROLL_ZONE_W:
            self._hovered_scroll = "left"
        elif mouse_x > self._sw - SCROLL_ZONE_W:
            self._hovered_scroll = "right"
        else:
            self._hovered_scroll = None

        if self.state == "LOAD_MENU":
            self._hovered_slot = None
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint((mouse_x, mouse_y)):
                    self._hovered_slot = i
                    break

    def draw(self) -> None:
        self._screen.blit(self._bg, (0, 0))

        # Scroll edge overlays (behind logo)
        self._draw_scrolls()

        logo_x = (self._sw - self._logo_surf.get_width()) // 2
        self._screen.blit(self._logo_surf, (logo_x, LOGO_Y))

        if self.state == "LOAD_MENU":
            self._draw_load_overlay()

        self._draw_cursor()

    def _draw_scrolls(self) -> None:
        """Draw scroll hover overlay on the active edge only."""
        if self._hovered_scroll == "left":
            self._screen.blit(self._scroll_on, (0, 0))
        elif self._hovered_scroll == "right":
            self._screen.blit(self._scroll_on_r, (self._sw - SCROLL_W, 0))

    # ── Load overlay ───────────────────────────────────────────────────────────

    def _refresh_slots(self) -> None:
        """Reload slot data from SaveManager (call when entering LOAD_MENU)."""
        self._slots = self._save_manager.list_slots()

    def _draw_load_overlay(self) -> None:
        self._screen.blit(self._overlay, (0, 0))
        panel_rect = self._panel_load.get_rect(center=(self._sw // 2, self._sh // 2))
        self._screen.blit(self._panel_load, panel_rect)

        title = self._font.render("Charger une partie", True, (220, 200, 150))
        self._screen.blit(title, title.get_rect(midtop=(panel_rect.centerx, panel_rect.top + 50)))

        for i, (slot_rect, slot_info) in enumerate(zip(self.slot_rects, self._slots)):
            state = "hover" if self._hovered_slot == i else "idle"
            self._screen.blit(self._slot_states[state], slot_rect)
            self._draw_slot_content(slot_rect, i + 1, slot_info)

    def _draw_slot_content(
        self, rect: pygame.Rect, slot_id: int, info: SlotInfo | None
    ) -> None:
        if info is None:
            label = f"Emplacement {slot_id} — Vide"
            color = (140, 120, 100)
        else:
            label = f"Emplacement {slot_id} — {info.map_name}"
            color = (220, 200, 150)
        text = self._font_small.render(label, True, color)
        self._screen.blit(text, text.get_rect(midleft=(rect.x + 20, rect.centery)))

    def _draw_cursor(self) -> None:
        """Draw custom cursor on top of everything."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        self._screen.blit(img, mouse_pos)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _handle_main_menu(self, event: pygame.Event) -> GameEvent | None:
        """Stub — new menu interactions to be added here."""
        return None

    def _enter_load_menu(self) -> None:
        self.state = "LOAD_MENU"
        self._refresh_slots()

    def _enter_options(self) -> None:
        self.state = "OPTIONS"
        logging.info("TitleScreen: Options menu (stub)")

    def _handle_load_menu(self, event: pygame.Event) -> GameEvent | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "MAIN_MENU"
            return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        for i, rect in enumerate(self.slot_rects):
            if rect.collidepoint(event.pos):
                return GameEvent.load_game(i + 1)
        return None
