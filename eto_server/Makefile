# ETO Server Development Makefile

# Python virtual environment directory
VENV_DIR = venv
PYTHON = $(VENV_DIR)/Scripts/python
PIP = $(VENV_DIR)/Scripts/pip

# Default target
.DEFAULT_GOAL := help

.PHONY: help setup dev dev-flask clean install-deps create-dirs reset-all

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

dev: $(VENV_DIR) logs storage ## Start FastAPI development server (setup only if needed)
	@echo "Starting ETO FastAPI development server..."
	set DEBUG=true && set RELOAD=false && $(PYTHON) main.py

logs:
	@mkdir -p logs

storage:
	@mkdir -p storage

clean-data: ## Clean up logs and storage data (keep venv)
	@rm -rf logs/* storage/*
	@echo "Cleaned up logs and storage data (virtual environment preserved)"
	@./scripts/database/manage-database.sh reset --confirm

clean: ## Clean up virtual environment and generated files
	@rm -rf $(VENV_DIR) logs storage
	@echo "Cleaned up virtual environment and directories"

reset-all: ## Reset database and clear storage/logs completely
	@echo "Resetting database and clearing all data..."
	@rm -rf logs/* storage/* || true
	@mkdir -p logs storage
	@echo "Database reset and storage/logs cleared successfully!"