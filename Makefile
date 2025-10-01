# Makefile for Farnsworth Fusor project
# Common development tasks - USE THESE COMMANDS DAILY!

.PHONY: help install lint format test clean setup-dev pre-commit-all run check-all dev-setup

# Default target - show help
.DEFAULT_GOAL := help

help: ## 📖 Show this help message
	@echo ""
	@echo "🚀 Farnsworth Fusor Development Commands"
	@echo "========================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "💡 Quick Start:"
	@echo "   make dev-setup    # First time setup"
	@echo "   make run          # Run the application"
	@echo "   make check-all    # Check code before committing"
	@echo ""

install: ## 📦 Install all dependencies
	@echo "Installing dependencies..."
	pip install -r requirements.txt

setup-dev: ## 🔧 Set up development environment with pre-commit
	@echo "Setting up development environment..."
	python setup_dev.py

lint: ## 🔍 Run pylint on source code
	@echo "Running pylint..."
	pylint src/

format: ## 🎨 Format code with black
	@echo "Formatting code with black..."
	black src/

format-check: ## ✅ Check if code is formatted correctly
	@echo "Checking code formatting..."
	black --check src/

test-env: ## 🧪 Test environment setup
	@echo "Testing environment..."
	python testEnv.py

pre-commit-all: ## 🔄 Run pre-commit on all files
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files

pre-commit-install: ## 📌 Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	pre-commit install

clean: ## 🧹 Clean up temporary files
	@echo "Cleaning up temporary files..."
ifeq ($(OS),Windows_NT)
	@echo "Windows cleanup..."
	@if exist logs rmdir /s /q logs
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist .coverage del .coverage
	@for /r . %%i in (*.pyc) do del "%%i"
	@for /r . %%i in (*.log) do del "%%i"
	@for /d /r . %%i in (__pycache__) do rmdir /s /q "%%i"
else
	@echo "Unix/Linux cleanup..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -rf logs/
	rm -rf .pytest_cache/
	rm -rf .coverage
endif
	@echo "Cleanup complete!"

run: ## 🚀 Run the main fusor application
	@echo "Starting Farnsworth Fusor application..."
	python src/Host_Codebase/fusor_main.py

run-target: ## 🎯 Run the target codebase server
	@echo "Starting Target Codebase server..."
	python src/Target_Codebase/target_ssh_server.py

test-target: ## 🧪 Test target codebase functionality
	@echo "Testing Target Codebase..."
	python src/Target_Codebase/target_test.py

check-all: format-check lint test-env ## 🔍 Run all checks (format, lint, test)
	@echo ""
	@echo "✅ All checks completed!"

# Development workflow
dev-setup: install pre-commit-install ## 🎯 Complete development setup (USE THIS FIRST!)
	@echo ""
	@echo "🎉 Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  make run          # Run the application"
	@echo "  make check-all    # Check your code"
	@echo "  make clean        # Clean up when done"
	@echo ""

# Quick development commands
quick-check: format lint ## ⚡ Quick code check (format + lint only)
	@echo "Quick check completed!"

# CI/CD helpers
ci-check: format-check lint test-env ## 🤖 Run checks suitable for CI/CD
	@echo "CI checks completed!"

# Test commands
test-commands: ## 🧪 Test if all make commands work
	@echo "Testing make commands..."
	@echo "✓ make help"
	@make help > /dev/null 2>&1 && echo "✓ help command works" || echo "✗ help command failed"
	@echo "✓ make install"
	@make install > /dev/null 2>&1 && echo "✓ install command works" || echo "✗ install command failed"
	@echo "✓ make test-env"
	@make test-env > /dev/null 2>&1 && echo "✓ test-env command works" || echo "✗ test-env command failed"
	@echo "✓ make format-check"
	@make format-check > /dev/null 2>&1 && echo "✓ format-check command works" || echo "✗ format-check command failed"
	@echo "✓ make lint"
	@make lint > /dev/null 2>&1 && echo "✓ lint command works" || echo "✗ lint command failed"
	@echo "✓ make clean"
	@make clean > /dev/null 2>&1 && echo "✓ clean command works" || echo "✗ clean command failed"
	@echo "Testing complete!"
