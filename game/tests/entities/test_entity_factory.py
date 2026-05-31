from unittest.mock import MagicMock, patch

import pygame


def _make_game():
    with patch("src.engine.game.Game._load_map"):
        from src.engine.game import Game

        return Game()


def _make_ef():
    from src.engine.entity_factory import EntityFactory

    game = MagicMock()
    game.visible_sprites = MagicMock()
    game.interactives = MagicMock()
    game.npcs = MagicMock()
    game.teleports_group = MagicMock()
    game.pickups = MagicMock()
    game.obstacles_group = MagicMock()
    game.world_state.get.return_value = None
    game.loot_table = MagicMock()
    game.audio_manager = MagicMock()
    game.tile_size = 32
    game.time_system = MagicMock()
    return EntityFactory(game)


class TestEntityFactoryCoverage:
    def test_get_property_nested_in_io_sprite(self):
        from src.engine.entity_factory import _get_property

        # L41: io has nested sprite
        result = _get_property({"interactive_object": {"sprite": {"color": "red"}}}, "color")
        assert result == "red"

    def test_get_property_top_level_sprite(self):
        from src.engine.entity_factory import _get_property

        # L45-47: top-level sprite dict
        result = _get_property({"sprite": {"depth": 2}}, "depth")
        assert result == 2

    def test_spawn_npc_restores_world_state(self):
        ef = _make_ef()
        ef.game.world_state.get.return_value = {
            "pos": [120.0, 80.0],
            "facing": "down",
        }
        ent = {"x": 100, "y": 100, "id": 42, "width": 32, "height": 32}
        with patch("src.engine.entity_factory.NPC") as MockNPC:
            inst = MagicMock()
            inst.element_id = "npc1"
            inst.pos = pygame.math.Vector2(100, 100)
            inst.target_pos = pygame.math.Vector2(100, 100)
            inst.rect = MagicMock()
            MockNPC.return_value = inst
            ef.spawn_npc(ent, {})
        assert inst.target_pos.x == 120.0

    def test_spawn_npc_passes_facing_direction(self):
        ef = _make_ef()
        ent = {"x": 100, "y": 100, "id": 42, "width": 32, "height": 32}
        props = {"facing_direction": "left", "sub_type": "static_npc"}
        with patch("src.engine.entity_factory.NPC") as MockNPC:
            inst = MagicMock()
            inst.element_id = "npc1"
            inst.pos = pygame.math.Vector2(100, 100)
            inst.target_pos = pygame.math.Vector2(100, 100)
            inst.rect = MagicMock()
            MockNPC.return_value = inst
            ef.spawn_npc(ent, props)
            # Verify MockNPC was called with facing_direction="left"
            args, kwargs = MockNPC.call_args
            assert kwargs.get("facing_direction") == "left"
            assert kwargs.get("sub_type") == "static_npc"

    def test_spawn_pickup_skips_collected(self):
        ef = _make_ef()
        ef.game.world_state.get.return_value = {"collected": True}
        ef.spawn_pickup({"x": 0, "y": 0, "id": 1}, {"element_id": "x", "item_id": "herb"})
        ef.game.pickups.add.assert_not_called()

    def test_spawn_pickup_restores_quantity(self):
        ef = _make_ef()
        ef.game.world_state.get.return_value = {"quantity": 7, "collected": False}
        ef.game._current_map_name = "test.tmj"
        props = {"object_id": "gem", "sprite_sheet": "gem.png", "quantity": 1}
        with patch("src.engine.entity_factory.PickupItem") as MockItem:
            MockItem.return_value = MagicMock()
            ef.spawn_pickup({"x": 0, "y": 0, "id": 2}, props)
            assert MockItem.called
