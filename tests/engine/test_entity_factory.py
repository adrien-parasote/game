"""Tests for entity_factory.py missing branch (line 258: saved quantity restore)."""

import pytest
from unittest.mock import MagicMock, patch

import pygame


def _make_game():
    game = MagicMock()
    game.tile_size = 32
    game.visible_sprites = MagicMock()
    game.pickups = MagicMock()
    game._current_map_name = "test_map.tmj"
    return game


class TestSpawnPickupQuantityRestore:
    def test_spawn_pickup_restores_quantity_from_world_state(self):
        """Ligne 260 : quand saved['quantity'] existe, quantity est écrasée par saved value."""
        from src.engine.entity_factory import EntityFactory

        game = _make_game()
        game.world_state.get.return_value = {"quantity": 3}  # collected=False, quantity=3

        factory = EntityFactory(game)

        ent = {"id": 42, "x": 64, "y": 64, "properties": {
            "entity_type": "object",
            "object_id": "herb",
            "sprite_sheet": "herb.png",
            "quantity": 10,  # sera remplacé par 3 depuis world_state
        }}
        props = ent["properties"]

        surf = pygame.Surface((32, 32))
        with patch("src.engine.entity_factory.PickupItem") as MockPickup:
            MockPickup.return_value = MagicMock()
            factory.spawn_pickup(ent, props)
            # Vérifier que PickupItem a été appelé avec quantity=3 (depuis world_state)
            call_kwargs = MockPickup.call_args[1]
            assert call_kwargs["quantity"] == 3

    def test_spawn_pickup_skips_when_collected(self):
        """saved['collected'] = True → spawn_pickup retourne immédiatement."""
        from src.engine.entity_factory import EntityFactory

        game = _make_game()
        game.world_state.get.return_value = {"collected": True}

        factory = EntityFactory(game)
        ent = {"id": 10, "x": 64, "y": 64, "properties": {
            "entity_type": "object",
            "object_id": "coin",
            "sprite_sheet": "coin.png",
            "quantity": 1,
        }}

        with patch("src.engine.entity_factory.PickupItem") as MockPickup:
            factory.spawn_pickup(ent, ent["properties"])
            MockPickup.assert_not_called()
