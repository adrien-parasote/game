import json
import logging
import os
from unittest.mock import patch

import pytest

from src.config import Settings
from src.engine.game import Game


@pytest.fixture(autouse=True)
def skip_display_init():
    with patch("pygame.display.set_mode") as mock_set_mode, \
         patch("pygame.display.set_caption"), \
         patch("pygame.display.toggle_fullscreen"), \
         patch("pygame.display.update"):
        mock_set_mode.return_value.get_size.return_value = (800, 600)
        yield

def test_chest_loot_is_loaded_correctly(tmp_path):
    """
    Reproduces the bug where chests are empty because property_types is passed
    as an empty list instead of the actual item dictionary.
    """
    # Create fake propertytypes.json
    prop_file = tmp_path / "propertytypes.json"
    prop_file.write_text(json.dumps({
        "potion_red": {"name": "Potion Rouge", "stack_max": 10}
    }))

    # Create fake loot_table.json
    loot_file = tmp_path / "loot_table.json"
    loot_file.write_text(json.dumps({
        "chest_debug_1": [{"item_id": "potion_red", "quantity": 1}]
    }))

    # Patch os.path.join so game.py uses our tmp files instead of actual assets
    original_join = os.path.join
    def fake_join(*args):
        path = original_join(*args)
        if "propertytypes.json" in path:
            return str(prop_file)
        if "loot_table.json" in path:
            return str(loot_file)
        if "world.world" in path:
            return "/nonexistent"
        return path

    with patch("os.path.join", side_effect=fake_join):
        # Prevent actually loading the map so we only test initialization
        game = Game(skip_map_load=True)

        # The loot table should have successfully parsed the chest
        chest_loot = game.loot_table.get_contents("chest_debug_1")
        assert len(chest_loot) == 1, f"Expected 1 item in chest, got {len(chest_loot)}"
        assert chest_loot[0]["item_id"] == "potion_red"
