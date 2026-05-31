.PHONY: setup run test clean

PYTHON = python3
VENV = venv
BIN = $(VENV)/bin

setup:
	@echo "Setting up virtual environment for game..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(BIN)/pip install -r requirements.txt
	@echo "Setup complete. Use 'make run' to start the game."

run:
	@echo "Starting the game..."
	cd .. && PYTHONPATH=. game/$(BIN)/python -m game.src.main

test:
	@echo "Running tests..."
	cd .. && PYTHONPATH=. game/$(BIN)/python -m pytest game/tests/

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
