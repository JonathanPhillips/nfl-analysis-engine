# Configuration Guide

Configure the NFL Analysis Engine for your specific environment and requirements.

## Environment Variables

### Database Configuration
```bash
# PostgreSQL (Production)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nfl_analysis
DB_USER=nfl_user
DB_PASSWORD=secure_password

# Alternative: Full database URL
DATABASE_URL=postgresql://nfl_user:secure_password@localhost:5432/nfl_analysis
```

### API Configuration
```bash
# Server settings
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Authentication
API_KEY=your-secure-api-key-here

# Environment
ENVIRONMENT=development  # development, staging, production
DEBUG=true
```

### Machine Learning Configuration
```bash
# Model settings
ML_MODEL_PATH=models/
DEFAULT_MODEL=nfl_predictor_optimized.pkl

# Feature engineering
FEATURE_CACHE_TTL=3600  # seconds
ENABLE_FEATURE_CACHING=true

# Training configuration
ML_TRAIN_SEASONS=2020,2021,2022,2023
ML_TEST_SIZE=0.2
ML_RANDOM_STATE=42
```

## Configuration Files

### .env File Template
Create `.env` in your project root:

```bash
# Database
DATABASE_URL=postgresql://nfl_user:password@localhost:5432/nfl_analysis

# API
API_KEY=your-secure-api-key
ENVIRONMENT=development
DEBUG=true

# Machine Learning
ML_MODEL_PATH=models/
DEFAULT_MODEL=nfl_predictor_optimized.pkl
FEATURE_CACHE_TTL=3600

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Docker Environment
For Docker deployments, use `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  web:
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/nfl_analysis
      - API_KEY=docker-api-key
      - ENVIRONMENT=development
    ports:
      - "8080:8000"  # Custom port mapping
  
  db:
    environment:
      - POSTGRES_PASSWORD=custom_password
    volumes:
      - ./custom_data:/var/lib/postgresql/data
```

## Database Configuration

### PostgreSQL Production Setup
```sql
-- Create optimized database
CREATE DATABASE nfl_analysis
  WITH ENCODING='UTF8'
       LC_COLLATE='en_US.UTF-8'
       LC_CTYPE='en_US.UTF-8'
       TEMPLATE=template0;

-- Create user with limited privileges
CREATE USER nfl_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE nfl_analysis TO nfl_app;
GRANT USAGE ON SCHEMA public TO nfl_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nfl_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO nfl_app;
```

### Connection Pool Settings
In your application configuration:

```python
# Database settings
DATABASE_CONFIG = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
    "echo": False,  # Set True for SQL debugging
}
```

## API Configuration

### Authentication Setup
Configure API key authentication:

```python
# In src/api/auth.py
API_KEYS = {
    "admin": ["admin-api-key"],
    "read-only": ["readonly-api-key"],
    "ml-training": ["training-api-key"]
}
```

### Rate Limiting
```python
# Rate limiting configuration
RATE_LIMITS = {
    "predictions": "10/minute",
    "training": "1/hour",
    "general": "100/minute"
}
```

### CORS Configuration
```python
# CORS settings for web interface
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://yourdomain.com"
]
```

## Machine Learning Configuration

### Model Training Parameters
```python
# ML hyperparameters
ML_CONFIG = {
    "random_forest": {
        "n_estimators": 200,
        "max_depth": 20,
        "min_samples_split": 5,
        "min_samples_leaf": 2
    },
    "xgboost": {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8
    },
    "gradient_boosting": {
        "n_estimators": 150,
        "max_depth": 5,
        "learning_rate": 0.05
    }
}
```

### Feature Engineering Settings
```python
# Feature configuration
FEATURE_CONFIG = {
    "enable_momentum_features": True,
    "enable_situational_features": True,
    "enable_weather_features": False,  # Requires weather API
    "lookback_games": 5,
    "min_games_for_stats": 3
}
```

## Logging Configuration

### Structured Logging
```yaml
# logging.yml
version: 1
formatters:
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s"}'
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/nfl_analysis.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    formatter: json

loggers:
  nfl_analysis:
    level: INFO
    handlers: [console, file]
  uvicorn:
    level: WARNING
    handlers: [console]
```

## Performance Tuning

### Database Optimization
```sql
-- Performance indexes
CREATE INDEX CONCURRENTLY idx_plays_game_id ON plays(game_id);
CREATE INDEX CONCURRENTLY idx_plays_player_id ON plays(passer_player_id);
CREATE INDEX CONCURRENTLY idx_games_season ON games(season);
CREATE INDEX CONCURRENTLY idx_players_position ON players(position);

-- Connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

### Application Performance
```python
# Caching configuration
CACHE_CONFIG = {
    "team_stats": 1800,      # 30 minutes
    "player_stats": 900,     # 15 minutes
    "predictions": 300,      # 5 minutes
    "league_leaders": 3600,  # 1 hour
}
```

## Security Configuration

### API Security
```python
# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
}
```

### Database Security
```bash
# PostgreSQL security
# In postgresql.conf
ssl = on
log_connections = on
log_disconnections = on
log_statement = 'all'
```

## Monitoring Configuration

### Health Checks
```python
# Health check endpoints
HEALTH_CHECKS = {
    "database": True,
    "ml_models": True,
    "external_apis": False
}
```

### Metrics Collection
```python
# Prometheus metrics
METRICS_CONFIG = {
    "enable_prometheus": True,
    "metrics_port": 9090,
    "collect_db_metrics": True,
    "collect_api_metrics": True
}
```

## Deployment Environments

### Development
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nfl_dev
```

### Staging
```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://nfl_user:password@staging-db:5432/nfl_staging
```

### Production
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://nfl_user:secure_password@prod-db:5432/nfl_production
API_KEY=production-secure-key
```