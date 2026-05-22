import pytest

from src.engine.game_events import GameEvent, GameEventType


class TestGameEventFactories:
    def test_none_factory(self):
        e = GameEvent.none()
        assert e.type == GameEventType.NONE
        assert e.slot_id is None

    def test_new_game_factory(self):
        e = GameEvent.new_game()
        assert e.type == GameEventType.NEW_GAME

    def test_load_game_factory(self):
        e = GameEvent.load_game(slot_id=2)
        assert e.type == GameEventType.LOAD_GAME
        assert e.slot_id == 2

    def test_quit_factory(self):
        """GameEvent.quit() — ligne 36 non couverte."""
        e = GameEvent.quit()
        assert e.type == GameEventType.QUIT
        assert e.slot_id is None

    def test_pause_requested_factory(self):
        e = GameEvent.pause_requested()
        assert e.type == GameEventType.PAUSE_REQUESTED

    def test_resume_factory(self):
        e = GameEvent.resume()
        assert e.type == GameEventType.RESUME

    def test_goto_title_factory(self):
        e = GameEvent.goto_title()
        assert e.type == GameEventType.GOTO_TITLE

    def test_save_requested_factory(self):
        e = GameEvent.save_requested(slot_id=1)
        assert e.type == GameEventType.SAVE_REQUESTED
        assert e.slot_id == 1

    def test_load_requested_factory(self):
        e = GameEvent.load_requested(slot_id=3)
        assert e.type == GameEventType.LOAD_REQUESTED
        assert e.slot_id == 3
