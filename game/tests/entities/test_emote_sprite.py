"""Tests for EmoteSprite (emote_sprite.py).

Covers: lifecycle, animation frame selection, rise-offset movement, auto-kill.
"""

import pygame


def _make_frames(n: int = 4) -> list[pygame.Surface]:
    return [pygame.Surface((16, 16)) for _ in range(n)]


def _make_player(cx: int = 100, top: int = 200) -> object:
    from unittest.mock import MagicMock
    player = MagicMock()
    player.rect = pygame.Rect(cx - 8, top - 32, 16, 32)
    return player


class TestEmoteSpriteLifecycle:
    def test_initial_state(self):
        """Sprite starts at frame 0, elapsed=0, and is alive."""
        from src.entities.emote_sprite import EmoteSprite
        frames = _make_frames()
        player = _make_player()
        group = pygame.sprite.Group()
        sprite = EmoteSprite(frames, player, group, duration=0.6)

        assert sprite.elapsed == 0.0
        assert sprite.image is frames[0]
        assert sprite in group.sprites()

    def test_killed_after_duration(self):
        """Sprite kills itself when elapsed >= duration."""
        from src.entities.emote_sprite import EmoteSprite
        frames = _make_frames()
        player = _make_player()
        group = pygame.sprite.Group()
        sprite = EmoteSprite(frames, player, group, duration=0.6)

        sprite.update(0.7)
        assert sprite not in group.sprites()

    def test_still_alive_before_duration(self):
        """Sprite is still alive when elapsed < duration."""
        from src.entities.emote_sprite import EmoteSprite
        frames = _make_frames()
        player = _make_player()
        group = pygame.sprite.Group()
        sprite = EmoteSprite(frames, player, group, duration=0.6)

        sprite.update(0.3)
        assert sprite in group.sprites()


class TestEmoteSpriteAnimation:
    def test_frame_advances_over_time(self):
        """Frame index advances as time passes."""
        from src.entities.emote_sprite import EmoteSprite
        frames = _make_frames(4)
        player = _make_player()
        group = pygame.sprite.Group()
        sprite = EmoteSprite(frames, player, group, duration=0.8)

        sprite.update(0.4)  # halfway → frame 2
        assert sprite.image is frames[2]

    def test_frame_stays_in_bounds(self):
        """Frame index never exceeds number of frames."""
        from src.entities.emote_sprite import EmoteSprite
        frames = _make_frames(2)
        player = _make_player()
        group = pygame.sprite.Group()
        sprite = EmoteSprite(frames, player, group, duration=0.4)

        sprite.update(0.35)  # almost at end, should not IndexError
        assert sprite.image in frames


class TestEmoteSpriteRise:
    def test_rises_over_time(self):
        """Sprite bottom moves upward as elapsed increases."""
        from src.entities.emote_sprite import EmoteSprite
        frames = _make_frames()
        player = _make_player()
        group = pygame.sprite.Group()
        sprite = EmoteSprite(frames, player, group, duration=0.6)

        initial_bottom = sprite.rect.bottom
        sprite.update(0.3)
        assert sprite.rect.bottom < initial_bottom

    def test_follows_player_x(self):
        """Sprite centerx tracks player centerx when player moves."""
        from src.entities.emote_sprite import EmoteSprite
        frames = _make_frames()
        player = _make_player(cx=100)
        group = pygame.sprite.Group()
        sprite = EmoteSprite(frames, player, group, duration=0.6)

        player.rect.centerx = 200
        sprite.update(0.1)
        assert sprite.rect.centerx == 200
