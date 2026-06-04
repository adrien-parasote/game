.PHONY: run-tool run-tools test lint typecheck clean setup

# Délègue au Makefile racine depuis le dossier tools/
# Usage : cd tools && make run-tool

ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || echo "..")

run-tool run-tools:
	@echo "Démarrage du convertisseur autotile..."
	@cd "$(ROOT)" && make run-tools

test:
	@echo "Lancement des tests tools..."
	@cd "$(ROOT)" && make test

lint:
	@cd "$(ROOT)" && make lint

typecheck:
	@cd "$(ROOT)" && make typecheck

clean:
	@cd "$(ROOT)" && make clean

setup:
	@cd "$(ROOT)" && make setup
