.PHONY: setup run test clean

PYTHON = python3
VENV = venv
BIN = $(VENV)/bin

setup:
	@echo "Setting up virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(BIN)/pip install -r requirements.txt
	@echo "Setup complete. Use 'make run' to start the game."

run:
	@echo "Starting the game..."
	$(BIN)/python src/main.py

test:
	@echo "Running tests..."
	$(BIN)/python -m pytest tests/

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
