
from src.entities.interactive import InteractiveEntity
from src.entities.player import Player
from src.ui.chest import ChestUI


class DummyChest(InteractiveEntity):
    def __init__(self, contents):
        self.contents = contents
        self.sub_type = "chest"

class DummyPlayer(Player):
    def __init__(self):
        self.inventory = DummyInventory()

class DummyInventory:
    def __init__(self):
        self.slots = [None] * 20
        self.item_data = {}

def test_chest_ui_get_contents(setup_pygame):
    ui = ChestUI()
    chest = DummyChest([{"item_id": "ether_potion", "quantity": 10}])
    player = DummyPlayer()

    ui.open(chest, player)

    contents = ui._get_chest_contents()
    assert len(contents) == 20
    assert contents[0] is not None
    assert contents[0]["item_id"] == "ether_potion"
    assert contents[0]["quantity"] == 10

    for i in range(1, 20):
        assert contents[i] is None
