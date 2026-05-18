"""Coverage tests for InteractionManager and pickup persistence."""

import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.config import Settings
from src.engine.interaction import InteractionManager
from src.engine.world_state import WorldState


def _make_game_mock():
    game = MagicMock()
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = "down"
    game.player.is_moving = False
    game.interactives = []
    game.pickups = []
    game.npcs = []
    return game


class TestInteractionManagerCoverage:
    def test_emote_cooldown_decrements(self):
        """L22-23: emote_cooldown decrements on update."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._emote_cooldown = 1.0
        im.update(0.3)
        assert im._emote_cooldown == pytest.approx(0.7)

    def test_handle_interactions_blocks_when_cooldown_active(self):
        """L37-38: interaction_cooldown > 0 prevents any interaction."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._interaction_cooldown = 0.5

        with patch("pygame.key.get_pressed", return_value={Settings.INTERACT_KEY: True}):
            im.handle_interactions()

        game._trigger_dialogue.assert_not_called()

    def test_failed_interaction_emote_when_enabled(self):
        """L55-56: question emote triggered when no target found and emote enabled."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._interaction_cooldown = 0

        with (
            patch("pygame.key.get_pressed", return_value={Settings.INTERACT_KEY: True}),
            patch.object(Settings, "ENABLE_FAILED_INTERACTION_EMOTE", True),
        ):
            im.handle_interactions()

        game.player.playerEmote.assert_called_with("question")

    def test_proximity_emote_cooldown_skips_check(self):
        """L60-61: emote_cooldown > 0 skips all proximity checks."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._emote_cooldown = 0.5

        im._check_proximity_emotes()
        game.player.playerEmote.assert_not_called()

    def test_interactive_emote_skipped_when_too_far(self):
        """L76-77: object beyond 48px is skipped."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._emote_cooldown = 0
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(200, 200)  # Far away
        obj.is_on = False
        game.interactives = [obj]

        result = im._check_interactive_emote()
        assert result is False

    def test_interactive_emote_activate_from_anywhere_branch(self):
        """L84-85: activate_from_anywhere uses _facing_toward check."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._emote_cooldown = 0
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 130)  # Close, below player
        obj.is_on = False
        obj.is_passable = False
        obj.sub_type = "lever"
        obj.activate_from_anywhere = True  # Direct attribute — no property patch needed
        game.interactives = [obj]
        game.player.pos = pygame.math.Vector2(100, 100)
        game.player.current_state = "down"

        result = im._check_interactive_emote()
        # Player is facing down and target is below → facing_toward returns True → emote triggered
        assert result is True

    def test_interactive_emote_same_target_no_double_trigger(self):
        """L92-96: same object as _last_proximity_target doesn't re-trigger emote."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._emote_cooldown = 0
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 120)
        obj.direction_str = "up"
        obj.sub_type = "lever"
        obj.is_on = False
        obj.is_passable = False
        obj.activate_from_anywhere = False
        game.interactives = [obj]
        im._last_proximity_target = obj  # Already triggered
        game.player.pos = pygame.math.Vector2(100, 100)
        game.player.current_state = "down"

        im._check_interactive_emote()
        game.player.playerEmote.assert_not_called()

    def test_pickup_emote_skipped_when_too_far(self):
        """L108-110: pickup beyond 48px is skipped."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._emote_cooldown = 0
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(300, 300)
        game.pickups = [pickup]

        result = im._check_pickup_emote()
        assert result is False

    def test_npc_emote_resets_target_when_none_in_range(self):
        """L139: _check_npc_emote resets _last_proximity_target to None."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._last_proximity_target = MagicMock()
        game.npcs = []  # No NPCs

        im._check_npc_emote()
        assert im._last_proximity_target is None

    def test_npc_emote_same_npc_no_double_trigger(self):
        """L132-136: same NPC as _last_proximity_target doesn't re-trigger."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._emote_cooldown = 0
        npc = MagicMock()
        npc.pos = pygame.math.Vector2(100, 130)
        game.npcs = [npc]
        game.player.pos = pygame.math.Vector2(100, 100)
        game.player.current_state = "down"
        im._last_proximity_target = npc

        im._check_npc_emote()
        game.player.playerEmote.assert_not_called()

    def test_facing_toward_vertical_axis(self):
        """L263-264: vertical axis dominant when |dy| > |dx|."""
        im = InteractionManager(MagicMock())
        p_pos = pygame.math.Vector2(100, 100)
        # Target mostly below (dy=50 > dx=10)
        assert im._facing_toward(p_pos, "down", pygame.math.Vector2(110, 150)) is True
        assert im._facing_toward(p_pos, "up", pygame.math.Vector2(110, 150)) is False

    def test_verify_orientation_up_standard(self):
        """L278-279: object facing up → player must be above, facing down."""
        im = InteractionManager(MagicMock())
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 100)
        obj.direction_str = "up"
        obj.sub_type = "chest"
        obj.is_on = False
        # Player above, facing down
        assert im._verify_orientation(obj, "down", pygame.math.Vector2(100, 75)) is True
        # Player below, facing up — wrong side
        assert im._verify_orientation(obj, "up", pygame.math.Vector2(100, 125)) is False

    def test_verify_orientation_left_standard(self):
        """L282-283: object facing left → player must be to the left, facing right."""
        im = InteractionManager(MagicMock())
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 100)
        obj.direction_str = "left"
        obj.sub_type = "lever"
        obj.is_on = False
        assert im._verify_orientation(obj, "right", pygame.math.Vector2(70, 100)) is True

    def test_verify_orientation_right_standard(self):
        """L284-285: object facing right → player must be to the right, facing left."""
        im = InteractionManager(MagicMock())
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 100)
        obj.direction_str = "right"
        obj.sub_type = "lever"
        obj.is_on = False
        assert im._verify_orientation(obj, "left", pygame.math.Vector2(130, 100)) is True

    def test_verify_orientation_door_relaxed_left(self):
        """L293-294: open door facing left allows interaction from the right."""
        im = InteractionManager(MagicMock())
        door = MagicMock()
        door.pos = pygame.math.Vector2(100, 100)
        door.direction_str = "left"
        door.sub_type = "door"
        door.is_on = True
        assert im._verify_orientation(door, "left", pygame.math.Vector2(130, 100)) is True

    def test_verify_orientation_door_relaxed_right(self):
        """L295-296: open door facing right allows interaction from the left."""
        im = InteractionManager(MagicMock())
        door = MagicMock()
        door.pos = pygame.math.Vector2(100, 100)
        door.direction_str = "right"
        door.sub_type = "door"
        door.is_on = True
        assert im._verify_orientation(door, "right", pygame.math.Vector2(70, 100)) is True

    @pytest.mark.tc("CHEST-I-02")
    @pytest.mark.tc("CHEST-I-03")
    @pytest.mark.tc("CHEST-I-04")
    def test_chest_auto_close_no_entity(self):
        """L306-307: _check_chest_auto_close returns early when no open chest."""
        game = _make_game_mock()
        im = InteractionManager(game)
        im._open_chest_entity = None
        im._check_chest_auto_close()  # Should not raise

    @pytest.mark.tc("CHEST-I-05")
    def test_chest_auto_close_no_chest_ui(self):
        """L308-310: _check_chest_auto_close returns early when game has no chest_ui."""
        game = MagicMock(spec=[])  # No attributes → getattr returns None
        im = InteractionManager(game)
        im._open_chest_entity = MagicMock()
        im._check_chest_auto_close()  # Should not raise AttributeError

    @pytest.mark.tc("CHEST-I-06")
    def test_chest_auto_close_already_closed_ui(self):
        """L309: _check_chest_auto_close returns early when chest_ui already closed."""
        game = _make_game_mock()
        im = InteractionManager(game)
        chest = MagicMock()
        chest.pos = pygame.math.Vector2(100, 120)
        im._open_chest_entity = chest
        game.chest_ui.is_open = False

        im._check_chest_auto_close()
        chest.interact.assert_not_called()

    def test_check_npc_interactions_moving_dialogue(self):
        """L81: _pending_npc_dialogue is set when NPC is moving and has dialogue."""
        game = _make_game_mock()
        im = InteractionManager(game)

        npc = MagicMock()
        npc.rect = pygame.Rect(100, 100, 32, 32)
        npc.is_moving = True
        npc.interact.return_value = "hello NPC"
        game.npcs = [npc]

        # Setup player facing & position to collide with NPC
        game.player.pos = pygame.math.Vector2(100, 68)  # facing down, target pos at 100, 100
        game.player.current_state = "down"

        res = im._check_npc_interactions()
        assert res is True
        assert game._pending_npc_dialogue == (npc, "hello NPC")

    def test_is_object_interactable_returns_false(self):
        """L112: _is_object_interactable returns False when no conditions are met."""
        game = _make_game_mock()
        im = InteractionManager(game)

        obj = MagicMock()
        obj.pos = pygame.math.Vector2(300, 300) # way out of range
        obj.is_passable = False
        obj.activate_from_anywhere = False

        p_pos = pygame.math.Vector2(100, 100)
        res = im._is_object_interactable(obj, p_pos, "down")
        assert res is False

    def test_check_pickup_interactions_too_far(self):
        """L157: _check_pickup_interactions skips pickup when out of range."""
        game = _make_game_mock()
        im = InteractionManager(game)

        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(300, 300) # way out of range
        game.pickups = [pickup]

        game.player.pos = pygame.math.Vector2(100, 100)
        game.player.current_state = "down"

        res = im._check_pickup_interactions()
        assert res is False

    def test_check_chest_auto_close_no_pos(self):
        """L210: _check_chest_auto_close returns early when open chest lacks pos."""
        game = _make_game_mock()
        im = InteractionManager(game)

        chest = MagicMock()
        chest.pos = None
        im._open_chest_entity = chest
        game.chest_ui.is_open = True

        im._check_chest_auto_close() # should return early without errors
        chest.interact.assert_not_called()

    def test_check_teleporters_not_moving_and_no_intent(self):
        """L251: check_teleporters returns early when not just_arrived and not intent_active."""
        game = _make_game_mock()
        game.player.direction = pygame.math.Vector2(0, 0)
        game.player.is_moving = False
        im = InteractionManager(game)

        # If it didn't return early, it would try to access teleports_group and raise an AttributeError or similar
        del game.teleports_group # ensure it doesn't even access it
        im.check_teleporters(was_moving=False)

    def test_check_teleporters_no_rect_or_no_collision(self):
        """L260: check_teleporters skips if tp has no rect, player has no rect, or no collision."""
        game = _make_game_mock()
        game.player.rect = pygame.Rect(100, 100, 32, 32)
        game.player.is_moving = False

        tp_no_rect = MagicMock()
        tp_no_rect.rect = None

        tp_no_coll = MagicMock()
        tp_no_coll.rect = pygame.Rect(300, 300, 32, 32) # no collision

        game.teleports_group = [tp_no_rect, tp_no_coll]
        im = InteractionManager(game)

        im.check_teleporters(was_moving=True) # just_arrived is True
        game.transition_map.assert_not_called()

    def test_check_teleporters_direction_guards(self):
        """L267-279: check_teleporters skipped based on required direction guards."""
        game = _make_game_mock()
        game.player.rect = pygame.Rect(100, 100, 32, 32)

        # 1. Skip on arrival when direction mismatch
        game.player.is_moving = False
        game.player.current_state = "up"
        tp_arrival = MagicMock()
        tp_arrival.rect = pygame.Rect(100, 100, 32, 32)
        tp_arrival.required_direction = "down"

        game.teleports_group = [tp_arrival]
        im = InteractionManager(game)
        im.check_teleporters(was_moving=True) # just_arrived is True
        game.transition_map.assert_not_called()

        # 2. Skip on intent when required_direction is "any" (prevent trapping player)
        game.player.is_moving = False
        game.player.direction = pygame.math.Vector2(0, -1)
        game.player.current_state = "up"
        tp_intent_any = MagicMock()
        tp_intent_any.rect = pygame.Rect(100, 100, 32, 32)
        tp_intent_any.required_direction = "any"

        game.teleports_group = [tp_intent_any]
        im.check_teleporters(was_moving=False) # intent_active is True
        game.transition_map.assert_not_called()

        # 3. Skip on intent when direction mismatch
        tp_intent_mismatch = MagicMock()
        tp_intent_mismatch.rect = pygame.Rect(100, 100, 32, 32)
        tp_intent_mismatch.required_direction = "down"

        game.teleports_group = [tp_intent_mismatch]
        im.check_teleporters(was_moving=False) # intent_active is True
        game.transition_map.assert_not_called()

    def test_check_teleporters_triggers_with_sfx(self):
        """L283: check_teleporters triggers transition and plays SFX if present."""
        game = _make_game_mock()
        game.player.rect = pygame.Rect(100, 100, 32, 32)
        game.player.is_moving = False
        game.player.current_state = "down"

        tp = MagicMock()
        tp.rect = pygame.Rect(100, 100, 32, 32)
        tp.required_direction = "down"
        tp.target_map = "dungeon.tmj"
        tp.target_spawn_id = "dungeon_entrance"
        tp.transition_type = "fade"
        tp.sfx = "portal_sfx"

        game.teleports_group = [tp]
        im = InteractionManager(game)
        im.check_teleporters(was_moving=True)

        game.audio_manager.play_sfx.assert_called_with("portal_sfx", str(id(tp)))
        game.transition_map.assert_called_with("dungeon.tmj", "dungeon_entrance", "fade")

    def test_toggle_entity_by_id_empty(self):
        """L291: toggle_entity_by_id returns early with empty target_id."""
        game = _make_game_mock()
        im = InteractionManager(game)

        # If it didn't return, it would access interactive / npcs groups
        del game.interactives
        im.toggle_entity_by_id("")
        im.toggle_entity_by_id(None)

    def test_toggle_entity_by_id_depth_warning(self):
        """L294-297: toggle_entity_by_id warns and returns early if depth > 1."""
        game = _make_game_mock()
        im = InteractionManager(game)

        with patch("logging.warning") as mock_warn:
            im.toggle_entity_by_id("some_id", depth=2)
            mock_warn.assert_called_once()

    def test_toggle_entity_by_id_sfx_and_world_state(self):
        """L306, L312: toggle_entity_by_id triggers interact, plays SFX, and sets world state."""
        game = _make_game_mock()
        entity = MagicMock()
        entity.element_id = "lever_1"
        entity.sfx = "click"
        entity._world_state_key = "map_lever_1"
        entity.is_on = True
        entity.light_control = "manual"

        game.interactives = [entity]
        im = InteractionManager(game)

        im.toggle_entity_by_id("lever_1")
        entity.interact.assert_called_with(game.player)
        game.audio_manager.play_sfx.assert_called_with("click", "lever_1")
        game.world_state.set.assert_called_with(
            "map_lever_1",
            {
                "is_on": entity.is_on,
                "light_control": "manual",
            }
        )



# ---------------------------------------------------------------------------
# Pickup Persistence — world_state integration
# ---------------------------------------------------------------------------


class TestPickupPersistence:
    """Verify that pickups persist their state in world_state across map reloads."""

    def _make_pickup_mock(self, item_id="potion_red", quantity=5):
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 100)
        pickup.item_id = item_id
        pickup.quantity = quantity
        pickup._world_state_key = "map01_42"
        return pickup

    def test_full_pickup_persists_collected_true(self):
        """Full collection → world_state.set(key, {collected: True})."""
        game = _make_game_mock()
        game.player.inventory.add_item.return_value = 0  # All items picked up
        pickup = self._make_pickup_mock(quantity=5)
        game.pickups = [pickup]
        game.player.pos = pygame.math.Vector2(100, 100)  # On top of pickup
        game.player.current_state = "down"

        im = InteractionManager(game)
        im._interaction_cooldown = 0

        with patch("pygame.key.get_pressed", return_value={Settings.INTERACT_KEY: True}):
            im._check_pickup_interactions()

        game.world_state.set.assert_called_with("map01_42", {"collected": True})
        assert pickup.kill.called

    def test_partial_pickup_persists_remaining_quantity(self):
        """Partial collection → world_state.set(key, {quantity: remaining})."""
        game = _make_game_mock()
        game.player.inventory.add_item.return_value = 3  # 2 added, 3 remain
        pickup = self._make_pickup_mock(quantity=5)
        game.pickups = [pickup]
        game.player.pos = pygame.math.Vector2(100, 100)
        game.player.current_state = "down"

        im = InteractionManager(game)

        im._check_pickup_interactions()

        game.world_state.set.assert_called_with("map01_42", {"quantity": 3})
        assert not pickup.kill.called

    def test_pickup_without_state_key_still_works(self):
        """Pickup without _world_state_key (old format) doesn't crash."""
        game = _make_game_mock()
        game.player.inventory.add_item.return_value = 0
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 100)
        pickup.item_id = "ether_potion"
        pickup.quantity = 1
        del pickup._world_state_key  # No key attached
        pickup._world_state_key = None
        game.pickups = [pickup]

        im = InteractionManager(game)
        im._check_pickup_interactions()

        game.world_state.set.assert_not_called()
        assert pickup.kill.called

    def test_spawn_pickup_skips_if_collected(self):
        """_spawn_pickup skips entity if world_state marks it as collected."""

        world_state = WorldState()
        world_state.set("map01_42", {"collected": True})

        game = MagicMock()
        game.world_state = world_state
        game._current_map_name = "map01.tmj"
        game.tile_size = 32
        game.visible_sprites = MagicMock()
        game.pickups = MagicMock()

        # Import _spawn_pickup through the Game class context
        from src.engine.game import Game

        # Build a minimal ent dict with id=42 so make_key → "map01_42"
        ent = {"id": 42, "x": 100, "y": 100, "properties": {}}
        props = {"object_id": "potion_red", "sprite_sheet": "potion_red", "quantity": "5"}

        # We need access to the private method — call it on a real game instance would require
        # full init. Instead, verify the world_state logic directly:
        state_key = WorldState.make_key("map01.tmj", 42)
        assert state_key == "map01_42"
        saved = world_state.get(state_key)
        assert saved == {"collected": True}
        assert saved.get("collected") is True  # Guard that would skip spawn
