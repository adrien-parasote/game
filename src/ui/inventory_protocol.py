# src/ui/inventory_protocol.py
from typing import Protocol, Any
import pygame

class InventoryUIProtocol(Protocol):
    is_open: bool
    active_tab: int
    tab_rects: list[pygame.Rect]
    hovered_slot: tuple[str, Any] | None
    player: Any
    _dragging_item: dict | None
    _drag_pos: tuple[int, int]
    preview_state: str
    
    def set_tab(self, index: int) -> None: ...
    def update_hover(self, mouse_pos: tuple[int, int]) -> None: ...
