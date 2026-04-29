import pygame
import json
import os
import logging
from typing import Any, Dict

class Settings:
    """
    Centralized game configuration settings.
    Loads data from settings.json if available, otherwise uses defaults.
    """
    
    # Internal Defaults (Fallback)
    _DEFAULTS = {
        "version": "0.0.0",
        "display": {
            "width": 1280, "height": 720, "fps": 60, 
            "title": "RPG Tile Engine", "fullscreen": False
        },
        "map": {"tile_size": 32, "map_size": 32, "initial_hour": 16},
        "colors": {
            "background": "#1a1a1a"
        },
        "player": {"speed": 150, "size": 32},
        "controls": {
            "move_up": "K_UP", 
            "move_down": "K_DOWN", 
            "move_left": "K_LEFT", 
            "move_right": "K_RIGHT",
            "quit_key": "K_ESCAPE", 
            "interact_key": "K_e",
            "inventory_key": "K_i",
            "toggle_fullscreen_key": "K_F11"
        },
        "debug": {"log_level": "INFO"},
        "overlay": {"occlusion_alpha": 102},
        "time": {
            "minute_duration": 1.0, 
            "days_per_season": 30, 
            "initial_season": 0
        },
        "npc": {
            "speed": 40,
            "animation_speed": 8.0
        },
        "ui": {
            "text_speed": 0.05,
            "cursor_size": 48,
            "enable_failed_interaction_emote": True
        },
        "audio": {
            "bgm_volume": 0.5,
            "sfx_volume": 0.5
        },
        "locale": "fr",
        "fonts": {
            "noble": "assets/fonts/metamorphous-regular.ttf",
            "narrative": "assets/fonts/vcr_osd_mono.ttf",
            "tech": "assets/fonts/m5x7.ttf",
            "size_noble": 18,
            "size_narrative": 14,
            "size_tech": 12
        }
    }

    @classmethod
    def _map_key(cls, key_str: Any) -> int:
        """Safely map a string key name to its pygame.K_* constant."""
        if not isinstance(key_str, str):
            return pygame.K_UP
        return getattr(pygame, key_str, pygame.K_UP)

    @classmethod
    def load(cls):
        """Load settings from JSON files and map to class attributes."""
        root = os.path.join(os.path.dirname(__file__), "..")
        tech_path = os.path.join(root, "settings.json")
        game_path = os.path.join(root, "gameplay.json")
        
        data = cls._DEFAULTS.copy()
        
        # Load Tech
        if os.path.exists(tech_path):
            try:
                with open(tech_path, "r") as f:
                    tech_config = json.load(f)
                    for section, values in tech_config.items():
                        if section in data:
                            if isinstance(values, dict) and isinstance(data[section], dict):
                                data[section].update(values)
                            else:
                                data[section] = values
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Could not load settings.json ({e}). Using defaults.")

        # Load Gameplay
        if os.path.exists(game_path):
            try:
                with open(game_path, "r") as f:
                    game_config = json.load(f)
                    for section, values in game_config.items():
                        # Gameplay might have sections NOT in tech defaults, or overlapping
                        if section in data:
                            if isinstance(values, dict) and isinstance(data[section], dict):
                                data[section].update(values)
                            else:
                                data[section] = values
                        else:
                            data[section] = values
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Could not load gameplay.json ({e}).")

        # Versioning
        cls.VERSION: str = data.get("version", "0.0.0")

        # Display
        cls.WINDOW_WIDTH: int = data["display"]["width"]
        cls.WINDOW_HEIGHT: int = data["display"]["height"]
        cls.FPS: int = data["display"]["fps"]
        cls.GAME_TITLE: str = data["display"]["title"]
        cls.FULLSCREEN: bool = data["display"]["fullscreen"]
        
        # Map
        cls.TILE_SIZE: int = data["map"]["tile_size"]
        cls.MAP_SIZE: int = data["map"]["map_size"]
        cls.INITIAL_HOUR: int = data["map"].get("initial_hour", 16)
        
        # Colors
        cls.COLOR_BG = data["colors"]["background"]
        
        # Player
        cls.PLAYER_SPEED: int = data["player"]["speed"]
        cls.PLAYER_SIZE: int = data["player"]["size"]
        
        # Controls (Optimized mapping)
        controls = data["controls"]
        cls.MOVE_UP = cls._map_key(controls.get("move_up", "K_UP"))
        cls.MOVE_DOWN = cls._map_key(controls.get("move_down", "K_DOWN"))
        cls.MOVE_LEFT = cls._map_key(controls.get("move_left", "K_LEFT"))
        cls.MOVE_RIGHT = cls._map_key(controls.get("move_right", "K_RIGHT"))
        cls.QUIT_KEY = cls._map_key(controls.get("quit_key", "K_ESCAPE"))
        cls.INTERACT_KEY = cls._map_key(controls.get("interact_key", "K_e"))
        cls.INVENTORY_KEY = cls._map_key(controls.get("inventory_key", "K_i"))
        cls.TOGGLE_FULLSCREEN_KEY = cls._map_key(controls.get("toggle_fullscreen_key", "K_F11"))
        
        # Logging
        level_name = data.get("debug", {}).get("log_level", "INFO").upper()
        cls.LOG_LEVEL = getattr(logging, level_name, logging.INFO)
        cls.DEBUG: bool = data.get("debug", {}).get("enabled", False)

        # Overlay
        cls.OCCLUSION_ALPHA = data.get("overlay", {}).get("occlusion_alpha", 102)

        # Time
        time_data = data.get("time", {})
        cls.MINUTE_DURATION: float = time_data.get("minute_duration", 1.0)
        cls.DAYS_PER_SEASON: int = time_data.get("days_per_season", 30)
        cls.INITIAL_SEASON: int = time_data.get("initial_season", 0)

        # UI
        ui_data = data.get("ui", {})
        cls.TEXT_SPEED: float = ui_data.get("text_speed", 0.05)
        cls.CURSOR_SIZE: int = ui_data.get("cursor_size", 48)
        cls.ENABLE_FAILED_INTERACTION_EMOTE: bool = ui_data.get("enable_failed_interaction_emote", True)

        # NPC
        npc_data = data.get("npc", {})
        cls.NPC_SPEED: float = npc_data.get("speed", 40)
        cls.NPC_ANIMATION_SPEED: float = npc_data.get("animation_speed", 8.0)
        
        # Audio
        audio_data = data.get("audio", {})
        cls.BGM_VOLUME: float = audio_data.get("bgm_volume", 0.5)
        cls.SFX_VOLUME: float = audio_data.get("sfx_volume", 0.5)

        # Fonts
        font_data = data.get("fonts", {})
        cls.FONT_NOBLE: str = font_data.get("noble", "assets/fonts/metamorphous-regular.ttf")
        cls.FONT_NARRATIVE: str = font_data.get("narrative", "assets/fonts/vcr_osd_mono.ttf")
        cls.FONT_TECH: str = font_data.get("tech", "assets/fonts/m5x7.ttf")
        cls.FONT_SIZE_NOBLE: int = font_data.get("size_noble", 18)
        cls.FONT_SIZE_NARRATIVE: int = font_data.get("size_narrative", 14)
        cls.FONT_SIZE_TECH: int = font_data.get("size_tech", 12)

        # Locale
        cls.LOCALE: str = data.get("locale", "fr")

# Initialize on import
Settings.load()
