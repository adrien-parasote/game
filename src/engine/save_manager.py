"""
SaveManager — Serialization and persistence of save slots.
Spec: docs/specs/game-flow-spec.md#21-srcenginesave_managerpy-new
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pygame.system


def _get_saves_dir() -> str:
    """Return the OS-appropriate saves directory path.

    Uses pygame.system.get_pref_path() for cross-OS compatibility:
    - macOS: ~/Library/Application Support/adrien/game/
    - Windows: %APPDATA%/adrien/game/
    - Linux: ~/.local/share/adrien/game/

    Falls back to "saves" if pygame is not initialized (e.g. test context).

    Migration: if legacy "./saves" exists and the new directory is empty,
    moves all saves to the new directory and renames "./saves" to "./saves_migrated".
    """
    try:
        path = pygame.system.get_pref_path("adrien", "game")

        # MIGRATION: Preserve user data from legacy paths
        legacy_path = "saves"
        if os.path.isdir(legacy_path):
            if not os.path.exists(path) or not os.listdir(path):
                os.makedirs(path, exist_ok=True)
                for item in os.listdir(legacy_path):
                    src = str(Path(legacy_path) / item)
                    dst = str(Path(path) / item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                # Safe rename — avoid collision with existing saves_migrated
                migrated = legacy_path + "_migrated"
                if os.path.exists(migrated):
                    counter = 1
                    while os.path.exists(f"{migrated}_{counter}"):
                        counter += 1
                    migrated = f"{migrated}_{counter}"
                os.rename(legacy_path, migrated)
                logging.info(f"SaveManager: migrated saves from '{legacy_path}' to '{path}'")

        return path
    except Exception as exc:
        logging.warning(f"SaveManager: get_pref_path failed ({exc}), using fallback 'saves'")
        return "saves"


SAVES_DIR = _get_saves_dir()
MAX_SLOTS = 3
SCHEMA_VERSION = "0.4.0"


@dataclass
class SlotInfo:
    slot_id: int
    saved_at: str
    playtime_seconds: float
    map_name: str
    map_display_name: str
    player_name: str
    level: int


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

    def list_slots(self) -> list[SlotInfo | None]:
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
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
            logging.info(f"SaveManager: Slot {slot_id} saved to {path}")
        except OSError as e:
            logging.error(f"SaveManager: Failed to write slot {slot_id}: {e}")

    def save_thumbnail(self, slot_id: int, surface) -> None:
        """Save a screenshot for the slot thumbnail."""
        import pygame

        self._validate_slot_id(slot_id)
        os.makedirs(self._saves_dir, exist_ok=True)
        path = str(Path(self._saves_dir) / f"slot_{slot_id}_thumb.png")
        try:
            pygame.image.save(surface, path)
        except pygame.error as e:
            logging.warning(f"SaveManager: Failed to save thumbnail {slot_id}: {e}")

    def load_thumbnail(self, slot_id: int):
        """Return the slot thumbnail as a pygame.Surface, or None if not found."""
        import pygame

        self._validate_slot_id(slot_id)
        path = str(Path(self._saves_dir) / f"slot_{slot_id}_thumb.png")
        if not os.path.exists(path):
            return None
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.warning(f"SaveManager: Failed to load thumbnail {slot_id}: {e}")
            return None

    def load(self, slot_id: int) -> SaveData | None:
        """Deserialize save slot. Returns None if empty or corrupted."""
        self._validate_slot_id(slot_id)
        path = self._slot_path(slot_id)

        if not os.path.exists(path):
            return None

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logging.warning(f"SaveManager: Slot {slot_id} corrupted: {e}")
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
        return str(Path(self._saves_dir) / f"slot_{slot_id}.json")

    def _validate_slot_id(self, slot_id: int) -> None:
        if slot_id < 1 or slot_id > MAX_SLOTS:
            raise ValueError(
                f"SaveManager: slot_id must be between 1 and {MAX_SLOTS}, got {slot_id}"
            )

    def _read_slot_info(self, slot_id: int) -> SlotInfo | None:
        """Read minimal slot metadata without full deserialization."""
        path = self._slot_path(slot_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            player_data = data.get("player", {})
            return SlotInfo(
                slot_id=slot_id,
                saved_at=data.get("saved_at", ""),
                playtime_seconds=data.get("playtime_seconds", 0),
                map_name=player_data.get("map_name", ""),
                map_display_name=player_data.get("map_display_name", ""),
                player_name=player_data.get("name", "Hero"),
                level=player_data.get("level", 1),
            )
        except (OSError, json.JSONDecodeError, KeyError) as e:
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
                "name": getattr(game.player, "name", "Hero"),
                "map_name": game._current_map_name,
                "map_display_name": getattr(game.map_manager, "name", ""),
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
