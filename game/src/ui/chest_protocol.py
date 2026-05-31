# src/ui/chest_protocol.py
"""Protocol defining the interface required by Chest mixins."""

from typing import TYPE_CHECKING, Protocol

import pygame

if TYPE_CHECKING:
    from src.entities.interactive import InteractiveEntity
    from src.entities.player import Player


class ChestUIProtocol(Protocol):
    """Protocol for ChestUI components."""

    is_open: bool
    _chest_entity: "InteractiveEntity | None"
    _player: "Player | None"
    _dragging_item: dict | None
    _drag_pos: tuple[int, int]
    _inv_offset: int

    _bg: pygame.Surface | None
    _inv_bg: pygame.Surface | None
    _bg_rect: pygame.Rect | None
    _title_rect: pygame.Rect | None
    _content_rect: pygame.Rect | None
    _inv_bg_rect: pygame.Rect | None

    _slot_positions: list[pygame.Rect]
    _inv_slot_positions: list[pygame.Rect]

    _hovered_chest_slot: int | None
    _hovered_inv_slot: int | None
    _hovered_chest_arrow: str | None
    _hovered_inv_arrow: str | None

    _qty_font: pygame.font.Font | None
    _slot_img: pygame.Surface | None
    _hover_img: pygame.Surface | None

    _arrow_up_rect: pygame.Rect | None
    _arrow_down_rect: pygame.Rect | None
    _inv_arrow_left_rect: pygame.Rect | None
    _inv_arrow_right_rect: pygame.Rect | None

    _arrow_up_hover_img: pygame.Surface | None
    _arrow_down_hover_img: pygame.Surface | None
    _arrow_left_hover_img: pygame.Surface | None
    _arrow_right_hover_img: pygame.Surface | None

    _pointer_img: pygame.Surface | None
    _pointer_select_img: pygame.Surface | None
    _layout_computed: bool

    def _get_chest_contents(self) -> list: ...
    def _get_item_icon(self, icon_filename: str, slot_size: int) -> pygame.Surface | None: ...
    def _capacity(self) -> int: ...
    def _can_scroll_left(self) -> bool: ...
    def _can_scroll_right(self) -> bool: ...
    def _resolve_icon_name(self, item_id: str) -> str: ...
    def _load_and_scale_arrow(self, path: str, scale: float) -> pygame.Surface | None: ...
    def _current_page_slots(self) -> list: ...
    def _compute_inv_layout(
        self, slot_size: int, step: int, screen_w: int, screen_h: int, arrow_scale: float
    ) -> None: ...
