# src/ui/inventory_protocol.py
"""Protocol defining the interface required by InventoryUI mixins."""

from typing import TYPE_CHECKING, Protocol

import pygame

if TYPE_CHECKING:
    from src.entities.player import Player


class InventoryUIProtocol(Protocol):
    """Protocol for InventoryUI mixin consumers."""

    is_open: bool
    active_tab: int
    player: "Player"

    bg: pygame.Surface
    bg_rect: pygame.Rect
    slot_img: pygame.Surface
    active_tab_img: pygame.Surface
    hover_img: pygame.Surface
    pointer_img: pygame.Surface
    pointer_select_img: pygame.Surface

    scale_factor: float
    tab_rects: list[pygame.Rect]
    equip_rect_side: int
    equipment_slots: dict[str, tuple[int, int]]
    grid_start: tuple[int, int]
    grid_cols: int
    grid_rows: int
    grid_spacing_x: int
    grid_spacing_y: int
    char_preview_pos: tuple[int, int]
    char_name_pos: tuple[int, int]

    anim_timer: float
    anim_frame: int
    preview_state: str
    hovered_slot: tuple[str, object] | None

    _dragging_item: dict | None
    _drag_pos: tuple[int, int]

    noble_font: pygame.font.Font
    narrative_font: pygame.font.Font
    tech_font: pygame.font.Font
    icon_cache: dict[str, pygame.Surface]

    def _get_item_icon(self, icon_filename: str) -> pygame.Surface | None: ...
