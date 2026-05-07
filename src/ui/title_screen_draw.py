# src/ui/title_screen_draw.py
"""Drawing mixin for TitleScreen — handles text rendering helpers and menu item display."""

import pygame

from src.ui.title_screen_constants import (
    _MENU_ITEM_DEFAULTS,
    _MENU_ITEM_KEYS,
    BACK_BTN_GAP,
    BACK_BTN_LABEL_DEFAULT,
    BACK_BTN_LABEL_KEY,
    BACK_BTN_OFFSET_X,
    BACK_BTN_OFFSET_Y,
    BACK_BTN_X,
    BACK_BTN_Y,
    MENU_ENGRAVE_LIGHT,
    MENU_ENGRAVE_SHADOW,
    MENU_ENGRAVE_TEXT,
    MENU_HOVER_COLOR,
    MENU_HOVER_HALO,
    MENU_ITEM_OFFSET_X,
    MENU_ITEM_OFFSET_Y,
    MENU_ITEM_SPACING,
    MENU_ITEM_X,
    MENU_ITEM_Y_START,
)


class TitleDrawMixin:
    """Mixin handling text rendering helpers and menu item display for TitleScreen."""

    def _draw_menu_items(self) -> None:
        """Render menu items: pre-rendered engraved idle, halo text on hover."""
        hovered = self._hovered_item

        # P3: Invalidate blur cache only when hover changes
        if hovered != self._prev_hovered_item:
            self._blur_cache.pop(self._prev_hovered_item, None)
            self._prev_hovered_item = hovered

        for i, (key, default) in enumerate(zip(_MENU_ITEM_KEYS, _MENU_ITEM_DEFAULTS, strict=False)):
            cx = MENU_ITEM_X + MENU_ITEM_OFFSET_X
            cy = MENU_ITEM_Y_START + MENU_ITEM_OFFSET_Y + i * MENU_ITEM_SPACING
            if hovered == i:
                # P3: Cache the blur surface for this item
                if i not in self._blur_cache:
                    label = self._i18n.get(key, default=default)
                    self._blur_cache[i] = self._render_halo_text(
                        label, self._menu_item_font, MENU_HOVER_COLOR, MENU_HOVER_HALO
                    )
                surf = self._blur_cache[i]
                w, h = surf.get_size()
                self._screen.blit(surf, (cx - w // 2, cy - h // 2))
            else:
                # P3: Use pre-rendered idle surface
                surf = self._menu_label_surfaces[i]
                w, h = surf.get_size()
                self._screen.blit(surf, (cx - w // 2, cy - h // 2))

    def _render_halo_text(
        self,
        label: str,
        font: pygame.font.Font,
        text_color: tuple[int, int, int],
        halo_color: tuple[int, int, int],
    ) -> pygame.Surface:
        """Render text with halo blur and return composited Surface."""
        base_surf = font.render(label, True, halo_color)
        w, h = base_surf.get_size()
        pad = 24
        padded = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        padded.blit(base_surf, (pad, pad))
        try:
            blurred = pygame.transform.gaussian_blur(padded, 8)
        except Exception:
            blurred = padded
        out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        out.blit(blurred, (0, 0))
        text_surf = font.render(label, True, text_color)
        out.blit(text_surf, (pad, pad))
        return out

    def _render_engraved(self, label: str) -> pygame.Surface:
        """Render idle engraved stone effect and return composited Surface."""
        w_hint, h_hint = self._menu_item_font.size(label)
        pad = 4
        out = pygame.Surface((w_hint + pad * 2, h_hint + pad * 2), pygame.SRCALPHA)
        shadow = self._menu_item_font.render(label, True, MENU_ENGRAVE_SHADOW)
        highlight = self._menu_item_font.render(label, True, MENU_ENGRAVE_LIGHT)
        text = self._menu_item_font.render(label, True, MENU_ENGRAVE_TEXT)
        out.blit(shadow, (pad - 1, pad - 1))
        out.blit(highlight, (pad + 1, pad + 1))
        out.blit(text, (pad, pad))
        return out

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

    def _blit_engraved(
        self, label: str, cx: int, cy: int, font: pygame.font.Font | None = None
    ) -> None:
        """3-pass engraved-in-stone text effect.

        Pass 1 — shadow (bottom-right): simulates the dark background of the engraving.
        Pass 2 — highlight (top-left): simulates light on the upper edge.
        Pass 3 — main text: slightly lighter than the stone.
        Uses self._menu_item_font by default; pass a custom font to override.
        """
        f = font if font is not None else self._menu_item_font
        shadow = f.render(label, True, MENU_ENGRAVE_SHADOW)
        light = f.render(label, True, MENU_ENGRAVE_LIGHT)
        text = f.render(label, True, MENU_ENGRAVE_TEXT)
        r = text.get_rect(center=(cx, cy))
        self._screen.blit(shadow, r.move(-1, -1))
        self._screen.blit(light, r.move(1, 1))
        self._screen.blit(text, r)

    def _draw_cursor(self) -> None:
        """Draw custom cursor on top of everything."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        self._screen.blit(img, mouse_pos)

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
            self._blit_halo_text(
                label, label_cx, cy, self._back_label_font, MENU_HOVER_COLOR, MENU_HOVER_HALO
            )
        else:
            self._blit_engraved(label, label_cx, cy, font=self._back_label_font)
