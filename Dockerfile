FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/
COPY pytest.ini .

# Create data directory
RUN mkdir -p /app/data

# Run tests during build to ensure code quality
RUN python -m pytest tests/ -v

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_ENV=production

# Expose port for web interface
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]