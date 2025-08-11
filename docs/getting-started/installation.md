# Installation Guide

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher
- Git
- Docker (optional, for containerized deployment)

## Installation Methods

### Option 1: Docker (Recommended)

The easiest way to get started is with Docker Compose:

```bash
# Clone the repository
git clone https://github.com/JonathanPhillips/nfl-analysis-engine.git
cd nfl-analysis-engine

# Start the application
docker-compose up --build
```

This will:
- Start PostgreSQL database on port 5432
- Launch the web application on port 8000
- Set up all necessary dependencies

### Option 2: Local Development

For local development with more control:

```bash
# Clone the repository
git clone https://github.com/JonathanPhillips/nfl-analysis-engine.git
cd nfl-analysis-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials
```

### Database Setup

Create PostgreSQL database:

```sql
-- Connect to PostgreSQL as admin user
CREATE DATABASE nfl_analysis;
CREATE USER nfl_user WITH PASSWORD 'nfl_password';
GRANT ALL PRIVILEGES ON DATABASE nfl_analysis TO nfl_user;
```

Update `.env` file:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nfl_analysis
DB_USER=nfl_user
DB_PASSWORD=nfl_password
```

### Initialize Database

Run database migrations:

```bash
# Run Alembic migrations
alembic upgrade head

# Load initial data (optional)
python load_teams.py
python load_2024_data.py
```

### Start Application

```bash
# Start the web server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Verification

Visit these URLs to verify installation:

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/v1/health

## Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Check database logs
docker logs nfl-analysis-engine-db-1
```

**Port Already in Use**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process or use different port
uvicorn src.api.main:app --port 8001
```

**Missing Dependencies**
```bash
# Reinstall requirements
pip install --upgrade -r requirements.txt
```

### Getting Help

If you encounter issues not covered here:

1. Check the [troubleshooting guide](../development/setup.md)
2. Review logs in `logs/` directory
3. Create an issue on GitHub