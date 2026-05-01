"""Tests for InteractionManager — proximity, orientation, diagonals, chest flow."""
import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.interaction import InteractionManager
from src.config import Settings
from src.entities.player import Player


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def interaction_setup():
    """Shared game + InteractionManager for diagonal/orthogonal tests."""
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0

    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.player.inventory.add_item.return_value = 0

    return game, im


# ---------------------------------------------------------------------------
# Cooldown & basic state
# ---------------------------------------------------------------------------

def test_interaction_cooldown():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0.5
    im.update(0.1)
    assert im._interaction_cooldown == pytest.approx(0.4)


def test_emote_interruption():
    """A second emote should interrupt the first one."""
    game = MagicMock()
    game.player = MagicMock(spec=Player)
    game.emote_group = MagicMock()
    game.emote_group.__len__.return_value = 1

    im = InteractionManager(game)
    im._emote_cooldown = 0

    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 110)
    obj.direction_str = 'up'
    obj.sub_type = 'chest'
    obj.is_on = False
    game.interactives = [obj]
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'

    im._check_proximity_emotes()
    assert game.player.playerEmote.called


# ---------------------------------------------------------------------------
# Orientation & facing helpers
# ---------------------------------------------------------------------------

def test_interaction_orientation():
    """_verify_orientation respects object front/back."""
    im = InteractionManager(MagicMock())
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 120)
    obj.direction_str = 'up'
    obj.sub_type = 'chest'

    assert im._verify_orientation(obj, 'down', pygame.math.Vector2(100, 100)) is True
    assert im._verify_orientation(obj, 'up', pygame.math.Vector2(100, 140)) is False


def test_get_player_facing_vector():
    im = InteractionManager(MagicMock())
    im.game.player.current_state = 'up'
    assert im._get_player_facing_vector() == pygame.math.Vector2(0, -1)
    im.game.player.current_state = 'down'
    assert im._get_player_facing_vector() == pygame.math.Vector2(0, 1)
    im.game.player.current_state = 'left'
    assert im._get_player_facing_vector() == pygame.math.Vector2(-1, 0)
    im.game.player.current_state = 'right'
    assert im._get_player_facing_vector() == pygame.math.Vector2(1, 0)


def test_facing_toward():
    im = InteractionManager(MagicMock())
    p_pos = pygame.math.Vector2(100, 100)

    assert im._facing_toward(p_pos, 'right', pygame.math.Vector2(150, 100)) is True
    assert im._facing_toward(p_pos, 'left', pygame.math.Vector2(150, 100)) is False
    assert im._facing_toward(p_pos, 'down', pygame.math.Vector2(100, 150)) is True
    assert im._facing_toward(p_pos, 'up', pygame.math.Vector2(100, 150)) is False


def test_verify_orientation_door_relaxed():
    """Open door allows approach from any side."""
    im = InteractionManager(MagicMock())
    door = MagicMock()
    door.pos = pygame.math.Vector2(100, 100)
    door.sub_type = 'door'
    door.direction_str = 'down'
    door.is_on = True

    p_pos = pygame.math.Vector2(100, 80)
    assert im._verify_orientation(door, 'down', p_pos) is True


# ---------------------------------------------------------------------------
# Interaction: pickups
# ---------------------------------------------------------------------------

def test_handle_interaction_pickup():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0

    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.player.inventory.add_item.return_value = 0

    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 105)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]

        im.handle_interactions()
        assert game.player.inventory.add_item.called
        assert pickup.kill.called


def test_handle_interaction_pickup_partial():
    """Partial pickup updates quantity and triggers frustration emote."""
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0

    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.player.inventory.add_item.return_value = 3

    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 105)
        pickup.item_id = "potion_red"
        pickup.quantity = 5
        game.pickups = [pickup]

        im.handle_interactions()
        assert pickup.quantity == 3
        assert not pickup.kill.called
        assert game.player.playerEmote.called


# ---------------------------------------------------------------------------
# Interaction: NPC
# ---------------------------------------------------------------------------

def test_handle_interaction_npc():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0

    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False

    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        npc = MagicMock()
        npc.pos = pygame.math.Vector2(100, 132)
        npc.rect = pygame.Rect(100 - 16, 132 - 16, 32, 32)
        npc.element_id = "npc_1"
        npc.is_moving = False

        def mock_interact(initiator):
            npc.state = "interact"
            return "hello"

        npc.interact.side_effect = mock_interact
        game.npcs = [npc]

        im.handle_interactions()
        assert game._trigger_npc_bubble.called
        assert npc.state == "interact"


# ---------------------------------------------------------------------------
# Interaction: interactive objects
# ---------------------------------------------------------------------------

def test_handle_interaction_object():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0

    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'up'
    game.player.is_moving = False

    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 80)
        obj.direction_str = 'down'
        obj.sub_type = 'switch'
        obj.element_id = 'switch_1'
        obj.target_id = 'door_1'
        obj.sfx = 'click'
        obj._world_state_key = 'switch_1_key'
        obj.is_on = True
        obj.interact.return_value = None
        game.interactives = [obj]

        im.handle_interactions()
        assert obj.interact.called
        game.audio_manager.play_sfx.assert_called_with('click', 'switch_1')
        game.world_state.set.assert_called_with('switch_1_key', {'is_on': True})
        game.toggle_entity_by_id.assert_called_with('door_1', depth=1)


# ---------------------------------------------------------------------------
# Interaction: chest
# ---------------------------------------------------------------------------

def test_handle_interaction_chest_opens_ui():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0

    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False

    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        chest = MagicMock()
        chest.pos = pygame.math.Vector2(100, 120)
        chest.direction_str = 'up'
        chest.sub_type = 'chest'
        chest.is_on = True
        chest.interact.return_value = None
        game.interactives = [chest]

        im.handle_interactions()
        assert chest.interact.called
        game.chest_ui.open.assert_called_with(chest, game.player)


def test_handle_interaction_chest_closes_ui_on_action_key():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0

    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.chest_ui.is_open = True

    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        chest = MagicMock()
        chest.pos = pygame.math.Vector2(100, 120)
        chest.direction_str = 'up'
        chest.sub_type = 'chest'
        chest.is_on = False
        chest.interact.return_value = None
        game.interactives = [chest]
        im._open_chest_entity = chest

        im.handle_interactions()
        assert chest.interact.called
        game.chest_ui.close.assert_called()
        assert im._open_chest_entity is None


def test_chest_auto_close_out_of_range():
    game = MagicMock()
    im = InteractionManager(game)
    chest = MagicMock()
    chest.pos = pygame.math.Vector2(100, 100)
    chest.direction_str = 'up'
    chest.sub_type = 'chest'
    im._open_chest_entity = chest
    game.chest_ui.is_open = True
    game.player.pos = pygame.math.Vector2(500, 500)

    im._check_chest_auto_close()
    assert chest.interact.called
    assert game.chest_ui.close.called
    assert im._open_chest_entity is None


def test_chest_auto_close_wrong_orientation():
    game = MagicMock()
    im = InteractionManager(game)
    chest = MagicMock()
    chest.pos = pygame.math.Vector2(100, 120)
    chest.direction_str = 'up'
    chest.sub_type = 'chest'
    im._open_chest_entity = chest
    game.chest_ui.is_open = True
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'up'

    im._check_chest_auto_close()
    assert chest.interact.called
    assert game.chest_ui.close.called
    assert im._open_chest_entity is None


def test_chest_proximity_emote_logic():
    game = MagicMock()
    im = InteractionManager(game)
    im._emote_cooldown = 0

    chest = MagicMock()
    chest.pos = pygame.math.Vector2(100, 120)
    chest.direction_str = 'up'
    chest.sub_type = 'chest'
    game.interactives = [chest]
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'

    chest.is_on = False
    im._check_proximity_emotes()
    assert game.player.playerEmote.called

    game.player.playerEmote.reset_mock()
    im._emote_cooldown = 0
    im._last_proximity_target = None

    chest.is_on = True
    im._check_proximity_emotes()
    assert not game.player.playerEmote.called


# ---------------------------------------------------------------------------
# Diagonal rejection / orthogonal acceptance
# ---------------------------------------------------------------------------

def test_pickup_diagonal_rejection(interaction_setup):
    game, im = interaction_setup
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(120, 120)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]
        game.player.current_state = 'down'

        im.handle_interactions()
        assert not game.player.inventory.add_item.called
        assert not pickup.kill.called


def test_pickup_orthogonal_acceptance(interaction_setup):
    game, im = interaction_setup
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 120)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]
        game.player.current_state = 'down'

        im.handle_interactions()
        assert game.player.inventory.add_item.called
        assert pickup.kill.called


def test_anywhere_object_diagonal_rejection(interaction_setup):
    game, im = interaction_setup
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(120, 120)
        obj.activate_from_anywhere = True
        obj.is_on = False
        game.interactives = [obj]
        game.player.current_state = 'down'

        im.handle_interactions()
        assert not obj.interact.called


def test_anywhere_object_orthogonal_acceptance(interaction_setup):
    game, im = interaction_setup
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 120)
        obj.activate_from_anywhere = True
        obj.is_on = False
        game.interactives = [obj]
        game.player.current_state = 'down'

        im.handle_interactions()
        assert obj.interact.called


def test_pickup_proximity_emote_diagonal_rejection(interaction_setup):
    game, im = interaction_setup
    pickup = MagicMock()
    pickup.pos = pygame.math.Vector2(120, 120)
    game.pickups = [pickup]
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'

    im._check_proximity_emotes()
    assert not game.player.playerEmote.called


def test_pickup_proximity_emote_orthogonal_acceptance(interaction_setup):
    game, im = interaction_setup
    pickup = MagicMock()
    pickup.pos = pygame.math.Vector2(100, 120)
    game.pickups = [pickup]
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'

    im._check_proximity_emotes()
    assert game.player.playerEmote.called


def test_pickup_on_top_acceptance(interaction_setup):
    game, im = interaction_setup
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 100)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]
        game.player.current_state = 'up'

        im.handle_interactions()
        assert game.player.inventory.add_item.called
        assert pickup.kill.called


def test_passable_object_on_top_acceptance(interaction_setup):
    game, im = interaction_setup
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 100)
        obj.is_passable = True
        obj.is_on = False
        game.interactives = [obj]
        game.player.current_state = 'up'

        im.handle_interactions()
        assert obj.interact.called
