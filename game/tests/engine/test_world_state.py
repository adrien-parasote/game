from src.engine.world_state import WorldState


class TestWorldState:
    def test_set_and_get(self):
        ws = WorldState()
        ws.set("key1", {"hp": 10})
        assert ws.get("key1") == {"hp": 10}

    def test_get_missing_returns_default(self):
        ws = WorldState()
        assert ws.get("missing") is None
        assert ws.get("missing", default={"x": 1}) == {"x": 1}

    def test_clear_resets_state(self):
        """WorldState.clear() — ligne 17 non couverte."""
        ws = WorldState()
        ws.set("a", {"v": 1})
        ws.set("b", {"v": 2})
        ws.clear()
        assert ws.get("a") is None
        assert ws.get("b") is None

    def test_make_key_with_extension(self):
        key = WorldState.make_key("01-castel-ext.tmj", 42)
        assert key == "01-castel-ext_42"

    def test_make_key_without_extension(self):
        key = WorldState.make_key("my_map", 7)
        assert key == "my_map_7"
