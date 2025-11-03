# Transformation Pipeline Server Development Makefile

# Python virtual environment directory
VENV_DIR = venv
PYTHON = $(VENV_DIR)/Scripts/python
PIP = $(VENV_DIR)/Scripts/pip

# Default target
.DEFAULT_GOAL := help

.PHONY: help setup dev clean install-deps create-dirs reset-all modules-sync modules-list modules-clear modules-refresh

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

$(VENV_DIR): ## Create virtual environment
	python -m venv $(VENV_DIR)
	@echo "Virtual environment created at $(VENV_DIR)"

install-deps: $(VENV_DIR) requirements.txt ## Install Python dependencies from requirements.txt
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Dependencies installed"

create-dirs: ## Create necessary directories (logs, storage)
	@mkdir -p logs storage
	@echo "Directories created: logs/, storage/"

setup: install-deps create-dirs ## Complete development setup (install deps + create dirs)
	@echo "Development environment setup complete!"
	@echo "Run 'make dev' to start the development server"

reset: ## Clean up logs and storage data (keep venv)
	@rm -rf logs/* storage/*
	@echo "Cleaned up logs and storage data (virtual environment preserved)"
	@./scripts/database/manage-database.sh reset --confirm


clean: ## Clean up virtual environment and generated files
	@rm -rf $(VENV_DIR) logs storage
	@echo "Cleaned up virtual environment and directories"

# Module Management Commands
modules-sync: $(VENV_DIR) ## Sync all registered modules to database catalog
	@echo "Syncing modules to database catalog..."
	$(PYTHON) -m src.cli.sync_modules sync

dev: $(VENV_DIR) ## Start FastAPI development server (setup only if needed)
	@echo "Starting Transformation Pipeline Server..."
	set DEBUG=true && set RELOAD=true && $(PYTHON) main.py

