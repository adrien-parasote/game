"""
Save Menu UI Components.
Spec: docs/game/specs/save-system.md
"""

from pathlib import Path

import pygame

from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.i18n import I18nManager
from src.engine.save_manager import SaveManager, SlotInfo
from src.ui.save_menu_constants import (
    BACK_BTN_H,
    BACK_BTN_W,
    BACK_FONT_PATH,
    BACK_FONT_SIZE,
    BACK_HALO_COLOR,
    BACK_ICON_H,
    BACK_ICON_HOVER_H,
    BACK_ICON_HOVER_W,
    BACK_ICON_W,
    BACK_LABEL_GAP,
    BACK_TEXT_COLOR,
    ENGRAVE_LIGHT,
    ENGRAVE_SHADOW,
    ENGRAVE_TEXT,
    SAVE_DETAIL_COLOR,
    SAVE_HALO_BLUR_PADDING,
    SAVE_HALO_BLUR_RADIUS,
    SAVE_PANEL_FILL,
    SAVE_PANEL_H,
    SAVE_PANEL_W,
    SAVE_PANEL_Y_OFFSET,
    SAVE_SLOT_SPACING,
    SAVE_TITLE_COLOR,
)
from src.ui.save_slot import SaveSlotUI


class SaveMenuOverlay:
    """
    Overlay menu managing 3 save slots.
    Can be used for both Loading (TitleScreen) and Saving (PauseScreen).
    """

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager, title: str):
        self._screen = screen
        self._save_manager = save_manager
        self._title_text = title
        self._i18n = I18nManager()
        self._slots_info: list[SlotInfo | None] = [None, None, None]
        self._thumbnails: list[pygame.Surface | None] = [None, None, None]
        self._hovered_slot: int | None = None

        self._sw, self._sh = screen.get_size()

        # Load asset manager fonts
        am = AssetManager()
        self._font_title = am.get_font(
            Settings.FONT_NOBLE, int(Settings.FONT_SIZE_NOBLE * 1.5)
        )

        self._slot_ui = SaveSlotUI(am)

        # Semi-transparent background panel
        self._panel = pygame.Surface((SAVE_PANEL_W, SAVE_PANEL_H), pygame.SRCALPHA)
        self._panel.fill(SAVE_PANEL_FILL)

        # Cached title surfaces — populated in refresh(), one per slot
        self._cached_title_surfs: list[pygame.Surface | None] = [None, None, None]
        # Cached per-slot level / time text surfaces (populated in refresh())
        self._cached_level_surfs: list[pygame.Surface | None] = [None, None, None]
        self._cached_time_surfs: list[pygame.Surface | None] = [None, None, None]

        # Back button assets
        self._back_hovered = False
        self._back_offset_x = 10  # Default padding from left
        self._back_offset_y = 10  # Default padding from bottom
        self._load_back_assets()

        self._compute_layout()

    def _load_back_assets(self) -> None:
        """Load icon and font for the Back button. Pre-render idle/hover label surfaces."""
        path = str(Path("assets") / "images" / "menu" / "01-menu_back_cursor.png")
        raw = AssetManager().get_image(path, fallback=True)
        self._back_btn_icon = pygame.transform.smoothscale(raw, (BACK_ICON_W, BACK_ICON_H))
        self._back_btn_icon_hover = pygame.transform.smoothscale(
            raw, (BACK_ICON_HOVER_W, BACK_ICON_HOVER_H)
        )

        try:
            self._font_back = pygame.font.Font(BACK_FONT_PATH, BACK_FONT_SIZE)
        except OSError:
            self._font_back = pygame.font.SysFont(None, BACK_FONT_SIZE)

        # Pre-render back button label surfaces (idle + hover) — zero allocs in draw()
        label = self._i18n.get("menu.back", "Back")
        self._back_idle_surf: pygame.Surface = self._make_back_idle_surf(label)
        self._back_hover_surf: pygame.Surface = self._make_back_hover_surf(label)

    def _make_back_idle_surf(self, label: str) -> pygame.Surface:
        """Pre-render 3-pass engraved back-button label to a composite surface."""
        shadow = self._font_back.render(label, True, ENGRAVE_SHADOW)
        light = self._font_back.render(label, True, ENGRAVE_LIGHT)
        text = self._font_back.render(label, True, ENGRAVE_TEXT)
        w = text.get_width() + 2
        h = text.get_height() + 2
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.blit(shadow, (0, 0))
        out.blit(light, (2, 2))
        out.blit(text, (1, 1))
        return out

    def _make_back_hover_surf(self, label: str) -> pygame.Surface:
        """Pre-render halo glow + main text for the hovered back-button label."""
        base = self._font_back.render(label, True, BACK_HALO_COLOR)
        w, h = base.get_size()
        pad = SAVE_HALO_BLUR_PADDING
        padded = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        padded.blit(base, (pad, pad))
        out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        try:
            blurred = pygame.transform.gaussian_blur(padded, SAVE_HALO_BLUR_RADIUS)
            out.blit(blurred, (0, 0))
            out.blit(blurred, (0, 0))
        except AttributeError:
            base.set_alpha(80)
            for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3)]:
                out.blit(base, (pad + dx, pad + dy))
        main = self._font_back.render(label, True, BACK_TEXT_COLOR)
        out.blit(main, (pad, pad))
        return out

    def _compute_layout(self) -> None:

        slot_w, slot_h = self._slot_ui.get_size()
        spacing = SAVE_SLOT_SPACING
        total_h = (slot_h * 3) + (spacing * 2)

        start_y = (self._sh - total_h) // 2 + SAVE_PANEL_Y_OFFSET
        start_x = (self._sw - slot_w) // 2

        self.slot_rects = [
            pygame.Rect(start_x, start_y + i * (slot_h + spacing), slot_w, slot_h) for i in range(3)
        ]

        # Panel rect (shared with draw)
        self._panel_rect = pygame.Rect(
            self._sw // 2 - 300,
            max(0, self.slot_rects[0].y - 80),
            600,
            (self.slot_rects[-1].bottom - self.slot_rects[0].y + 120),
        )

        # Back button at bottom left of the panel
        self.back_btn_rect = pygame.Rect(
            self._panel_rect.left + self._back_offset_x,
            self._panel_rect.bottom - BACK_BTN_H - self._back_offset_y,
            BACK_BTN_W,
            BACK_BTN_H,
        )

    def refresh(self) -> None:
        """Re-read slot metadata and thumbnails from disk; pre-cache all text surfaces."""
        self._slots_info = self._save_manager.list_slots()
        self._cached_title_surfs = []
        self._cached_level_surfs = []
        self._cached_time_surfs = []
        for i in range(3):
            if self._slots_info[i] is not None:
                info = self._slots_info[i]
                assert info is not None  # narrow SlotInfo|None → SlotInfo for Pyright
                self._thumbnails[i] = self._save_manager.load_thumbnail(i + 1)

                # Pre-render overlay title
                display_name = info.map_display_name or ""
                self._cached_title_surfs.append(
                    self._font_title.render(display_name, True, SAVE_TITLE_COLOR)
                )
                # Pre-render detail level text
                level_str = self._i18n.get(
                    "save_menu.level", "Niveau: {level}"
                ).format(level=info.level)
                self._cached_level_surfs.append(
                    self._font_small.render(level_str, True, SAVE_DETAIL_COLOR)
                    if hasattr(self, "_font_small")
                    else None
                )
                # Pre-render detail time text
                hours = int(info.playtime_seconds // 3600)
                minutes = int((info.playtime_seconds % 3600) // 60)
                time_str = self._i18n.get(
                    "save_menu.time", "Temps: {hours:02d}h {minutes:02d}m"
                ).format(hours=hours, minutes=minutes)
                self._cached_time_surfs.append(
                    self._font_small.render(time_str, True, SAVE_DETAIL_COLOR)
                    if hasattr(self, "_font_small")
                    else None
                )
            else:
                self._thumbnails[i] = None
                self._cached_title_surfs.append(None)
                self._cached_level_surfs.append(None)
                self._cached_time_surfs.append(None)

    def update(self, dt: float) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self._hovered_slot = None
        for i, rect in enumerate(self.slot_rects):
            if rect.collidepoint(mouse_pos):
                self._hovered_slot = i
                break

        self._back_hovered = self.back_btn_rect.collidepoint(mouse_pos)

    def draw(self) -> None:
        # Draw background panel
        self._screen.blit(self._panel, self._panel_rect)

        # Draw title
        title_surf = self._font_title.render(self._title_text, True, SAVE_TITLE_COLOR)
        self._screen.blit(
            title_surf, title_surf.get_rect(midtop=(self._sw // 2, self._panel_rect.y + 20))
        )

        # Draw slots
        for i, rect in enumerate(self.slot_rects):
            self._slot_ui.draw(
                surface=self._screen,
                rect=rect,
                slot_id=i + 1,
                info=self._slots_info[i],
                thumbnail=self._thumbnails[i],
                is_hovered=(self._hovered_slot == i),
                cached_level_surf=self._cached_level_surfs[i]
                if i < len(self._cached_level_surfs)
                else None,
                cached_time_surf=self._cached_time_surfs[i]
                if i < len(self._cached_time_surfs)
                else None,
            )

        # Draw Back Button
        self._draw_back_button()

    def _draw_back_button(self) -> None:
        """Render the Back button at the bottom left of the panel using pre-rendered surfaces."""
        # Center of the button area for alignment
        cx = self.back_btn_rect.centerx
        cy = self.back_btn_rect.centery

        # Render icon (hover = slightly larger)
        icon = self._back_btn_icon_hover if self._back_hovered else self._back_btn_icon
        icon_w = icon.get_width()

        # Measure label width from pre-rendered surface
        label_surf = self._back_hover_surf if self._back_hovered else self._back_idle_surf
        label_w = label_surf.get_width()
        gap = BACK_LABEL_GAP

        total_w = icon_w + gap + label_w
        start_x = cx - total_w // 2

        # Draw icon
        icon_r = icon.get_rect(midleft=(start_x, cy))
        self._screen.blit(icon, icon_r)

        # Blit pre-rendered label surface — zero alloc in draw()
        text_cx = start_x + icon_w + gap + label_w // 2
        self._screen.blit(label_surf, label_surf.get_rect(center=(text_cx, cy)))

    def is_back_clicked(self, event: pygame.Event) -> bool:
        """Return True if the Back button was clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn_rect.collidepoint(event.pos):
                return True
        return False

    def get_clicked_slot(self, event: pygame.Event) -> int | None:
        """Return slot index (0, 1, 2) if clicked, else None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(event.pos):
                    return i
        return None
