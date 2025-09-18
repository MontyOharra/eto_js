# ETO Server Development Makefile

# Python virtual environment directory
VENV_DIR = venv
PYTHON = $(VENV_DIR)/Scripts/python
PIP = $(VENV_DIR)/Scripts/pip

# Default target
.DEFAULT_GOAL := help

.PHONY: help setup dev clean install-deps create-dirs

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

$(VENV_DIR): ## Create virtual environment
	python -m venv $(VENV_DIR)
	@echo "Virtual environment created at $(VENV_DIR)"

install-deps: $(VENV_DIR) requirements.txt ## Install Python dependencies from requirements.txt
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch install-deps
	@echo "Dependencies installed"

create-dirs: ## Create necessary directories (logs, storage)
	@mkdir -p logs storage
	@touch create-dirs
	@echo "Directories created: logs/, storage/"

setup: install-deps create-dirs ## Complete development setup (install deps + create dirs)
	@echo "Development environment setup complete!"
	@echo "Run 'make dev' to start the development server"

dev: $(VENV_DIR) logs storage ## Start development server (setup only if needed)
	@echo "Starting ETO development server..."
	set FLASK_ENV=development && set DEBUG=true && $(PYTHON) main.py

logs:
	@mkdir -p logs

storage:
	@mkdir -p storage

clean-data: ## Clean up logs and storage data (keep venv)
	@rm -rf logs/* storage/*
	@echo "Cleaned up logs and storage data (virtual environment preserved)"

clean: ## Clean up virtual environment and generated files
	@rm -rf $(VENV_DIR) logs storage
	@echo "Cleaned up virtual environment and directories"

test: setup ## Run tests (placeholder for future test implementation)
	@echo "Test target not yet implemented"

lint: setup ## Run linting (placeholder for future linting implementation)
	@echo "Lint target not yet implemented"