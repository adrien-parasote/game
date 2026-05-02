"""
Tests RED — SaveManager (TC-001 à TC-008)
Spec: docs/specs/game-flow-spec.md#4-test-case-specifications
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch
from src.engine.save_manager import SaveManager, SlotInfo, SaveData


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_saves_dir(tmp_path):
    """Répertoire temporaire isolé pour chaque test."""
    return str(tmp_path / "saves")


@pytest.fixture
def manager(tmp_saves_dir):
    """SaveManager pointant vers un dossier temporaire vide."""
    return SaveManager(saves_dir=tmp_saves_dir)


def _make_mock_game(tmp_saves_dir):
    """Construit un mock Game minimal avec tous les champs requis par save()."""
    game = MagicMock()
    game._current_map_name = "00-spawn.tmj"
    game.player.pos.x = 320.0
    game.player.pos.y = 480.0
    game.player.current_state = "down"
    game.player.level = 1
    game.player.hp = 100
    game.player.max_hp = 100
    game.player.gold = 0

    # Inventory: 28 slots dont un item
    from src.engine.inventory_system import Inventory, Item
    inv = Inventory(capacity=28)
    inv.slots[3] = Item(id="sword_iron", name="Épée", description="", quantity=1, stack_max=1)
    inv.equipment["LEFT_HAND"] = Item(id="sword_iron", name="Épée", description="", quantity=1, stack_max=1)
    game.player.inventory = inv

    from src.engine.time_system import TimeSystem
    ts = TimeSystem(initial_hour=6)
    ts._total_minutes = 7200.0
    game.time_system = ts

    from src.engine.world_state import WorldState
    ws = WorldState()
    ws.set("castle_hall_chest_01", {"is_on": True})
    game.world_state = ws

    return game


# ── TC-001 : list_slots — dossier vide ───────────────────────────────────────

def test_list_slots_empty(manager):
    """TC-001 : dossier saves/ vide → [None, None, None]"""
    result = manager.list_slots()
    assert result == [None, None, None]


# ── TC-002 : save — création du fichier ───────────────────────────────────────

def test_save_creates_file(manager, tmp_saves_dir):
    """TC-002 : save(1, game) crée saves/slot_1.json avec version correcte."""
    game = _make_mock_game(tmp_saves_dir)
    manager.save(1, game)

    path = os.path.join(tmp_saves_dir, "slot_1.json")
    assert os.path.exists(path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["version"] == "0.4.0"
    assert data["player"]["map_name"] == "00-spawn.tmj"
    assert data["player"]["x"] == 320.0
    assert data["player"]["facing"] == "down"


# ── TC-003 : load — slot existant ─────────────────────────────────────────────

def test_load_existing_slot(manager, tmp_saves_dir):
    """TC-003 : load(1) retourne SaveData avec player.map_name correct."""
    game = _make_mock_game(tmp_saves_dir)
    manager.save(1, game)

    result = manager.load(1)

    assert result is not None
    assert isinstance(result, SaveData)
    assert result.player["map_name"] == "00-spawn.tmj"
    assert result.time_system["total_minutes"] == pytest.approx(7200.0)


# ── TC-004 : load — slot vide ─────────────────────────────────────────────────

def test_load_empty_slot_returns_none(manager):
    """TC-004 : load(2) sur slot vide retourne None."""
    result = manager.load(2)
    assert result is None


# ── TC-005 : load — JSON corrompu ─────────────────────────────────────────────

def test_load_corrupted_json_returns_none(manager, tmp_saves_dir, caplog):
    """TC-005 : load(1) avec JSON invalide → None + log WARNING."""
    os.makedirs(tmp_saves_dir, exist_ok=True)
    path = os.path.join(tmp_saves_dir, "slot_1.json")
    with open(path, "w") as f:
        f.write("{ invalid json !!!")

    import logging
    with caplog.at_level(logging.WARNING):
        result = manager.load(1)

    assert result is None
    assert any("corrompu" in r.message.lower() or "slot" in r.message.lower()
               for r in caplog.records)


# ── TC-006 : delete ───────────────────────────────────────────────────────────

def test_delete_slot(manager, tmp_saves_dir):
    """TC-006 : delete(1) supprime le fichier, slot_exists(1) == False."""
    game = _make_mock_game(tmp_saves_dir)
    manager.save(1, game)
    assert manager.slot_exists(1)

    manager.delete(1)

    assert not manager.slot_exists(1)


# ── TC-007 : Inventory roundtrip ──────────────────────────────────────────────

def test_inventory_roundtrip(manager, tmp_saves_dir):
    """TC-007 : item slot[3] et equipment LEFT_HAND survivent save/load."""
    game = _make_mock_game(tmp_saves_dir)
    manager.save(1, game)

    result = manager.load(1)

    assert result is not None
    # slots
    slot_3 = result.inventory["slots"][3]
    assert slot_3 is not None
    assert slot_3["id"] == "sword_iron"
    assert slot_3["quantity"] == 1
    # equipment
    lh = result.inventory["equipment"]["LEFT_HAND"]
    assert lh is not None
    assert lh["id"] == "sword_iron"


# ── TC-008 : WorldState roundtrip ─────────────────────────────────────────────

def test_world_state_roundtrip(manager, tmp_saves_dir):
    """TC-008 : world_state survit save/load sans perte."""
    game = _make_mock_game(tmp_saves_dir)
    manager.save(1, game)

    result = manager.load(1)

    assert result is not None
    ws = result.world_state
    assert "castle_hall_chest_01" in ws
    assert ws["castle_hall_chest_01"]["is_on"] is True


# ── Cas limites ───────────────────────────────────────────────────────────────

def test_slot_id_out_of_range_raises(manager):
    """save() avec slot_id hors [1..3] lève ValueError."""
    game = _make_mock_game("/tmp")
    with pytest.raises(ValueError):
        manager.save(0, game)
    with pytest.raises(ValueError):
        manager.save(4, game)


def test_list_slots_reflects_saved(manager, tmp_saves_dir):
    """list_slots() retourne SlotInfo pour les slots sauvegardés."""
    game = _make_mock_game(tmp_saves_dir)
    manager.save(2, game)

    result = manager.list_slots()

    assert result[0] is None   # slot 1 vide
    assert isinstance(result[1], SlotInfo)   # slot 2 sauvegardé
    assert result[2] is None   # slot 3 vide
    assert result[1].slot_id == 2
    assert result[1].map_name == "00-spawn.tmj"


def test_save_io_error_does_not_crash(manager, tmp_saves_dir, caplog):
    """save() ne crash pas sur IOError — log ERROR."""
    import logging
    game = _make_mock_game(tmp_saves_dir)
    with patch("builtins.open", side_effect=IOError("disk full")):
        with caplog.at_level(logging.ERROR):
            # Ne doit pas lever d'exception
            manager.save(1, game)
    assert any("error" in r.levelname.lower() for r in caplog.records)
