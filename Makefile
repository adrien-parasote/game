.PHONY: setup run-game run-tools test lint typecheck clean version

PYTHON = python3
VENV = venv
BIN = $(VENV)/bin

setup:
	@echo "Setting up global virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing global dependencies..."
	$(BIN)/pip install -r requirements.txt
	@echo "Setup complete!"
	@echo "  -> make run-game  : Start the game"
	@echo "  -> make run-tools : Start the asset convertor tool"

run-game:
	@echo "Starting the game..."
	PYTHONPATH=. $(BIN)/python -m game.src.main

run-tools:
	@echo "Starting Asset Convertor Tools..."
	PYTHONPATH=tools/src $(BIN)/python -m asset_convertor

test:
	@echo "Running all tests..."
	PYTHONPATH=. $(BIN)/python -m pytest

lint:
	@echo "Running linter (ruff)..."
	$(BIN)/ruff check .

typecheck:
	@echo "Running type checker (pyright)..."
	$(BIN)/pyright

clean:
	@echo "Cleaning up environments and caches..."
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

version:
	@$(PYTHON) scripts/build/get_version.py
