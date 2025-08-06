# NFL Analysis Engine - Development Makefile

.PHONY: help install install-dev test test-cov lint format type-check security clean docker-build docker-run docker-stop setup-db migrate

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)NFL Analysis Engine - Development Commands$(NC)"
	@echo "=============================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install -r requirements.txt
	pip install black flake8 isort mypy bandit[toml] pytest pytest-cov pytest-asyncio pre-commit
	pre-commit install
	@echo "$(GREEN)Development environment set up!$(NC)"

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest -v

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest -v --cov=src --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without slow/integration tests
	@echo "$(BLUE)Running fast tests...$(NC)"
	pytest -v -m "not slow and not integration"

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest -v -m integration

lint: ## Run all linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	flake8 src/ tests/
	@echo "$(GREEN)Linting passed!$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black src/ tests/
	isort src/ tests/
	@echo "$(GREEN)Code formatted!$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	mypy src/ --ignore-missing-imports --no-strict-optional
	@echo "$(GREEN)Type checking passed!$(NC)"

security: ## Run security scan with bandit
	@echo "$(BLUE)Running security scan...$(NC)"
	bandit -r src/ -f json -o bandit-report.json || true
	@echo "$(YELLOW)Security report generated: bandit-report.json$(NC)"

clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + || true
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ || true
	rm -f bandit-report.json || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

quality: format lint type-check security ## Run all code quality checks
	@echo "$(GREEN)All quality checks completed!$(NC)"

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker-compose build
	@echo "$(GREEN)Docker image built!$(NC)"

docker-run: ## Run application in Docker
	@echo "$(BLUE)Starting NFL Analysis Engine...$(NC)"
	./docker-run.sh

docker-stop: ## Stop Docker containers
	@echo "$(BLUE)Stopping containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)Containers stopped!$(NC)"

docker-logs: ## Show Docker logs
	docker-compose logs -f

setup-db: ## Set up database (create and migrate)
	@echo "$(BLUE)Setting up database...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)Database set up!$(NC)"

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(NC)"

migration: ## Create new database migration
	@echo "$(BLUE)Creating new migration...$(NC)"
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	@echo "$(GREEN)Migration created!$(NC)"

dev-setup: install-dev setup-db ## Complete development environment setup
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Run 'make docker-run' to start the application"
	@echo "  2. Visit http://localhost:8004 to see the web interface"
	@echo "  3. Visit http://localhost:8004/api/docs for API documentation"

benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running performance benchmarks...$(NC)"
	pytest -v -m benchmark --benchmark-json=benchmark.json

ci-test: ## Run tests as they would run in CI
	@echo "$(BLUE)Running CI test suite...$(NC)"
	pytest -v --cov=src --cov-report=term --cov-report=xml
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports --no-strict-optional
	bandit -r src/ -f json -o bandit-report.json || true
	@echo "$(GREEN)CI tests completed!$(NC)"

requirements: ## Update requirements.txt from current environment
	@echo "$(BLUE)Generating requirements.txt...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)Requirements updated!$(NC)"

# Development server
serve: ## Run development server
	@echo "$(BLUE)Starting development server...$(NC)"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "$(YELLOW)Documentation generation not implemented yet$(NC)"

# Git hooks
git-hooks: ## Install git hooks
	@echo "$(BLUE)Installing git hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)Git hooks installed!$(NC)"