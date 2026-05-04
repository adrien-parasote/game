import cProfile
import os
import pstats
import sys

import pygame

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.game_state_manager import GameStateManager


def run_profile():
    pygame.init()
    manager = GameStateManager()

    # Force state to playing to skip title screen
    manager._transition_to_playing(slot_id=None)

    frames = 0
    # start_time = time.time()

    # We'll run exactly 600 frames (10 seconds at 60fps)
    while frames < 600:
        dt = manager._game.clock.tick(60) / 1000.0
        events = pygame.event.get()
        manager._process_global_events(events)
        manager._handle_playing(events, dt)
        pygame.display.update()
        frames += 1

    pygame.quit()


if __name__ == "__main__":
    sys.stdout.write("Starting profiling...\n")
    profiler = cProfile.Profile()
    profiler.enable()

    try:
        run_profile()
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")

    profiler.disable()

    sys.stdout.write("Profiling complete. Saving stats...\n")
    with open("profile_results.txt", "w") as f:
        stats = pstats.Stats(profiler, stream=f).sort_stats("tottime")
        stats.print_stats(50)
    sys.stdout.write("Results saved to profile_results.txt\n")
