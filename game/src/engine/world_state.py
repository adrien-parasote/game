class WorldState:
    """Persistent storage for object states across maps during a game session."""

    def __init__(self):
        self._state = {}

    def set(self, key: str, value: dict):
        """Updates the state dictionary for a specific key."""
        self._state[key] = value

    def get(self, key: str, default=None):
        """Reads a state dictionary by its key. Returns default if not found."""
        return self._state.get(key, default)

    def clear(self):
        """Resets the state completely. Useful for tests or session resets."""
        self._state.clear()

    @staticmethod
    def make_key(map_name: str, tiled_id: int) -> str:
        """Constructs a standard unique key from the map name and the native Tiled ID."""
        stem = map_name.rsplit(".", 1)[0] if "." in map_name else map_name
        return f"{stem}_{tiled_id}"
