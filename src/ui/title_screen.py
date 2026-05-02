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

# Button spritesheet layout (measured from 02-menu_buttons.png 1024x182)
BTN_W_SRC = 341
BTN_H_SRC = 182
BTN_W_DST = 400
BTN_H_DST = 86
BTN_SPACING = 70          # px between button tops
BTN_Y_OFFSET = 80         # extra push downward to clear the logo

# Logo (00-title_logo.png 903x241)
LOGO_W_DST = 560
LOGO_Y = 60

# Save slot spritesheet (04-save_slot.png 1024x1024, 2 states stacked)
SLOT_H_SRC = 512
SLOT_W_DST = 800
SLOT_H_DST = 120
SLOT_SPACING = 140
SLOT_PANEL_Y_START = 140  # inside the panel overlay

# Semi-transparent overlay
OVERLAY_ALPHA = 180

_BUTTON_LABELS = ["Nouvelle Partie", "Charger", "Options", "Quitter"]


class TitleScreen:
    """Main menu screen with 4 buttons and a load-game overlay."""

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self.state = "MAIN_MENU"          # "MAIN_MENU" | "LOAD_MENU" | "OPTIONS"
        self._slots: list[SlotInfo | None] = [None, None, None]
        self._hovered_btn: int | None = None
        self._hovered_slot: int | None = None

        sw, sh = screen.get_size()
        self._sw = sw
        self._sh = sh

        self._load_assets()
        self._compute_layout()

    # ── Asset loading ──────────────────────────────────────────────────────────

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
        ratio = target_h / 535  # 535 is original pointer height
        target_w = int(309 * ratio)
        return pygame.transform.smoothscale(raw, (target_w, target_h))

    def _load_assets(self) -> None:
        # Background (scaled to full screen)
        bg_raw = self._load_asset("01-menu_background.png")
        self._bg = pygame.transform.smoothscale(bg_raw, (self._sw, self._sh))

        # Logo (colorkey for black background)
        logo_raw = self._load_asset("00-title_logo.png")
        logo_raw.set_colorkey((0, 0, 0))
        lw, lh = logo_raw.get_size()
        scale = LOGO_W_DST / lw
        logo_h_dst = int(lh * scale)
        self._logo = pygame.transform.smoothscale(logo_raw, (LOGO_W_DST, logo_h_dst))

        # Button spritesheet — 3 states side by side
        btn_sheet = self._load_asset("02-menu_buttons.png")
        btn_states: dict[str, pygame.Surface] = {}
        for i, state in enumerate(["idle", "hover", "pressed"]):
            raw = btn_sheet.subsurface(
                pygame.Rect(i * BTN_W_SRC, 0, BTN_W_SRC, BTN_H_SRC)
            )
            btn_states[state] = pygame.transform.smoothscale(
                raw, (BTN_W_DST, BTN_H_DST)
            )
        self._btn_states = btn_states

        # Save slot spritesheet — 2 states stacked vertically
        slot_sheet = self._load_asset("04-save_slot.png")
        slot_states: dict[str, pygame.Surface] = {}
        for i, state in enumerate(["idle", "hover"]):
            raw = slot_sheet.subsurface(
                pygame.Rect(0, i * SLOT_H_SRC, 1024, SLOT_H_SRC)
            )
            slot_states[state] = pygame.transform.smoothscale(
                raw, (SLOT_W_DST, SLOT_H_DST)
            )
        self._slot_states = slot_states

        # Panel overlay
        panel_raw = self._load_asset("03-panel_background.png")
        self._panel = pygame.transform.smoothscale(panel_raw, (900, 480))

        # Overlay surface (semi-transparent black)
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

        # Custom cursor (same assets as InventoryUI)
        self._pointer_img = self._load_cursor("05-pointer.png")
        self._pointer_select_img = self._load_cursor("06-pointer_select.png")
        pygame.mouse.set_visible(False)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _compute_layout(self) -> None:
        n = len(_BUTTON_LABELS)
        zone_h = (n - 1) * BTN_SPACING + BTN_H_DST
        y_start = (self._sh - zone_h) // 2 + BTN_Y_OFFSET
        x = (self._sw - BTN_W_DST) // 2

        self.button_rects: list[pygame.Rect] = []
        for i in range(n):
            self.button_rects.append(
                pygame.Rect(x, y_start + i * BTN_SPACING, BTN_W_DST, BTN_H_DST)
            )

        # Save slot rects (3 slots inside panel overlay)
        panel_rect = self._panel.get_rect(center=(self._sw // 2, self._sh // 2))
        self.slot_rects: list[pygame.Rect] = []
        for i in range(3):
            sx = panel_rect.centerx - SLOT_W_DST // 2
            sy = panel_rect.top + SLOT_PANEL_Y_START + i * SLOT_SPACING
            self.slot_rects.append(pygame.Rect(sx, sy, SLOT_W_DST, SLOT_H_DST))

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.Event) -> GameEvent | None:
        if self.state == "LOAD_MENU":
            return self._handle_load_menu(event)
        return self._handle_main_menu(event)

    def update(self, dt: float) -> None:
        mouse_pos = pygame.mouse.get_pos()
        if self.state == "MAIN_MENU":
            self._hovered_btn = None
            for i, rect in enumerate(self.button_rects):
                if rect.collidepoint(mouse_pos):
                    self._hovered_btn = i
                    break
        elif self.state == "LOAD_MENU":
            self._hovered_slot = None
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(mouse_pos):
                    self._hovered_slot = i
                    break

    def draw(self) -> None:
        self._screen.blit(self._bg, (0, 0))
        logo_x = (self._sw - LOGO_W_DST) // 2
        self._screen.blit(self._logo, (logo_x, LOGO_Y))

        self._draw_buttons()

        if self.state == "LOAD_MENU":
            self._draw_load_overlay()

        self._draw_cursor()

    def _refresh_slots(self) -> None:
        """Reload slot data from SaveManager (call when entering LOAD_MENU)."""
        self._slots = self._save_manager.list_slots()

    def _draw_cursor(self) -> None:
        """Draw custom cursor on top of everything."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        self._screen.blit(img, mouse_pos)

    # ── Private rendering ─────────────────────────────────────────────────────

    def _draw_buttons(self) -> None:
        for i, (rect, label) in enumerate(zip(self.button_rects, _BUTTON_LABELS)):
            state = "hover" if self._hovered_btn == i else "idle"
            self._screen.blit(self._btn_states[state], rect)
            text = self._font.render(label, True, (220, 200, 150))
            self._screen.blit(text, text.get_rect(center=rect.center))

    def _draw_load_overlay(self) -> None:
        self._screen.blit(self._overlay, (0, 0))
        panel_rect = self._panel.get_rect(center=(self._sw // 2, self._sh // 2))
        self._screen.blit(self._panel, panel_rect)

        title = self._font.render("Charger une partie", True, (220, 200, 150))
        self._screen.blit(
            title, title.get_rect(midtop=(panel_rect.centerx, panel_rect.top + 50))
        )

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

    # ── Event handlers ────────────────────────────────────────────────────────

    def _handle_main_menu(self, event: pygame.Event) -> GameEvent | None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        for i, rect in enumerate(self.button_rects):
            if not rect.collidepoint(event.pos):
                continue
            return self._on_button_click(i)
        return None

    def _on_button_click(self, index: int) -> GameEvent | None:
        actions = [
            GameEvent.new_game,           # 0 — Nouvelle Partie
            self._enter_load_menu,        # 1 — Charger
            self._enter_options,          # 2 — Options
            GameEvent.quit,               # 3 — Quitter
        ]
        return actions[index]()

    def _enter_load_menu(self) -> None:
        self.state = "LOAD_MENU"
        self._refresh_slots()
        return None

    def _enter_options(self) -> None:
        self.state = "OPTIONS"
        logging.info("TitleScreen: Options menu (stub)")
        return None

    def _handle_load_menu(self, event: pygame.Event) -> GameEvent | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "MAIN_MENU"
            return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        for i, rect in enumerate(self.slot_rects):
            if rect.collidepoint(event.pos):
                slot_id = i + 1
                return GameEvent.load_game(slot_id)
        return None
