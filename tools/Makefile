.PHONY: setup run test clean

PYTHON = python3
VENV = venv
BIN = $(VENV)/bin

setup:
	@echo "Setting up virtual environment for tools..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(BIN)/pip install -r requirements.txt
	@echo "Setup complete. Use 'make run' to start the tool."

run:
	@echo "Starting Asset Creator..."
	cd .. && PYTHONPATH=. tools/$(BIN)/python -m tools.src.asset_creator.cli gui

test:
	@echo "Running tests..."
	cd .. && PYTHONPATH=. tools/$(BIN)/python -m pytest tools/tests/

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
