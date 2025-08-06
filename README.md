# 🏈 NFL Analysis Engine

A professional-grade NFL data analysis and prediction platform built with modern Python technologies and comprehensive Test-Driven Development (TDD).

[![CI/CD](https://github.com/JonathanPhillips/nfl-analysis-engine/workflows/NFL%20Analysis%20Engine%20CI/CD/badge.svg)](https://github.com/JonathanPhillips/nfl-analysis-engine/actions)
[![codecov](https://codecov.io/gh/JonathanPhillips/nfl-analysis-engine/branch/main/graph/badge.svg)](https://codecov.io/gh/JonathanPhillips/nfl-analysis-engine)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=nfl-analysis-engine&metric=security_rating)](https://sonarcloud.io/dashboard?id=nfl-analysis-engine)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## 🎯 Overview

The NFL Analysis Engine is a comprehensive platform for NFL data analysis, featuring advanced metrics like Expected Points Added (EPA) and Win Probability (WP), machine learning predictions, Vegas line validation, and interactive web dashboards.

### Key Features

- **📊 Advanced Analytics**: EPA, WP, clutch performance, and 15+ situational metrics
- **🤖 Machine Learning**: Random Forest predictions with hyperparameter tuning
- **💰 Value Betting**: Vegas line validation with Kelly criterion optimization
- **🌐 Web Interface**: Interactive dashboards with real-time insights
- **🔌 REST API**: Comprehensive FastAPI with automatic documentation
- **🏗️ Professional Architecture**: TDD, containerization, and CI/CD pipelines

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/JonathanPhillips/nfl-analysis-engine.git
cd nfl-analysis-engine

# Start the application
./docker-run.sh
```

Visit [http://localhost:8004](http://localhost:8004) to access the web interface.

### Local Development

```bash
# Set up development environment
make dev-setup

# Run the application
make serve
```

## 📋 Requirements

- **Python**: 3.11 or higher
- **Database**: PostgreSQL 13+ (SQLite for development)
- **Docker**: Optional but recommended
- **Memory**: 4GB RAM minimum

## 🏗️ Architecture

```
├── src/
│   ├── analysis/          # ML models and advanced analytics
│   │   ├── features.py    # Feature engineering (30+ NFL features)
│   │   ├── models.py      # Random Forest prediction pipeline
│   │   ├── vegas.py       # Vegas line validation & value betting
│   │   └── insights.py    # EPA/WP calculator & insights generator
│   ├── api/               # FastAPI REST API
│   │   ├── routers/       # API endpoint routes
│   │   ├── insights.py    # Advanced analytics endpoints
│   │   └── main.py        # Application factory
│   ├── data/              # Data pipeline and validation
│   │   ├── nfl_data_client.py  # nfl_data_py integration
│   │   ├── validators.py  # Data validation framework
│   │   └── pipeline.py    # ETL pipeline orchestrator
│   ├── database/          # Database layer
│   │   ├── models/        # SQLAlchemy ORM models
│   │   └── migrations/    # Alembic database migrations
│   └── web/               # Server-side rendered UI
│       ├── routes.py      # Web interface routes
│       └── templates/     # Jinja2 HTML templates
└── tests/                 # Comprehensive test suite (90%+ coverage)
```

### Design Patterns

- **Repository Pattern**: Clean data access layer
- **Factory Pattern**: Application and service creation
- **Dependency Injection**: FastAPI's dependency system
- **Pipeline Pattern**: Data validation and ML workflows
- **Strategy Pattern**: Configurable validation and cleaning

## 🔧 Development

### Essential Commands

```bash
# Development workflow
make install-dev          # Install development dependencies
make format               # Format code with Black & isort
make lint                 # Run linting checks
make type-check           # Run MyPy type checking
make test                 # Run full test suite
make test-cov             # Run tests with coverage report
make security             # Run security analysis

# Database operations
make setup-db             # Set up database and run migrations
make migration            # Create new migration
make migrate              # Apply pending migrations

# Docker operations
make docker-build         # Build Docker images
make docker-run           # Start application in containers
make docker-stop          # Stop all containers

# Quality assurance
make quality              # Run all code quality checks
make ci-test              # Run tests as they would in CI
make pre-commit           # Run pre-commit hooks
```
