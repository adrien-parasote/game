"""
GameEvent — Events exchanged between game states and the GameStateManager.
"""
from enum import Enum
from dataclasses import dataclass, field


class GameEventType(Enum):
    NONE = "none"
    NEW_GAME = "new_game"
    LOAD_GAME = "load_game"
    QUIT = "quit"
    PAUSE_REQUESTED = "pause_requested"
    RESUME = "resume"
    GOTO_TITLE = "goto_title"
    SAVE_REQUESTED = "save_requested"
    LOAD_REQUESTED = "load_requested"


@dataclass
class GameEvent:
    type: GameEventType = GameEventType.NONE
    slot_id: int | None = None

    @staticmethod
    def none() -> "GameEvent":
        return GameEvent(type=GameEventType.NONE)

    @staticmethod
    def new_game() -> "GameEvent":
        return GameEvent(type=GameEventType.NEW_GAME)

    @staticmethod
    def load_game(slot_id: int) -> "GameEvent":
        return GameEvent(type=GameEventType.LOAD_GAME, slot_id=slot_id)

    @staticmethod
    def quit() -> "GameEvent":
        return GameEvent(type=GameEventType.QUIT)

    @staticmethod
    def pause_requested() -> "GameEvent":
        return GameEvent(type=GameEventType.PAUSE_REQUESTED)

    @staticmethod
    def resume() -> "GameEvent":
        return GameEvent(type=GameEventType.RESUME)

    @staticmethod
    def goto_title() -> "GameEvent":
        return GameEvent(type=GameEventType.GOTO_TITLE)

    @staticmethod
    def save_requested(slot_id: int) -> "GameEvent":
        return GameEvent(type=GameEventType.SAVE_REQUESTED, slot_id=slot_id)

    @staticmethod
    def load_requested(slot_id: int) -> "GameEvent":
        return GameEvent(type=GameEventType.LOAD_REQUESTED, slot_id=slot_id)
