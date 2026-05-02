import sys
import os
import logging

# Add src to path if needed for local execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine.game_state_manager import GameStateManager


def main():
    """Main entry point of the game."""
    try:
        manager = GameStateManager()
        manager.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
