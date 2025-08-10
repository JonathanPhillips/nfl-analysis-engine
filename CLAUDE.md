# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Development Commands

### Environment Setup
```bash
# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Testing Commands
```bash
# Run all tests with coverage
pytest

# Run specific test module
pytest tests/test_analysis/test_models.py -v

# Run single test function
pytest tests/test_api/test_teams.py::TestTeamsAPI::test_get_teams_empty -v

# Run tests without coverage (faster)
pytest --no-cov

# Run with detailed output
pytest -vvv -s
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Application Startup
```bash
# Development server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Docker development
docker-compose up --build

# Docker with scraper service
docker-compose --profile scraper up --build
```

## Architecture Overview

This is a professional-grade NFL analysis engine built with Test-Driven Development (TDD) methodology. The system is organized into distinct layers with clear separation of concerns:

### Core Architecture Layers

**Data Layer** (`src/data/`):
- `nfl_data_client.py`: Primary interface to nfl_data_py (nflverse ecosystem)
- `validators.py`: Data validation framework with severity levels (INFO/WARNING/ERROR/CRITICAL)  
- `cleaners.py`: Data cleaning pipeline with configurable strategies
- `pipeline.py`: Orchestrates validation and cleaning with comprehensive reporting

**Models Layer** (`src/models/`):
- SQLAlchemy 2.0 models compatible with nflfastR data structure
- Pydantic schemas for API serialization/validation
- Base classes providing common functionality (timestamps, soft deletes)

**Analysis Layer** (`src/analysis/`):
- `features.py`: Feature engineering with 30+ NFL-specific features
- `models.py`: Random Forest ML pipeline with training/prediction/evaluation
- `vegas.py`: Value betting framework with Kelly criterion and market analysis

**API Layer** (`src/api/`):
- FastAPI with async/await throughout
- Router-based organization by domain (teams, games, players, predictions, vegas)
- Dependency injection for database sessions
- Custom middleware for logging and database management

**Web Interface** (`src/web/`):
- Server-side rendered templates with Jinja2
- Bootstrap 5 + custom CSS with NFL theming
- Interactive prediction forms and model management

### Key Design Patterns

**Test-Driven Development**: Every module has comprehensive test coverage with fixtures in `conftest.py` files. Tests use SQLite for fast execution.

**Data Pipeline**: Three-stage validation (INFO→WARNING→ERROR→CRITICAL) with configurable failure thresholds and detailed reporting.

**ML Pipeline**: Reproducible training with train/test splits, feature scaling, model persistence, and performance metrics tracking.

**Dependency Injection**: Database sessions, predictors, and validators are injected via FastAPI's dependency system.

### Critical Integration Points

**nfl_data_py Integration**: All data ingestion goes through `NFLDataClient` which wraps nfl_data_py calls with error handling, caching, and our data models.

**Database Schema**: Designed to be compatible with nflfastR while adding analysis-specific fields. Uses Alembic for migrations.

**ML Model Lifecycle**: 
1. Feature engineering creates 30+ features from raw game data
2. Random Forest training with hyperparameter tuning
3. Model persistence with metadata (accuracy, feature importance)
4. Prediction pipeline with confidence scoring
5. Vegas line comparison for value betting

**API-Web Integration**: Web interface calls API endpoints internally, sharing the same database session and business logic.

## Development Patterns

### Model Training Workflow
```python
# 1. Initialize predictor with database session
predictor = NFLPredictor(db_session)

# 2. Train on historical seasons
predictor.train(seasons=[2020, 2021, 2022], test_size=0.2)

# 3. Save trained model
predictor.save_model("model_name")

# 4. Make predictions
prediction = predictor.predict_game("SF", "KC", date(2024, 1, 1), 2024)
```

### Data Pipeline Usage
```python
# 1. Initialize pipeline with configuration
pipeline = ValidationAndCleaningPipeline(PipelineConfig(
    strict_validation=False,
    fail_on_critical=True
))

# 2. Process data through pipeline
result = pipeline.process_data(data, DataType.GAMES)

# 3. Check results and access cleaned data
if result.success:
    cleaned_data = result.cleaned_data
```

### Testing Patterns
- Each module has a dedicated test file with `Test*` classes
- Database tests use function-scoped SQLite fixtures
- API tests override database dependencies with test sessions
- Analysis tests create minimal sample data for ML training

### Database Connection Strategy
- Production: PostgreSQL with connection pooling
- Development: Can use either PostgreSQL or SQLite
- Testing: Always SQLite with temporary files
- Connection configuration in `src/database/config.py`

## Important Configuration

**Environment Variables**:
- `DATABASE_URL`: PostgreSQL connection string for production
- `PYTHONPATH`: Should include project root for imports

**Key Files**:
- `pytest.ini`: Test configuration with coverage settings
- `alembic.ini`: Database migration configuration  
- `docker-compose.yml`: Multi-service development environments
- `requirements.txt`: All Python dependencies

**Model Storage**: Trained models saved to `models/` directory with pickle serialization and JSON metadata.

**Web Templates**: Located in `src/web/templates/` with shared base template using Bootstrap 5.

The codebase follows strict TDD principles - always run tests after changes and maintain >90% coverage.

**Browser Testing** Use Playwright MCP to do any testing where a browser is needed.s