"""
Tests for DT Clamp (Step 1 — TC-DT-001 to TC-DT-004).
Spec: game/docs/specs/remediation_01_dt_text_cache.md § Step 1

These tests are written RED-first: they will FAIL until the clamp is implemented.
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# TC-DT-001 — GSM run() with long tick → dt passed to _handle_playing ≤ 0.1
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-DT-001")
def test_gsm_dt_clamped_on_long_tick():
    """A 500ms tick must produce dt ≤ 0.1 inside _handle_playing."""
    from src.engine.game_state_manager import GameState, GameStateManager

    received_dt: list[float] = []

    with (
        patch("src.engine.game_state_manager.TitleScreen"),
        patch("src.engine.game_state_manager.PauseScreen"),
        patch("src.engine.game_state_manager.Game") as MockGame,
        patch("src.engine.game_state_manager.SaveManager"),
    ):
        mock_game_instance = MagicMock()
        mock_game_instance.clock.tick.return_value = 500  # 500ms tick

        # run_frame captures dt argument
        call_count = 0

        def fake_run_frame(dt):
            nonlocal call_count
            received_dt.append(dt)
            call_count += 1
            raise StopIteration  # exit run() after 1 iteration

        MockGame.return_value = mock_game_instance
        gsm = GameStateManager()
        gsm.state = GameState.PLAYING
        mock_game_instance.run_frame.side_effect = fake_run_frame

        with pytest.raises(StopIteration):
            gsm.run()

    assert len(received_dt) == 1
    assert received_dt[0] <= 0.1, f"dt not clamped: got {received_dt[0]}"


# ---------------------------------------------------------------------------
# TC-DT-002 — GSM run() with normal 16ms tick → dt ≈ 0.016 (not over-clamped)
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-DT-002")
def test_gsm_dt_not_clamped_on_normal_tick():
    """A normal 16ms tick must not be clamped below 0.016."""
    from src.engine.game_state_manager import GameState, GameStateManager

    received_dt: list[float] = []

    with (
        patch("src.engine.game_state_manager.TitleScreen"),
        patch("src.engine.game_state_manager.PauseScreen"),
        patch("src.engine.game_state_manager.Game") as MockGame,
        patch("src.engine.game_state_manager.SaveManager"),
    ):
        mock_game_instance = MagicMock()
        mock_game_instance.clock.tick.return_value = 16  # 16ms normal tick

        def fake_run_frame(dt):
            received_dt.append(dt)
            raise StopIteration

        MockGame.return_value = mock_game_instance
        gsm = GameStateManager()
        gsm.state = GameState.PLAYING
        mock_game_instance.run_frame.side_effect = fake_run_frame

        with pytest.raises(StopIteration):
            gsm.run()

    assert len(received_dt) == 1
    assert abs(received_dt[0] - 0.016) < 0.001, f"dt distorted: got {received_dt[0]}"


# ---------------------------------------------------------------------------
# TC-DT-004 — Static check: every clock.tick call followed by min() within 2 lines
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-DT-004")
def test_static_clock_tick_followed_by_clamp():
    """Every `clock.tick(Settings.FPS) / 1000.0` in game_state_manager.py and
    game.py must have `min(` on the same or immediately following line."""
    import re

    files = [
        "game/src/engine/game_state_manager.py",
        "game/src/engine/game.py",
    ]

    pattern_tick = re.compile(r"clock\.tick\(.*?\)\s*/\s*1000\.0")
    # After finding a tick-with-division, the next non-empty line must contain min(
    pattern_clamp = re.compile(r"min\(")

    violations: list[str] = []

    for filepath in files:
        with open(filepath) as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if pattern_tick.search(line):
                # Check current line or next line for min(
                window = "".join(lines[i : i + 3])
                if not pattern_clamp.search(window):
                    violations.append(f"{filepath}:{i + 1}: missing min() clamp after clock.tick")

    assert not violations, "\n".join(violations)
