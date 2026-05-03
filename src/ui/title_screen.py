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
from src.engine.i18n import I18nManager

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
LOGO_ZONE_W = 720          # left panel width — logo is centered within this zone
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

# Right panel scroll banner — position of text centre inside the parchment
# Adjust offsets to reposition without touching draw logic
SCROLL_TITLE_X = 1000      # centre-x of the scroll text zone (pixels)
SCROLL_TITLE_Y = 80       # centre-y of the scroll text zone (pixels)
SCROLL_TITLE_OFFSET_X = 0  # fine-tune x  (>0 right, <0 left)
SCROLL_TITLE_OFFSET_Y = 0  # fine-tune y  (>0 down,  <0 up)
SCROLL_TITLE_FONT_SIZE = 50  # taille de la police du titre menu (px)
SCROLL_TITLE_FONT_PATH = "assets/fonts/cormorant-garamond-regular.ttf"  # police du scroll titre
SCROLL_TITLE_COLOR = (72, 40, 12)   # encre sépia — accordé au parchemin RGB(211,186,145)

# Right panel — menu items (Pillow analysis of 01-menu_background.png)
# Panel bounds: x=786-1225, y=250-680  |  fond RGB(37,54,58) sombre bleu
# Zone texte (hors bordure 40px): x=826-1185, y=290-650
MENU_ITEM_X = 1005          # centre-x des items (centre zone texte)
MENU_ITEM_Y_START = 360     # y du premier item
MENU_ITEM_SPACING = 80      # espacement vertical entre items
MENU_ITEM_FONT_SIZE = 38    # taille police items (px)
MENU_ITEM_COLOR = (220, 195, 140)        # doré chaud au hover
MENU_ITEM_HOVER_COLOR = (255, 235, 180)  # doré lumineux au hover (inchangé)
MENU_ITEM_OFFSET_X = 0      # décalage fin x
MENU_ITEM_OFFSET_Y = 0      # décalage fin y
# Effet "gravé dans la roche" pour l'état idle
# Fond pierre RGB(37,54,58) — 3 passes : ombre | reflet | texte
MENU_ENGRAVE_TEXT   = (58, 85, 92)   # texte : légèrement plus clair que pierre
MENU_ENGRAVE_SHADOW = (12, 20, 23)   # ombre (bas-droite +1,+2) : fond de la gravure
MENU_ENGRAVE_LIGHT  = (75, 105, 112) # reflet (haut-gauche -1,-1) : bord éclairé

_MENU_ITEM_KEYS = ["menu.new_game", "menu.load", "menu.options", "menu.quit"]
_MENU_ITEM_DEFAULTS = ["Nouvelle Partie", "Charger", "Options", "Quitter"]

# Options back button — 01-menu_back_cursor.png (asset: 57x51, ratio 1.12)
# Positioné en bas-centre du panel (x=786-1225, y=250-680)
BACK_BTN_W = 114          # largeur de rendu (2× native 57px)
BACK_BTN_H = 102          # hauteur de rendu (2× native 51px)
BACK_BTN_X = 1005         # centre-x (même axe que les items)
BACK_BTN_Y = 620          # centre-y (bas du panel)
BACK_BTN_OFFSET_X = 0     # décalage fin x
BACK_BTN_OFFSET_Y = 0     # décalage fin y


class TitleScreen:
    """Main menu screen — background, logo, cursor. Menu to be added."""

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager) -> None:
        self._screen = screen
        self._save_manager = save_manager
        self.state = "MAIN_MENU"          # "MAIN_MENU" | "LOAD_MENU"
        self._slots: list[SlotInfo | None] = [None, None, None]
        self._hovered_slot: int | None = None
        self._hovered_item: int | None = None
        self._i18n = I18nManager()

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

        # Load overlay panel (semi-transparent black, pas de spritesheet)
        self._panel_load = pygame.Surface((900, 480))
        self._panel_load.set_alpha(200)
        self._panel_load.fill((10, 18, 22))

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
            self._scroll_title_font = pygame.font.Font(SCROLL_TITLE_FONT_PATH, SCROLL_TITLE_FONT_SIZE)
            self._menu_item_font = pygame.font.Font(SCROLL_TITLE_FONT_PATH, MENU_ITEM_FONT_SIZE)
        except OSError:
            logging.warning("TitleScreen: Cormorant Garamond not found, falling back to Noble font")
            self._scroll_title_font = self._font
            self._menu_item_font = self._font

        # Options back button — 01-menu_back_cursor.png
        back_raw = self._load_asset("01-menu_back_cursor.png")
        self._back_btn = pygame.transform.smoothscale(back_raw, (BACK_BTN_W, BACK_BTN_H))
        self._back_btn_hover = pygame.transform.smoothscale(
            back_raw, (BACK_BTN_W + 8, BACK_BTN_H + 7)
        )

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
        # Back button rect (OPTIONS state)
        bcx = BACK_BTN_X + BACK_BTN_OFFSET_X
        bcy = BACK_BTN_Y + BACK_BTN_OFFSET_Y
        self.back_btn_rect = pygame.Rect(
            bcx - BACK_BTN_W // 2, bcy - BACK_BTN_H // 2, BACK_BTN_W, BACK_BTN_H
        )
        self._back_hovered: bool = False
        # Save slot rects (inside the load overlay panel, 900x480 centered)
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
        if self.state == "OPTIONS":
            return self._handle_options(event)
        return self._handle_main_menu(event)

    def update(self, dt: float) -> None:
        mouse_pos = pygame.mouse.get_pos()
        if self.state == "MAIN_MENU":
            self._hovered_item: int | None = None
            for i, rect in enumerate(self.menu_item_rects):
                if rect.collidepoint(mouse_pos):
                    self._hovered_item = i
                    break
        elif self.state == "LOAD_MENU":
            self._hovered_slot = None
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(mouse_pos):
                    self._hovered_slot = i
                    break
        elif self.state == "OPTIONS":
            self._back_hovered = self.back_btn_rect.collidepoint(mouse_pos)

    def draw(self) -> None:
        self._screen.blit(self._bg, (0, 0))

        logo_x = (LOGO_ZONE_W - self._logo_surf.get_width()) // 2
        self._screen.blit(self._logo_surf, (logo_x, LOGO_Y))

        self._draw_scroll_title()

        if self.state == "MAIN_MENU":
            self._draw_menu_items()
        elif self.state == "LOAD_MENU":
            self._draw_load_overlay()
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
                surf = self._menu_item_font.render(label, True, MENU_ITEM_HOVER_COLOR)
                self._screen.blit(surf, surf.get_rect(center=(cx, cy)))
            else:
                self._blit_engraved(label, cx, cy)

    def _blit_engraved(self, label: str, cx: int, cy: int) -> None:
        """3-pass engraved-in-stone text effect.

        Pass 1 — ombre (bas-droite) : simule le fond sombre de la gravure.
        Pass 2 — reflet (haut-gauche) : simule la luz sur le bord supérieur.
        Pass 3 — texte principal : légèrement plus clair que la pierre.
        """
        shadow = self._menu_item_font.render(label, True, MENU_ENGRAVE_SHADOW)
        light  = self._menu_item_font.render(label, True, MENU_ENGRAVE_LIGHT)
        text   = self._menu_item_font.render(label, True, MENU_ENGRAVE_TEXT)
        r = text.get_rect(center=(cx, cy))
        self._screen.blit(shadow, r.move(1, 2))
        self._screen.blit(light,  r.move(-1, -1))
        self._screen.blit(text,   r)

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

    def _draw_scroll_title(self) -> None:
        """Render the menu title on the right panel scroll banner."""
        label = self._i18n.get("menu.title", default="Menu")
        text_surf = self._scroll_title_font.render(label, True, SCROLL_TITLE_COLOR)
        cx = SCROLL_TITLE_X + SCROLL_TITLE_OFFSET_X
        cy = SCROLL_TITLE_Y + SCROLL_TITLE_OFFSET_Y
        self._screen.blit(text_surf, text_surf.get_rect(center=(cx, cy)))

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
        """Draw options panel with back button. Options content is a stub."""
        btn = self._back_btn_hover if self._back_hovered else self._back_btn
        r = btn.get_rect(center=(
            BACK_BTN_X + BACK_BTN_OFFSET_X,
            BACK_BTN_Y + BACK_BTN_OFFSET_Y,
        ))
        self._screen.blit(btn, r)

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
