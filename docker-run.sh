#!/bin/bash

# NFL Analysis Engine - Docker Runner Script

echo "=========================================="
echo "NFL Analysis Engine - Docker Container"
echo "=========================================="
echo ""

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running!"
        echo "Please start Docker Desktop and try again."
        exit 1
    fi
    echo "✅ Docker is running"
}

# Function to build and run containers
run_app() {
    echo ""
    echo "🔨 Building Docker images..."
    docker-compose build
    
    echo ""
    echo "🚀 Starting containers..."
    docker-compose up -d
    
    echo ""
    echo "⏳ Waiting for services to be ready..."
    sleep 5
    
    # Run database migrations
    echo "📊 Running database migrations..."
    docker-compose exec web alembic upgrade head
    
    echo ""
    echo "=========================================="
    echo "✅ NFL Analysis Engine is running!"
    echo ""
    echo "Access the application at:"
    echo "  → http://localhost:8004"
    echo "  → http://localhost:8004/web/"
    echo "  → http://localhost:8004/api/docs"
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
    echo "=========================================="
}

# Function to stop containers
stop_app() {
    echo "Stopping containers..."
    docker-compose down
    echo "✅ Containers stopped"
}

# Function to view logs
view_logs() {
    docker-compose logs -f
}

# Function to reset everything
reset_app() {
    echo "⚠️  This will remove all containers and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        echo "✅ All containers and volumes removed"
    fi
}

# Main menu
case "${1:-}" in
    stop)
        stop_app
        ;;
    logs)
        view_logs
        ;;
    reset)
        reset_app
        ;;
    *)
        check_docker
        run_app
        ;;
esac