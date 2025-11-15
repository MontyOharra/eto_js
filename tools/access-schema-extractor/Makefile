# Makefile for Access Schema Extractor
# Handles virtual environment setup and script execution

# Python interpreter
PYTHON := python
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
VENV_PIP := $(VENV_DIR)/Scripts/pip.exe

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ Setup

.PHONY: setup
setup: $(VENV_DIR)/touchfile ## Set up virtual environment and install dependencies
	@echo "$(GREEN)Setup complete!$(NC)"
	@echo "$(BLUE)Virtual environment ready at: $(VENV_DIR)$(NC)"

$(VENV_DIR)/touchfile: requirements.txt
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	@$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@$(VENV_PIP) install --upgrade pip
	@$(VENV_PIP) install -r requirements.txt
	@echo "" > $(VENV_DIR)/touchfile
	@echo "$(GREEN)Dependencies installed successfully$(NC)"

##@ Usage

.PHONY: extract-table
extract-table: setup ## Extract single table schema (usage: make extract-table DB=path/db.accdb TABLE="Table Name" OUT=output.json)
ifndef DB
	@echo "$(RED)Error: DB variable not set$(NC)"
	@echo "$(YELLOW)Usage: make extract-table DB=path/to/database.accdb TABLE=\"Table Name\" OUT=output.json$(NC)"
	@exit 1
endif
ifndef TABLE
	@echo "$(RED)Error: TABLE variable not set$(NC)"
	@echo "$(YELLOW)Usage: make extract-table DB=path/to/database.accdb TABLE=\"Table Name\" OUT=output.json$(NC)"
	@exit 1
endif
ifndef OUT
	@echo "$(RED)Error: OUT variable not set$(NC)"
	@echo "$(YELLOW)Usage: make extract-table DB=path/to/database.accdb TABLE=\"Table Name\" OUT=output.json$(NC)"
	@exit 1
endif
	@echo "$(BLUE)Extracting table: $(TABLE)$(NC)"
	@echo "$(BLUE)From database: $(DB)$(NC)"
	@echo "$(BLUE)Output file: $(OUT)$(NC)"
	@$(VENV_PYTHON) extract_single_table.py "$(DB)" "$(TABLE)" "$(OUT)"

.PHONY: extract
extract: setup ## Extract full database schema (usage: make extract DB=path/to/db.accdb OUT=output.json)
ifndef DB
	@echo "$(RED)Error: DB variable not set$(NC)"
	@echo "$(YELLOW)Usage: make extract DB=path/to/database.accdb OUT=output.json$(NC)"
	@exit 1
endif
ifndef OUT
	@echo "$(RED)Error: OUT variable not set$(NC)"
	@echo "$(YELLOW)Usage: make extract DB=path/to/database.accdb OUT=output.json$(NC)"
	@exit 1
endif
	@echo "$(BLUE)Extracting schema from: $(DB)$(NC)"
	@echo "$(BLUE)Output file: $(OUT)$(NC)"
	@$(VENV_PYTHON) extract_schema.py "$(DB)" "$(OUT)"

.PHONY: extract-compact
extract-compact: setup ## Extract schema with compact JSON output
ifndef DB
	@echo "$(RED)Error: DB variable not set$(NC)"
	@echo "$(YELLOW)Usage: make extract-compact DB=path/to/database.accdb OUT=output.json$(NC)"
	@exit 1
endif
ifndef OUT
	@echo "$(RED)Error: OUT variable not set$(NC)"
	@echo "$(YELLOW)Usage: make extract-compact DB=path/to/database.accdb OUT=output.json$(NC)"
	@exit 1
endif
	@echo "$(BLUE)Extracting schema (compact) from: $(DB)$(NC)"
	@$(VENV_PYTHON) extract_schema.py "$(DB)" "$(OUT)" --compact

##@ Maintenance

.PHONY: clean
clean: ## Remove virtual environment and cached files
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@if exist $(VENV_DIR) rmdir /s /q $(VENV_DIR)
	@echo "$(YELLOW)Removing Python cache files...$(NC)"
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist *.pyc del /q *.pyc
	@echo "$(GREEN)Cleanup complete$(NC)"

.PHONY: reinstall
reinstall: clean setup ## Clean and reinstall virtual environment
	@echo "$(GREEN)Reinstall complete$(NC)"

.PHONY: update
update: $(VENV_DIR)/touchfile ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	@$(VENV_PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)Dependencies updated$(NC)"

##@ Information

.PHONY: help
help: ## Display this help message
	@echo ""
	@echo "$(BLUE)Access Schema Extractor - Makefile Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-18s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(GREEN)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make extract-table DB=db.accdb TABLE=\"Orders\" OUT=schema.json"
	@echo "  make extract DB=C:/path/to/database.accdb OUT=schema.json"
	@echo "  make extract DB=\"C:/My Database.accdb\" OUT=docs/schema.json"
	@echo "  make extract-compact DB=db.mdb OUT=output.json"
	@echo ""

.PHONY: info
info: ## Show environment information
	@echo "$(BLUE)Environment Information:$(NC)"
	@echo "  Python executable: $(PYTHON)"
	@echo "  Virtual environment: $(VENV_DIR)"
	@if exist $(VENV_DIR) (echo "  Status: $(GREEN)Installed$(NC)") else (echo "  Status: $(RED)Not installed$(NC)")
	@if exist $(VENV_DIR) ($(VENV_PYTHON) --version)
	@if exist $(VENV_DIR) (echo "  Installed packages:" && $(VENV_PIP) list)
