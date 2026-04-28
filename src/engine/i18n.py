import json
import os
import logging
from typing import Dict, Any, Optional

class I18nManager:
    """
    Manages game localization by loading JSON language files.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(I18nManager, cls).__new__(cls)
            cls._instance.data = {}
            cls._instance.current_locale = "en"
        return cls._instance

    def load(self, locale: str):
        """Load a language file from assets/langs/{locale}.json."""
        self.current_locale = locale
        root = os.path.join(os.path.dirname(__file__), "..", "..")
        path = os.path.normpath(os.path.join(root, "assets", "langs", f"{locale}.json"))
        
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logging.info(f"I18nManager: Loaded locale '{locale}'")
            else:
                logging.warning(f"I18nManager: Locale file not found: {path}")
                self.data = {}
        except Exception as e:
            logging.error(f"I18nManager: Failed to load locale '{locale}': {e}")
            self.data = {}

    def get(self, key: str, default: str = "") -> str:
        """Get a translation string by dot-separated key (e.g., 'seasons.SPRING')."""
        keys = key.split('.')
        val = self.data
        try:
            for k in keys:
                val = val[k]
            return str(val)
        except (KeyError, TypeError):
            return default or key

    def get_item(self, item_id: str) -> Dict[str, str]:
        """Specific helper for item metadata."""
        items = self.data.get("items", {})
        item_data = items.get(item_id, {})
        return {
            "name": item_data.get("name", item_id.replace('_', ' ').capitalize()),
            "description": item_data.get("description", "No description available.")
        }
