# Nexus Shell Makefile

.PHONY: install test lint doctor help

install: venv
	./install.sh

venv:
	@echo "Setting up Python virtual environment..."
	python3 -m venv .venv
	./.venv/bin/pip install -e .

test:
	./tests/unit/run_tests.sh

lint:
	@echo "Linting Shell scripts..."
	shellcheck core/boot/*.sh core/layout/*.sh core/api/*.sh core/exec/*.sh scripts/installers/*.sh
	@echo "Linting Python scripts..."
	ruff check .

doctor:
	./bin/nxs doctor

help:
	@echo "Nexus Shell Developer Tools"
	@echo "  make install - Run the system installer"
	@echo "  make test    - Run unit tests"
	@echo "  make lint    - Run shellcheck and ruff"
	@echo "  make doctor  - Run system health check"
