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
        "display": {
            "width": 1280, "height": 720, "fps": 60, 
            "title": "RPG Tile Engine", "fullscreen": False
        },
        "map": {"tile_size": 32, "map_size": 32, "initial_hour": 16},
        "colors": {
            "background": "#1a1a1a", "player": "#00DDFF", "player_border": "white",
            "tile_floor": "gray15", "tile_border": "gray20", "tile_wall": "red"
        },
        "player": {"speed": 150, "size": 32},
        "controls": {
            "move_up": "K_UP", 
            "move_down": "K_DOWN", 
            "move_left": "K_LEFT", 
            "move_right": "K_RIGHT",
            "quit_key": "K_ESCAPE", 
            "interact_key": "K_e",
            "toggle_fullscreen_key": "K_F11"
        },
        "debug": {"log_level": "INFO"},
        "overlay": {"occlusion_alpha": 102},
        "time": {
            "minute_duration": 1.0, 
            "days_per_season": 30, 
            "initial_season": 0
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
        """Load settings from JSON file and map to class attributes."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "settings.json")
        data = cls._DEFAULTS.copy()
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    user_config = json.load(f)
                    for section, values in user_config.items():
                        if section in data:
                            data[section].update(values)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings.json ({e}). Using defaults.")

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
        cls.COLOR_PLAYER = data["colors"]["player"]
        cls.COLOR_PLAYER_BORDER = data["colors"]["player_border"]
        
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
        cls.TOGGLE_FULLSCREEN_KEY = cls._map_key(controls.get("toggle_fullscreen_key", "K_F11"))
        
        # Logging
        level_name = data.get("debug", {}).get("log_level", "INFO").upper()
        cls.LOG_LEVEL = getattr(logging, level_name, logging.INFO)

        # Overlay
        cls.OCCLUSION_ALPHA = data.get("overlay", {}).get("occlusion_alpha", 102)

        # Time
        time_data = data.get("time", {})
        cls.MINUTE_DURATION: float = time_data.get("minute_duration", 1.0)
        cls.DAYS_PER_SEASON: int = time_data.get("days_per_season", 30)
        cls.INITIAL_SEASON: int = time_data.get("initial_season", 0)

# Initialize on import
Settings.load()
