# Transformation Pipeline Server Development Makefile

# Conda environment directory (local to project)
CONDA_ENV_DIR = conda_env
PYTHON = conda run --no-capture-output -p $(CONDA_ENV_DIR) python
PIP = conda run --no-capture-output -p $(CONDA_ENV_DIR) pip
PYTEST = conda run --no-capture-output -p $(CONDA_ENV_DIR) pytest

# Default target
.DEFAULT_GOAL := help

.PHONY: help setup dev clean install-deps create-dirs reset-all modules-sync modules-list modules-clear modules-refresh test test-all test-unit test-integration test-cov

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

$(CONDA_ENV_DIR): ## Create local conda environment
	conda create -p $(CONDA_ENV_DIR) python=3.12 -y
	@echo "Conda environment created at $(CONDA_ENV_DIR)"

install-deps: $(CONDA_ENV_DIR) requirements.txt requirements-dev.txt ## Install Python dependencies from requirements.txt and requirements-dev.txt
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "Dependencies installed (production + development)"

create-dirs: ## Create necessary directories (logs, storage)
	@mkdir -p logs storage
	@echo "Directories created: logs/, storage/"

setup: install-deps create-dirs ## Complete development setup (install deps + create dirs)
	@echo "Development environment setup complete!"
	@echo "Run 'make dev' to start the development server"

reset: ## Clean up logs and storage data (keep conda env)
	@rm -rf logs/* storage/*
	@echo "Cleaned up logs and storage data (conda environment preserved)"
	@./scripts/database/manage-database.sh reset --confirm


clean: ## Clean up conda environment and generated files
	@rm -rf $(CONDA_ENV_DIR) logs storage
	@echo "Cleaned up conda environment and directories"

# Module Management Commands
modules-sync: $(CONDA_ENV_DIR) ## Sync all registered modules to database catalog
	@echo "Syncing modules to database catalog..."
	$(PYTHON) -m src.cli.sync_modules sync

dev: $(CONDA_ENV_DIR) ## Start FastAPI development server (setup only if needed)
	@echo "Starting Transformation Pipeline Server..."
	@bash -c "eval \"\$$(conda shell.bash hook)\" && conda activate ./$(CONDA_ENV_DIR) && DEBUG=true RELOAD=true PYTHONUNBUFFERED=1 python main.py"

# Testing Commands
test: ## Run specific test file (usage: make test TEST=tests/test_modules/...)
ifdef TEST
	$(PYTEST) $(TEST) -v
else
	@echo "Usage: make test TEST=tests/test_modules/transform/test_data_duplicator.py"
	@echo "   or: make test TEST=tests/test_modules/transform/"
endif

test-all: ## Run all tests
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only
	$(PYTEST) tests/ -v -m unit

test-integration: ## Run integration tests only (requires database setup)
	$(PYTEST) tests/ -v -m integration

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

