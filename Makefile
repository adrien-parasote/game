.PHONY: setup run test clean version

setup:
	@echo "Setting up game..."
	$(MAKE) -C game setup
	@echo "Setting up tools..."
	$(MAKE) -C tools setup

run:
	@echo "Running Asset Creator Tools..."
	$(MAKE) -C tools run

test:
	@echo "Running game tests..."
	$(MAKE) -C game test
	@echo "Running tools tests..."
	$(MAKE) -C tools test

clean:
	@echo "Cleaning up game..."
	$(MAKE) -C game clean
	@echo "Cleaning up tools..."
	$(MAKE) -C tools clean
	@echo "Cleaning global pycache..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

version:
	@python3 scripts/build/get_version.py
