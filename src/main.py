import sys
import os

# Add src to path if needed for local execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine.game import Game

def main():
    """Main entry point of the game."""
    try:
        game = Game()
        game.run()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
