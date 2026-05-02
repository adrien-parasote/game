"""
SaveManager — Serialization and persistence of save slots.
Spec: docs/specs/game-flow-spec.md#21-srcenginesave_managerpy-new
"""
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

SAVES_DIR = "saves"
MAX_SLOTS = 3
SCHEMA_VERSION = "0.4.0"


@dataclass
class SlotInfo:
    slot_id: int
    saved_at: str
    playtime_seconds: float
    map_name: str


@dataclass
class SaveData:
    version: str
    saved_at: str
    playtime_seconds: float
    player: dict
    time_system: dict
    inventory: dict
    world_state: dict


class SaveManager:
    """Manages serialization and deserialization of save slots (1-3)."""

    def __init__(self, saves_dir: str = SAVES_DIR) -> None:
        self._saves_dir = saves_dir

    # ── Public API ────────────────────────────────────────────────────────────

    def list_slots(self) -> list[Optional[SlotInfo]]:
        """Return a list of 3 elements — None for empty slots."""
        result = []
        for slot_id in range(1, MAX_SLOTS + 1):
            info = self._read_slot_info(slot_id)
            result.append(info)
        return result

    def save(self, slot_id: int, game) -> None:
        """Serialize game state to saves/slot_{id}.json."""
        self._validate_slot_id(slot_id)
        os.makedirs(self._saves_dir, exist_ok=True)

        data = self._serialize(game)
        path = self._slot_path(slot_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info(f"SaveManager: Slot {slot_id} saved to {path}")
        except IOError as e:
            logging.error(f"SaveManager: Failed to write slot {slot_id}: {e}")

    def load(self, slot_id: int) -> Optional[SaveData]:
        """Deserialize save slot. Returns None if empty or corrupted."""
        self._validate_slot_id(slot_id)
        path = self._slot_path(slot_id)

        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"SaveManager: Slot {slot_id} corrompu: {e}")
            return None

        if data.get("version") != SCHEMA_VERSION:
            logging.warning(
                f"SaveManager: Slot {slot_id} version mismatch "
                f"({data.get('version')} != {SCHEMA_VERSION})"
            )
            return None

        return SaveData(
            version=data["version"],
            saved_at=data.get("saved_at", ""),
            playtime_seconds=data.get("playtime_seconds", 0),
            player=data["player"],
            time_system=data["time_system"],
            inventory=data["inventory"],
            world_state=data["world_state"],
        )

    def delete(self, slot_id: int) -> None:
        """Delete the save file for the given slot."""
        self._validate_slot_id(slot_id)
        path = self._slot_path(slot_id)
        if os.path.exists(path):
            os.remove(path)
            logging.info(f"SaveManager: Slot {slot_id} deleted")

    def slot_exists(self, slot_id: int) -> bool:
        """Return True if a save file exists for the given slot."""
        self._validate_slot_id(slot_id)
        return os.path.exists(self._slot_path(slot_id))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _slot_path(self, slot_id: int) -> str:
        return os.path.join(self._saves_dir, f"slot_{slot_id}.json")

    def _validate_slot_id(self, slot_id: int) -> None:
        if slot_id < 1 or slot_id > MAX_SLOTS:
            raise ValueError(
                f"SaveManager: slot_id must be between 1 and {MAX_SLOTS}, got {slot_id}"
            )

    def _read_slot_info(self, slot_id: int) -> Optional[SlotInfo]:
        """Read minimal slot metadata without full deserialization."""
        path = self._slot_path(slot_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SlotInfo(
                slot_id=slot_id,
                saved_at=data.get("saved_at", ""),
                playtime_seconds=data.get("playtime_seconds", 0),
                map_name=data.get("player", {}).get("map_name", ""),
            )
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logging.warning(f"SaveManager: Could not read slot {slot_id} info: {e}")
            return None

    def _serialize(self, game) -> dict:
        """Build the full save dict from a live Game instance."""
        inv = game.player.inventory
        return {
            "version": SCHEMA_VERSION,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "playtime_seconds": 0,
            "player": {
                "map_name": game._current_map_name,
                "x": float(game.player.pos.x),
                "y": float(game.player.pos.y),
                "facing": game.player.current_state,
                "level": game.player.level,
                "hp": game.player.hp,
                "max_hp": game.player.max_hp,
                "gold": game.player.gold,
            },
            "time_system": {
                "total_minutes": float(game.time_system._total_minutes),
            },
            "inventory": {
                "slots": self._serialize_slots(inv.slots),
                "equipment": self._serialize_equipment(inv.equipment),
            },
            "world_state": dict(game.world_state._state),
        }

    def _serialize_slots(self, slots: list) -> list:
        """Convert Item slots to JSON-safe dicts."""
        result = []
        for item in slots:
            if item is None:
                result.append(None)
            else:
                result.append({"id": item.id, "quantity": item.quantity})
        return result

    def _serialize_equipment(self, equipment: dict) -> dict:
        """Convert equipment dict to JSON-safe dict."""
        result = {}
        for slot_name, item in equipment.items():
            if item is None:
                result[slot_name] = None
            else:
                result[slot_name] = {"id": item.id, "quantity": item.quantity}
        return result
